"""Supplementary physical stress with every deterministic regression packet.

Run after the specified bitstream has been programmed in authorized SRAM mode.
This tool never programs hardware or changes organizer tests. All eight response
bytes are checked, including warm-up. The port stays open across sessions.
Latencies use the organizer's write/read timing, but are not organizer scores.
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

from reference_model import ReferenceModel

ROOT = Path(__file__).resolve().parents[1]
BAUD, TIMEOUT_S, QUIET_WINDOW_S = 115200, 1.0, 0.2
FIELDS = ("event", "packet_ordinal", "session_number", "session_name", "packet_index",
          "tx_hex", "expected_rx_hex", "rx_hex", "write_count", "elapsed_us", "status", "error")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate_inputs(bitstream, build_summary, source_root):
    """Refuse unproven build/source identity before opening serial."""
    if not bitstream.is_file() or bitstream.suffix.lower() != ".fs":
        raise ValueError("A built .fs file is required")
    build = read_json(build_summary)
    if sha256(bitstream) != build.get("bitstream_sha256"):
        raise ValueError("Bitstream hash does not match the build summary")
    identities = build.get("source_sha256", {})
    if not isinstance(identities, dict) or not identities:
        raise ValueError("Build summary has no source_sha256 mapping")
    source_root, normalized = source_root.resolve(), {}
    for name, expected in identities.items():
        relative = Path(name.replace("\\", "/"))
        source = (source_root / relative).resolve()
        if relative.is_absolute() or not source.is_relative_to(source_root):
            raise ValueError(f"Source path escapes source root: {name}")
        if not source.is_file() or sha256(source) != expected:
            raise ValueError(f"Build source hash mismatch: {name}")
        normalized[relative.as_posix()] = expected
    required = {"src/top.v", "src/uart_rx.v", "src/uart_tx.v", "src/packet_controller.v",
                "src/trade_engine.v", "constraints/19_tang_nano_20k.cst",
                "gowin/uart.sdc", "gowin/build_uart.tcl"}
    required.update(p.relative_to(source_root).as_posix()
                    for p in (source_root / "src").glob("*.v"))
    if required - normalized.keys():
        raise ValueError(f"Build summary omits sources: {sorted(required - normalized.keys())}")
    return normalized


def load_vectors():
    """Verify saved vectors against their manifest and independent model."""
    directory = ROOT / "testbench/vectors"
    manifest = read_json(directory / "vectors.json")
    path = directory / "packets.mem"
    if sha256(path) != manifest["packets_sha256"]:
        raise ValueError("Packet-vector hash does not match vectors.json")
    for name, expected in manifest["organizer_sha256"].items():
        if sha256(ROOT / "scripts" / name) != expected:
            raise ValueError(f"Organizer reference hash mismatch: {name}")
    lines = path.read_text().splitlines()
    if len(lines) != manifest["packet_count"] or not lines:
        raise ValueError("Invalid packet-vector count")
    packets, model, cursor = [], ReferenceModel(), 0
    for number, session in enumerate(manifest["sessions"]):
        count = session["packets"]
        if session["start"] != cursor or count <= 0 or cursor + count > len(lines):
            raise ValueError("Noncontiguous or invalid session ranges")
        for index in range(count):
            line = lines[cursor]
            if len(line) != 32 or any(c not in "0123456789abcdefABCDEF" for c in line):
                raise ValueError(f"Invalid eight-byte TX/RX vector at row {cursor}")
            value = bytes.fromhex(line)
            tx, expected = value[:8], value[8:]
            if int.from_bytes(tx[:2], "big") != index or model.process(tx) != expected:
                raise ValueError(f"Packet index or independent reference mismatch at row {cursor}")
            packets.append({"packet_ordinal": cursor, "session_number": number,
                            "session_name": session["name"], "packet_index": index,
                            "tx_hex": tx.hex(), "expected_rx_hex": expected.hex()})
            cursor += 1
    if cursor != len(lines):
        raise ValueError("Session ranges do not cover all vectors")
    return packets, manifest


def capture(ser, packets, writer, flush):
    """Stop on failure; retain extra bytes instead of resetting input buffers."""
    result = {"attempted_packets": 0, "correct_packets": 0, "timeouts": 0,
              "failures": [], "unsolicited_bytes": 0, "all_passed": False}
    latencies = []

    def record(row):
        writer.writerow(row)
        flush()
        if row["status"] != "PASS":
            result["failures"].append(row)

    def extra(event, context, data):
        if data:
            result["unsolicited_bytes"] += len(data)
            record({**context, "event": event, "tx_hex": "", "expected_rx_hex": "",
                    "rx_hex": data.hex(), "status": "UNSOLICITED"})
        return bool(data)

    try:
        time.sleep(QUIET_WINDOW_S)
        if extra("startup", {}, ser.read(ser.in_waiting)):
            return result
        for packet in packets:
            if extra("before_request", packet, ser.read(ser.in_waiting)):
                break
            row = {**packet, "event": "transaction", "rx_hex": "", "write_count": ""}
            result["attempted_packets"] += 1
            tx = bytes.fromhex(packet["tx_hex"])
            start = time.perf_counter_ns()
            try:
                row["write_count"] = ser.write(tx)
                rx = ser.read(8)
                elapsed = (time.perf_counter_ns() - start) / 1000.0
                row.update(rx_hex=rx.hex(), elapsed_us=f"{elapsed:.3f}")
                if row["write_count"] != 8:
                    row["status"] = "SHORT_WRITE"
                elif len(rx) != 8:
                    row["status"] = "TIMEOUT"
                    result["timeouts"] += 1
                elif rx.hex() != packet["expected_rx_hex"]:
                    row["status"] = "MISMATCH"
                else:
                    row["status"] = "PASS"
                    result["correct_packets"] += 1
                if len(rx) == 8:
                    latencies.append(elapsed)
            except Exception as exc:
                row.update(status="SERIAL_ERROR", error=f"{type(exc).__name__}: {exc}",
                           elapsed_us=f"{(time.perf_counter_ns() - start) / 1000.0:.3f}")
            record(row)
            if extra("after_response", packet, ser.read(ser.in_waiting)):
                break
            if row["status"] != "PASS":
                break
        # Detect delayed duplicate bytes outside the packet latency measurement.
        ser.timeout = QUIET_WINDOW_S
        extra("end_quiet_check", {}, ser.read(4096))
        result["all_passed"] = (result["correct_packets"] == len(packets)
                                and not result["failures"])
    except Exception as exc:
        record({"event": "transport", "status": "SERIAL_ERROR",
                "error": f"{type(exc).__name__}: {exc}"})
    finally:
        if latencies:
            result["physical_latency_us"] = {
                "complete_responses": len(latencies), "min": min(latencies),
                "mean": sum(latencies) / len(latencies), "max": max(latencies)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--bitstream", required=True, type=Path,
                        help="Exact .fs already programmed in SRAM mode")
    parser.add_argument("--board", required=True, help="Board asset tag or serial")
    parser.add_argument("--build-summary", required=True, type=Path,
                        help="Build JSON with bitstream_sha256 and source_sha256")
    parser.add_argument("--source-root", type=Path, default=ROOT,
                        help="Matching source root, optionally a saved build source snapshot")
    parser.add_argument("--validate-only", action="store_true",
                        help="Verify inputs without importing serial or opening a port")
    args = parser.parse_args()
    try:
        sources = validate_inputs(args.bitstream, args.build_summary, args.source_root)
        packets, vector_manifest = load_vectors()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    if args.validate_only:
        print(f"PASS preflight: build/source identity and {len(packets)} packets / "
              f"{len(vector_manifest['sessions'])} sessions; no serial port opened")
        return 0
    # Optional dependency: importing this module and preflight need no pyserial.
    try:
        import serial
    except ImportError:
        parser.error("pyserial is required for physical capture")
    run_root = ROOT / "results" / ("stress_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    run_root.mkdir(parents=True)
    for name in sources:
        target = run_root / "source" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.source_root / name, target)
        if sha256(target) != sources[name]:
            raise ValueError(f"Source changed during capture preparation: {name}")
    shutil.copyfile(args.bitstream, run_root / "programmed.fs")
    shutil.copyfile(args.build_summary, run_root / "build_summary.json")
    if sha256(run_root / "programmed.fs") != read_json(run_root / "build_summary.json")["bitstream_sha256"]:
        raise ValueError("Bitstream changed during capture preparation")
    artifacts = ["scripts/capture_vector_stress.py", "scripts/reference_model.py",
                 "scripts/generate_vectors.py", "scripts/21_quick_uart_test.py",
                 "scripts/22_robust_uart_test.py", "testbench/vectors/packets.mem",
                 "testbench/vectors/vectors.json"]
    artifact_hashes = {}
    for name in artifacts:
        target = run_root / "test_sources" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
        artifact_hashes[name] = sha256(target)
    report = {"scope": "supplementary physical vector stress; not organizer scoring",
              "started_utc": datetime.now(timezone.utc).isoformat(),
              "board": args.board, "port": args.port, "baud": BAUD,
              "timeout_s": TIMEOUT_S, "quiet_window_s": QUIET_WINDOW_S,
              "programming_mode": "SRAM (operator-reported; tool does not program)",
              "bitstream_sha256": sha256(run_root / "programmed.fs"),
              "build_summary_sha256": sha256(run_root / "build_summary.json"),
              "source_root": str(args.source_root.resolve()), "source_sha256": sources,
              "test_source_sha256": artifact_hashes, "python": sys.version,
              "expected_packets": len(packets), "sessions": vector_manifest["sessions"],
              "reset_or_reprogram_between_sessions": False,
              "latency_method": "perf_counter_ns around write(8 bytes) then read(8)",
              "status": "running", "all_passed": False}

    def save():
        (run_root / "manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    save()
    print(f"Capturing {len(packets)} packets on {args.port}; evidence: {run_root}", flush=True)
    try:
        with (run_root / "packets.csv").open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDS)
            writer.writeheader()
            file.flush()
            with serial.Serial(args.port, BAUD, timeout=TIMEOUT_S) as ser:
                report.update(capture(ser, packets, writer, file.flush))
        report["status"] = "passed" if report["all_passed"] else "failed"
    except (Exception, KeyboardInterrupt) as exc:
        report.update(status="failed", all_passed=False, error=f"{type(exc).__name__}: {exc}")
    finally:
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        save()
    print(f"{report['status'].upper()}: {report.get('correct_packets', 0)}/{len(packets)} "
          f"exact responses; evidence: {run_root}")
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
