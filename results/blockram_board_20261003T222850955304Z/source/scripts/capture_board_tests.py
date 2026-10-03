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

from reference_model import ReferenceModel, REQUEST, RESPONSE
from capture_vector_stress import validate_inputs

ROOT = Path(__file__).resolve().parents[1]


def review_csv(path):
    """Independently check all returned fields, including unscored warm-up."""
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    model = ReferenceModel()
    names = {0: "NONE", 1: "SELL", 2: "BUY"}
    if len(rows) != 100:
        raise ValueError(f"Expected 100 CSV rows, found {len(rows)}")
    latencies = []
    for index, row in enumerate(rows):
        if int(row["index"]) != index:
            raise ValueError(f"CSV index out of order at row {index}")
        request = REQUEST.pack(index, int(row["tx_item1"], 16), int(row["tx_price1"]),
                               int(row["tx_item2"], 16), int(row["tx_price2"]))
        expected = RESPONSE.unpack(model.process(request))
        actual = (int(row["rx_index"]), int(row["rx_item1"], 16), row["rx_action1"],
                  int(row["rx_item2"], 16), row["rx_action2"], int(row["rx_reserved"], 16))
        wanted = (expected[0], expected[1], names[expected[2]], expected[3],
                  names[expected[4]], expected[5])
        if actual != wanted:
            raise ValueError(f"Response mismatch at CSV row {index}: {actual} != {wanted}")
        expected_status = "IGNORED_WARMUP" if index < 16 else "CORRECT"
        if row["status"] != expected_status:
            raise ValueError(f"Unexpected status at CSV row {index}")
        if index >= 16 and any(row[key] != "YES" for key in (
                "action1_correct", "action2_correct", "packet_correct")):
            raise ValueError(f"Scoring mismatch at CSV row {index}")
        latencies.append(float(row["latency_us"]))
    return {"successful_packets": len(latencies), "mean": sum(latencies) / len(latencies),
            "max": max(latencies), "all_rows_verified_including_warmup": True}


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
    parser.add_argument("--source-root", type=Path, default=ROOT,
                        help="Exact candidate build source snapshot; defaults to workspace")
    parser.add_argument("--build-summary", required=True, type=Path,
                        help="Verify bitstream/source hashes before opening serial")
    parser.add_argument("--programming-log", type=Path,
                        help="Saved log of successful SRAM programming for this capture")
    args = parser.parse_args()
    if args.runs < 2:
        parser.error("At least two robust sessions are required")
    fs = args.bitstream.resolve()
    if not fs.is_file() or fs.suffix != ".fs":
        parser.error("A built .fs file is required")
    source_root = args.source_root.resolve()
    build = None
    if args.build_summary:
        build = json.loads(args.build_summary.read_text(encoding="utf-8"))
        try:
            validate_inputs(fs, args.build_summary, source_root)
        except (OSError, ValueError, KeyError, TypeError) as error:
            parser.error(str(error))
    if args.programming_log:
        programming_text = args.programming_log.read_text(encoding="utf-8-sig", errors="replace")
        if 'Operation "SRAM Program"' not in programming_text or "Finished." not in programming_text:
            parser.error("Programming log does not confirm SRAM Program completion")
    run_root = ROOT / "results" / ("board_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    run_root.mkdir(parents=True)
    snapshot = run_root / "source"
    build_paths = [*sorted((source_root / "src").glob("*.v")),
                   source_root / "constraints/19_tang_nano_20k.cst",
                   source_root / "gowin/build_uart.tcl", source_root / "gowin/uart.sdc"]
    paths = [(path, path.relative_to(source_root)) for path in build_paths]
    paths += [(ROOT / "scripts" / name, Path("scripts") / name)
              for name in ("21_quick_uart_test.py", "22_robust_uart_test.py")]
    identities = {}
    for path, relative in paths:
        dest = snapshot / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
        identities[relative.as_posix()] = sha256(path)
    if args.build_summary:
        shutil.copyfile(args.build_summary, run_root / "build_summary.json")
    if args.programming_log:
        shutil.copyfile(args.programming_log, run_root / "programming.log")
    shutil.copyfile(fs, run_root / "programmed.fs")
    validate_inputs(run_root / "programmed.fs", run_root / "build_summary.json", snapshot)
    test_hashes = {}
    for name in ("capture_board_tests.py", "capture_vector_stress.py", "reference_model.py"):
        target = run_root / "test_sources/scripts" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "scripts" / name, target)
        test_hashes["scripts/" + name] = sha256(target)
    def git_read(*argv):
        git = shutil.which("git")
        if git is None:
            return "unavailable"
        p = subprocess.run([git, "-c", "safe.directory=" + ROOT.as_posix(), *argv], cwd=ROOT, text=True, capture_output=True)
        return p.stdout.strip() if p.returncode == 0 else "unavailable"
    report = {"scope": "physical UART tests on operator-programmed board",
              "board": args.board, "port": args.port, "baud": 115200,
              "programming_mode": "SRAM (saved programmer log)" if args.programming_log else "SRAM (operator-reported)",
              "programming_evidence": "programming.log" if args.programming_log else None,
              "build_verified": build is not None, "source_root": str(source_root),
              "bitstream_sha256": sha256(fs), "base_commit": git_read("rev-parse", "HEAD"),
              "worktree_status": git_read("status", "--short"), "source_sha256": identities,
              "test_source_sha256": test_hashes,
              "python": sys.version, "reprogram_between_sessions": False, "tests": [],
              "all_passed": False}
    def save():
        (run_root / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    for label, filename in [("quick", "21_quick_uart_test.py"), *[(f"robust_{i+1}", "22_robust_uart_test.py") for i in range(args.runs)]]:
        directory = run_root / label
        directory.mkdir()
        test = directory / filename
        test.write_text(port_copy(snapshot / "scripts" / filename, args.port))
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
        if label != "quick":
            try:
                measurement["physical_latency_us"] = review_csv(csv_path)
            except (OSError, ValueError, KeyError) as error:
                passed = False
                measurement["csv_review_error"] = str(error)
            measurement["passed"] = passed
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
