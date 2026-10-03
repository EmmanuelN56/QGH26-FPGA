"""Compare reviewed baseline and minimum-gap FPGA at the active approved COM4 timer."""
import argparse, hashlib, json, shutil, subprocess, sys, winreg
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from capture_vector_stress import validate_inputs

def save(p,v): p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--timer-ms',type=int,choices=[1,2,16],required=True); args=ap.parse_args()
    keypath=r'SYSTEM\CurrentControlSet\Enum\FTDIBUS\VID_0403+PID_6010+2025030317B\0000\Device Parameters'
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,keypath) as key:
        timer=winreg.QueryValueEx(key,'LatencyTimer')[0]; port=winreg.QueryValueEx(key,'PortName')[0]
    assert port=='COM4' and timer==args.timer_ms
    review=json.loads((ROOT/'results/latency_audit_20261003/review.json').read_text())
    minimum=next(c for c in review['candidates'] if c['name']=='gap_0cycles')
    original=ROOT/'results/build_windows_20261003'
    candidate=ROOT/minimum['evidence_directory']
    entries=[('baseline',ROOT/'bitstream/trade_core.fs',original/'build_summary.json',original/'source',review['baseline_sha256']),
             ('gap_0cycles',candidate/'candidate.fs',candidate/'build_summary.json',candidate/'source',minimum['bitstream_sha256'])]
    for _,fs,summary,source,expected in entries:
        validate_inputs(fs,summary,source); assert sha(fs)==expected
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=ROOT/'results'/('latency_host_'+stamp); out.mkdir()
    native=Path('C:/Users/Lenovo/AppData/Local/GatorFPGA')/('latency_host_'+stamp); native.mkdir(); native=native.resolve()
    shutil.copyfile(Path(__file__),out/'run_host_compare.py')
    previous=json.loads((ROOT/'results/latency_physical_20261003T174553624297Z/manifest.json').read_text())
    setting_dir=Path(previous['native_work'])
    for name in ['set_com4_latency.ps1','original_latency_setting.json',f'set_latency_{timer}.json']:
        shutil.copyfile(setting_dir/name,out/name)
    programmer=Path('C:/Users/Lenovo/AppData/Local/GatorFPGA/gowin/extracted/Gowin_V1.9.11.03_Education_x64/Programmer/bin/programmer_cli.exe')
    context={'port':'COM4','board_serial':'2025030317','host_latency_timer_ms':timer,'registry_path':keypath}
    report={'scope':'Physical FPGA comparison at separately authorized host receive timer','context':context,'status':'running','runs':[]}
    save(out/'manifest.json',report); print('HOST '+str(timer)+'ms evidence: '+str(out),flush=True)
    def run(command,log,cwd=ROOT,timeout=240):
        with log.open('w',encoding='utf-8',newline='\n') as stream:
            stream.write(subprocess.list2cmdline([str(c) for c in command])+'\n'); stream.flush()
            p=subprocess.run([str(c) for c in command],cwd=cwd,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
        return p.returncode,log.read_text(encoding='utf-8',errors='replace')
    try:
        for label,fs,summary,source,expected in entries:
            directory=out/label; directory.mkdir(); localfs=native/(label+'.fs'); shutil.copyfile(fs,localfs); assert sha(localfs)==expected
            item={'name':label,'bitstream_sha256':expected,'status':'programming'}; report['runs'].append(item); save(out/'manifest.json',report)
            code,text=run([programmer,'--device','GW2AR-18C','--operation_index','2','--cable-index','4','--location','561','--frequency','2.5MHz','--fsFile',localfs],directory/'programming.log',cwd=native,timeout=60)
            assert code==0 and 'Operation "SRAM Program"' in text and 'Finished.' in text and '0x0000081B' in text
            item['programming_passed']=True
            print(label+': SRAM programmed; organizer+stress at timer='+str(timer)+'ms',flush=True)
            before=set((ROOT/'results').glob('board_*'))
            code,_=run([sys.executable,'-B',ROOT/'scripts/capture_board_tests.py','--port','COM4','--board','USB-debugger-2025030317','--bitstream',fs,'--runs','3','--source-root',source,'--build-summary',summary,'--programming-log',directory/'programming.log'],directory/'organizer_capture.log')
            created=set((ROOT/'results').glob('board_*'))-before; assert len(created)==1; d=created.pop()
            capture=json.loads((d/'manifest.json').read_text()); save(d/'host_context.json',context)
            item.update(organizer_directory=d.relative_to(ROOT).as_posix(),organizer_passed=code==0 and capture['all_passed'],organizer_tests=capture['tests'])
            tests=[t['physical_latency_us'] for t in capture['tests'] if 'physical_latency_us' in t]
            if tests:
                item.update(organizer_mean_us=sum(t['mean']*t['successful_packets'] for t in tests)/sum(t['successful_packets'] for t in tests),organizer_max_us=max(t['max'] for t in tests))
            save(out/'manifest.json',report)
            before=set((ROOT/'results').glob('stress_*'))
            code,_=run([sys.executable,'-B',ROOT/'scripts/capture_vector_stress.py','--port','COM4','--board','USB-debugger-2025030317','--bitstream',fs,'--source-root',source,'--build-summary',summary],directory/'stress_capture.log')
            created=set((ROOT/'results').glob('stress_*'))-before; assert len(created)==1; d=created.pop()
            stress=json.loads((d/'manifest.json').read_text()); save(d/'host_context.json',context); shutil.copyfile(directory/'programming.log',d/'programming.log')
            item.update(stress_directory=d.relative_to(ROOT).as_posix(),stress_passed=code==0 and stress['all_passed'],stress_correct_packets=stress.get('correct_packets',0),stress_latency_us=stress.get('physical_latency_us'))
            item['status']='passed' if item['organizer_passed'] and item['stress_passed'] else 'failed'
            save(out/'manifest.json',report)
            print(label+': '+item['status'].upper()+'; organizer mean/max us='+str(item.get('organizer_mean_us'))+'/'+str(item.get('organizer_max_us'))+'; stress='+str(item['stress_correct_packets'])+'/1509',flush=True)
        report['status']='completed'
    except BaseException as error:
        report.update(status='failed',error=str(error)); raise
    finally: save(out/'manifest.json',report)
    print('COMPLETE host='+str(timer)+'ms; evidence: '+str(out),flush=True)
if __name__=='__main__': main()
