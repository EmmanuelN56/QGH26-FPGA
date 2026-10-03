from pathlib import Path
import re
out=Path('results/area_20261003T192105403559Z')
p=Path('docs/lut_optimization_study.md');s=p.read_text(encoding='utf-8')
rows=re.findall(r'^\| (?!Candidate|---|Tested release).+\|$',s,re.M)
assert len(rows)==17
newrows=sorted(rows,key=lambda x:int(x.split('|')[2].strip()))
first=s.index(rows[0]);last=s.index(rows[-1])+len(rows[-1]);s=s[:first]+'\n'.join(newrows)+s[last:]
p.write_text(s,encoding='utf-8',newline='\n')
p=Path('docs/human_review.md');s=p.read_text(encoding='utf-8')
s+='''
To stage only this area study and its documentation, after reviewing the existing changes in README.md and PROJECT_BRIEF.md:

```powershell
git -c safe.directory=//wsl.localhost/Ubuntu-26.04/home/hao/QuizletFPGA status --short
git -c safe.directory=//wsl.localhost/Ubuntu-26.04/home/hao/QuizletFPGA diff --check
git -c safe.directory=//wsl.localhost/Ubuntu-26.04/home/hao/QuizletFPGA diff -- README.md PROJECT_BRIEF.md docs/human_review.md
Get-Content docs/lut_optimization_study.md
git -c safe.directory=//wsl.localhost/Ubuntu-26.04/home/hao/QuizletFPGA add -- README.md PROJECT_BRIEF.md docs/human_review.md docs/lut_optimization_study.md results/area_20261003T192105403559Z
git -c safe.directory=//wsl.localhost/Ubuntu-26.04/home/hao/QuizletFPGA commit -m "Measure and validate reduced-LUT trading core candidates"
git -c safe.directory=//wsl.localhost/Ubuntu-26.04/home/hao/QuizletFPGA push
```
'''
p.write_text(s,encoding='utf-8',newline='\n')
'@ | & 'C:/Users/Lenovo/AppData/Local/GatorFPGA/python_env/bin/python.exe' -
@'
from pathlib import Path
import hashlib,json,sys
from datetime import datetime,timezone
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from capture_vector_stress import validate_inputs

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
context=read(OUT/'context.json');summary=read(OUT/'study_summary.json')
checks={'checked_utc':datetime.now(timezone.utc).isoformat()}
assert summary['best_luts']==230 and not summary['global_minimum_proved']
assert summary['bitstream_sha256']=='f33a5f114d87616951c13435718ed73c124a23b2a02452ec93f26593e1278bf8'
validate_inputs(ROOT/'bitstream/trade_core.fs',OUT/'baseline/build_summary.json',ROOT)
assert sha(ROOT/'bitstream/trade_core.fs')==context['release_sha256']=='bc7edc25e995168772989e199c9cd43252f6120bec68e21fba034c8a35d4313d'
for relative,digest in context['baseline_source_sha256'].items():assert sha(ROOT/relative)==digest
checks['live_release_source_and_bitstream_unchanged']=True
for path in (OUT/'verification_source').rglob('*'):
    if path.is_file():assert sha(path)==sha(ROOT/path.relative_to(OUT/'verification_source'))
checks['organizer_tests_reference_and_original_benches_unchanged']=True
assert len(summary['candidates'])==17
for c in summary['candidates']:
    folder=OUT/c['name'];metadata=read(folder/'build_summary.json')
    validate_inputs(folder/'candidate.fs',folder/'build_summary.json',folder/'source')
    assert sha(Path(metadata['native_root'])/'.build/gowin_trade/trade_core/impl/pnr/trade_core.fs')==metadata['bitstream_sha256']
    assert metadata['pins']==read(OUT/'baseline/build_summary.json')['pins']
    assert metadata['pnr']['setup_violations']==metadata['pnr']['hold_violations']==0
    assert metadata['physical_validation'] is False
    assert all('PASS ' in test['result'] for test in metadata['simulation'])
    for rel in ['constraints/19_tang_nano_20k.cst','gowin/build_uart.tcl','gowin/uart.sdc']:
        assert sha(folder/'source'/rel)==context['baseline_source_sha256'][rel]
checks['seventeen_candidate_sources_files_tests_pins_and_timing_validated']=True
best=read(OUT/'carry_direct_equality/expanded_validation.json');other=read(OUT/'expanded_validation.json')
assert best['all_passed'] and other['all_passed']
assert best['checks'][-1]['packets']==1509 and 'PASS top_sessions_tb: 1509' in best['checks'][-1]['result']
for prefix in ['engine_batch_','top_batch_']:
    assert sum(c['packets'] for c in best['checks'] if c['test'].startswith(prefix))==13508
assert all('PASS ' in c['result'] for c in best['checks']+other['checks'])
manifest=read(OUT/'expanded_vectors/manifest.json')
for name,digest in manifest['files_sha256'].items():assert sha(OUT/'expanded_vectors'/name)==digest
assert len(manifest['sessions'])==31
checks['expanded_corpus_and_both_final_full_speed_candidates_passed']=True
checks['best_candidate_physical_validation']=False
checks['physical_after_latency_available']=False
checks['lowest_luts']=230
checks['alternative_luts']=234
checks['all_checks_passed']=True
(OUT/'final_checks.json').write_text(json.dumps(checks,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(checks,indent=2))
