"""Run the optimizer's gated fresh build after checking generated-file cleanup."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import fpgaopt

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--resume-gated-build', action='store_true', help='Reuse a passing gate only after checking every recorded input hash')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    build = root / '.build' / 'gowin_trade'
    if build.exists():
        if build.resolve() != build.absolute() or build.is_junction():
            raise ValueError('Unexpected build cleanup target')
        entries = [build, *build.rglob('*')]
        for entry in entries:
            if not entry.resolve().is_relative_to(build) or entry.is_symlink() or entry.is_junction():
                raise ValueError('Reparse point or escaping path in build directory')
        if os.name == 'nt':
            powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
            subprocess.run([str(powershell), '-NoProfile', '-NonInteractive', '-File',
                            str(root / 'scripts' / 'clear_gowin_build_readonly.ps1')], check=True)
        else:
            for entry in entries:
                if entry.is_file():
                    entry.chmod(entry.stat().st_mode | stat.S_IWRITE)
    os.environ['PATH'] = str(root / '.build' / 'tools' / 'icarus' / 'app' / 'bin') + os.pathsep + os.environ['PATH']
    if args.resume_gated_build:
        validation = json.loads((root / 'results' / 'software_validation.json').read_text())
        if validation['all_passed'] is not True:
            raise ValueError('No passing gate to resume')
        for relative, digest in validation['source_sha256'].items():
            if hashlib.sha256((root / relative).read_bytes()).hexdigest() != digest:
                raise ValueError(f'Gate input changed: {relative}')
        fpgaopt.run_gate = lambda: (True, 'Reusing completed regression: every recorded source/test input hash matches')
    fpgaopt.cmd_measure(argparse.Namespace(label=args.label, skip_gate=False, reuse_project=False, flow='all', gw_sh=None))

if __name__ == '__main__':
    main()
