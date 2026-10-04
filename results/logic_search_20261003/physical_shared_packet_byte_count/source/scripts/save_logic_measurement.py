"""Preserve source, regression and fresh Gowin evidence for one measurement."""
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import sys
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
dest = root / 'results' / 'logic_search_20261003' / sys.argv[1]
if dest.exists():
    raise SystemExit(f'Evidence already exists: {dest}')
build = root / '.build' / 'gowin_trade' / 'trade_core'
for name in ('src', 'gowin', 'constraints'):
    shutil.copytree(root / name, dest / 'source' / name)
for name in ('scripts/reference_model.py', 'scripts/generate_vectors.py', 'scripts/run_regression.py',
             'scripts/fpgaopt.py', 'scripts/measure_logic_candidate.py', 'scripts/qualify_candidate.py',
             'scripts/22_robust_uart_test_fullrange.py', 'scripts/clear_gowin_build_readonly.ps1',
             'scripts/save_logic_measurement.py', 'scripts/stress_board_vectors.py',
             'docs/official/SCORING_AND_RANKING_CLARIFICATION.md', 'SKILL.md'):
    target = dest / 'source' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / name, target)
shutil.copytree(root / 'testbench', dest / 'source' / 'testbench')
for name in ('software_validation.json', 'simulation.log', 'optimization_log.csv'):
    shutil.copy2(root / 'results' / name, dest / name)
shutil.copy2(root / '.build' / 'opt' / 'last_build.log', dest / 'build.log')
for source in build.rglob('*'):
    if source.is_file() and source.suffix in ('.html', '.txt', '.xml', '.log', '.fs', '.gprj'):
        target = dest / 'build' / source.relative_to(build)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

def flat(path):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]*>', ' ', path.read_text(errors='replace'))))

syn = flat(next(build.rglob('*_syn.rpt.html')))
pnr = flat(next(build.rglob('*.rpt.txt')))
timing_html = next(build.rglob('*_tr_content.html')).read_text()
timing = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]*>', ' ', timing_html)))
tree = ET.parse(next(build.rglob('*_syn_rsc.xml'))).getroot()
modules = []
def walk(node, path):
    path = f'{path}/{node.attrib["name"]}' if path else node.attrib['name']
    modules.append(dict(module=path, **{key: int(node.attrib.get(attr, 0)) for key, attr in
                   [('lut', 'Lut'), ('alu', 'Alu'), ('registers', 'Register'), ('ssram', 'Ssram'), ('bsram', 'Bsram')]}))
    for child in node:
        walk(child, path)
walk(tree, '')
def slack(anchor):
    section = timing_html.split(f'name="{anchor}"', 1)[1]
    data = re.findall(r'<td[^>]*>(.*?)</td>', section, re.S)
    return float(html.unescape(re.sub(r'<[^>]*>', '', data[1])).strip())
validation = json.loads((dest / 'software_validation.json').read_text())
summary = {
    'label': sys.argv[1], 'digit_width': int(sys.argv[2]),
    'gate': validation['all_passed'], 'packet_count': validation.get('vectors', {}).get('packet_count'),
    'logic': int(re.search(r'\bLogic\s+(\d+)\s*\(', syn)[1]),
    'lut': sum(m['lut'] for m in modules), 'alu': sum(m['alu'] for m in modules),
    'ram16': sum(m['ssram'] for m in modules),
    'registers': sum(m['registers'] for m in modules), 'bsram': sum(m['bsram'] for m in modules),
    'pnr_logic': int(re.search(r'\bLogic\s*\|\s*(\d+)', pnr)[1]),
    'fmax_mhz': float(re.search(r'27\.000\(MHz\)\s+(\d+\.\d+)\(MHz\)', timing)[1]),
    'setup_slack_ns': slack('Setup_Slack_Table'), 'hold_slack_ns': slack('Hold_Slack_Table'),
    'setup_violations': int(re.search(r'Numbers of Setup Violated Endpoints\s+(\d+)', timing)[1]),
    'hold_violations': int(re.search(r'Numbers of Hold Violated Endpoints\s+(\d+)', timing)[1]),
    'latency_simulation': re.findall(r'LATENCY[^\n]*', (dest / 'simulation.log').read_text()),
    'physical_latency_ms': None, 'physical_validation': False,
    'modules_own_cells': modules,
    'source_sha256': {str(p.relative_to(dest / 'source')).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (dest / 'source').rglob('*') if p.is_file()},
    'bitstream_sha256': {str(p.relative_to(dest)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in dest.rglob('*.fs')},
}
(dest / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps({k: v for k, v in summary.items() if k not in ('source_sha256', 'bitstream_sha256', 'modules_own_cells')}, indent=2))
