"""Check organizer full-range practice vectors and qualification order in RTL simulation.

Organizer serial loops are never executed. This does not measure host latency,
program hardware, or establish qualification on the judges' hidden seeds.
"""
import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import random
import re
import subprocess

from capture_vector_stress import validate_inputs
from reference_model import ITEM_A, ITEM_B, NONE, REQUEST, RESPONSE, ReferenceModel

ROOT = Path(__file__).resolve().parents[1]
AREA = ROOT / 'results/area_20261003T192105403559Z'
TOOLS = Path('C:/Users/Lenovo/AppData/Local/GatorFPGA/iverilog/bin')
DEFAULT_CANDIDATES = ('context_ram', 'carry_uart_pointer', 'carry_direct_equality')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


def practice(filename):
    """Execute only the reviewed pre-transmission model/vector definitions."""
    path = ROOT / 'scripts' / filename
    nodes = []
    for node in ast.parse(path.read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'rows' for t in node.targets):
            break
        if isinstance(node, ast.Import):
            if any(alias.name == 'serial' for alias in node.names):
                continue
            if any(alias.name not in {'csv', 'random', 'struct', 'time'} for alias in node.names):
                raise ValueError('Unexpected organizer import')
        elif isinstance(node, ast.ImportFrom):
            if node.module != 'collections':
                raise ValueError('Unexpected organizer import')
        elif not isinstance(node, (ast.Assign, ast.FunctionDef, ast.ClassDef, ast.Expr)):
            raise ValueError('Unexpected organizer vector definition')
        if isinstance(node, ast.Expr) and not isinstance(node.value, ast.Constant):
            raise ValueError('Unexpected organizer executable statement')
        nodes.append(node)
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
    if (namespace['PACKET_COUNT'], namespace['WINDOW_SIZE'], namespace['PRICE_MIN']) != (100, 16, 0):
        raise ValueError('Organizer test contract changed')
    return namespace


