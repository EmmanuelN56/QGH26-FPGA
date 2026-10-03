"""Program an authorized SRAM candidate and capture normal/full-range practice pairs."""

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LOCAL_DEPS = ROOT / ".build/python_deps"
if LOCAL_DEPS.is_dir():
    sys.path.insert(0, str(LOCAL_DEPS))

from serial.tools import list_ports
from capture_board_tests import review_csv
from capture_vector_stress import sha256, validate_inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--board", required=True)
    parser.add_argument("--programmer", type=Path, required=True)
    parser.add_argument("--location", type=int, required=True)
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be positive")
    fs = ROOT / "bitstream/trade_core.fs"
    summary = ROOT / "bitstream/build_summary.json"
    build = json.loads(summary.read_text(encoding="utf-8-sig"))
    source_root = ROOT
    checkout_differences = []
    try:
        identities = validate_inputs(fs, summary, ROOT)
    except ValueError:
        # An exact archived build is permitted only when the sole checkout
        # difference is CRLF versus LF in the organizer pin constraint file.
        source_root = ROOT / "results/area_20261003T192105403559Z" / build["name"] / "source"
        identities = validate_inputs(fs, summary, source_root)
        for relative, expected in identities.items():
            live = ROOT / relative
            if sha256(live) != expected:
                recorded = source_root / relative
                if (relative != "constraints/19_tang_nano_20k.cst" or
                        live.read_bytes().replace(b"\r\n", b"\n") !=
                        recorded.read_bytes().replace(b"\r\n", b"\n")):
                    raise ValueError(f"Active build content differs from archive: {relative}")
                checkout_differences.append({"path": relative, "difference": "CRLF/LF only",
                                             "checkout_sha256": sha256(live), "build_sha256": expected})
    ports = [{"device": p.device, "description": p.description, "hwid": p.hwid}
             for p in list_ports.comports()]
    if not any(p["device"] == args.port and args.board in p["hwid"] for p in ports):
        parser.error("Requested board identity is not present on the selected port")
    out = ROOT / "results" / ("blockram_board_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    out.mkdir()
    snapshot = out / "source"
    test_names = ["21_quick_uart_test.py", "22_robust_uart_test.py",
                  "22_robust_uart_test_fullrange.py", "reference_model.py",
                  "capture_board_tests.py", "capture_vector_stress.py",
                  Path(__file__).name]
    for relative in [*identities, *["scripts/" + name for name in test_names]]:
        target = snapshot / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile((ROOT if relative.startswith("scripts/") else source_root) / relative, target)
    shutil.copyfile(summary, out / "build_summary.json")
    shutil.copyfile(fs, out / "programmed.fs")
    validate_inputs(out / "programmed.fs", out / "build_summary.json", snapshot)
    def git_read(*argv):
        return subprocess.check_output(["git", *argv], cwd=ROOT, text=True).strip()
    command = [str(args.programmer.resolve()), "--device", "GW2AR-18C",
               "--operation_index", "2", "--cable-index", "4", "--location",
               str(args.location), "--frequency", "2.5MHz", "--fsFile", str(out / "programmed.fs")]
    report = {"started_utc": datetime.now(timezone.utc).isoformat(),
              "branch": git_read("branch", "--show-current"),
              "source_commit": git_read("rev-parse", "HEAD"),
              "worktree_status_before_programming": git_read("status", "--short"),
              "board": args.board, "port": args.port, "serial_inventory": ports,
              "bitstream_sha256": sha256(fs), "source_sha256": identities,
              "exact_build_source_root": str(source_root), "checkout_differences": checkout_differences,
              "test_source_sha256": {name: sha256(snapshot / "scripts" / name) for name in test_names},
              "resources": build.get("resource_summary", build["synthesis"]),
              "timing": build["pnr"], "python": sys.version,
              "programming_command": command, "programming_mode": "volatile SRAM",
              "reprogram_between_tests": False, "manual_reset_between_tests": False,
              "scope": "Practice seeds on physical board; not the official or hidden judge runs",
              "tests": [], "all_passed": False}
    def save():
        (out / "manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    save()
    print(f"Evidence directory: {out}", flush=True)
    with (out / "programming.log").open("w", encoding="utf-8") as log:
        proc = subprocess.run(command, cwd=out, stdout=log, stderr=subprocess.STDOUT, timeout=90)
    text = (out / "programming.log").read_text(encoding="utf-8", errors="replace")
    report["programmer_exit_code"] = proc.returncode
    report["programming_passed"] = (proc.returncode == 0 and 'Operation "SRAM Program"' in text
                                     and "Finished." in text)
    save()
    if not report["programming_passed"]:
        sys.exit(f"Programming failed; evidence retained in {out}")
    print("SRAM programming completed successfully.", flush=True)
    schedule = [("quick", test_names[0])]
    for i in range(1, args.runs + 1):
        schedule += [(f"normal_{i}", test_names[1]), (f"fullrange_{i}", test_names[2])]
    for label, filename in schedule:
        directory = out / label
        directory.mkdir()
        original = (snapshot / "scripts" / filename).read_bytes()
        changed, count = re.subn(rb'^PORT = "COM6"', (f'PORT = "{args.port}"').encode(),
                                original, flags=re.MULTILINE)
        if count != 1:
            raise ValueError(f"Unexpected PORT setting in {filename}")
        test = directory / filename
        test.write_bytes(changed)
        # Run the exact organizer copy; only PORT differs. Dependency loading is external.
        loader = "import sys,runpy; sys.path.insert(0,sys.argv[1]); runpy.run_path(sys.argv[2],run_name='__main__')"
        print(f"Running {label} on {args.port}...", flush=True)
        with (directory / "console.log").open("w", encoding="utf-8") as log:
            try:
                proc = subprocess.run([sys.executable, "-u", "-c", loader, str(LOCAL_DEPS), str(test)],
                                      cwd=directory, stdout=log, stderr=subprocess.STDOUT, timeout=150)
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                exit_code = -1
        console = (directory / "console.log").read_text(encoding="utf-8", errors="replace")
        result = {"name": label, "exit_code": exit_code, "port_only_change": True,
                  "executed_script_sha256": sha256(test), "passed": False}
        if label == "quick":
            result["passed"] = exit_code == 0 and "PASS" in console.splitlines()
        else:
            suffix = "_fullrange" if label.startswith("fullrange") else ""
            csv_path = directory / f"trade_results_100{suffix}.csv"
            try:
                result["physical_latency_us"] = review_csv(csv_path)
                with csv_path.open(newline="") as stream:
                    rows = list(csv.DictReader(stream))
                latency = [float(r["latency_us"]) for r in rows]
                prices = [int(r[key]) for r in rows for key in ("tx_price1", "tx_price2")]
                result["physical_latency_us"]["median"] = statistics.median(latency)
                result["price_min"] = min(prices)
                result["price_max"] = max(prices)
                result["packets_with_swapped_slots"] = sum(r["tx_item1"] == "0x22" for r in rows)
                summary_text = (directory / f"trade_summary_100{suffix}.txt").read_text()
                result["passed"] = exit_code == 0 and all(line in summary_text.splitlines() for line in (
                    "Packets successfully received: 100", "Correct packets: 84",
                    "Correct individual actions: 168/168", "Timeouts: 0"))
            except (OSError, ValueError, KeyError) as error:
                result["review_error"] = str(error)
        report["tests"].append(result)
        save()
        print(json.dumps(result), flush=True)
        if not result["passed"]:
            sys.exit(f"Failed {label}; evidence retained in {out}")
    report["all_passed"] = True
    report["completed_utc"] = datetime.now(timezone.utc).isoformat()
    for kind in ("normal", "fullrange"):
        runs = [r["physical_latency_us"] for r in report["tests"] if r["name"].startswith(kind)]
        report[kind + "_aggregate_latency_us"] = {
            "mean": statistics.mean(r["mean"] for r in runs),
            "median_of_run_means": statistics.median(r["mean"] for r in runs),
            "median_of_run_medians": statistics.median(r["median"] for r in runs),
            "max": max(r["max"] for r in runs)}
    save()
    print(f"PASS quick + {args.runs} normal/full-range pairs; evidence in {out}", flush=True)


if __name__ == "__main__":
    main()
