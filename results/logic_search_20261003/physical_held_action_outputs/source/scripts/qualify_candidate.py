"""Program an explicitly selected SRAM build and preserve practice qualification evidence."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.build' / 'python_deps'))
os.environ['PYTHONPATH'] = str(ROOT / '.build' / 'python_deps') + os.pathsep + os.environ.get('PYTHONPATH', '')
from serial.tools import list_ports
from reference_model import ReferenceModel, REQUEST, RESPONSE

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def review(path):
    rows = list(csv.DictReader(path.open(newline='')))
    if len(rows) != 100:
        raise ValueError(f'{path}: expected 100 rows, got {len(rows)}')
    model = ReferenceModel()
    actions = {'NONE': 0, 'SELL': 1, 'BUY': 2}
    times = []
    for index, row in enumerate(rows):
        request = REQUEST.pack(index, int(row['tx_item1'], 16), int(row['tx_price1']),
                               int(row['tx_item2'], 16), int(row['tx_price2']))
        expected = model.process(request)
        observed = RESPONSE.pack(int(row['rx_index']), int(row['rx_item1'], 16), actions[row['rx_action1']],
                                 int(row['rx_item2'], 16), actions[row['rx_action2']], int(row['rx_reserved'], 16))
        if int(row['index']) != index or observed != expected or row['status'] == 'TIMEOUT':
            raise ValueError(f'{path}: independent response mismatch at {index}')
        times.append(float(row['latency_us']))
    return {'rows_independently_verified': len(rows), 'mean_us': statistics.mean(times),
            'median_us': statistics.median(times), 'max_us': max(times), 'min_us': min(times)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--port', default='COM4')
    parser.add_argument('--board', default='2025030317')
    parser.add_argument('--location', type=int, default=561)
    parser.add_argument('--runs', type=int, default=1)
    args = parser.parse_args()
    evidence = args.evidence.resolve()
    summary = json.loads((evidence / 'summary.json').read_text())
    if summary['gate'] is not True or args.runs < 1:
        raise ValueError('A passing regression and positive run count are required')
    for relative, digest in summary['source_sha256'].items():
        if relative.startswith(('src/', 'gowin/', 'constraints/')) and sha(ROOT / relative) != digest:
            raise ValueError(f'Current source differs from selected build: {relative}')
    fs_relative, fs_digest = next(iter(summary['bitstream_sha256'].items()))
    fs = evidence / fs_relative
    if sha(fs) != fs_digest:
        raise ValueError('Bitstream hash mismatch')
    ports = [{'device': p.device, 'hwid': p.hwid, 'description': p.description} for p in list_ports.comports()]
    if not any(p['device'] == args.port and args.board in p['hwid'] for p in ports):
        raise ValueError('Selected board serial is absent from requested port')
    out = ROOT / 'results' / 'logic_search_20261003' / ('physical_' + args.label)
    out.mkdir(parents=True, exist_ok=False)
    shutil.copy2(fs, out / 'programmed.fs')
    shutil.copy2(evidence / 'summary.json', out / 'build_summary.json')
    shutil.copytree(evidence / 'source', out / 'source')
    for filename in ('21_quick_uart_test.py', '22_robust_uart_test.py', '22_robust_uart_test_fullrange.py',
                     'reference_model.py', 'qualify_candidate.py'):
        shutil.copy2(ROOT / 'scripts' / filename, out / 'source' / 'scripts' / filename)
    programmer = Path('C:/Gowin/Gowin_V1.9.11.03_Education_x64/Programmer/bin/programmer_cli.exe')
    command = [str(programmer), '--device', 'GW2AR-18C', '--operation_index', '2',
               '--cable-index', '4', '--location', str(args.location), '--frequency', '2.5MHz',
               '--fsFile', str(out / 'programmed.fs')]
    report = {'started_utc': datetime.now(timezone.utc).isoformat(), 'board': args.board,
              'port': args.port, 'serial_inventory': ports, 'programming_mode': 'volatile SRAM',
              'programming_command': command, 'bitstream_sha256': fs_digest,
              'logic': summary['logic'], 'lut': summary['lut'], 'registers': summary['registers'],
              'bsram': summary['bsram'], 'timing': {k: summary[k] for k in ('fmax_mhz', 'setup_slack_ns', 'hold_slack_ns')},
              'source_sha256': summary['source_sha256'], 'reprogram_between_runs': False,
              'reset_between_runs': False, 'tests': [], 'all_correct': False, 'local_rubric_100': False,
              'scope': 'Physical practice qualification on local PC; official judge score and hidden seed are unverified'}
    def save():
        (out / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    with (out / 'programming.log').open('w') as log:
        proc = subprocess.run(command, cwd=out, stdout=log, stderr=subprocess.STDOUT, timeout=90)
    text = (out / 'programming.log').read_text(errors='replace')
    report['programming_passed'] = proc.returncode == 0 and 'Operation "SRAM Program"' in text and 'Finished.' in text
    save()
    if not report['programming_passed']:
        raise RuntimeError(f'SRAM programming failed; see {out}')
    print(f'SRAM programmed; saving {args.label} to {out}', flush=True)
    schedule = [('quick', '21_quick_uart_test.py')]
    for i in range(1, args.runs + 1):
        schedule += [(f'normal_{i}', '22_robust_uart_test.py'), (f'fullrange_{i}', '22_robust_uart_test_fullrange.py')]
    for label, filename in schedule:
        folder = out / label
        folder.mkdir()
        original = (ROOT / 'scripts' / filename).read_bytes()
        changed, count = re.subn(rb'^PORT = "COM6"', f'PORT = "{args.port}"'.encode(), original, flags=re.M)
        if count != 1:
            raise ValueError('Unexpected organizer PORT declaration')
        test = folder / filename
        test.write_bytes(changed)
        with (folder / 'console.log').open('w') as log:
            proc = subprocess.run([sys.executable, '-u', str(test)], cwd=folder,
                                  stdout=log, stderr=subprocess.STDOUT, timeout=180)
        text = (folder / 'console.log').read_text(errors='replace')
        entry = {'name': label, 'exit_code': proc.returncode, 'original_sha256': sha(ROOT / 'scripts' / filename),
                 'executed_sha256': sha(test), 'only_port_changed': test.read_bytes() == changed, 'passed': False}
        if label == 'quick':
            entry['passed'] = proc.returncode == 0 and 'PASS' in text.splitlines()
        else:
            suffix = '_fullrange' if label.startswith('fullrange') else ''
            try:
                entry.update(review(folder / f'trade_results_100{suffix}.csv'))
                result = (folder / f'trade_summary_100{suffix}.txt').read_text()
                entry['passed'] = proc.returncode == 0 and all(line in result.splitlines() for line in
                    ('Packets successfully received: 100', 'Correct packets: 84', 'Correct individual actions: 168/168', 'Timeouts: 0'))
                if label.startswith('normal'):
                    entry['local_rubric_score'] = (70 + (15 if entry['mean_us'] <= 16626 * 1.25 else 8 if entry['mean_us'] <= 16626 * 2 else 0)
                                                  + 15 * min(1, 542 / summary['lut']))
            except (ValueError, KeyError, FileNotFoundError) as error:
                entry['failure'] = str(error)
        report['tests'].append(entry)
        save()
        print(json.dumps(entry), flush=True)
        if not entry['passed']:
            raise RuntimeError(f'Physical correctness failed in {label}; evidence retained at {out}')
    normal = [t for t in report['tests'] if t['name'].startswith('normal')]
    report['all_correct'] = all(t['passed'] for t in report['tests'])
    report['local_rubric_100'] = report['all_correct'] and all(t['local_rubric_score'] == 100 for t in normal)
    report['median_of_normal_run_means_us'] = statistics.median(t['mean_us'] for t in normal)
    report['median_of_normal_packet_medians_us'] = statistics.median(t['median_us'] for t in normal)
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    save()
    print(f"RESULT all_correct={report['all_correct']} local_rubric_100={report['local_rubric_100']}", flush=True)
    return 0 if report['local_rubric_100'] else 2

if __name__ == '__main__':
    sys.exit(main())
