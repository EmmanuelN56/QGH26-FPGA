"""Verify recovered candidate files and simulation benches without opening serial."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from capture_vector_stress import validate_inputs
AREA=ROOT/'results/area_20261003T192105403559Z'
TOOLS=Path('C:/Users/Lenovo/AppData/Local/GatorFPGA/iverilog/bin')

def write(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')

def verify(name,board_count):
    folder=AREA/name
    metadata=json.loads((folder/'build_summary.json').read_text(encoding='utf-8'))
    validate_inputs(folder/'candidate.fs',folder/'build_summary.json',folder/'source')
    corpus=json.loads((AREA/'expanded_vectors/manifest.json').read_text(encoding='utf-8'))
    out=folder/'recovery_simulation';out.mkdir(exist_ok=False)
    work=ROOT/'.build/recovered_candidate_sim'/name;work.mkdir(parents=True,exist_ok=True)
    report={'scope':'Fresh Windows simulations after source recovery; no physical board testing','checked_utc':datetime.now(timezone.utc).isoformat(),'candidate':name,'bitstream_sha256':metadata['bitstream_sha256'],'original_packets':1509,'expanded_packets':corpus['packets'],'actual_uart_timing_packets':board_count,'checks':[],'all_passed':False,'physical_validation':False}
    write(out/'validation.json',report)
    sources=sorted((folder/'source/src').glob('*.v'))
    def run(command,label,timeout=900):
        log=out/(label+'.log')
        with log.open('w',encoding='utf-8') as stream:
            stream.write(subprocess.list2cmdline([str(x) for x in command])+'\n');stream.flush()
            proc=subprocess.run([str(x) for x in command],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
        text=log.read_text(encoding='utf-8',errors='replace')
        if proc.returncode:raise RuntimeError(f'{name}: {label} failed: {log}')
        return text
    for bench in ['uart_rx_tb','uart_tx_tb','top_tb','trade_pair_tb','top_sessions_tb']:
        source=folder/'verification_source/testbench'/(bench+'.v')
        output=work/(bench+'.vvp')
        run([TOOLS/'iverilog.exe','-g2012','-Wall','-s',bench,'-o',output,*sources,source],bench+'_compile')
        cases=[('original',['+COUNT=1509','+VECTORS='+str(ROOT/'testbench/vectors/packets.mem'),'+STATES='+str(ROOT/'testbench/vectors/states.mem')])] if bench in ['trade_pair_tb','top_sessions_tb'] else [('unit',[])]
        if bench in ['trade_pair_tb','top_sessions_tb']:
            cases += [(batch['name'],['+COUNT='+str(batch['packets']),'+VECTORS='+str(AREA/'expanded_vectors'/(batch['name']+'_packets.mem')),'+STATES='+str(AREA/'expanded_vectors'/(batch['name']+'_states.mem'))]) for batch in corpus['batches']]
        for label,arguments in cases:
            result=run([TOOLS/'vvp.exe',output,*arguments],bench+'_'+label)
            if 'PASS ' not in result:raise RuntimeError('Missing PASS: '+bench+' '+label)
            report['checks'].append({'test':bench,'case':label,'result':result.strip()});write(out/'validation.json',report)
        print('PASS '+name+' '+bench,flush=True)
    output=work/'top_sessions_tb_board.vvp'
    run([TOOLS/'iverilog.exe','-g2012','-Wall','-DBOARD_TIMING','-s','top_sessions_tb','-o',output,*sources,folder/'verification_source/testbench/top_sessions_tb.v'],'actual_uart_compile')
    # Use an exact-count subset to avoid readmemh range warnings.
    subset=work/'actual_uart_packets.mem'
    subset.write_text('\n'.join((ROOT/'testbench/vectors/packets.mem').read_text().splitlines()[:board_count])+'\n',encoding='utf-8')
    result=run([TOOLS/'vvp.exe',output,'+COUNT='+str(board_count),'+VECTORS='+str(subset)],'actual_uart_timing')
    assert 'PASS ' in result
    report['checks'].append({'test':'actual_27MHz_115200_baud','packets':board_count,'result':result.strip()})
    validate_inputs(folder/'candidate.fs',folder/'build_summary.json',folder/'source')
    report.update(all_passed=True,status='passed');write(out/'validation.json',report)
    metadata['simulation']=report['checks'];metadata['status']='recovered_build_and_fresh_simulations_passed_awaiting_physical_validation'
    metadata['recovery']['fresh_validation']='recovery_simulation/validation.json';write(folder/'build_summary.json',metadata)
    print('PASS '+name+' full recovery validation',flush=True)
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--board-packets',type=int,default=3,help='Actual UART timing simulation count; no board access')
    args=parser.parse_args()
    if not 1<=args.board_packets<=1509:parser.error('board-packets must be 1..1509')
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures=[executor.submit(verify,name,args.board_packets) for name in ['carry_direct_equality','carry_uart_pointer']]
        reports=[future.result() for future in futures]
    write(ROOT/'results/recovery_candidate_validation.json',{'scope':'Fresh simulations following recovery, no physical board validation','all_passed':all(report['all_passed'] for report in reports),'candidates':reports})
if __name__=='__main__':main()
