"""Run the additional and full-speed data against one identified area candidate."""
from pathlib import Path
import importlib.util,json,sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
spec=importlib.util.spec_from_file_location('area_runner',OUT/'run_experiments.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
from capture_vector_stress import validate_inputs

def main():
    name=sys.argv[1];folder=OUT/name;build=json.loads((folder/'build_summary.json').read_text(encoding='utf-8'))
    validate_inputs(folder/'candidate.fs',folder/'build_summary.json',folder/'source')
    native=Path(build['native_root']);context=json.loads((OUT/'context.json').read_text(encoding='utf-8'))
    vectors=json.loads((OUT/'expanded_vectors/manifest.json').read_text(encoding='utf-8'))
    report={'scope':'Additional and physical-timing simulations; no board programming','candidate':name,'candidate_luts':build['synthesis']['LUT'],'bitstream_sha256':build['bitstream_sha256'],'expanded_packets':vectors['packets'],'expanded_sessions':len(vectors['sessions']),'checks':[],'all_passed':False,'status':'running'}
    path=folder/'expanded_validation.json';runner.save(path,report)
    for label,bench in [('engine','trade_pair_tb'),('top','top_sessions_tb')]:
        output=native/('expanded_'+label+'.vvp')
        runner.run([runner.IVERILOG,'-g2012','-Wall','-s',bench,'-o',output,*sorted((native/'src').glob('*.v')),native/'testbench'/(bench+'.v')],native,folder/(label+'_expanded_compile.log'))
        for batch in vectors['batches']:
            text=runner.run([runner.VVP,output,'+COUNT='+str(batch['packets']),'+VECTORS=../expanded_vectors/'+batch['name']+'_packets.mem','+STATES=../expanded_vectors/'+batch['name']+'_states.mem'],native,folder/(label+'_'+batch['name']+'.log'),timeout=900)
            assert 'PASS ' in text
            report['checks'].append({'test':label+'_'+batch['name'],'packets':batch['packets'],'result':text.strip()});runner.save(path,report)
        print('PASS '+name+' '+label+' '+str(vectors['packets'])+' additional packets',flush=True)
    output=native/'actual_uart_timing.vvp'
    runner.run([runner.IVERILOG,'-g2012','-Wall','-DBOARD_TIMING','-s','top_sessions_tb','-o',output,*sorted((native/'src').glob('*.v')),native/'testbench/top_sessions_tb.v'],native,folder/'actual_uart_timing_compile.log')
    text=runner.run([runner.VVP,output,'+COUNT=1509','+VECTORS=../vectors/packets.mem'],native,folder/'actual_uart_timing.log',timeout=1200)
    assert 'PASS ' in text and '1509 packets' in text
    report['checks'].append({'test':'actual_27MHz_115200_baud','packets':1509,'result':text.strip()})
    validate_inputs(folder/'candidate.fs',folder/'build_summary.json',folder/'source')
    validate_inputs(ROOT/'bitstream/trade_core.fs',OUT/'baseline/build_summary.json',ROOT)
    assert runner.sha(ROOT/'bitstream/trade_core.fs')==context['release_sha256']
    report.update(all_passed=True,status='passed',release_unchanged=True)
    runner.save(path,report);print('PASS identified candidate expanded and full-speed validation',flush=True)
if __name__=='__main__':main()
