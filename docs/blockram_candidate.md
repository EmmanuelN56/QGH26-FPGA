# Block-RAM candidate publication

The frozen test candidate is context_ram: 312 synthesis Logic, 179 registers,
271 LUT primitives (272 in the total resource summary), 40 ALUs and one B-SRAM.
Its routed Logic is 316, Fmax 102.750 MHz, setup/hold slack +27.305/+0.425 ns.
The active source will match the archived build exactly. Physical validation
and qualification remain pending.

Bitstream SHA-256:
825bf4d70b30f3ed7f01a09e725d65304f37f7b26c551289ea06fd13b947ef8d

Branch: codex/logic-312-blockram
Source: src/
Build settings: gowin/build_uart.tcl, gowin/uart.sdc
Pins: constraints/19_tang_nano_20k.cst
Bitstream: bitstream/trade_core.fs
Build/source identity: bitstream/build_summary.json
Archived vendor source/reports: results/area_20261003T192105403559Z/context_ram/
Fresh simulation evidence: results/fullrange_20261003_ranking/context_ram/
Organizer clarification: docs/official/SCORING_AND_RANKING_CLARIFICATION.md

The exact current candidate passed 4,176 packets in paired-engine state and
complete UART benches, plus 200 exact normal->full-range practice packets at
27 MHz / 115200 baud without a reset between runs. Source hashes and bitstream
hash were checked. This is simulation evidence, not physical qualification.

Reproduce the source simulation from the repository root:

```powershell
& 'C:\Users\Lenovo\AppData\Local\GatorFPGA\python_env\bin\python.exe' .\scripts\verify_fullrange_candidates.py --candidates context_ram
```

The paired engine is the active strategy. testbench/trade_pair_tb.v verifies it;
the standalone trade_engine remains for compatibility and does not validate the
shared RAM strategy on its own. Preserve full-system UART testing.

For physical testing, use only the identified .fs after explicit SRAM-programming
authorization. Run the normal organizer suite then the full-range organizer suite
without reprogramming or reset, changing only PORT in physical-run copies. Save
CSV/console logs, source commit and bitstream SHA-256. Qualification requires
100/100 on the official run and a perfect hidden full-range run, with no timeouts.
Judges rebuild committed source/settings and confirm matching .fs behavior.

Further optimization starts from this source and minimizes the complete synthesis
Logic row. Preserve this candidate as the comparison baseline. See
`docs/logic_optimization.md` for the next experiments and evidence requirements.
