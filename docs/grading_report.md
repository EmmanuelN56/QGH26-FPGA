# Qualification, ranking and current evidence

The organizer [scoring and ranking clarification](official/SCORING_AND_RANKING_CLARIFICATION.md)
supplements the Participant Guide. Qualification requires **100/100 on the
normal official judge run** and a following hidden full-range 0..65535 run
with every packet/action correct and no timeouts. The second run follows without
reprogramming and does not rescore latency or LUTs. A normal-run latency-tier miss
may receive one judge rerun. Nonqualifiers rank below every qualifier by rubric score.

Qualified designs rank by **lowest total Logic**, then total registers, then
median latency over five runs (within 5% tied). Judges rebuild committed source
with Gowin V1.9.11.03 and the committed project settings, and check behavior
against the submitted .fs. B-SRAM is permitted and excluded from Logic. Local
counts below are provisional; only the judge rebuild determines placement.

## Corrected resource comparison

These values are the complete vendor summary rows, not sums of hierarchy cells.

| Candidate | Primitive LUTs | Synthesis Logic | Registers | B-SRAM | Routed Logic |
| --- | ---: | ---: | ---: | ---: | ---: |
| context_ram | 271 | **312** | **179** | 1 | 316 |
| carry_uart_pointer | 234 | 354 | 222 | 0 | 360 |
| carry_direct_equality | 230 | 382 | 222 | 0 | 392 |

The ranking audit reads all 17 recovered candidates. context_ram has the lowest
synthesis Logic among them. It uses 42 fewer logic units than the 234-LUT design
and 70 fewer than the 230-LUT design. Prioritize its physical qualification.
Earlier 314/342 figures were incomplete: eight distributed RAM16 blocks add more
than eight units to Gowin's Logic total. The context RAM summary includes 272
LUTs although the primitive LUT row is 271. Read the total Logic row directly;
synthesis and routed totals are different and must be labeled separately.

Primary source paths and exact rows are saved in
`results/fullrange_20261003_ranking/ranking_audit.json`.
No source, bitstream or vendor report was edited by this validation.

## Organizer practice test and fresh simulation

Preserved attachment: `scripts/22_robust_uart_test_fullrange.py`.
It is byte-for-byte identical to the supplied Downloads file; PORT remains COM6.
SHA-256: `73295ff02aa06bac869f2c9c5c6ad6f244084b514f697846c176bc4c2ff2fc9c`.
Change **only PORT** in a physical-run copy. The organizer practice seed is
`0x1F00D16B`; the hidden seed is unknown. This is a full-price-range test with
100 packets, rather than a higher packet count than the normal robust test.

The new `scripts/verify_fullrange_candidates.py` loads only the reviewed
pre-transmission model/vector definitions. It never executes the serial loops.
The independent model agrees with all generated organizer responses.
Fresh evidence is under `results/fullrange_20261003_ranking/`:

- All three candidates passed 4,176 packets in their paired-engine/state benches.
- All three passed the same 4,176 complete UART transactions in accelerated timing.
- All three passed the exact normal 100-packet practice run followed by the exact
  full-range 100-packet practice run at 27 MHz / 115200-baud simulation timing.
- No reset occurs between runs inside a sequence; the new index-zero packet
  clears prior state. All eight reply bytes are checked, including warm-up,
  reserved zeros and slot order; early/extra replies and missing replies fail.
- The corpus includes two normal/full-range pairs plus 3,776 supplementary
  packets: 32 additional seeds, 65535/zero extremes, signed-boundary transitions,
  alternating values, midpoint plateaus and floor-average boundaries.
- Source/build-input hashes and bitstream hashes matched before and after testing.

Each candidate has a validation JSON and raw compile/simulation logs. The shared
manifest records organizer/vector hashes. This is **simulation evidence**. No
serial port was opened or FPGA programmed. Host latency, official qualification,
and hidden-seed correctness have not been established by these tests.

To reproduce, use native Python/Icarus and a fresh output directory:

```powershell
& 'C:\Users\Lenovo\AppData\Local\GatorFPGA\python_env\bin\python.exe' .\scripts\verify_fullrange_candidates.py
```

## Physical comparison handoff

For each identified candidate, program its matching .fs in volatile SRAM mode
only after the required explicit programming authorization. Preserve its Git
commit, eight build-input hashes, resource reports and .fs SHA-256.

Run the unchanged normal robust practice script, then immediately the unchanged
full-range practice script without reprogramming or resetting the board. Change
only PORT in isolated physical-run copies. Retain both CSVs, summaries and console
logs in a new directory for each attempt. Independently check all 100 rows,
including the warm-up fields which the organizer practice score ignores. A
70/70 practice correctness summary does not establish official 100/100.

Collect five complete normal/full-range pairs per candidate using identical board
and host settings. Save all normal-run per-packet latency values, plus mean and
median for each run, so judges can apply their median-over-five convention.
No exact aggregation or relative-5% formula beyond the announcement is assumed.
Latency is still necessary for qualification, and only breaks ranking ties after
both total Logic and registers tie. Do not reduce price or sum widths.

context_ram bitstream SHA-256:
`825bf4d70b30f3ed7f01a09e725d65304f37f7b26c551289ea06fd13b947ef8d`.
No physical validation of this candidate is recorded.

## Historical evidence limitation

Earlier local estimates were 85 supported points plus conditional latency points.
Later physical CSVs were lost with the deleted Ubuntu folder. Earlier published
physical logs/CSVs remain under `results/board_20261003T064213338565Z/`.
The previous full aggregate grading report was not recovered. Neither historical
estimates nor simulations demonstrate qualification for any experimental design.
See [recovery inventory](repository_recovery.md).
