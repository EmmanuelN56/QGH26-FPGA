"""Prepare and verify isolated UART-gap candidates; never programs a board.

Run natively on Windows with installed Icarus and Gowin. Each candidate changes
only top's default TX_GAP_CYCLES in a source snapshot. The release RTL/bitstream
stay unchanged until physical measurements justify a selection.
"""

import argparse
from datetime import datetime, timezone
import hashlib
from html import unescape
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from generate_vectors import ROOT, generate

BUILD_FILES = ["src/top.v", "src/uart_rx.v", "src/uart_tx.v",
               "src/packet_controller.v", "src/trade_engine.v",
               "constraints/19_tang_nano_20k.cst", "gowin/uart.sdc",
               "gowin/build_uart.tcl"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def plain(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"<(style|script)\b.*?</\1>", "", text, flags=re.S)
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", text)))


def number(pattern, text, cast=int):
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f"Missing report metric: {pattern}")
    return cast(match.group(1))


def metrics(impl):
    syn = plain(impl / "gwsynthesis/trade_core_syn.rpt.html")
    timing = plain(impl / "pnr/trade_core_tr_content.html")
    pnr = (impl / "pnr/trade_core.rpt.txt").read_text(errors="replace")
    pins = {name: number(r"(?m)^" + name + r"\s*\|\s*-\s*\|\s*(\d+)/", pnr)
            for name in ("sys_clk", "reset_btn", "uart_rx_i", "uart_tx_o", "led0_n", "led1_n")}
    if pins != dict(sys_clk=4, reset_btn=87, uart_rx_i=70, uart_tx_o=69, led0_n=15, led1_n=16):
        raise ValueError(f"Routed pins disagree with organizer CST: {pins}")
    result = {
        "tool": "Gowin " + number(r"<Tool Version>:[ \t]*([^\r\n]+)", pnr, str).strip(),
        "tool_identity_source": "PnR report <Tool Version>",
        "synthesis": {
            "LUT": number(r"\bLUT (\d+) LUT2", syn),
            "LUT2": number(r"\bLUT2 (\d+)", syn),
            "LUT3": number(r"\bLUT3 (\d+)", syn),
            "LUT4": number(r"\bLUT4 (\d+)", syn),
            "registers": number(r"\bRegister (\d+) DFF", syn),
            "BSRAM": number(r"\bBSRAM (\d+) /", syn),
            "SSRAM": number(r"\bSSRAM (\d+)", syn),
        },
        "pnr": {
            "fmax_mhz": number(r"sys_clk 27\.000\(MHz\) ([\d.]+)\(MHz\)", timing, float),
            "worst_setup_slack_ns": number(r"Setup Paths Table.*?Data Delay 1 ([\d.-]+)", timing, float),
            "worst_hold_slack_ns": number(r"Hold Paths Table.*?Data Delay 1 ([\d.-]+)", timing, float),
            "setup_violations": number(r"Numbers of Setup Violated Endpoints (\d+)", timing),
            "hold_violations": number(r"Numbers of Hold Violated Endpoints (\d+)", timing),
        }, "pins": pins,
        "warnings": [line for line in (impl / "pnr/trade_core.log").read_text().splitlines()
                     if "WARN" in line or "ERROR" in line],
    }
    if result["pnr"]["setup_violations"] or result["pnr"]["hold_violations"]:
        raise ValueError("Timing violations in candidate")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-root", required=True, type=Path,
                        help="New native Windows directory, not a UNC path")
    parser.add_argument("--gowin", required=True, type=Path)
    parser.add_argument("--iverilog", required=True, type=Path)
    parser.add_argument("--vvp", required=True, type=Path)
    gaps = parser.add_mutually_exclusive_group()
    gaps.add_argument("--gaps-us", nargs="+", type=int)
    gaps.add_argument("--gaps-cycles", nargs="+", type=int,
                      help="Clock-cycle sweep, including zero configured gap; handshake idle remains")
    parser.add_argument("--board-packets", type=int, default=221)
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Hardware build must run natively on Windows")
    work = args.work_root.resolve()
    if str(work).startswith("\\\\") or work.exists():
        parser.error("work-root must be a new native Windows directory")
    if args.gaps_cycles is not None:
        gap_specs = [(f"gap_{cycles}cycles", cycles) for cycles in args.gaps_cycles]
    else:
        gap_specs = [(f"gap_{us}us", us * 27) for us in (args.gaps_us or [500, 250, 100, 10, 1])]
    values = [cycles for _, cycles in gap_specs]
    if len(set(values)) != len(values) or any(g < 0 or g >= 27000 for g in values):
        parser.error("Gaps must be unique and between 0 and 26999 clocks (below 1000 us)")
    for tool in (args.gowin, args.iverilog, args.vvp):
        if not tool.is_file():
            parser.error(f"Missing installed tool: {tool}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ROOT / "results" / ("latency_sweep_" + stamp)
    out.mkdir()
    work.mkdir(parents=True)
    baseline = json.loads((ROOT / "results/build_windows_20261003/build_summary.json").read_text())
    if any(sha(ROOT / f) != h for f, h in baseline["source_sha256"].items()
           if f.replace("\\", "/") != "gowin/build_uart.tcl"):
        raise ValueError("Current RTL/CST/SDC differ from the physically validated baseline")
    if sha(ROOT / "bitstream/trade_core.fs") != baseline["bitstream_sha256"]:
        raise ValueError("Release bitstream differs from baseline")
    shutil.copy2(ROOT / "bitstream/trade_core.fs", out / "baseline.fs")
    shutil.copy2(ROOT / "results/board_20261003T064213338565Z/csv_review.json", out / "baseline_physical.json")
    save(out / "baseline_build.json", baseline)
    vector_dir = work / "vectors"
    vectors = generate(vector_dir)
    if not 1 <= args.board_packets <= vectors["packet_count"]:
        parser.error("board-packets outside vector count")
    board_vectors = vector_dir / "board.mem"
    board_vectors.write_text("\n".join((vector_dir / "packets.mem").read_text().splitlines()[:args.board_packets]) + "\n", newline="\n")
    manifest = {"scope": "UART-gap experiment; software/build candidates only",
                "physical_validation": False, "programming_performed": False,
                "release_unchanged": True, "work_root": str(work),
                "baseline_sha256": baseline["bitstream_sha256"],
                "candidates": [], "status": "running"}
    verification_files = [*sorted((ROOT / "testbench").glob("*.v")),
                          ROOT / "scripts/reference_model.py", ROOT / "scripts/generate_vectors.py",
                          ROOT / "scripts/prepare_latency_sweep.py",
                          ROOT / "scripts/21_quick_uart_test.py", ROOT / "scripts/22_robust_uart_test.py"]
    identities = {}
    for path in verification_files:
        relative = path.relative_to(ROOT)
        dest = out / "verification_source" / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        identities[relative.as_posix()] = sha(dest)
    for path in vector_dir.iterdir():
        if path.is_file():
            dest = out / "verification_source/vectors" / path.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            identities["vectors/" + path.name] = sha(dest)
    manifest["verification_source_sha256"] = identities
    manifest["simulated_latency_method"] = (
        "First request start to final response stop-bit center; includes deliberate two-bit "
        "request pause; no USB/host delay. Turnaround: controller acceptance of eighth RX byte "
        "to first TX start.")
    save(out / "sweep.json", manifest)

    def run(command, cwd, log, env=None, timeout=300):
        with log.open("w", encoding="utf-8") as stream:
            stream.write(subprocess.list2cmdline([str(x) for x in command]) + "\n")
            stream.flush()
            proc = subprocess.run([str(x) for x in command], cwd=cwd, env=env,
                                  stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
        text = log.read_text(encoding="utf-8", errors="replace")
        if proc.returncode:
            raise RuntimeError(f"Command exit {proc.returncode}: {log}")
        return text

    try:
        run([args.iverilog, "-V"], work, out / "iverilog_version.log")
        for name, gap_cycles in gap_specs:
            gap_us = gap_cycles / 27
            native = work / name
            result = out / name
            native.mkdir(); result.mkdir()
            candidate = {"name": name, "gap_us": gap_us, "gap_cycles": gap_cycles,
                         "native_root": str(native), "status": "running",
                         "physical_validation": False}
            manifest["candidates"].append(candidate); save(out / "sweep.json", manifest)
            for folder in ("src", "constraints", "gowin", "testbench"):
                shutil.copytree(ROOT / folder, native / folder)
            top = native / "src/top.v"
            source = top.read_text()
            source, count = re.subn(r"TX_GAP_CYCLES = CLOCK_FREQ / 1000",
                                   f"TX_GAP_CYCLES = {gap_cycles}", source)
            if count != 1:
                raise ValueError("Baseline top default changed unexpectedly")
            top.write_text(source, encoding="utf-8", newline="\n")
            print(f"VERIFY {name}: source snapshot and simulations", flush=True)
            sources = sorted((native / "src").glob("*.v"))
            tests = [("top_tb", [], [], None),
                     ("top_sessions_tb", ["-DBOARD_TIMING"],
                      [f"+COUNT={args.board_packets}", "+VECTORS=../vectors/board.mem"], args.board_packets)]
            for bench, defines, extra, count in tests:
                output = native / (bench + ".vvp")
                compile_text = run([args.iverilog, "-g2012", "-Wall", *defines,
                                   "-s", bench, f"-P{bench}.GAP_CYCLES={gap_cycles}",
                                   "-o", output, *sources, native / "testbench" / (bench + ".v")],
                                  native, result / (bench + "_compile.log"))
                sim_text = run([args.vvp, output, *extra], native, result / (bench + ".log"))
                if "PASS " not in sim_text:
                    raise RuntimeError(f"No simulation PASS: {name}/{bench}")
                print(sim_text.strip(), flush=True)
            print(f"BUILD {name}: Gowin synthesis and PnR", flush=True)
            env = os.environ.copy(); env["UART_BUILD_FLOW"] = "all"
            build_text = run([args.gowin, native / "gowin/build_uart.tcl"], native, result / "build.log", env)
            if "Bitstream generation completed" not in build_text:
                raise RuntimeError("Gowin did not confirm bitstream generation")
            impl = native / ".build/gowin_trade/trade_core/impl"
            candidate.update(metrics(impl))
            for f in BUILD_FILES:
                dst = result / "source" / f; dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(native / f, dst)
            for f in impl.rglob("*"):
                if f.is_file() and f.suffix in (".html", ".txt", ".log", ".xml"):
                    dst = result / "reports" / f.relative_to(impl)
                    dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(f, dst)
            fs = impl / "pnr/trade_core.fs"
            shutil.copy2(fs, result / "candidate.fs")
            candidate.update(status="awaiting_physical_validation", bitstream_sha256=sha(fs),
                             bitstream_path=str((result / "candidate.fs").relative_to(ROOT)),
                             source_sha256={f: sha(native / f) for f in BUILD_FILES},
                             target="GW2AR-LV18QN88C8/I7", device_version="C", top="top",
                             simulation_packets=args.board_packets,
                             physical_latency=None)
            save(result / "build_summary.json", candidate)
            save(out / "sweep.json", manifest)
            print(f"READY {name}: {candidate['bitstream_sha256']} {candidate['synthesis']} {candidate['pnr']}", flush=True)
        manifest["status"] = "awaiting_explicit_programming_authorization"
    except Exception as error:
        manifest["status"] = "failed"
        manifest["error"] = str(error)
        raise
    finally:
        save(out / "sweep.json", manifest)
    print(f"Prepared candidates at {out}; no board programming performed", flush=True)


if __name__ == "__main__":
    main()
