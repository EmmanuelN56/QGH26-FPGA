"""Independently recheck saved responses and apply the organizer rubric."""
from pathlib import Path
from datetime import datetime, timezone
import csv, hashlib, json, re, sys
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from capture_board_tests import review_csv, port_copy
from capture_vector_stress import validate_inputs, load_vectors
from reference_model import ReferenceModel

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
def board(folder):
    manifest=read(folder/'manifest.json')
    assert manifest['all_passed'] and len(manifest['tests'])==4
    tests=[]
    for item in manifest['tests']:
        label=item['name']; source='21_quick_uart_test.py' if label=='quick' else '22_robust_uart_test.py'
        original=(ROOT/'scripts'/source)
        assert (folder/label/source).read_text()==port_copy(original,'COM4'), 'Organizer test changed beyond PORT'
        assert sha(folder/'source/scripts'/source)==sha(original)
        assert item['passed'] and item['exit_code']==0
        if label=='quick':
            assert 'PASS' in (folder/label/'console.log').read_text().splitlines()
            continue
        latency=review_csv(folder/label/'trade_results_100.csv')
        tests.append({'name':label,'scored_packets':84,'correct_packets':84,'scored_actions':168,'correct_actions':168,'timeouts':0,'all_100_rows_verified':True,'mean_ms':latency['mean']/1000,'max_ms':latency['max']/1000})
    return {'directory':folder.relative_to(ROOT).as_posix(),'bitstream_sha256':manifest['bitstream_sha256'],'runs':tests,'mean_ms':sum(t['mean_ms'] for t in tests)/len(tests),'max_ms':max(t['max_ms'] for t in tests),'csv_rows_verified':len(tests)*100}
def stress(folder):
    manifest=read(folder/'manifest.json')
    assert manifest['all_passed'] and manifest['timeouts']==0 and manifest['unsolicited_bytes']==0
    packets,vectors=load_vectors()
    with (folder/'packets.csv').open(newline='') as stream:
        rows=list(csv.DictReader(stream))
    assert len(rows)==len(packets)==1509
    model=ReferenceModel()
    times=[]
    for row,wanted in zip(rows,packets):
        assert row['event']=='transaction' and row['status']=='PASS' and int(row['write_count'])==8
        for key in ('packet_ordinal','session_number','packet_index'):
            assert int(row[key])==wanted[key]
        for key in ('session_name','tx_hex','expected_rx_hex'):
            assert row[key]==wanted[key]
        assert bytes.fromhex(row['rx_hex'])==model.process(bytes.fromhex(row['tx_hex']))==bytes.fromhex(wanted['expected_rx_hex'])
        times.append(float(row['elapsed_us'])/1000)
    return {'directory':folder.relative_to(ROOT).as_posix(),'verified_packets':len(rows),'sessions':len(vectors['sessions']),'timeouts':0,'extra_bytes':0,'mean_ms':sum(times)/len(times),'max_ms':max(times),'min_ms':min(times)}
