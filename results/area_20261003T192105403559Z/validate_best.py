"""Validate baseline and smallest measured candidate on additional data."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
spec=importlib.util.spec_from_file_location('area_runner',OUT/'run_experiments.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
from capture_vector_stress import validate_inputs

def main():
    context=json.loads((OUT/'context.json').read_text(encoding='utf-8'))
    candidates=[json.loads(p.read_text(encoding='utf-8')) for p in OUT.glob('*/build_summary.json') if p.parent.name!='baseline']
    best=min(candidates,key=lambda c:c['synthesis']['LUT'])
    folder=OUT/best['name'];native=Path(best['native_root'])
    validate_inputs(folder/'candidate.fs',folder/'build_summary.json',folder/'source')
    vector_info=json.loads((OUT/'expanded_vectors/manifest.json').read_text(encoding='utf-8'))
    work=Path(context['native_root']).resolve();vectors=work/'expanded_vectors'
    shutil.copytree(OUT/'expanded_vectors',vectors)
    baseline=work/'baseline_expanded';baseline.mkdir()
    shutil.copytree(OUT/'baseline/source/src',baseline/'src');shutil.copytree(ROOT/'testbench',baseline/'testbench')
    report={'scope':'Additional simulations; not physical validation','best_candidate':best['name'],'baseline_luts':365,'candidate_luts':best['synthesis']['LUT'],'expanded_packets_per_design':vector_info['packets'],'expanded_sessions':len(vector_info['sessions']),'checks':[],'status':'running','all_passed':False,'release_unchanged':True}
    runner.save(OUT/'expanded_validation.json',report)
    for label,source,bench in [('baseline_engine',baseline,'trade_engine_tb'),('baseline_top',baseline,'top_sessions_tb'),('candidate_engine',native,'trade_pair_tb'),('candidate_top',native,'top_sessions_tb')]:
        output=source/(label+'.vvp');sources=sorted((source/'src').glob('*.v'))
        runner.run([runner.IVERILOG,'-g2012','-Wall','-s',bench,'-o',output,*sources,source/'testbench'/(bench+'.v')],source,OUT/(label+'_compile.log'))
        for batch in vector_info['batches']:
            name=label+'_'+batch['name']
            text=runner.run([runner.VVP,output,'+COUNT='+str(batch['packets']),'+VECTORS=../expanded_vectors/'+batch['name']+'_packets.mem','+STATES=../expanded_vectors/'+batch['name']+'_states.mem'],source,OUT/(name+'.log'),timeout=900)
            assert 'PASS ' in text
            report['checks'].append({'test':name,'packets':batch['packets'],'result':text.strip()});runner.save(OUT/'expanded_validation.json',report)
        print('PASS '+label+': '+str(vector_info['packets'])+' additional packets',flush=True)
    # Repeat all original vectors at actual board UART timing for the smallest candidate.
    output=native/'full_board_timing.vvp'
    runner.run([runner.IVERILOG,'-g2012','-Wall','-DBOARD_TIMING','-s','top_sessions_tb','-o',output,*sorted((native/'src').glob('*.v')),native/'testbench/top_sessions_tb.v'],native,OUT/'full_board_timing_compile.log')
    text=runner.run([runner.VVP,output,'+COUNT=1509','+VECTORS=../vectors/packets.mem'],native,OUT/'full_board_timing.log',timeout=900)
    assert 'PASS ' in text and '1509 packets' in text
    report['checks'].append({'test':'candidate_actual_27MHz_115200_baud','packets':1509,'result':text.strip()})
    validate_inputs(folder/'candidate.fs',folder/'build_summary.json',folder/'source')
    validate_inputs(ROOT/'bitstream/trade_core.fs',OUT/'baseline/build_summary.json',ROOT)
    assert runner.sha(ROOT/'bitstream/trade_core.fs')==context['release_sha256']
    report.update(status='passed',all_passed=True,candidate_bitstream_sha256=best['bitstream_sha256'])
    runner.save(OUT/'expanded_validation.json',report)
    print('PASS expanded baseline/candidate tests and all1509 full-speed candidate transactions',flush=True)
if __name__=='__main__':main()
