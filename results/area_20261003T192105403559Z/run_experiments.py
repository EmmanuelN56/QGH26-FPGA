"""Native isolated area experiments; no programming, serial or release edits."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import prepare_latency_sweep as vendor_report
from prepare_latency_sweep import BUILD_FILES

def metrics(impl):
    original_number=vendor_report.number
    summary=vendor_report.plain(impl / "gwsynthesis/trade_core_syn.rpt.html")
    def reported_number(pattern,text,cast=int):
        if pattern==r"\bSSRAM (\d+)" and "SSRAM" not in summary:
            import xml.etree.ElementTree as ET
            tree=ET.parse(impl / "gwsynthesis/trade_core_syn_rsc.xml").getroot()
            assert "T_Ssram" not in tree.attrib
            return 0
        return original_number(pattern,text,cast)
    vendor_report.number=reported_number
    try:
        result=vendor_report.metrics(impl)
    finally:
        vendor_report.number=original_number
    result["zero_ssram_source"]="omitted unused resource row and absent hierarchy cell count" if result["synthesis"]["SSRAM"]==0 else None
    return result
from capture_vector_stress import validate_inputs
from generate_vectors import generate
TOOLS=Path('C:/Users/Lenovo/AppData/Local/GatorFPGA')
GOWIN=TOOLS/'gowin/extracted/Gowin_V1.9.11.03_Education_x64/IDE/bin/gw_sh.exe'
IVERILOG=TOOLS/'iverilog/bin/iverilog.exe';VVP=TOOLS/'iverilog/bin/vvp.exe'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
def run(cmd,cwd,log,env=None,timeout=300):
    with log.open('w',encoding='utf-8',newline='\n') as f:
        f.write(subprocess.list2cmdline([str(x) for x in cmd])+'\n');f.flush()
        p=subprocess.run([str(x) for x in cmd],cwd=cwd,stdout=f,stderr=subprocess.STDOUT,env=env,timeout=timeout)
    text=log.read_text(encoding='utf-8',errors='replace')
    if p.returncode:raise RuntimeError(f'Exit {p.returncode}: {log}')
    return text

def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('names',nargs='*',default=['logical_clear','compact_packet','compact_logical'])
    args=parser.parse_args()
    context=json.loads((OUT/'context.json').read_text(encoding='utf-8'))
    validate_inputs(ROOT/'bitstream/trade_core.fs',OUT/'baseline/build_summary.json',ROOT)
    software=json.loads((ROOT/'results/software_validation.json').read_text(encoding='utf-8'))
    assert software['all_passed'], 'Validated reference regression required before experiments'
    work=Path(context['native_root']).resolve();work.mkdir(parents=True,exist_ok=True)
    vectors=work/'vectors';vectors.mkdir(exist_ok=True)
    vector_manifest=generate(vectors)
    (vectors/'board.mem').write_text('\n'.join((vectors/'packets.mem').read_text().splitlines()[:221])+'\n',encoding='utf-8',newline='\n')
    if not (OUT/'verification_source').exists():
        shutil.copytree(ROOT/'testbench',OUT/'verification_source/testbench')
        for name in ['generate_vectors.py','reference_model.py','prepare_latency_sweep.py','21_quick_uart_test.py','22_robust_uart_test.py']:
            dest=OUT/'verification_source/scripts'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'scripts'/name,dest)
    context.setdefault('candidates',[]);save(OUT/'context.json',context)
    for name in args.names:
        assert name not in [v['name'] for v in context['candidates']], 'Use unique fresh names'
        native=work/name;out=OUT/name;native.mkdir();out.mkdir()
        item={'name':name,'status':'running','native_root':str(native),'physical_validation':False,'physical_latency':None}
        context['candidates'].append(item);save(OUT/'context.json',context)
        for folder in ['src','constraints','gowin']:
            shutil.copytree(OUT/'baseline/source'/folder,native/folder)
        shutil.copytree(ROOT/'testbench',native/'testbench')
        if name in ('compact_packet','compact_logical'):
            shutil.copyfile(OUT/'prototypes/compact_packet_controller.v',native/'src/packet_controller.v')
        if name in ('logical_clear','compact_logical'):
            shutil.copyfile(OUT/'prototypes/logical_trade_engine.v',native/'src/trade_engine.v')
        # A named custom prototype can replace any subset of the five source files.
        custom=OUT/'prototypes'/name
        if custom.is_dir():
            for file in custom.glob('*.v'):shutil.copyfile(file,native/'src'/file.name)
        sources=sorted((native/'src').glob('*.v'))
        try:
            checks=[]
            tests=[('trade_engine_tb',[],['+COUNT=1509','+VECTORS=../vectors/packets.mem','+STATES=../vectors/states.mem']),
                   ('top_tb',[],[]),('top_sessions_tb',[],['+COUNT=1509','+VECTORS=../vectors/packets.mem']),
                   ('top_sessions_tb',['-DBOARD_TIMING'],['+COUNT=221','+VECTORS=../vectors/board.mem'])]
            for bench,defines,extra in tests:
                label=bench+('_board' if defines else '')
                output=native/(label+'.vvp')
                run([IVERILOG,'-g2012','-Wall',*defines,'-s',bench,'-o',output,*sources,native/'testbench'/(bench+'.v')],native,out/(label+'_compile.log'))
                text=run([VVP,output,*extra],native,out/(label+'.log'),timeout=900 if defines else 300)
                if 'PASS ' not in text:raise RuntimeError('No PASS marker: '+label)
                checks.append({'test':label,'result':text.strip()})
            item['simulation']=checks;save(OUT/'context.json',context)
            print('PASS simulations '+name+'; building synthesis/PnR',flush=True)
            env=os.environ.copy();env['UART_BUILD_FLOW']='all'
            text=run([GOWIN,native/'gowin/build_uart.tcl'],native,out/'build.log',env,timeout=600)
            if 'Bitstream generation completed' not in text:raise RuntimeError('Missing complete bitstream')
            impl=native/'.build/gowin_trade/trade_core/impl'
            item.update(metrics(impl))
            item.update(target='GW2AR-LV18QN88C8/I7',device_version='C',top='top',
                        source_sha256={f:sha(native/f) for f in BUILD_FILES},bitstream_sha256=sha(impl/'pnr/trade_core.fs'))
            for f in BUILD_FILES:
                dest=out/'source'/f;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(native/f,dest)
            for file in impl.rglob('*'):
                if file.is_file() and file.suffix in ('.html','.txt','.log','.xml'):
                    dest=out/'reports'/file.relative_to(impl);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,dest)
            shutil.copyfile(impl/'pnr/trade_core.fs',out/'candidate.fs')
            item['status']='simulation_and_build_passed_awaiting_physical_validation'
            save(out/'build_summary.json',item)
            print('READY '+name+' '+json.dumps({'synthesis':item['synthesis'],'pnr':item['pnr']}),flush=True)
        except Exception as exc:
            item.update(status='failed',error=str(exc));print('FAILED '+name+': '+str(exc),flush=True)
        save(OUT/'context.json',context)
    assert sha(ROOT/'bitstream/trade_core.fs')==context['release_sha256']
    assert all(sha(ROOT/f)==h for f,h in context['baseline_source_sha256'].items())
    context['release_unchanged']=True;context['status']='area_experiments_recorded';save(OUT/'context.json',context)
    print('COMPLETE isolated experiments; release unchanged; '+str(OUT),flush=True)
if __name__=='__main__':main()
