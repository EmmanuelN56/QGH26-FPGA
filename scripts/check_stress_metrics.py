"""Apply local correctness/resource/physical-latency budgets to saved evidence.

Missing measurements fail as INCOMPLETE. This reads reported measurements;
it neither synthesizes hardware nor certifies the provenance of supplied logs.
"""

import argparse
import json
import math
from pathlib import Path


def evaluate(correctness, metrics, max_luts=542, max_mean_us=20782.5, max_p99_us=33300.0, baseline=None):
    missing, failures = [], []
    for field in ("luts", "registers", "bsram_blocks", "timing_slack_ns"):
        value = metrics.get(field)
        if value is None:
            missing.append(field)
        elif type(value) not in (int, float) or not math.isfinite(value):
            failures.append(f"{field} is not a finite number")
        elif field != "timing_slack_ns" and (type(value) is not int or value < 0):
            failures.append(f"{field} must be a nonnegative integer")
    for field in ("source_revision", "bitstream_sha256", "resource_report", "timing_report", "board_capture"):
        if not isinstance(metrics.get(field), str) or not metrics[field].strip():
            missing.append(field)
    if metrics.get("capture_kind") != "physical_board":
        missing.append("physical_board capture_kind")
    if not correctness.get("pass_all") or correctness.get("correct_packets") != correctness.get("requested_packets"):
        failures.append("stress correctness must be 100%, with no missing or extra responses")
    latency = correctness.get("latency_us")
    if not latency or not latency.get("samples"):
        missing.append("physical latency measurements")
    else:
        for field, budget in (("mean", max_mean_us), ("p99", max_p99_us)):
            value = latency.get(field)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                failures.append(f"latency {field} must be finite and nonnegative")
            elif value > budget:
                failures.append(f"latency {field} {value} us exceeds {budget} us")
        if latency.get("samples") != correctness.get("requested_packets"):
            failures.append("latency must cover every requested packet, including warm-up")
    luts, slack = metrics.get("luts"), metrics.get("timing_slack_ns")
    if type(luts) is int and luts > max_luts:
        failures.append(f"LUT count {luts} exceeds {max_luts}")
    if type(slack) in (int, float) and slack < 0:
        failures.append("timing slack is negative")
    deltas = {}
    if baseline is not None:
        for field in ("luts", "registers", "bsram_blocks", "timing_slack_ns"):
            a, b = metrics.get(field), baseline.get(field)
            if type(a) in (int, float) and type(b) in (int, float):
                deltas[field] = a - b
        # Baseline latency values are recorded from its separate physical report.
        for field in ("mean", "p99"):
            a, b = (latency or {}).get(field), baseline.get("latency_us", {}).get(field)
            if type(a) in (int, float) and type(b) in (int, float):
                deltas[f"latency_{field}_us"] = a - b
    return dict(status="FAIL" if failures else "INCOMPLETE" if missing else "PASS",
                missing=missing, failures=failures, candidate_minus_baseline=deltas,
                budgets=dict(max_luts=max_luts, max_mean_us=max_mean_us, max_p99_us=max_p99_us),
                note="Local budgets; reported evidence must be inspected. No structural redundancy proof or official score.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--correctness", type=Path, required=True, help="verify_stress_responses JSON report")
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--max-luts", type=int, default=542)
    parser.add_argument("--max-mean-us", type=float, default=20782.5)
    parser.add_argument("--max-p99-us", type=float, default=33300.0)
    args = parser.parse_args()
    if args.max_luts < 0 or not all(math.isfinite(v) and v >= 0 for v in (args.max_mean_us, args.max_p99_us)):
        parser.error("budgets must be finite and nonnegative")
    read = lambda p: json.loads(p.read_text(encoding="utf-8"))
    result = evaluate(read(args.correctness), read(args.metrics), args.max_luts, args.max_mean_us,
                      args.max_p99_us, read(args.baseline) if args.baseline else None)
    print(json.dumps(result, indent=2))
    raise SystemExit({"PASS": 0, "FAIL": 1, "INCOMPLETE": 2}[result["status"]])


if __name__ == "__main__":
    main()
