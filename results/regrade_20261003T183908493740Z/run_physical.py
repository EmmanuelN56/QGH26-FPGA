"""Repeat previously authorized release tests with immutable build inputs."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, shutil, subprocess, sys, winreg
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from capture_vector_stress import validate_inputs
from serial.tools.list_ports import comports
EXPECTED = 'bc7edc25e995168772989e199c9cd43252f6120bec68e21fba034c8a35d4313d'
FS = ROOT / 'bitstream/trade_core.fs'
SUMMARY = ROOT / 'results/release_zero_gap_20261003T180901633856Z/build_summary.json'
PROGRAMMER = Path('C:/Users/Lenovo/AppData/Local/GatorFPGA/gowin/extracted/Gowin_V1.9.11.03_Education_x64/Programmer/bin/programmer_cli.exe')
def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def host():
    key_name = r'SYSTEM\CurrentControlSet\Enum\FTDIBUS\VID_0403+PID_6010+2025030317B\0000\Device Parameters'
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_name) as key:
        timer = winreg.QueryValueEx(key, 'LatencyTimer')[0]
    ports = [{'device': p.device, 'description': p.description, 'hwid': p.hwid,
              'serial_number': p.serial_number, 'vid': p.vid, 'pid': p.pid} for p in comports()]
    assert timer == 16, 'Expected unchanged original COM4 timer'
    assert any(p['device'] == 'COM4' and p['vid'] == 0x0403 and p['pid'] == 0x6010
               and p['serial_number'] == '2025030317B' for p in ports)
    return {'utc': datetime.now(timezone.utc).isoformat(), 'computer': os.environ.get('COMPUTERNAME'),
            'com4_latency_timer_ms': timer, 'ports': ports, 'driver_changes': False}
def run(command, log, cwd=ROOT, timeout=240):
    with (OUT / log).open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(subprocess.list2cmdline([str(x) for x in command]) + '\n'); stream.flush()
        proc = subprocess.run([str(x) for x in command], cwd=cwd, stdout=stream,
                              stderr=subprocess.STDOUT, timeout=timeout)
    transcript = (OUT / log).read_text(encoding='utf-8', errors='replace')
    assert proc.returncode == 0, f'Command failed; see {log}'
    return transcript
def main():
    validate_inputs(FS, SUMMARY, ROOT)
    assert sha(FS) == EXPECTED
    review = json.loads((ROOT / 'results/latency_audit_20261003/review.json').read_text())
    assert any(c['bitstream_sha256'] == EXPECTED for c in review['candidates'])
    software = json.loads((ROOT / 'results/software_validation.json').read_text())
    assert software['all_passed'] and '1509 packets' in software['checks'][-1]['result']
    for name in ('software_validation.json', 'simulation.log'):
        shutil.copyfile(ROOT / 'results' / name, OUT / name)
    build = json.loads(SUMMARY.read_text())
    native = Path(build['native_root'])
    native_fs = native / 'final_release.fs'
    assert sha(native_fs) == EXPECTED, 'Native programmer file must match authorized release'
    save('host_before.json', host())
    status = {'status': 'running', 'bitstream_sha256': EXPECTED,
              'authorization': 'Existing explicit approval of this exact zero-gap candidate and physical tests',
              'source_and_build_verified': True, 'no_reprogram_between_test_sessions': True}
    save('physical_context.json', status)
    try:
        scan = run([PROGRAMMER, '--scan-cables', 'F'], 'cables.log', cwd=native, timeout=30)
        assert '561' in scan
        base = [PROGRAMMER, '--device', 'GW2AR-18C', '--cable-index', '4', '--location', '561', '--frequency', '2.5MHz']
        identity = run([*base, '--operation_index', '0'], 'device_identity.log', cwd=native, timeout=30)
        assert 'ID Code is: 0x0000081B' in identity and 'Finished.' in identity
        programmed = run([*base, '--operation_index', '2', '--fsFile', native_fs], 'programming.log', cwd=native, timeout=60)
        assert 'Operation "SRAM Program"' in programmed and 'Finished.' in programmed and '0x0000081B' in programmed
        print('Approved release programmed in SRAM; running quick and three robust sessions', flush=True)
        common = ['--port', 'COM4', '--board', 'USB-debugger-2025030317', '--bitstream', FS, '--build-summary', SUMMARY, '--source-root', ROOT]
        before = set((ROOT / 'results').glob('board_*'))
        run([sys.executable, '-B', ROOT / 'scripts/capture_board_tests.py', *common, '--runs', '3', '--programming-log', OUT / 'programming.log'], 'organizer_capture.log')
        created = set((ROOT / 'results').glob('board_*')) - before
        assert len(created) == 1
        board = created.pop(); board_report = json.loads((board / 'manifest.json').read_text())
        assert board_report['all_passed']
        status['organizer_directory'] = board.relative_to(ROOT).as_posix(); save('physical_context.json', status)
        print('PASS organizer quick and three robust sessions; running 1509 expanded packets', flush=True)
        before = set((ROOT / 'results').glob('stress_*'))
        run([sys.executable, '-B', ROOT / 'scripts/capture_vector_stress.py', *common], 'stress_capture.log')
        created = set((ROOT / 'results').glob('stress_*')) - before
        assert len(created) == 1
        stress = created.pop(); stress_report = json.loads((stress / 'manifest.json').read_text())
        assert stress_report['all_passed'] and stress_report['correct_packets'] == 1509
        shutil.copyfile(OUT / 'programming.log', stress / 'programming.log')
        status.update(status='passed', stress_directory=stress.relative_to(ROOT).as_posix())
        validate_inputs(FS, SUMMARY, ROOT); save('host_after.json', host())
        print('PASS physical organizer and expanded tests; ' + str(OUT), flush=True)
    except BaseException as exc:
        status.update(status='failed', error=str(exc)); raise
    finally:
        save('physical_context.json', status)
if __name__ == '__main__':
    main()
