"""Compare captured, one-response-per-line hex packets to a saved answer key.

No board I/O. A short capture fails against the entire requested packet count.
Latency is optional and must come from an actual DUT capture, not this oracle.
"""

import argparse
from collections import Counter
import csv
import itertools
import json
import math
from pathlib import Path
import statistics

from reference_model import RESPONSE
from stress_suite import sha256


def percentile(values, percent):
    return sorted(values)[max(0, math.ceil(len(values) * percent / 100) - 1)]


def read_latencies(path):
    values = []
    with path.open(newline="", encoding="utf-8") as source:
        for sequence, row in enumerate(csv.DictReader(source)):
            if int(row["sequence"]) != sequence:
                raise ValueError("latency rows must use consecutive sequence numbers from zero")
            value = float(row["latency_us"])
            if not math.isfinite(value) or value < 0:
                raise ValueError("latency_us must be finite and nonnegative")
            values.append(value)
    return values


def verify(vectors, captured, latency_csv=None):
    manifest = json.loads((vectors / "manifest.json").read_text(encoding="utf-8"))
    for name, expected_hash in manifest["files"].items():
        if sha256(vectors / name) != expected_hash:
            raise ValueError(f"answer key integrity failure: {name}")
    latencies = read_latencies(latency_csv) if latency_csv else None
    correct_packets = correct_actions = decision_correct = decision_actions = received = extra = 0
    failures, examples, measured = Counter(), [], []
    fields = ("INDEX", "ITEM1", "ACTION1", "ITEM2", "ACTION2", "RESERVED")
    with (vectors / "answers.csv").open(newline="", encoding="utf-8") as key, \
            captured.open(encoding="ascii") as capture:
        for sequence, (row, line) in enumerate(itertools.zip_longest(csv.DictReader(key), capture)):
            if row is None:
                extra += 1
                failures["EXTRA_RESPONSE"] += 1
                continue
            expected = bytes.fromhex(row["response_hex"])
            is_decision = int(row["index"]) >= 16
            failed = []
            if line is None:
                failed.append("MISSING_RESPONSE")
                raw = b""
            else:
                received += 1
                try:
                    raw = bytes.fromhex(line.strip())
                except ValueError:
                    raw = b""
                    failed.append("INVALID_HEX")
                if len(raw) != 8:
                    failed.append("LENGTH")
            if len(raw) == 8:
                want, got = RESPONSE.unpack(expected), RESPONSE.unpack(raw)
                failed.extend(field for field, a, b in zip(fields, want, got) if a != b)
                actions_ok = int(want[2] == got[2]) + int(want[4] == got[4])
                correct_actions += actions_ok
                decision_actions += actions_ok if is_decision else 0
                if latencies is not None:
                    if sequence >= len(latencies):
                        raise ValueError("missing latency for a captured response")
                    measured.append(latencies[sequence])
            if not failed:
                correct_packets += 1
                decision_correct += int(is_decision)
            else:
                failures.update(failed)
                if len(examples) < 20:
                    examples.append(dict(sequence=sequence, case=row["case"], index=int(row["index"]),
                                         expected=expected.hex(), actual=raw.hex(), failed=failed))
    if latencies is not None and len(latencies) != received + extra:
        raise ValueError("latency row count must equal captured response row count")
    total, decisions = manifest["packets"], manifest["decision_packets"]
    summary = dict(pass_all=correct_packets == total and extra == 0,
                   requested_packets=total, received_rows=received, extra_rows=extra,
                   correct_packets=correct_packets, packet_correctness_percent=100 * correct_packets / total,
                   correct_actions=correct_actions, requested_actions=total * 2,
                   decision_correct_packets=decision_correct, requested_decision_packets=decisions,
                   decision_correct_actions=decision_actions, requested_decision_actions=2 * decisions,
                   failures=dict(failures), first_failures=examples,
                   latency_us=None, lut_count=None,
                   note="Local stress verification; not an official judging score or physical validation.")
    if measured:
        summary["latency_us"] = dict(samples=len(measured), mean=statistics.mean(measured),
                                     p50=percentile(measured, 50), p95=percentile(measured, 95),
                                     p99=percentile(measured, 99), maximum=max(measured))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vectors", type=Path, default=Path(__file__).resolve().parents[1] / "tests/vectors/stress")
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--latencies", type=Path, help="optional CSV: sequence,latency_us")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        summary = verify(args.vectors, args.responses, args.latencies)
    except (ValueError, KeyError, OSError) as error:
        parser.exit(2, f"Invalid capture or answer key: {error}\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"{'PASS' if summary['pass_all'] else 'FAIL'}: {summary['correct_packets']:,}/{summary['requested_packets']:,} packets; "
          f"{summary['extra_rows']} extra responses. Report: {args.report.resolve()}")
    raise SystemExit(0 if summary["pass_all"] else 1)


if __name__ == "__main__":
    main()
