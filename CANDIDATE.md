# 234-LUT physical-test candidate

Branch: codex/lut-234
Source: src/ (matches the archived candidate source exactly)
Bitstream: bitstream/trade_core.fs
Build identity: bitstream/build_summary.json
SHA-256: ea5279614794fc79c7f3632b429584b29a3cb7c0fdb80811f3e4b95ef2cb8d4a
Resources: 234 LUTs, 222 registers, 72 ALUs, 314 reported logic units, 0 B-SRAM, 8 SSRAM.
Evidence: results/area_20261003T192105403559Z/carry_uart_pointer/
Fresh expanded simulation evidence: results/area_20261003T192105403559Z/carry_uart_pointer/recovery_simulation/validation.json
Combined comparison evidence: results/recovery_candidate_validation.json

The exact source and bitstream were recovered from native Windows build copies.
Fresh recovery simulations are in the candidate recovery_simulation/ directory.
Synthesis/routing passed. Physical validation is pending.
The paired engine is tested by testbench/trade_pair_tb.v. The legacy standalone
engine remains in the source for compatibility; testing that legacy module alone
does not validate the shared candidate datapath. Include full-system tests.

Add the expanded physical suite to this branch, program the identified bitstream
in volatile SRAM mode, and save logs/CSVs with the branch commit and this SHA-256.
Use identical board/host settings when comparing the two branches. After testing,
merge only the selected candidate into main. Historical release documents describe
the archived baseline and must be updated when a new physical release is selected.
