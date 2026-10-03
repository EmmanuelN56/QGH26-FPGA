"""One authorized physical sweep of the seven reviewed SRAM candidates."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil, subprocess, sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from capture_vector_stress import validate_inputs

REVIEW = ROOT / 'results/latency_audit_20261003/review.json'
PROGRAMMER = Path('C:/Users/Lenovo/AppData/Local/GatorFPGA/gowin/extracted/Gowin_V1.9.11.03_Education_x64/Programmer/bin/programmer_cli.exe')
EXPECTED = {
    'gap_500us': '717ed8d11578dc5312b4059f90ee8218185746ff9a1b4af5cd19398398551bf4',
    'gap_250us': '512c248e8eec63eeacf66ead160e4186779b6e2daf0449c51abff0adfabed00b',
    'gap_100us': 'e2b0eef3a7e90749e1562ea1a115f9cd8ce5518a23daa468f109a63ef079cf1d',
    'gap_10us': '593550b63f26965821d478deb33deb472abdea67ed33a5c1a86d8b88b02c3f89',
    'gap_1us': 'ecbb7dca4abcc612d12f4020f6ab1ba1883b06740a50fa920fa1345da9ac0742',
    'gap_1cycles': 'd11282640e878fbdc2814b21251cd123d04e18a53ae03e6034705c11ea5316ef',
    'gap_0cycles': 'bc7edc25e995168772989e199c9cd43252f6120bec68e21fba034c8a35d4313d',
}
BASELINE = 'e0b5bdc80f568ba7e7036693b6aa08fe2e0708843aa295db5cc83fca105afce7'

def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    review = json.loads(REVIEW.read_text(encoding='utf-8'))
    assert review['baseline_sha256'] == BASELINE
    assert {c['name']: c['bitstream_sha256'] for c in review['candidates']} == EXPECTED
    base = ROOT / 'results/build_windows_20261003'
    entries = [('baseline_before', ROOT / 'bitstream/trade_core.fs', base / 'build_summary.json', base / 'source', BASELINE)]
    for c in review['candidates']:
        folder = ROOT / c['evidence_directory']
        entries.append((c['name'], folder / 'candidate.fs', folder / 'build_summary.json', folder / 'source', c['bitstream_sha256']))
    entries.append(('baseline_after', ROOT / 'bitstream/trade_core.fs', base / 'build_summary.json', base / 'source', BASELINE))
    # Preflight every source/bitstream before the first programming operation.
    for _, fs, summary, source, expected in entries:
        validate_inputs(fs, summary, source)
        assert sha(fs) == expected
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = ROOT / 'results' / ('latency_physical_' + stamp)
    native = Path('C:/Users/Lenovo/AppData/Local/GatorFPGA') / ('latency_physical_' + stamp)
    out.mkdir(); native.mkdir(parents=True)
    shutil.copyfile(REVIEW, out / 'authorized_review.json')
    shutil.copyfile(Path(__file__), out / 'run_physical_sweep.py')
    report = {'scope': 'Authorized volatile SRAM physical latency sweep',
              'authorization': 'User answered yes to seven identified candidates and baseline comparison/recovery',
              'review_sha256': sha(REVIEW), 'port': 'COM4', 'board_serial': '2025030317',
              'location': 561, 'cable_index': 4, 'operation_index': 2,
              'native_work': str(native.resolve()), 'status': 'running', 'runs': []}
    save(out / 'manifest.json', report)
    print('PHYSICAL SWEEP evidence: ' + str(out), flush=True)

    def run(command, log, cwd=ROOT, timeout=240):
        with log.open('w', encoding='utf-8', newline='\n') as stream:
            stream.write(subprocess.list2cmdline([str(x) for x in command]) + '\n'); stream.flush()
            process = subprocess.run([str(x) for x in command], cwd=cwd, stdout=stream,
                                     stderr=subprocess.STDOUT, timeout=timeout)
        return process.returncode, log.read_text(encoding='utf-8', errors='replace')

    def program(fs, expected, directory):
        copy = native / (directory.name + '.fs')
        shutil.copyfile(fs, copy)
        assert sha(copy) == expected
        code, text = run([PROGRAMMER, '--device', 'GW2AR-18C', '--operation_index', '2',
                          '--cable-index', '4', '--location', '561', '--frequency', '2.5MHz',
                          '--fsFile', copy], directory / 'programming.log', cwd=native, timeout=60)
        if code or 'Operation "SRAM Program"' not in text or 'Finished.' not in text or '0x0000081B' not in text:
            raise RuntimeError('SRAM programming not confirmed: ' + str(directory / 'programming.log'))
        return directory / 'programming.log'

    try:
        code, scan = run([PROGRAMMER, '--scan-cables', 'F'], out / 'cables.log', cwd=native, timeout=30)
        assert code == 0 and '561' in scan
        code, identity = run([PROGRAMMER, '--device', 'GW2AR-18C', '--operation_index', '0',
                              '--cable-index', '4', '--location', '561', '--frequency', '2.5MHz'],
                             out / 'device_identity.log', cwd=native, timeout=30)
        assert code == 0 and 'ID Code is: 0x0000081B' in identity and 'Finished.' in identity
        for label, fs, summary, source, expected in entries:
            directory = out / label; directory.mkdir()
            item = {'name': label, 'bitstream_sha256': expected, 'status': 'programming'}
            report['runs'].append(item); save(out / 'manifest.json', report)
            programming = program(fs, expected, directory)
            item['programming_passed'] = True
            print(label + ': SRAM programmed; running organizer tests', flush=True)
            before = set((ROOT / 'results').glob('board_*'))
            code, _ = run([sys.executable, '-B', ROOT / 'scripts/capture_board_tests.py',
                           '--port', 'COM4', '--board', 'USB-debugger-2025030317',
                           '--bitstream', fs, '--runs', '3', '--source-root', source,
                           '--build-summary', summary, '--programming-log', programming],
                          directory / 'organizer_capture.log')
            created = set((ROOT / 'results').glob('board_*')) - before
            assert len(created) == 1, 'Expected one organizer capture directory'
            capture_dir = created.pop(); capture = json.loads((capture_dir / 'manifest.json').read_text())
            item.update(organizer_directory=capture_dir.relative_to(ROOT).as_posix(),
                        organizer_passed=code == 0 and capture['all_passed'],
                        organizer_tests=capture['tests'])
            save(out / 'manifest.json', report)
            before = set((ROOT / 'results').glob('stress_*'))
            code, _ = run([sys.executable, '-B', ROOT / 'scripts/capture_vector_stress.py',
                           '--port', 'COM4', '--board', 'USB-debugger-2025030317',
                           '--bitstream', fs, '--source-root', source, '--build-summary', summary],
                          directory / 'stress_capture.log')
            created = set((ROOT / 'results').glob('stress_*')) - before
            assert len(created) == 1, 'Expected one stress capture directory'
            stress_dir = created.pop(); stress = json.loads((stress_dir / 'manifest.json').read_text())
            shutil.copyfile(programming, stress_dir / 'programming.log')
            item.update(stress_directory=stress_dir.relative_to(ROOT).as_posix(),
                        stress_passed=code == 0 and stress['all_passed'],
                        stress_correct_packets=stress.get('correct_packets', 0),
                        stress_latency_us=stress.get('physical_latency_us'),
                        status='passed' if item['organizer_passed'] and code == 0 and stress['all_passed'] else 'failed')
            tests = [t['physical_latency_us'] for t in capture['tests'] if 'physical_latency_us' in t]
            if tests:
                item['organizer_mean_us'] = sum(t['mean'] * t['successful_packets'] for t in tests) / sum(t['successful_packets'] for t in tests)
                item['organizer_max_us'] = max(t['max'] for t in tests)
            save(out / 'manifest.json', report)
            print(label + ': ' + item['status'].upper() + '; organizer mean/max us=' + str(item.get('organizer_mean_us')) + '/' + str(item.get('organizer_max_us')) + '; stress=' + str(item['stress_correct_packets']) + '/1509', flush=True)
        report['status'] = 'completed_baseline_restored'
    except BaseException as exc:
        report.update(status='failed', error=str(exc))
        recovery = out / 'baseline_recovery'; recovery.mkdir(exist_ok=True)
        try:
            program(ROOT / 'bitstream/trade_core.fs', BASELINE, recovery)
            report['baseline_recovery_programmed'] = True
        except BaseException as recovery_error:
            report['baseline_recovery_error'] = str(recovery_error)
        raise
    finally:
        save(out / 'manifest.json', report)
    print('COMPLETE sweep; validated baseline restored. Evidence: ' + str(out), flush=True)

if __name__ == '__main__':
    main()
