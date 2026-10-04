"""Validate the saved full-range stress corpus, then check engine and complete UART RTL."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

from generate_vectors import ROOT, organizer_reference
from reference_model import ITEM_A, ITEM_B, REQUEST, RESPONSE, ReferenceModel

CORPORA = ('qualification_sequence', 'fullrange_edges', 'original', 'expanded')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def validate(corpora):
    cls = organizer_reference('22_robust_uart_test_fullrange.py', 'MovingAverageReference')
    model = ReferenceModel()
    counts = Counter()
    residues, old_residues, pointers, request_bytes, prices = set(), set(), set(), set(), set()
    maximum_sum = 0
    combined = []
    identities = {}
    for name in CORPORA:
        packet_path, state_path = corpora / (name + '_packets.mem'), corpora / (name + '_states.mem')
        packets, states = packet_path.read_text().splitlines(), state_path.read_text().splitlines()
        if len(packets) != len(states) or len(packets) > 4096:
            raise ValueError(f'Invalid corpus length: {name}')
        for number, (line, state) in enumerate(zip(packets, states, strict=True)):
            raw = bytes.fromhex(line)
            if len(raw) != 16:
                raise ValueError(f'Invalid vector: {name}:{number}')
            request, expected = raw[:8], raw[8:]
            index, id1, p1, id2, p2 = REQUEST.unpack(request)
            if index == 0:
                refs = {ITEM_A: cls(), ITEM_B: cls()}
                model = ReferenceModel()
                counts['index_zero_restarts'] += 1
            elif not combined:
                raise ValueError('First vector must start a session')
            actions = [refs[item].process(price) for item, price in ((id1, p1), (id2, p2))]
            organizer = RESPONSE.pack(index, id1, actions[0] or 0, id2, actions[1] or 0, 0)
            before_actions = {item: model.items[item].action for item in (ITEM_A, ITEM_B)}
            for item, price in ((id1, p1), (id2, p2)):
                before = model.items[item]
                old_residues.add(before.total % 16)
                if len(before.prices) == 16:
                    updated = before.total - before.prices[0] + price
                    for label, delta in (('previous_old_average', before.previous - before.total // 16),
                                         ('current_new_average', price - updated // 16)):
                        if delta in (-1, 0, 1):
                            counts[label + '_' + str(delta)] += 1
                    if before.pointer == 15:
                        counts['full_history_wraps'] += 1
            if organizer != expected or model.process(request) != expected:
                raise ValueError(f'Model mismatch: {name}:{number}')
            sa, sb = model.items[ITEM_A], model.items[ITEM_B]
            for item in (ITEM_A, ITEM_B):
                action = model.items[item].action
                if index >= 16 and action:
                    counts[('held_' if before_actions[item] == action else 'transition_to_') + str(action)] += 1
            actual_state = (f'{sa.total:06x}{sb.total:06x}{sa.previous:04x}{sb.previous:04x}'
                            f'{sa.pointer:02x}{sb.pointer:02x}{len(sa.prices):02x}{len(sb.prices):02x}0000')
            if actual_state != state:
                raise ValueError(f'State mismatch: {name}:{number}')
            for item in (sa, sb):
                maximum_sum = max(maximum_sum, item.total)
                residues.add(item.total % 16)
                pointers.add(item.pointer)
                counts['action_' + str(item.action)] += 1
            request_bytes.update(request)
            prices.update((p1, p2))
            counts['packets'] += 1
            counts['swapped_slots' if id1 == ITEM_B else 'ordinary_slots'] += 1
            if index in (15, 16, 17):
                counts['boundary_index_' + str(index)] += 1
            combined.append(line)
        identities[name] = {'packets': len(packets), 'packets_sha256': digest(packet_path),
                            'states_sha256': digest(state_path)}
    if maximum_sum != 16 * 65535 or residues != set(range(16)) or old_residues != set(range(16)) or pointers != set(range(16)):
        raise ValueError('Missing maximum-sum, floor-residue, or pointer coverage')
    if request_bytes != set(range(256)) or not {0, 65535, 32767, 32768} <= prices:
        raise ValueError('Missing UART byte or unsigned price boundary coverage')
    for comparison in ('previous_old_average', 'current_new_average'):
        if any(counts[comparison + '_' + str(delta)] == 0 for delta in (-1, 0, 1)):
            raise ValueError('Missing equality or one-unit comparison boundary')
    return combined, {'independent_model_agrees': True, 'organizer_model_agrees': True,
                      'counts': dict(counts), 'corpora': identities, 'maximum_rolling_sum': maximum_sum,
                      'floor_residues': sorted(residues), 'old_floor_residues': sorted(old_residues), 'pointers': sorted(pointers),
                      'request_byte_values': len(request_bytes), 'distinct_prices': len(prices),
                      'minimum_price': min(prices), 'maximum_price': max(prices)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpora', type=Path, default=ROOT / 'testbench/vectors/extensive')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    combined, coverage = validate(args.corpora)
    (out / 'coverage.json').write_text(json.dumps(coverage, indent=2) + '\n')
    (out / 'packets.mem').write_text('\n'.join(combined) + '\n')
    sources = sorted((ROOT / 'src').glob('*.v'))
    files = [*sources, ROOT / 'testbench/trade_engine_tb.v', ROOT / 'testbench/top_sessions_tb.v',
             Path(__file__), ROOT / 'scripts/reference_model.py', ROOT / 'scripts/generate_vectors.py',
             ROOT / 'scripts/22_robust_uart_test_fullrange.py']
    identities = {str(p.relative_to(ROOT)): digest(p) for p in files}
    report = {'all_passed': False, 'physical_validation': False, 'coverage': coverage,
              'source_sha256': identities, 'checks': []}
    tools = ROOT / '.build/tools/icarus/app'
    def run(command, label):
        with (out / (label + '.log')).open('w') as log:
            log.write(subprocess.list2cmdline([str(x) for x in command]) + '\n')
            log.flush()
            result = subprocess.run([str(x) for x in command], cwd=ROOT, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=600)
        transcript = (out / (label + '.log')).read_text(errors='replace')
        if result.returncode:
            raise RuntimeError(f'{label}: see saved log')
        return transcript
    try:
        for bench in ('trade_engine_tb', 'top_sessions_tb'):
            binary = out / (bench + '.vvp')
            run([tools / 'bin/iverilog.exe', '-g2012', '-Wall',
                 '-s', bench, '-o', binary, *sources, ROOT / 'testbench' / (bench + '.v')], bench + '_compile')
            for name in CORPORA:
                transcript = run([tools / 'bin/vvp.exe', binary,
                                  '+COUNT=' + str(coverage['corpora'][name]['packets']),
                                  '+VECTORS=' + str(args.corpora.resolve() / (name + '_packets.mem')),
                                  '+STATES=' + str(args.corpora.resolve() / (name + '_states.mem'))], bench + '_' + name)
                if 'PASS ' not in transcript:
                    raise RuntimeError(f'Missing PASS: {bench}:{name}')
                report['checks'].append({'bench': bench, 'corpus': name, 'passed': True})
                print(f'PASS {bench} {name} {coverage["corpora"][name]["packets"]} packets', flush=True)
        if any(digest(ROOT / name) != sha for name, sha in identities.items()):
            raise ValueError('Inputs changed during simulation')
        report['all_passed'] = True
    finally:
        (out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS extensive RTL: {len(combined)} packets in both engine and complete UART checks', flush=True)

if __name__ == '__main__':
    main()
