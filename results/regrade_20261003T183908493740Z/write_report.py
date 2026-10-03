"""Publish the checked grade and latest validation status into project docs."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
def write(path,text):
    path.write_text(text,encoding='utf-8',newline='\n')
def main():
    r=json.loads((OUT/'grade.json').read_text())
    assert r['all_passed']
    original=r['original_baseline']; previous=r['previous_optimized_run']; fresh=r['fresh_run']
    stress=r['fresh_stress']; before=r['baseline_build']; after=r['release_build']
    outcome='lower' if fresh['mean_ms']<previous['mean_ms'] else 'higher' if fresh['mean_ms']>previous['mean_ms'] else 'equal'
    estimate=', '.join(str(v['estimated_total']) for v in r['per_run_estimates'])
    board=fresh['directory']; stress_dir=stress['directory']; evidence=OUT.relative_to(ROOT).as_posix()
    text=f'''# Organizer rubric and release revalidation

Validation completed {r['completed_utc']}. The release source and programmed
bitstream match the last optimized release. No new RTL optimization was made.

## Grade

The fresh local evidence supports 85 points: 50 packet, 20 action and 15 LUT.
Using the published 16.626 ms reference as an estimate, the three fresh robust
runs score {estimate} points out of 100. This is not an official award: the
organizers compare latency with their reference on the same judging PC and
use an unpublished price seed. The corresponding conditional totals are
85, 93 or 100 for zero, eight or fifteen latency points, assuming the same
correctness and synthesis results during judging.

| Criterion | Fresh evidence per robust run | Locally supported points |
| --- | --- | ---: |
| Packet correctness | 84/84 scored packets, all response fields correct | 50/50 |
| Action correctness | 168/168 scored actions | 20/20 |
| Synthesis LUT usage | 365 total LUTs; reference 542 | 15/15 |
| Mean latency | See each run below; same-PC reference still required | Pending /15 |

The denominators remain 84 packets and 168 actions even if a timeout ends a
run early. At least 80 correct packets are required to retain latency and LUT
points. Warm-up indices 0–15 are excluded from correctness scoring but included
in mean latency. A complete response must arrive within one second. Every
fresh robust run returned all 100 responses, with zero timeouts. The independent
CSV review also checked every warm-up response.

The formulas are `50 * correct_packets / 84`, `20 * correct_actions / 168`,
and `15 * min(1, 542 / total_synthesis_LUTs)`. Latency earns 15 points at or
below 1.25 times the same-PC reference, eight at or below twice that reference,
and zero above it. Published thresholds are exactly 20.7825 and 33.252 ms.
The original 412-LUT baseline also earned full LUT points; resource savings
below 542 do not earn additional points.

| Fresh organizer run | Correct packets | Correct actions | Mean ms | Maximum ms |
| --- | ---: | ---: | ---: | ---: |
'''
    for t in fresh['runs']:
        text+=f"| {t['name']} | 84/84 | 168/168 | {t['mean_ms']:.6f} | {t['max_ms']:.4f} |\n"
    text+=f'''
## Comparison with saved runs

| Measurement | Original 1 ms gap baseline | Previous optimized release | Fresh optimized release |
| --- | ---: | ---: | ---: |
| Organizer packet/action accuracy | 100% / 100% | 100% / 100% | 100% / 100% |
| Organizer mean across 300 responses, ms | {original['mean_ms']:.6f} | {previous['mean_ms']:.6f} | {fresh['mean_ms']:.6f} |
| Organizer maximum, ms | {original['max_ms']:.4f} | {previous['max_ms']:.4f} | {fresh['max_ms']:.4f} |
| Total synthesis LUTs | 412 | 365 | 365 |
| Registers | 328 | 296 | 296 |
| B-SRAM / SSRAM blocks | 0 / 8 | 0 / 8 | 0 / 8 |
| Routed Fmax, MHz | 77.985 | 75.176 | 75.176 |
| Setup / hold slack, ns | +24.214 / +0.425 | +23.735 / +0.425 | +23.735 / +0.425 |
| Setup / hold violations | 0 / 0 | 0 / 0 | 0 / 0 |
| Full-speed UART simulation packets | 221 | 221 | 1509 |
| Supplementary physical responses | Not in original capture | 1509/1509 | 1509/1509 |

The fresh organizer mean is {outcome} than the previous optimized run by
{abs(r['fresh_mean_change_vs_previous_ms']):.6f} ms. The RTL and bitstream are
unchanged, so this difference is a host measurement, not evidence of a new
FPGA improvement. Fresh mean latency is {r['fresh_mean_reduction_vs_original_percent']:.3f}%
lower than the original baseline; the prior sweep showed host variability,
so these captures alone do not establish a repeatable percentage gain.

The verified implementation improvements over the original baseline remain:
47 fewer LUTs (11.408%), 32 fewer registers (9.756%), and removal of the seven
configured 1 ms response gaps. Full-system simulation measures
{r['simulation_roundtrip_ms']['original_baseline_range'][0]:.6f} ms before and
{r['simulation_roundtrip_ms']['current_range'][0]:.6f} ms after. These simulation
measurements stop at the final stop-bit center, include a deliberate two-bit
pause before the last request byte, and exclude USB and host overhead. Fmax
and setup slack decreased slightly but still exceed the 27 MHz requirement.
PR1014 remains documented.

## Expanded organizer-derived verification

The independent model agrees byte-for-byte with reference classes extracted
from both unchanged organizer scripts. The deterministic corpus contains
1,509 packets across 15 sessions: quick, practice robust, repeated robust
without reset, equality/held-action boundaries, floor division boundaries,
maximum unsigned rolling sum, zero prices immediately after maximum prices,
and eight random full-range unsigned-16-bit seeds. The 300-packet seed covers
indices above 255. Slot swaps and index-zero session clearing are exercised.
This corpus is unchanged from the prior optimized capture.

Fresh native Windows Icarus checks passed RX 260 bytes, TX 256 bytes, smoke
three packets, isolated engines 1,509 packets with state checks, accelerated
full system 1,509 packets, and actual 27 MHz / 115200-baud full system all
1,509 packets. Full-speed coverage increased from 221 to 1,509 packets
({1509/221:.3f} times). The first full-speed attempt exceeded the runner's
300-second wall limit without reporting an HDL assertion failure. A new
`--simulation-timeout` option retains the 300-second default; the same full
suite passed with an explicit 900-second limit. The timed-out evidence is kept.

Fresh SRAM programming at JTAG location 561 confirmed device ID 0x0000081B.
Organizer quick plus three robust sessions passed. Then all {stress['verified_packets']}
expanded physical responses matched every byte, across {stress['sessions']} sessions
without reprogramming or reset between sessions; zero timeouts and extra bytes.
Supplementary mean/max latency is {stress['mean_ms']:.6f}/{stress['max_ms']:.4f} ms;
previous supplementary mean/max was {r['previous_stress']['mean_ms']:.6f}/{r['previous_stress']['max_ms']:.4f} ms.
These different traffic statistics do not enter the organizer score. COM4's
original receive timer remained 16 ms before and after the fresh run.

The unchanged CST, fixed pins, packet format, state routing, floor averages,
held actions and index-zero clear order remain associated with the verified
release build. All official decision logic executes on the FPGA. The host
scripts provide test stimulus and validation only.

## Evidence and remaining submission work

- Fresh audit, grade JSON, previous results, simulator logs, programming log and reproducible runners: `{evidence}/`.
- Fresh organizer console logs, three CSVs, summaries, source snapshot and programmed file: `{board}/`.
- Fresh expanded physical CSV, source/test snapshot and programmed file: `{stress_dir}/`.
- Matching release build/resource/timing reports: `results/release_zero_gap_20261003T180901633856Z/`.
- Original baseline: `{original['directory']}/` and `results/build_windows_20261003/`.
- Previous optimized organizer/stress: `{previous['directory']}/` and `{r['previous_stress']['directory']}/`.

Tested file: `bitstream/trade_core.fs`, SHA-256
`{r['bitstream_sha256']}`.
The archived release summary has a stale
`matches_reviewed_authorized_zero_gap_bitstream=false` field referring to the
raw clean rebuild. Independent comparison confirms the retained release matches
the approved hash; the raw rebuild differs only in its `//Created Time` comment.
Frozen evidence was preserved. The fresh grade JSON records this distinction.

The current organizer rubric downloaded for this audit exactly matches the
archived copy (SHA-256 `{r['rubric_local_sha256']}`).
[Organizer judging rules](https://github.com/ShayanNazir/GQH-Hardware-Track-Submission/blob/main/JUDGING_AND_TESTING.md),
[archived participant guide](official/GQH_Hardware_Track_Participant_Guide.pdf)
(section 11 takes precedence), and unchanged organizer tests are the sources.

Human team names/contact, borrowed-board asset confirmation, public repository
access, review/commit/push, final full SHA and Devpost submission remain required.
This local program grade does not confirm submission eligibility. The bridge
warning remains relevant: the tiny remaining idle passed this connected board,
but a separate BL616 bridge and the judging PC have not been validated.
Use [human review commands](human_review.md) to review and freeze the release.
'''
    write(ROOT/'docs/grading_report.md',text)
    brief=ROOT/'PROJECT_BRIEF.md'; s=brief.read_text()
    s=s.replace('and 221 complete transactions at the actual 27 MHz / 115200-baud timing (quick plus two robust sessions).','and 1,509 complete transactions at the actual 27 MHz / 115200-baud timing across all 15 expanded sessions.')
    s=s.replace('/27MHz top221 all PASS','/27MHz top1509 all PASS')
    note=f'Fresh organizer-rubric revalidation: quick + three robust runs PASS, all300 CSV rows verified, organizer mean/max{fresh["mean_ms"]:.6f}/{fresh["max_ms"]:.4f} ms; expanded physical1509/1509 across15 sessions PASS; COM4 timer16ms unchanged; local evidence supports85 points plus conditional0/8/15 latency points; see docs/grading_report.md and {evidence}/\n'
    s=s.replace('Known blockers: human metadata/Git review',note+'Known blockers: human metadata/Git review',1)
    write(brief,s)
    readme=ROOT/'README.md'; s=readme.read_text()
    marker='Team members/contact: TODO'
    note=f'Latest revalidation expanded actual UART-timing simulation to all 1,509 packets; fresh organizer quick/three robust runs and all 1,509 physical stress packets passed. Fresh organizer mean/max: {fresh["mean_ms"]:.6f}/{fresh["max_ms"]:.4f} ms. Local rubric evidence supports 85 points plus conditional latency points; see [grading and comparison](docs/grading_report.md).\n\n'
    s=s.replace(marker,note+marker,1); write(readme,s)
    human=ROOT/'docs/human_review.md'; s=human.read_text()
    s=s.replace("    'docs/latency_optimization.md',","    'docs/latency_optimization.md',\n    'docs/grading_report.md',",1)
    s+=f'\nLatest organizer-rubric revalidation and comparison: `docs/grading_report.md`; fresh saved evidence: `{evidence}/`, `{board}/`, and `{stress_dir}/`. The review path list includes the report, configurable simulation timeout and saved results.\n'
    write(human,s)
    print('Updated grading report, README, project status and human review path list')
if __name__=='__main__':
    main()
