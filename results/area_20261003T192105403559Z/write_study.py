"""Publish measured area limits and validated candidate evidence."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,sys,xml.etree.ElementTree as ET
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from capture_vector_stress import validate_inputs
from prepare_latency_sweep import plain

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,s):p.write_text(s,encoding='utf-8',newline='\n')
def totals(folder):
    text=plain(folder/'reports/gwsynthesis/trade_core_syn.rpt.html')
    xml=ET.parse(folder/'reports/gwsynthesis/trade_core_syn_rsc.xml').getroot()
    match=re.search(r'\bLogic (\d+)\(',text)
    return {'ALU':int(re.match(r'\d+',xml.attrib.get('T_Alu','0')).group()),'logic_units':int(match.group(1)) if match else None,
            'modules':{x.attrib['name']:int(x.attrib.get('Lut','0')) for x in xml if x.tag=='SubModule'}}
def main():
    context=read(OUT/'context.json');baseline=read(OUT/'baseline/build_summary.json')
    baseline_extra=totals(ROOT/'results/release_zero_gap_20261003T180901633856Z')
    rows=[]
    for path in OUT.glob('*/build_summary.json'):
        if path.parent.name=='baseline':continue
        c=read(path);validate_inputs(path.parent/'candidate.fs',path,path.parent/'source')
        assert c['pnr']['setup_violations']==0 and c['pnr']['hold_violations']==0
        rows.append({**c,'other_resources':totals(path.parent),'directory':path.parent.relative_to(ROOT).as_posix()})
    best=min(rows,key=lambda c:c['synthesis']['LUT'])
    expanded=read(OUT/best['name']/'expanded_validation.json')
    reference=read(OUT/'expanded_validation.json')
    assert expanded['all_passed'] and reference['all_passed']
    assert expanded['candidate']==best['name'] and expanded['bitstream_sha256']==best['bitstream_sha256']
    assert expanded['expanded_packets']==13508
    corpus=read(OUT/'expanded_vectors/manifest.json')
    for name,digest in corpus['files_sha256'].items():assert sha(OUT/'expanded_vectors'/name)==digest
    validate_inputs(ROOT/'bitstream/trade_core.fs',OUT/'baseline/build_summary.json',ROOT)
    assert sha(ROOT/'bitstream/trade_core.fs')==context['release_sha256']
    release_grade=read(OUT/'baseline/latest_regrade/grade.json')
    latency=release_grade['fresh_run']
    table=[]
    for c in rows:
        s=c['synthesis'];t=c['pnr'];o=c['other_resources']
        table.append({'name':c['name'],'LUT':s['LUT'],'registers':s['registers'],'ALU':o['ALU'],'logic_units':o['logic_units'],'BSRAM':s['BSRAM'],'SSRAM':s['SSRAM'],'fmax_mhz':t['fmax_mhz'],'setup_ns':t['worst_setup_slack_ns'],'hold_ns':t['worst_hold_slack_ns'],'physical_latency_ms':None})
    bench_text=expanded['checks'][-1]['result']
    simulated=re.search(r'turnaround_ns=([\d.]+)\.\.([\d.]+) roundtrip_ns=([\d.]+)\.\.([\d.]+)',bench_text)
    assert simulated
    report={'completed_utc':datetime.now(timezone.utc).isoformat(),'objective':'Measure LUT reductions well below300; preserve protocol/full-range correctness; rubric is eligibility baseline per human team clarification.',
        'best_measured_candidate':best['name'],'best_luts':best['synthesis']['LUT'],'global_minimum_proved':False,
        'luts_before':365,'luts_removed':365-best['synthesis']['LUT'],'lut_reduction_percent':100*(365-best['synthesis']['LUT'])/365,
        'bitstream_sha256':best['bitstream_sha256'],'candidate_directory':best['directory'],'release_unchanged':True,'release_sha256':context['release_sha256'],
        'physical_validation':False,'physical_latency_before_ms':latency['mean_ms'],'physical_max_before_ms':latency['max_ms'],'physical_latency_after_ms':None,
        'original_corpus_packets':1509,'new_corpus_packets':13508,'new_sessions':len(corpus['sessions']),'original_full_speed_packets':1509,
        'best_build':best,'baseline_build':baseline,'baseline_other_resources':baseline_extra,
        'candidates':table,'simulated_turnaround_ns':[float(simulated[1]),float(simulated[2])],
        'simulated_roundtrip_ms':[float(simulated[3])/1e6,float(simulated[4])/1e6],
        'alternative_fewer_logic_units':next(c for c in table if c['name']=='carry_uart_pointer'),
        'scope_limit':'All candidates assume organizer packets contain exactly one of each fixed item ID; price and index fields retain16 bits.'}
    write(OUT/'study_summary.json',json.dumps(report,indent=2)+'\n')
    lines=['# LUT optimization study','',f"The lowest measured complete design is **{report['best_luts']} LUTs**, compared",
        f"with 365 in the physically tested release: **{report['luts_removed']} fewer LUTs",
        f"({report['lut_reduction_percent']:.3f}%)**. This establishes a feasible synthesis",
        'result, not a mathematical global minimum. No candidate has been programmed','onto the board. The tested release source and bitstream are unchanged.','',
        'The human team clarified that the organizer rubric is the minimum eligibility',
        'bar. The development objective is to reduce LUTs substantially below 300,',
        'remove avoidable duplication, and pass larger datasets with different patterns.',
        'The published score caps are retained as facts, not optimization stopping criteria.','',
        '## Measured candidates','',
        'All successful candidates passed the original 1,509-packet independent-model',
        'and applicable item-state tests, accelerated complete UART transactions,',
        'three board-timing smoke packets and 221 full-speed packets. The smallest',
        'candidate also passed the additional/full-speed checks below. All synthesize',
        'and route for GW2AR-LV18QN88C8/I7 version C, at27 MHz, with the unchanged',
        'organizer CST and all six matching pins. PR1014 remains; no setup/hold',
        'violations were reported. Physical latency after optimization is pending.','',
        '| Candidate | LUTs | Registers | ALUs | B-SRAM / SSRAM | Fmax MHz | Setup / hold ns |',
        '| --- | ---: | ---: | ---: | ---: | ---: | --- |',
        '| Tested release | 365 | 296 | 152 | 0 / 8 | 75.176 | +23.735 / +0.425 |']
    for c in table:
        lines.append(f"| {c['name']} | {c['LUT']} | {c['registers']} | {c['ALU']} | {c['BSRAM']} / {c['SSRAM']} | {c['fmax_mhz']:.3f} | +{c['setup_ns']:.3f} / +{c['hold_ns']:.3f} |")
    lines += ['', 'The two first compact-buffer attempts failed to compile because a missing',
        'space next to a hexadecimal literal changed Verilog tokenization; their logs',
        'remain saved and the corrected v2 builds are shown. The block-RAM build',
        'initially failed report extraction because Gowin omits an unused SSRAM row.',
        'Its simulations and vendor build had passed; the validated parser recovery',
        'and original logs are saved. These failures are not claimed as passing builds.','',
        '## What actually reduced LUTs','',
        '1. **Logical history clear.** Mask old entries until sixteen current-session',
        '   values have overwritten them. Removing physical RAM clearing alone',
        '   reduced365 to325 LUTs without leaking state between sessions.',
        '2. **One request/response buffer.** Receive into a shift register, then',
        '   reuse it after computation for the eight-byte response. Request and',
        '   response storage no longer coexist. Combining this with logical clear',
        '   reached306 LUTs and226 registers.',
        '3. **One strategy datapath for two contexts.** Process the slots on',
        '   successive clocks. Histories, sums, previous prices and held actions',
        '   remain per item; metadata may be shared because each valid request',
        '   always includes both fixed IDs exactly once. Full-width context',
        '   selectors offset much of the initial arithmetic saving.',
        '4. **Explicit unsigned carry-based comparisons.** Use zero-extended',
        '   17-bit subtraction and its borrow bit, preserving equality and strict',
        '   BUY/SELL boundaries. Equivalent RTL forms mapped very differently:',
        '   the initial shared design was302 LUTs; carry comparisons reached248.',
        '5. **Shift UART data rather than indexing individual bits.** Preserve',
        '   start confirmation, center sampling, framing errors, complete stop',
        '   bits and one-clock valid/done pulses. Combining the shifts with the',
        '   carry design reached236 LUTs.',
        '6. **Remove the duplicated fill counter.** Before full, the circular',
        '   pointer supplies the sample count; afterward a single full flag',
        '   represents saturation at sixteen. That reached234 LUTs. Direct',
        '   operand equality alongside carry comparisons reduced it to230.','',
        'The final module costs are RX32, TX33, packet/control59 and strategy106',
        'LUTs. The history RAM already uses dedicated distributed storage. Reducing',
        'window depth, price width or rolling-sum precision would change behavior',
        'and was not used. Response slot order, exact reserved zeros, index-zero',
        'clear-before-ingestion, floor averages and held actions are preserved.','',
        '## LUT minimum versus total resources','',
        'The230-LUT design uses104 ALU cells. The234-LUT alternative uses72 ALU',
        'cells with the same222 registers and0 B-SRAM /8 SSRAM. Gowin reports',
        '342 logic units for230 LUTs, versus314 for234 LUTs and525 for the',
        'release. Thus230 wins on LUT count;234 uses less total logic. The',
        'difference is four LUTs traded for32 additional carry/ALU cells. Both',
        'remain substantially smaller than the current release.','',
        'Moving only history storage to block RAM measured315 LUTs. Putting',
        'history and item context into one synchronous RAM address space measured',
        '271 LUTs,179 registers and one B-SRAM. It reduced registers and improved',
        'Fmax, but its address/microsequence control added LUTs. Removing the',
        'previous-price registers, deriving them from the preceding history entry,',
        'measured245 LUTs and193 registers. A logical redundancy can be cheaper',
        'than the multiplexers/control needed to remove it.','',
        '## Larger test data and full-speed checks','',
        'The additional corpus has13,508 packets across31 sessions and16 new',
        'deterministic random seeds. It includes constant extremes/midpoint,',
        'ascending/descending prices, sixteen-sample square waves, impulses,',
        'sawtooth waves, held-action plateaus, floor boundaries and noise around',
        'the midpoint. Prices cover the entire unsigned16-bit domain, including',
        '65535 and rolling sums approaching1048560. Echo indices include255,',
        '256,32767,32768,65534 and65535. Short repeated sessions exercise',
        'index-zero clearing after previously full/nonzero histories. Both',
        'organizer reference classes agree with the independent model byte-for-byte.',
        'The original release and234-LUT design passed all additional packets in',
        'their item-state and complete-UART benches; the230-LUT design passed',
        'the same13,508 additional packets in its two benches. The corpus was',
        'batched only to respect testbench capacity; no reset occurs between',
        'sessions inside a batch. The official unpublished seed was not tested.','',
        'Both230- and234-LUT candidates passed all original1,509 packets at',
        'actual27 MHz /115200-baud timing, as well as RX260-byte /TX256-byte',
        'unit tests. Candidate timing starts before the first request bit and',
        'ends at the final response stop-bit center; it includes a deliberate',
        'two-bit request pause, and excludes USB/host overhead.',
        f"The230-LUT simulated turnaround is {report['simulated_turnaround_ns'][0]:.3f} ns;",
        f"transaction time is {report['simulated_roundtrip_ms'][0]:.6f} ms, versus",
        '185.190 ns /1.397588 ms for the current release. Sharing adds only two',
        'processing clocks; the complete stop bit and three inter-byte handshake',
        'idle clocks remain. This is a simulation cost, not measured board latency.',
        f"Saved physical baseline mean/max is {latency['mean_ms']:.6f}/{latency['max_ms']:.4f} ms;",
        'after-candidate measurements are unavailable because no new candidate',
        'has been programmed. No physical reliability or host-latency gain is claimed.','',
        '## What to test next to go lower','',
        'Reaching below200 requires at least31 more LUTs beyond the measured230.',
        'There is no evidence yet that200 is an achievable minimum or a hard floor.',
        'Prioritize these experiments, with correctness and synthesis after each:',
        '', '1. **Packet/control logic (59 LUTs):** compare fixed-field capture and',
        '   staged response selection against the reused64-bit buffer. Direct',
        '   response selection already measured worse in this study; a new layout',
        '   must improve the selector/write-enable network, not merely remove registers.',
        '2. **Item-context selectors (within106 LUTs):** try narrower byte/nibble',
        '   transfers and a carefully scheduled shared datapath. Keep the efficient',
        '   carry comparison form. More computation clocks can fit inside UART',
        '   transport time, but the new microcontrol must cost less than the muxes.',
        '3. **Recompute versus cache:** previous prices and rolling sums are',
        '   derivable from the history. Recomputing can remove stored state at the',
        '   cost of more RAM reads and controls. The previous-price experiment',
        '   showed a LUT increase; benchmark a complete schedule before choosing it.',
        '4. **Synthesis encoding/placement:** examine actual FSM and critical-path',
        '   reports after structural changes. Treat small improvements as mapping',
        '   results, with exact tool/source identities, rather than assumed guarantees.','',
        'Integrate only after reviewing a selected candidate and measuring it on',
        'the physical board against the preserved release. Experimental files',
        'retain the old standalone engine for baseline/unit-test compatibility;',
        'it is unreachable from the candidate synthesis top and contributes no',
        'LUTs. Integration should migrate the unit interface and remove that source',
        'duplication. Larger protocol/item/window changes need a new contract; the',
        'current study does not change the fixed UART format or item set.','',
        '## Evidence and reproduction','',
        f"Experiment root: `{OUT.relative_to(ROOT).as_posix()}/`.",
        f"Smallest build/source/reports/file: `{best['directory']}/`.",
        f"Candidate SHA-256: `{best['bitstream_sha256']}`.",
        'Per-candidate build summaries, native source snapshots, compiler/model/UART',
        'logs and resource/timing reports are preserved, along with the release',
        'baseline, larger corpus, generator and validation tools. `study_summary.json`',
        'contains the full comparison and source/file identities. Before rerunning',
        'preparation, use a fresh experiment root; existing evidence is not overwritten.',
        'Native Windows Gowin V1.9.11.03 Education and Icarus12 were used; no',
        'tools, drivers or host settings were changed.',
        '', '[GowinSynthesis guide](https://cdn.gowinsemi.com.cn/SUG550E.pdf)',
        '(RAM templates and memory attributes, sections4.2 and5.16) informed the',
        'RAM experiments. Actual installed-tool reports determine the counts here.',
        'Use [human review commands](human_review.md) to inspect/stage any results.','']
    write(ROOT/'docs/lut_optimization_study.md','\n'.join(lines))
    brief=ROOT/'PROJECT_BRIEF.md';text=brief.read_text(encoding='utf-8')
    marker='## Two-person ownership plan'
    objective='## Optimization objective beyond the rubric\n\nThe human team clarified on2026-10-03 that the rubric is the minimum eligibility bar. The active objective is LUT usage substantially below300, removal of avoidable state/control duplication, and larger deterministic data suites. The lowest measured isolated candidate is230 LUTs /222 registers /104 ALUs /0 B-SRAM /8 SSRAM; the234-LUT alternative uses72 ALUs and less total logic. Both passed original and additional simulations, including all1509 original packets at actual UART timing. The extra corpus has13508 packets across31 sessions. The live source and bc7 release bitstream remain the physically validated365-LUT design; new candidates are unprogrammed. See docs/lut_optimization_study.md and '+OUT.relative_to(ROOT).as_posix()+'/study_summary.json. There is no proof of a global LUT minimum.\n\n'
    assert marker in text;text=text.replace(marker,objective+marker,1)
    text=text.replace('Next smallest task: humans review source/evidence/matching bitstream using docs/human_review.md, supply metadata, commit/push, and record final full SHA in submission','Next smallest task: review230-LUT versus234-LUT area candidates and validate a selected identified bitstream physically before integration; continue LUT reduction experiments listed in docs/lut_optimization_study.md; human metadata/Git/submission freeze remains pending')
    write(brief,text)
    readme=ROOT/'README.md';text=readme.read_text(encoding='utf-8')
    marker='Team members/contact: TODO'
    note='Area research beyond the rubric produced an isolated230-LUT candidate (365-LUT live release), with expanded simulation validation. It is unprogrammed; the matching physical release is unchanged. See [LUT study and remaining reduction targets](docs/lut_optimization_study.md).\n\n'
    write(readme,text.replace(marker,note+marker,1))
    human=ROOT/'docs/human_review.md';text=human.read_text(encoding='utf-8')
    text=text.replace("    'docs/grading_report.md',","    'docs/grading_report.md',\n    'docs/lut_optimization_study.md',",1)
    text+='\nArea-study review: `docs/lut_optimization_study.md` and `'+OUT.relative_to(ROOT).as_posix()+'/`. Candidate files are experimental; `bitstream/trade_core.fs` and live `src/` were preserved. The path list above includes the study and saved evidence.\n'
    write(human,text)
    context.update(status='study_complete_candidates_unprogrammed',lowest_measured_luts=best['synthesis']['LUT'],selected_candidate=best['name'],expanded_validation_passed=True,release_unchanged=True)
    write(OUT/'context.json',json.dumps(context,indent=2)+'\n')
    print(json.dumps({'best_luts':report['best_luts'],'reduction_percent':report['lut_reduction_percent'],'candidate_sha256':best['bitstream_sha256'],'all_new_data_passed':True,'physical_validation':False,'release_unchanged':True},indent=2))
if __name__=='__main__':main()
