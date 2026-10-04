"""Check directed full-range vectors on the already-qualified SRAM candidate."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.build' / 'python_deps'))
import serial
from reference_model import ReferenceModel

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--physical-evidence', type=Path, required=True)
    parser.add_argument('--vectors', type=Path, default=ROOT / 'testbench/vectors/packets.mem')
    parser.add_argument('--label', default='directed_fullrange')
    args = parser.parse_args()
    folder = args.physical_evidence.resolve()
    manifest = json.loads((folder / 'manifest.json').read_text())
    if not manifest['all_correct'] or not manifest['local_rubric_100']:
        raise ValueError('Select an already-qualified, still-programmed candidate')
    for relative, digest in manifest['source_sha256'].items():
        if relative.startswith(('src/', 'gowin/', 'constraints/')):
            if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
                raise ValueError(f'Source changed since programming: {relative}')
    if Path(args.label).name != args.label:
        raise ValueError('Label must be a directory name')
    output = folder / args.label
    output.mkdir(exist_ok=False)
    vectors = args.vectors
    data = vectors.read_bytes()
    (output / 'packets.mem').write_bytes(data)
    (output / 'stress_board_vectors.py').write_bytes(Path(__file__).read_bytes())
    rows, times = [], []
    model = ReferenceModel()
    report = {'bitstream_sha256': manifest['bitstream_sha256'], 'port': manifest['port'],
              'vectors_sha256': hashlib.sha256(data).hexdigest(), 'reprogrammed': False,
              'all_passed': False, 'packets_checked': 0}
    try:
        with serial.Serial(manifest['port'], 115200, timeout=1.0) as port:
            time.sleep(0.2)
            port.reset_input_buffer()
            for i, line in enumerate(data.decode().splitlines()):
                request, expected = bytes.fromhex(line[:16]), bytes.fromhex(line[16:])
                if model.process(request) != expected:
                    raise ValueError(f'Independent corpus mismatch at {i}')
                start = time.perf_counter_ns()
                port.write(request)
                observed = port.read(8)
                elapsed = (time.perf_counter_ns() - start) / 1000
                times.append(elapsed)
                rows.append([i, request.hex(), expected.hex(), observed.hex(), elapsed, observed == expected])
                if observed != expected:
                    raise ValueError(f'Physical mismatch/timeout at {i}: {observed.hex()} expected {expected.hex()}')
                if (i + 1) % 500 == 0:
                    print(f'PASS {i + 1} physical packets', flush=True)
            time.sleep(0.05)
            if port.in_waiting:
                raise ValueError('Unsolicited trailing bytes')
        report['all_passed'] = True
    finally:
        with (output / 'transactions.csv').open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['vector', 'request', 'expected', 'observed', 'latency_us', 'correct'])
            writer.writerows(rows)
        report['packets_checked'] = len(rows)
        if times:
            report.update(mean_us=statistics.mean(times), median_us=statistics.median(times), max_us=max(times))
        (output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
