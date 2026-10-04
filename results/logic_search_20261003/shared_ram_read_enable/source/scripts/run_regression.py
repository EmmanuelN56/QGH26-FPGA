"""Reproducible software-only model and HDL verification; never opens UART."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from generate_vectors import ROOT, generate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board-packets", type=int, default=221,
                        help="Board-default UART timing: quick + normal + full-range sessions")
    args = parser.parse_args()
    result_dir = ROOT / "results"
    result_dir.mkdir(exist_ok=True)
    (result_dir / "software_validation.json").write_text(json.dumps({
        "scope": "software simulation only", "physical_validation": False,
        "all_passed": False, "status": "running"}, indent=2) + "\n")
    vector_dir = ROOT / "testbench" / "vectors"
    manifest = generate(vector_dir)
    sim_dir = ROOT / ".build" / "sim"
    sim_dir.mkdir(parents=True, exist_ok=True)
    compiler = shutil.which("iverilog")
    runtime = shutil.which("vvp")
    base = []
    local = ROOT / ".build" / "tools" / "usr"
    if compiler is None and (local / "bin" / "iverilog").exists():
        compiler = str(local / "bin" / "iverilog")
        base = ["-B", str(local / "lib" / "x86_64-linux-gnu" / "ivl")]
    if runtime is None and (local / "bin" / "vvp").exists():
        runtime = str(local / "bin" / "vvp")
    if not compiler or not runtime:
        sys.exit("Model checks passed; HDL simulation requires installed Icarus Verilog (ask before installing).")
    logs, checks = [], []

    def run(command):
        display = " ".join(str(p) for p in command)
        print(display, flush=True)
        proc = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=300)
        logs.append(display + "\n" + proc.stdout)
        (result_dir / "simulation.log").write_text("\n".join(logs))
        print(proc.stdout, end="", flush=True)
        if proc.returncode:
            raise RuntimeError(f"Command failed ({proc.returncode}): {display}")
        return proc.stdout

    version = run([compiler, *base, "-V"]).splitlines()[0]
    sources = [str(p.relative_to(ROOT)) for p in sorted((ROOT / "src").glob("*.v"))]
    tests = [("uart_rx_tb", [], []), ("uart_tx_tb", [], []), ("top_tb", [], []),
             ("trade_engine_tb", [], [f"+COUNT={manifest['packet_count']}"]),
             ("top_sessions_tb", [], [f"+COUNT={manifest['packet_count']}"])]
    if args.board_packets:
        if not 1 <= args.board_packets <= manifest["packet_count"]:
            parser.error("board-packets exceeds vector count")
        tests.append(("top_sessions_tb", ["-DBOARD_TIMING"], [f"+COUNT={args.board_packets}"]))
    for name, defines, extra in tests:
        output = sim_dir / (name + ("_board" if defines else "") + ".vvp")
        run([compiler, *base, "-g2012", "-Wall", *defines, "-s", name, "-o", str(output), *[str(ROOT / f) for f in sources], str(ROOT / "testbench" / f"{name}.v")])
        vector_path = "testbench/vectors/packets.mem"
        if defines:
            subset = sim_dir / "board_packets.mem"
            subset.write_text("\n".join((vector_dir / "packets.mem").read_text().splitlines()[:args.board_packets]) + "\n")
            vector_path = str(subset.relative_to(ROOT))
        transcript = run([runtime, str(output), *extra,
                          f"+VECTORS={vector_path}",
                          "+STATES=testbench/vectors/states.mem"])
        if "PASS " not in transcript:
            raise RuntimeError(f"No PASS marker from {name}")
        checks.append({"test": name, "board_timing": bool(defines) or name in ("uart_rx_tb", "uart_tx_tb", "top_tb"), "result": transcript.strip()})
    files = [*sources, *[str(p.relative_to(ROOT)) for p in sorted((ROOT / "testbench").glob("*.v"))],
             "scripts/reference_model.py", "scripts/generate_vectors.py", "scripts/run_regression.py",
             "constraints/19_tang_nano_20k.cst", "gowin/build_uart.tcl", "gowin/uart.sdc",
             "scripts/21_quick_uart_test.py", "scripts/22_robust_uart_test.py",
             "scripts/22_robust_uart_test_fullrange.py", "testbench/vectors/packets.mem",
             "testbench/vectors/states.mem", "testbench/vectors/vectors.json"]
    report = {"scope": "software simulation only", "physical_validation": False,
              "all_passed": True, "status": "passed",
              "simulator": version, "python": sys.version, "vectors": manifest, "checks": checks,
              "source_sha256": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in files}}
    (result_dir / "software_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS all software regressions; evidence saved in results/", flush=True)


if __name__ == "__main__":
    main()