def main():
    context=read(OUT/'context.json'); physical=read(OUT/'physical_context.json')
    assert physical['status']=='passed'
    build_dir=ROOT/context['release_directory']; build=read(build_dir/'build_summary.json')
    validate_inputs(ROOT/'bitstream/trade_core.fs',build_dir/'build_summary.json',ROOT)
    software=read(OUT/'software_validation.json'); previous=read(OUT/'previous_software_validation.json')
    assert software['all_passed'] and len(software['checks'])==6 and '1509 packets' in software['checks'][-1]['result']
    assert '221 packets' in previous['checks'][-1]['result']
    assert all(software['source_sha256'][name.replace('/','\\')]==expected for name,expected in build['source_sha256'].items() if name.startswith('src/'))
    assert all(sha(ROOT/name)==expected for name,expected in build['source_sha256'].items())
    original=board(ROOT/context['original_baseline_directory'])
    last=board(ROOT/context['previous_organizer_directory'])
    latest=board(ROOT/physical['organizer_directory'])
    old_stress=stress(ROOT/context['previous_stress_directory'])
    new_stress=stress(ROOT/physical['stress_directory'])
    for directory in (physical['organizer_directory'],physical['stress_directory']):
        folder=ROOT/directory
        validate_inputs(folder/'programmed.fs',folder/'build_summary.json',folder/'source')
        assert sha(folder/'programmed.fs')==build['bitstream_sha256']
        assert (folder/'programming.log').read_bytes()==(OUT/'programming.log').read_bytes()
    assert sha(ROOT/'bitstream/trade_core.fs')==last['bitstream_sha256']==latest['bitstream_sha256']
    assert software['vectors']==previous['vectors'], 'Corpus must match for repeat comparison'
    for name in ('host_before.json','host_after.json'):
        assert read(OUT/name)['com4_latency_timer_ms']==16
    xml=(build_dir/'reports/gwsynthesis/trade_core_syn_rsc.xml').read_text()
    assert 'T_Lut="365(0)"' in xml and 'T_Register="296(2)"' in xml and 'T_Ssram="8(0)"' in xml
    html=(build_dir/'reports/gwsynthesis/trade_core_syn.rpt.html').read_text()
    assert re.search(r'<b>LUT\s*</b></td>\s*<td>365</td>',html)
    raw_dir=ROOT/build['raw_rebuild_directory']
    candidates=list(raw_dir.rglob('*.fs'))
    raw=next(p for p in candidates if sha(p)==build['raw_rebuild_bitstream_sha256'])
    final=ROOT/'bitstream/trade_core.fs'
    a=final.read_bytes().splitlines(); b=raw.read_bytes().splitlines()
    differences=[(x,y) for x,y in zip(a,b) if x!=y]
    assert len(a)==len(b) and len(differences)==1 and all(x.startswith(b'//Created Time:') and y.startswith(b'//Created Time:') for x,y in differences)
    estimate=[]
    for run in latest['runs']:
        points=15 if run['mean_ms']<=1.25*16.626 else 8 if run['mean_ms']<=2*16.626 else 0
        estimate.append({'run':run['name'],'packet_points':50,'action_points':20,'lut_points':15*min(1,542/build['synthesis']['LUT']),'latency_points_using_published_reference':points,'estimated_total':85+points})
    baseline_build=read(ROOT/'results/build_windows_20261003/build_summary.json')
    baseline_sim=(ROOT/'results/latency_audit_20261003/baseline/simulation.log').read_text()
    timing_regex=r'roundtrip_ns=([0-9.]+)\.\.([0-9.]+)'
    baseline_wire=[float(x)/1e6 for x in re.search(timing_regex,baseline_sim).groups()]
    latest_wire=[float(x)/1e6 for x in re.search(timing_regex,software['checks'][-1]['result']).groups()]
    report={'completed_utc':datetime.now(timezone.utc).isoformat(),'all_passed':True,'official_score':None,
        'rubric_url':'https://github.com/ShayanNazir/GQH-Hardware-Track-Submission/blob/main/JUDGING_AND_TESTING.md',
        'rubric_authority':'Participant guide section 11 takes precedence; matches current organizer web page',
        'rubric_local_sha256':sha(ROOT/'docs/official/JUDGING_AND_TESTING.md'),
        'locally_supported_points':85,'conditional_totals':[85,93,100],
        'published_reference_latency_ms':16.626,'published_latency_thresholds_ms':[20.7825,33.252],
        'published_reference_luts':542,'correctness_gate_min_packets':80,'practice_seed':'0x57214720',
        'official_seed':'Unpublished; not tested','judging_pc_reference_measured_here':False,
        'per_run_estimates':estimate,'source_unchanged_since_last_release':True,
        'bitstream_sha256':sha(final),'baseline_build':{'synthesis':baseline_build['synthesis'],'pnr':baseline_build['pnr']},
        'release_build':{'synthesis':build['synthesis'],'pnr':build['pnr'],'pins':build['pins'],'warnings':build['warnings']},
        'original_baseline':original,'previous_optimized_run':last,'fresh_run':latest,
        'fresh_mean_change_vs_previous_ms':latest['mean_ms']-last['mean_ms'],
        'fresh_mean_reduction_vs_previous_percent':100*(last['mean_ms']-latest['mean_ms'])/last['mean_ms'],
        'fresh_mean_reduction_vs_original_percent':100*(original['mean_ms']-latest['mean_ms'])/original['mean_ms'],
        'previous_stress':old_stress,'fresh_stress':new_stress,
        'board_timing_coverage':{'previous_packets':221,'fresh_packets':1509,'sessions':15,'factor':1509/221},
        'simulation_roundtrip_ms':{'original_baseline_range':baseline_wire,'current_range':latest_wire,'measurement':'stop-bit center; includes deliberate 2-bit request pause, excludes USB/host'},
        'simulation_initial_attempt':'300-second runner wall timeout; no assertion failure reported; rerun with --simulation-timeout 900',
        'metadata_review':{'stale_original_field':'matches_reviewed_authorized_zero_gap_bitstream=false describes the raw rebuild, not the retained release',
            'retained_release_matches_authorized_hash':True,'raw_rebuild_matches_release_file':False,'only_difference_created_time_comment':True,'frozen_evidence_unchanged':True},
        'limitations':['No new RTL optimization since last run; host timing differences are descriptive, not proof of further FPGA improvement.',
            'Original and optimized designs already fit the full LUT and published latency tiers; better measurements do not add rubric points above their caps.',
            'PR1014 remains; positive internal timing margin at 27 MHz.',
            'Tiny remaining response-frame idle passed this board; no separate BL616 bridge or judging-PC validation.',
            'Human team metadata, public repository, Git freeze and Devpost submission remain required.']}
    current_rubric=OUT/'organizer_current.md'
    if current_rubric.exists():
        report['rubric_current_sha256']=sha(current_rubric)
        report['rubric_current_matches_archived']=current_rubric.read_text().replace('\r\n','\n')==(ROOT/'docs/official/JUDGING_AND_TESTING.md').read_text().replace('\r\n','\n')
        assert report['rubric_current_matches_archived']
    save(OUT/'grade.json',report)
    context.update(status='passed',completed_utc=report['completed_utc'],grade='grade.json')
    save(OUT/'context.json',context)
    print(json.dumps({key:report[key] for key in ('locally_supported_points','conditional_totals','per_run_estimates','fresh_run','fresh_mean_reduction_vs_previous_percent','fresh_stress','board_timing_coverage')},indent=2))
if __name__=='__main__':
    main()
