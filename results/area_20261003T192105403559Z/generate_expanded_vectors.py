"""Additional deterministic area-validation data; official test files stay unchanged."""
from pathlib import Path
import hashlib,json,random,sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from generate_vectors import organizer_reference
from reference_model import ReferenceModel,REQUEST,RESPONSE,ITEM_A,ITEM_B,NONE

def main():
    directory=OUT/'expanded_vectors';directory.mkdir()
    classes=[organizer_reference('21_quick_uart_test.py','Reference'),organizer_reference('22_robust_uart_test.py','MovingAverageReference')]
    n=512;edge=[0,1,15,16,17,255,256,257,32767,32768,65534,65535]
    patterns=[
      ('constant_extremes',[0]*n,[65535]*n),
      ('constant_midpoint',[32768]*n,[32768]*n),
      ('ascending_descending',[i*127 for i in range(n)],[65535-i*127 for i in range(n)]),
      ('square_16',[65535 if i//16%2 else 0 for i in range(n)],[0 if i//16%2 else 65535 for i in range(n)]),
      ('impulses',[65535 if i%17==0 else 0 for i in range(n)],[0 if i%19==0 else 65535 for i in range(n)]),
      ('sawtooth',[i%31*2114 for i in range(n)],[i%19*3640 for i in range(n)]),
      ('field_boundaries',[edge[i%len(edge)] for i in range(n)],[edge[(i*5+3)%len(edge)] for i in range(n)]),
      ('held_plateaus',[[100,200,0][i//32%3] for i in range(n)],[[300,0,400][i//23%3] for i in range(n)]),
      ('floor_small_values',[i%17 for i in range(n)],[15-i%16 for i in range(n)]),
      ('midpoint_noise',[32768+(i%3)-1 for i in range(n)],[32768+(i*7%5)-2 for i in range(n)]),
    ]
    for seed in range(16):
        rng=random.Random(0xA2340000+seed)
        limit=101 if seed<4 else 65536
        patterns.append((f'random_{seed}_range_{limit}',[rng.randrange(limit) for _ in range(n)],[rng.randrange(limit) for _ in range(n)]))
    index_values=[16,255,256,257,511,512,32767,32768,65534,65535]
    patterns.append(('index_echo_edges',[i*1031 for i in range(64)],[65535-i*1029 for i in range(64)]))
    for k,length in enumerate([17,33,17,65]):
        patterns.append((f'early_session_reset_{k}',[65535 if k%2 else 0]*length,[k*177]*length))
    model=ReferenceModel();packets=[];states=[];sessions=[];batches=[];batch=[];batch_states=[];batch_sessions=[]
    def flush():
        if not batch:return
        label=f'batch_{len(batches)}'
        for suffix,lines in [('packets',batch),('states',batch_states)]:
            (directory/f'{label}_{suffix}.mem').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
        batches.append({'name':label,'packets':len(batch),'sessions':list(batch_sessions)})
        batch.clear();batch_states.clear();batch_sessions.clear()
    for number,(name,a,b) in enumerate(patterns):
        if len(batch)+len(a)>4096:flush()
        refs=[{ITEM_A:cls(),ITEM_B:cls()} for cls in classes]
        start=len(packets);swaps=random.Random(0x4000+number)
        for i,(pa,pb) in enumerate(zip(a,b)):
            index=i if name!='index_echo_edges' or i<16 else index_values[(i-16)%len(index_values)]
            swapped=bool(swaps.getrandbits(1))
            slots=(ITEM_B,pb,ITEM_A,pa) if swapped else (ITEM_A,pa,ITEM_B,pb)
            tx=REQUEST.pack(index,*slots);rx=model.process(tx)
            for oracle in refs:
                aa,ab=oracle[ITEM_A].process(pa),oracle[ITEM_B].process(pb)
                aa=NONE if aa is None else aa;ab=NONE if ab is None else ab
                assert rx==RESPONSE.pack(index,slots[0],ab if swapped else aa,slots[2],aa if swapped else ab,0)
            sa,sb=model.items[ITEM_A],model.items[ITEM_B]
            state=f'{sa.total:06x}{sb.total:06x}{sa.previous:04x}{sb.previous:04x}{sa.pointer:02x}{sb.pointer:02x}{len(sa.prices):02x}{len(sb.prices):02x}0000'
            packet=tx.hex()+rx.hex();packets.append(packet);states.append(state);batch.append(packet);batch_states.append(state)
        sessions.append({'name':name,'start':start,'packets':len(a)});batch_sessions.append(name)
    flush()
    report={'scope':'Additional deterministic simulation vectors; not official judging seeds','packets':len(packets),'sessions':sessions,'batches':batches,'oracle_classes_agree':True,'organizer_sha256':{name:hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest() for name in ['21_quick_uart_test.py','22_robust_uart_test.py']},'files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.mem')}}
    (directory/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f'PASS expanded model: {len(packets)} packets / {len(sessions)} sessions / {len(batches)} batches agree with both organizer classes')
if __name__=='__main__':main()
