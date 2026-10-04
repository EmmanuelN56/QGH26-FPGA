# Human release and Git review

The current source and programmed board are the final **186 Logic / 92 registers /
4 B-SRAM** candidate. Its exact tested .fs is
`physical_final_best_five_runs/programmed.fs`, SHA-256 `6fbefe4697c714b18f78830088c826b2f7cc1e2823de0070a688c84f3f6a6e23`.

The existing `bitstream/trade_core.fs` remains the saved 236-Logic release, hash
`cd708e137d143bdf52ca2ea6fe5ede4e09f18ba7849cd643ac7a7b0d5641c6e2`. The [optimizer skill](../../SKILL.md) explicitly assigns
promotion to the human: “the human copies the `.fs` and updates the hash in
`README.md` and `bitstream/README.md`.” Both replacement README files have already
been prepared with the correct measurements and hash. Review them, then copy
the three exact files below before staging or submitting the current source.

```powershell
git status --short
git diff --check
git diff
Get-Content results/logic_search_20261003/ready_release/README.md
Get-Content results/logic_search_20261003/ready_release/bitstream_README.md
Get-FileHash results/logic_search_20261003/physical_final_best_five_runs/programmed.fs -Algorithm SHA256
Copy-Item -LiteralPath results/logic_search_20261003/physical_final_best_five_runs/programmed.fs -Destination bitstream/trade_core.fs -Force
Copy-Item -LiteralPath results/logic_search_20261003/ready_release/README.md -Destination README.md -Force
Copy-Item -LiteralPath results/logic_search_20261003/ready_release/bitstream_README.md -Destination bitstream/README.md -Force
Get-FileHash bitstream/trade_core.fs -Algorithm SHA256
git diff --check
git diff
git add -- README.md PROJECT_BRIEF.md bitstream/README.md bitstream/trade_core.fs src/top.v src/packet_controller.v src/trade_engine.v src/uart_rx.v src/uart_tx.v scripts/22_robust_uart_test_fullrange.py scripts/generate_vectors.py scripts/run_regression.py scripts/fpgaopt.py scripts/clear_gowin_build_readonly.ps1 scripts/measure_logic_candidate.py scripts/save_logic_measurement.py scripts/qualify_candidate.py scripts/run_extensive_regression.py scripts/stress_board_vectors.py testbench/top_recovery_tb.v testbench/vectors/packets.mem testbench/vectors/states.mem testbench/vectors/vectors.json testbench/vectors/extensive docs/official/SCORING_AND_RANKING_CLARIFICATION.md results/optimization_log.csv results/software_validation.json results/simulation.log results/optimization_20261003 results/logic_search_20261003
git commit -m "Reduce FPGA logic and extend full-range validation"
git push
```

All stage paths are explicit. Changed HDL: top, UART RX/TX, packet controller and
shared trade_pair/digit-cell file. Added/updated tests include full-range organizer
original, vectors, recovery bench, model/regression and build/board evidence
helpers. Updated docs describe ranking and final measurements. The regression
rewrites software_validation.json, simulation.log and session vectors.

Pre-existing `scripts/capture_board_tests.py` changes and
`outputs/zip_judge_review_20261003/` are excluded from the stage command. Existing
untracked SKILL.md is unchanged. Inspect those separately if the team wants them.
No Git history, remote action or release-file promotion has been performed.
