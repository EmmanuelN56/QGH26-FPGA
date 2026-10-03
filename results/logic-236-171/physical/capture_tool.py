"""Capture a specifically authorized SRAM candidate and unchanged practice tests.

Default mode validates source/bitstream identity only. --program accesses hardware;
run it only after authorization for the exact --expected-hash candidate.
"""
import argparse,csv,hashlib,json,re,shutil,statistics,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate',default='digit_w1_compact_output_phase')
    p.add_argument('--expected-hash',required=True)
    p.add_argument('--program',action='store_true')
    p.add_argument('--skip-expanded',action='store_true',help='Run only quick plus five unchanged normal/full-range pairs')
    p.add_argument('--port',default='COM4');p.add_argument('--board',default='2025030317')
    p.add_argument('--location',type=int,default=561)
    p.add_argument('--programmer',type=Path,default=Path(r'C:/Gowin/Gowin_V1.9.11.03_Education_x64/Programmer/bin/programmer_cli.exe'))
    p.add_argument('--python-deps',type=Path,default=Path(r'C:/Users/Duke/Documents/ChatGPT/GatorHacks FPGA/.build/python_deps'))
    p.add_argument('--output',type=Path)
    a=p.parse_args();folder=ROOT/'experiments'/a.candidate;fs=folder/'candidate.fs'
    m=json.loads((folder/'measurement.json').read_text())
    if digest(fs)!=a.expected_hash or a.expected_hash!=m['bitstream_sha256']:raise ValueError('Exact authorized bitstream hash mismatch')
    for name,sha in m['source_sha256'].items():
        if digest(folder/'source'/name)!=sha:raise ValueError('Source mismatch: '+name)
    vectors=ROOT/'verification/corpora'
    for name,sha in json.loads((vectors/'hashes.json').read_text()).items():
        if digest(vectors/name)!=sha:raise ValueError('Corpus mismatch: '+name)
    print('Validated:',a.candidate,a.expected_hash,flush=True)
    if not a.program:return
    sys.path[:0]=[str(a.python_deps.resolve()),str(ROOT/'verification/reference')]
    import serial
    from serial.tools import list_ports
    from capture_board_tests import review_csv
    from reference_model import ReferenceModel
    ports=[{'device':x.device,'description':x.description,'hwid':x.hwid} for x in list_ports.comports()]
    if not any(x['device']==a.port and a.board in x['hwid'] for x in ports):raise ValueError('Selected board identity is absent on UART port')
    out=(a.output or ROOT/'physical'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')).resolve()
    out.mkdir(parents=True,exist_ok=False)
    shutil.copytree(folder/'source',out/'source');shutil.copyfile(fs,out/'programmed.fs');shutil.copyfile(folder/'measurement.json',out/'build_summary.json')
    command=[str(a.programmer.resolve()),'--device','GW2AR-18C','--operation_index','2','--cable-index','4','--location',str(a.location),'--frequency','2.5MHz','--fsFile',str(out/'programmed.fs')]
    report={'started_utc':datetime.now(timezone.utc).isoformat(),'candidate':a.candidate,'bitstream_sha256':a.expected_hash,
        'source_sha256':m['source_sha256'],'serial_inventory':ports,'board':a.board,'port':a.port,'programming_command':command,
        'programming_mode':'volatile SRAM','no_reprogram_between_tests':True,'manual_reset_between_tests':False,
        'host_settings_changed':False,'tests':[],'all_passed':False,'official_qualification':False,'hidden_seed_tested':False}
    def save():(out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    with (out/'programming.log').open('w') as f:pr=subprocess.run(command,cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=90)
    text=(out/'programming.log').read_text(errors='replace')
    if pr.returncode or 'Operation "SRAM Program"' not in text or 'Finished.' not in text:raise RuntimeError('Programming failed; inspect retained log')
    report['programming_passed']=True;save();print('SRAM programming PASS',flush=True)
    schedule=[('quick','21_quick_uart_test.py')]
    for i in range(1,6):schedule.extend([(f'normal_{i}','22_robust_uart_test.py'),(f'fullrange_{i}','22_robust_uart_test_fullrange.py')])
    for label,name in schedule:
        d=out/label;d.mkdir();original=(ROOT/'verification/reference'/name).read_bytes()
        changed,n=re.subn(rb'^PORT = "COM6"',f'PORT = "{a.port}"'.encode(),original,flags=re.M)
        if n!=1:raise ValueError('Unexpected organizer PORT setting')
        test=d/name;test.write_bytes(changed)
        loader='import sys,runpy;sys.path.insert(0,sys.argv[1]);runpy.run_path(sys.argv[2],run_name="__main__")'
        with (d/'console.log').open('w',encoding='utf-8') as f:
            proc=subprocess.run([sys.executable,'-u','-c',loader,str(a.python_deps.resolve()),str(test)],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=150)
        console=(d/'console.log').read_text(errors='replace')
        r={'name':label,'script_sha256':digest(test),'original_sha256':hashlib.sha256(original).hexdigest(),'port_only_change':True,'exit_code':proc.returncode}
        if label=='quick':r['passed']=proc.returncode==0 and 'PASS' in console.splitlines()
        else:
            suffix='_fullrange' if label.startswith('fullrange') else ''
            csv_path=d/f'trade_results_100{suffix}.csv';r['latency_us']=review_csv(csv_path)
            with csv_path.open(newline='') as f:rows=list(csv.DictReader(f))
            r['latency_us']['median']=statistics.median(float(x['latency_us']) for x in rows)
            summary=(d/f'trade_summary_100{suffix}.txt').read_text()
            r['passed']=proc.returncode==0 and all(x in summary.splitlines() for x in ('Packets successfully received: 100','Correct packets: 84','Correct individual actions: 168/168','Timeouts: 0'))
        report['tests'].append(r);save();print(label,'PASS' if r['passed'] else 'FAIL',flush=True)
        if not r['passed']:raise RuntimeError(label+' failed; keep all evidence')
    for kind in ('normal','fullrange'):
        runs=[r['latency_us'] for r in report['tests'] if r['name'].startswith(kind)]
        report[kind+'_latency_us']={'mean':statistics.mean(x['mean'] for x in runs),'median_of_five_run_means':statistics.median(x['mean'] for x in runs),
            'median_of_five_run_medians':statistics.median(x['median'] for x in runs),'max':max(x['max'] for x in runs)}
    save()
    if a.skip_expanded:
        report['expanded_physical_suite']='Excluded from this run by user instruction'
        report['all_passed']=True;report['completed_utc']=datetime.now(timezone.utc).isoformat();save()
        print('PASS quick + five normal/full-range pairs; expanded suite excluded; evidence:',out,flush=True)
        return
    with serial.Serial(a.port,115200,timeout=1.0) as port,(out/'expanded.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['corpus','ordinal','tx_hex','expected_rx_hex','rx_hex','elapsed_us','status']);writer.writeheader()
        time.sleep(0.2)
        if port.in_waiting:raise RuntimeError('Unsolicited data before expanded suite')
        count=0
        for corpus in ('qualification_sequence','fullrange_edges','original','expanded'):
            model=ReferenceModel()
            for ordinal,row in enumerate((vectors/(corpus+'_packets.mem')).read_text().splitlines()):
                raw=bytes.fromhex(row);tx,expected=raw[:8],raw[8:]
                if model.process(tx)!=expected:raise ValueError('Independent reference mismatch')
                start=time.perf_counter_ns();sent=port.write(tx);rx=port.read(8);elapsed=(time.perf_counter_ns()-start)/1000
                passed=sent==8 and rx==expected and not port.in_waiting
                writer.writerow({'corpus':corpus,'ordinal':ordinal,'tx_hex':tx.hex(),'expected_rx_hex':expected.hex(),'rx_hex':rx.hex(),'elapsed_us':f'{elapsed:.3f}','status':'PASS' if passed else 'FAIL'});f.flush()
                if not passed:raise RuntimeError(f'Expanded mismatch/timeout/extra data {corpus} {ordinal}')
                count+=1
                if count%1000==0:print('Expanded packets',count,flush=True)
        time.sleep(0.2)
        if port.in_waiting:raise RuntimeError('Extra data after expanded suite')
    report['expanded_packets']=count;report['all_passed']=True;report['completed_utc']=datetime.now(timezone.utc).isoformat();save()
    print('PASS quick + five normal/full-range pairs +',count,'expanded packets; evidence:',out,flush=True)
if __name__=='__main__':main()
