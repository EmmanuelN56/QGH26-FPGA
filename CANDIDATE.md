# 230-LUT physical-test candidate

Branch: codex/lut-230
Source: src/ (matches the archived candidate source exactly)
Bitstream: bitstream/trade_core.fs
Build identity: bitstream/build_summary.json
SHA-256: f33a5f114d87616951c13435718ed73c124a23b2a02452ec93f26593e1278bf8
Resources: 230 LUTs, 222 registers, 104 ALUs, 342 reported logic units, 0 B-SRAM, 8 SSRAM.
Evidence: results/area_20261003T192105403559Z/carry_direct_equality/
Fresh expanded simulation evidence: results/area_20261003T192105403559Z/carry_direct_equality/recovery_simulation/validation.json
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