def resource_rows(folder):
    syn = (folder / 'reports/gwsynthesis/trade_core_syn.rpt.html').read_text(encoding='utf-8')
    rows = [re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', ' ', row))).strip()
            for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>', syn, re.S | re.I)]
    logic = next(row for row in rows if re.match(r'Logic \d+\(', row))
    registers = next(row for row in rows if re.match(r'Register \d+ /', row))
    pnr = (folder / 'reports/pnr/trade_core.rpt.txt').read_text(encoding='utf-8')
    routed_logic = re.search(r'^\s*Logic\s*\|\s*(\d+)/', pnr, re.M)
    routed_reg = re.search(r'^\s*Register\s*\|\s*(\d+)/', pnr, re.M)
    if not routed_logic or not routed_reg:
        raise ValueError('Missing routed resource rows')
    return {'synthesis_logic': int(re.match(r'Logic (\d+)', logic)[1]),
            'synthesis_registers': int(re.match(r'Register (\d+)', registers)[1]),
            'synthesis_logic_row': logic, 'synthesis_register_row': registers,
            'routed_logic': int(routed_logic[1]), 'routed_registers': int(routed_reg[1]),
            'synthesis_report': str((folder / 'reports/gwsynthesis/trade_core_syn.rpt.html').relative_to(ROOT)),
            'routed_report': str((folder / 'reports/pnr/trade_core.rpt.txt').relative_to(ROOT))}


def emit(directory, name, sessions, reference_class):
    model = ReferenceModel()  # Keep FPGA-equivalent state across every index-zero session.
    packets, states, ranges = [], [], []
    for label, pa, pb, swaps in sessions:
        start = len(packets)
        refs = {ITEM_A: reference_class(), ITEM_B: reference_class()}
        for index, (a, b, swapped) in enumerate(zip(pa, pb, swaps, strict=True)):
            slots = (ITEM_B, b, ITEM_A, a) if swapped else (ITEM_A, a, ITEM_B, b)
            request = REQUEST.pack(index, *slots)
            response = model.process(request)
            actions = {ITEM_A: refs[ITEM_A].process(a), ITEM_B: refs[ITEM_B].process(b)}
            expected = RESPONSE.pack(index, slots[0], NONE if actions[slots[0]] is None else actions[slots[0]],
                                     slots[2], NONE if actions[slots[2]] is None else actions[slots[2]], 0)
            if response != expected:
                raise AssertionError((label, index, response.hex(), expected.hex()))
            sa, sb = model.items[ITEM_A], model.items[ITEM_B]
            packets.append(request.hex() + response.hex())
            states.append(f'{sa.total:06x}{sb.total:06x}{sa.previous:04x}{sb.previous:04x}'
                          f'{sa.pointer:02x}{sb.pointer:02x}{len(sa.prices):02x}{len(sb.prices):02x}0000')
        ranges.append({'name': label, 'start': start, 'packets': len(pa)})
    if len(packets) > 4096:
        raise ValueError('Corpus exceeds bench capacity')
    for suffix, lines in [('packets', packets), ('states', states)]:
        (directory / f'{name}_{suffix}.mem').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    return {'name': name, 'packets': len(packets), 'sessions': ranges,
            'packets_sha256': digest(directory / f'{name}_packets.mem'),
            'states_sha256': digest(directory / f'{name}_states.mem')}


def generate(out):
    normal = practice('22_robust_uart_test.py')
    full = practice('22_robust_uart_test_fullrange.py')
    if normal['PRICE_MAX'] != 100 or full['PRICE_MAX'] != 65535:
        raise ValueError('Unexpected price limits')
    ordinary = ('official_practice', normal['prices_a'], normal['prices_b'], normal['swap_slots'])
    wide = ('fullrange_practice', full['prices_a'], full['prices_b'], full['swap_slots'])
    sequence = [ordinary, wide, ('official_repeat', *ordinary[1:]), ('fullrange_repeat', *wide[1:])]
    corpora = [emit(out, 'qualification_sequence', sequence, full['MovingAverageReference'])]
    # The first 200 packets are the exact practice official->full-range sequence.
    for suffix in ['packets', 'states']:
        lines = (out / f'qualification_sequence_{suffix}.mem').read_text().splitlines()[:200]
        (out / f'actual_uart_{suffix}.mem').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    extra = []
    for name, a, b in [('all_max', [65535]*96, [65535]*96), ('zero_after_max', [0]*96, [0]*96),
                       ('alternating', [0,65535]*48, [65535,0]*48),
                       ('signed_boundary', [32767,32768]*48, [32768,32767]*48),
                       ('floor_edges', [1]*15+[0]+[1,0,1,2]*20, [0]*15+[15]+[1,0,15,16]*20),
                       ('midpoint', [32768]*96, [32768]*96)]:
        extra.append((name, a, b, [bool(i % 2) for i in range(len(a))]))
    for seed in range(32):
        rng = random.Random(0xB16B0000 + seed)
        a = [rng.randrange(65536) for _ in range(100)]
        b = [rng.randrange(65536) for _ in range(100)]
        swaps = [bool(rng.randrange(2)) for _ in range(100)]
        extra.append((f'supplementary_seed_{seed}', a, b, swaps))
    corpora.append(emit(out, 'fullrange_edges', extra, full['MovingAverageReference']))
    manifest = {'scope': 'Exact organizer practice vectors plus supplementary vectors; hidden seed unknown',
                'organizer_sha256': {f: digest(ROOT / 'scripts' / f) for f in ['22_robust_uart_test.py', '22_robust_uart_test_fullrange.py']},
                'practice_fullrange_seed': full['RANDOM_SEED'], 'corpora': corpora,
                'independent_model_agrees': True, 'no_serial_access': True}
    write_json(out / 'vectors.json', manifest)
    return corpora


def verify(name, out, corpora, actual_uart):
    folder = AREA / name
    validate_inputs(folder / 'candidate.fs', folder / 'build_summary.json', folder / 'source')
    candidate_out = out / name
    candidate_out.mkdir()
    work = ROOT / '.build' / out.name / name
    work.mkdir(parents=True, exist_ok=False)
    sources = sorted((folder / 'source/src').glob('*.v'))
    report = {'candidate': name, 'bitstream_sha256': digest(folder / 'candidate.fs'),
              'resources': resource_rows(folder), 'checks': [], 'physical_validation': False, 'all_passed': False}
    write_json(candidate_out / 'validation.json', report)
    def run(command, label):
        path = candidate_out / f'{label}.log'
        with path.open('w', encoding='utf-8') as stream:
            stream.write(subprocess.list2cmdline([str(x) for x in command]) + '\n')
            stream.flush()
            p = subprocess.run([str(x) for x in command], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=900)
        text = path.read_text(encoding='utf-8', errors='replace')
        if p.returncode:
            raise RuntimeError(f'{name}: {label} failed; see {path}')
        return text
    for bench in ['trade_pair_tb', 'top_sessions_tb']:
        compiled = work / f'{bench}.vvp'
        source = folder / 'verification_source/testbench' / f'{bench}.v'
        run([TOOLS / 'iverilog.exe', '-g2012', '-Wall', '-s', bench, '-o', compiled, *sources, source], bench + '_compile')
        for corpus in corpora:
            args = ['+COUNT=' + str(corpus['packets']), '+VECTORS=' + str(out / f"{corpus['name']}_packets.mem")]
            if bench == 'trade_pair_tb':
                args.append('+STATES=' + str(out / f"{corpus['name']}_states.mem"))
            text = run([TOOLS / 'vvp.exe', compiled, *args], bench + '_' + corpus['name'])
            if 'PASS ' not in text:
                raise RuntimeError('Missing bench PASS')
            report['checks'].append({'bench': bench, 'corpus': corpus['name'], 'packets': corpus['packets'], 'passed': True})
            write_json(candidate_out / 'validation.json', report)
            print(f'PASS {name} {bench} {corpus["name"]}', flush=True)
    if actual_uart:
        compiled = work / 'actual_uart.vvp'
        run([TOOLS / 'iverilog.exe', '-g2012', '-Wall', '-DBOARD_TIMING', '-s', 'top_sessions_tb', '-o', compiled,
             *sources, folder / 'verification_source/testbench/top_sessions_tb.v'], 'actual_uart_compile')
        text = run([TOOLS / 'vvp.exe', compiled, '+COUNT=200', '+VECTORS=' + str(out / 'actual_uart_packets.mem')], 'actual_uart')
        if 'PASS ' not in text:
            raise RuntimeError('Missing actual UART timing PASS')
        report['checks'].append({'bench': 'top_sessions_tb_actual_27MHz_115200', 'packets': 200, 'passed': True})
        print(f'PASS {name} actual UART timing 200 packets', flush=True)
    validate_inputs(folder / 'candidate.fs', folder / 'build_summary.json', folder / 'source')
    report['all_passed'] = True
    write_json(candidate_out / 'validation.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates', nargs='+', choices=DEFAULT_CANDIDATES, default=list(DEFAULT_CANDIDATES))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--skip-actual-uart', action='store_true', help='Skip the 200-packet actual UART timing simulation')
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = (args.output or ROOT / 'results' / ('fullrange_' + stamp)).resolve()
    out.mkdir(parents=True, exist_ok=False)
    print('Evidence directory: ' + str(out), flush=True)
    corpora = generate(out)
    rankings = []
    for folder in AREA.iterdir():
        if (folder / 'reports/gwsynthesis/trade_core_syn.rpt.html').is_file():
            rankings.append({'candidate': folder.name, **resource_rows(folder)})
    rankings.sort(key=lambda row: (row['synthesis_logic'], row['synthesis_registers']))
    write_json(out / 'ranking_audit.json', {'metric': 'Direct Logic row; do not sum hierarchy cells',
                'provisional_synthesis_order': rankings, 'judge_rebuild_required': True})
    with ThreadPoolExecutor(max_workers=len(args.candidates)) as pool:
        futures = [pool.submit(verify, name, out, corpora, not args.skip_actual_uart) for name in args.candidates]
        reports = [future.result() for future in futures]
    write_json(out / 'validation.json', {'scope': 'RTL simulation only; no board programming or serial access',
               'all_passed': all(report['all_passed'] for report in reports), 'candidates': reports,
               'qualified_on_official_judge_run': False, 'hidden_seed_tested': False})
    print('PASS all full-range simulations. Physical qualification remains pending.', flush=True)


if __name__ == '__main__':
    main()
