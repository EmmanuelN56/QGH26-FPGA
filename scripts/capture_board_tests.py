"""Run organizer tests on an already programmed board and preserve every run.

This script opens the selected serial port. Run only after SRAM programming has
been explicitly authorized and completed. It never programs the FPGA.
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def port_copy(source, port):
    text = source.read_text()
    updated, count = re.subn(r'^PORT = "COM6"', lambda _: "PORT = " + repr(port), text, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"Unexpected PORT setting in {source}; preserve organizer original")
    return updated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--bitstream", required=True, type=Path,
                        help="Exact .fs just programmed in SRAM mode")
    parser.add_argument("--board", required=True, help="Board asset tag or serial")
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    if args.runs < 2:
        parser.error("At least two robust sessions are required")
    fs = args.bitstream.resolve()
    if not fs.is_file() or fs.suffix != ".fs":
        parser.error("A built .fs file is required")
    run_root = ROOT / "results" / ("board_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    run_root.mkdir(parents=True)
    snapshot = run_root / "source"
    paths = [*sorted((ROOT / "src").glob("*.v")), ROOT / "constraints/19_tang_nano_20k.cst",
             ROOT / "gowin/build_uart.tcl", ROOT / "gowin/uart.sdc",
             ROOT / "scripts/21_quick_uart_test.py", ROOT / "scripts/22_robust_uart_test.py"]
    identities = {}
    for path in paths:
        relative = path.relative_to(ROOT)
        dest = snapshot / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
        identities[str(relative)] = sha256(path)
    shutil.copyfile(fs, run_root / "programmed.fs")
    def git_read(*argv):
        p = subprocess.run(["git", *argv], cwd=ROOT, text=True, capture_output=True)
        return p.stdout.strip() if p.returncode == 0 else "unavailable"
    report = {"scope": "physical UART tests on operator-programmed board",
              "board": args.board, "port": args.port, "baud": 115200,
              "programming_mode": "SRAM (operator-reported)",
              "bitstream_sha256": sha256(fs), "base_commit": git_read("rev-parse", "HEAD"),
              "worktree_status": git_read("status", "--short"), "source_sha256": identities,
              "python": sys.version, "reprogram_between_sessions": False, "tests": [],
              "all_passed": False}
    def save():
        (run_root / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    for label, filename in [("quick", "21_quick_uart_test.py"), *[(f"robust_{i+1}", "22_robust_uart_test.py") for i in range(args.runs)]]:
        directory = run_root / label
        directory.mkdir()
        test = directory / filename
        test.write_text(port_copy(ROOT / "scripts" / filename, args.port))
        print(f"Running {label} on {args.port}; saving to {directory}", flush=True)
        with (directory / "console.log").open("w") as log:
            try:
                proc = subprocess.run([sys.executable, "-u", str(test)], cwd=directory,
                                      stdout=log, stderr=subprocess.STDOUT, timeout=180)
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                exit_code = -1
        text = (directory / "console.log").read_text()
        if label == "quick":
            passed = exit_code == 0 and "PASS" in text.splitlines()
        else:
            summary_path = directory / "trade_summary_100.txt"
            summary = summary_path.read_text() if summary_path.exists() else ""
            passed = exit_code == 0 and all(line in summary.splitlines() for line in (
                "Packets successfully received: 100", "Correct packets: 84",
                "Correct individual actions: 168/168", "Timeouts: 0"))
        measurement = {"name": label, "exit_code": exit_code, "passed": passed}
        csv_path = directory / "trade_results_100.csv"
        if csv_path.exists():
            with csv_path.open(newline="") as file:
                rows = list(csv.DictReader(file))
            latencies = [float(row["latency_us"]) for row in rows if row["status"] != "TIMEOUT"]
            if latencies:
                measurement["physical_latency_us"] = {
                    "successful_packets": len(latencies),
                    "mean": sum(latencies) / len(latencies), "max": max(latencies)}
        report["tests"].append(measurement)
        save()
        print(text, end="")
        if not passed:
            sys.exit(f"Failed {label}; evidence retained in {run_root}")
    report["all_passed"] = True
    save()
    print(f"PASS quick + {args.runs} repeated robust sessions; physical evidence in {run_root}")


if __name__ == "__main__":
    main()
