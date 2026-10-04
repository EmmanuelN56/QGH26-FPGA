# Single strategy digit-width experiment — 2026-10-03

The frozen current design is the best measured result: **236 synthesis Logic cells, 171 registers, 3 B-SRAM blocks**. The single experiment widened `trade_pair`'s arithmetic digit from one bit to two bits. It passed correctness but raised Logic to 248, so it was rejected and the exact frozen `src/`, `gowin/`, and `constraints/` were restored. No HDL change remains.

## Comparison

| Measurement | Baseline W=1 (restored) | Experiment W=2 (rejected) |
|---|---:|---:|
| Regression gate | PASS | PASS |
| Synthesis Logic | 236 | 248 |
| LUT | 232 | 244 |
| ALU | 4 | 4 |
| RAM16 / SSRAM | 0 | 0 |
| Registers | 171 | 170 |
| B-SRAM blocks | 3 | 3 |
| Routed Logic | 237 | 249 |
| Routed Fmax (MHz) | 118.135 | 120.636 |
| Worst reported setup slack (ns) | +28.572 | +28.748 |
| Worst reported hold slack (ns) | +0.425 | +0.341 |
| Setup / hold violated endpoints | 0 / 0 | 0 / 0 |
| Simulated final-byte-to-response-start (µs) | 10.926210 | 5.592738 |
| Simulated full transaction range (ms) | 1.408328959–1.408329134 | 1.402995487–1.402995662 |
| Physical board mean / max latency | Not measured | Not measured |

Logic rose by 12 cells (+5.08%), registers fell by one, and simulated FPGA turnaround fell by 5.333472 µs. Under the skill's Logic-first, register-second comparison, the experiment is WORSE. UART transport and configured byte spacing were unchanged. The baseline already has zero top-level TX gap; this session did not establish its physical reliability.

## Module breakdown

These are **own cells**, so the rows can be summed without double-counting children. The strategy plus its arithmetic child is the largest independent cost center: baseline 118 LUT + 4 ALU = 122 Logic (51.7% of total); experiment 132 LUT + 4 ALU = 136 Logic.

| Instance | Baseline LUT | Experiment LUT | ALU (both) | Baseline registers | Experiment registers | B-SRAM (both) |
|---|---:|---:|---:|---:|---:|---:|
| `top` | 0 | 0 | 0 | 2 | 2 | 0 |
| `top/receiver` | 31 | 31 | 0 | 35 | 35 | 0 |
| `top/packets` | 35 | 34 | 0 | 59 | 59 | 0 |
| `top/packets/strategy` | 108 | 114 | 4 | 52 | 51 | 3 |
| `top/packets/strategy/arithmetic` | 10 | 18 | 0 | 0 | 0 | 0 |
| `top/transmitter` | 48 | 47 | 0 | 23 | 23 | 0 |
| **Total** | **232** | **244** | **4** | **171** | **170** | **3** |

The hypothesis was that reducing digit and address widths would offset widening the arithmetic cell. The strategy instead grew by 14 Logic cells; mapping elsewhere saved two LUTs. Only the `trade_pair` default parameter changed, `W=1` to `W=2`, in `src/trade_engine.v` line 80. Arithmetic remains unsigned with a 20-bit sum and 16-bit prices.

## Correctness and build evidence

Both measurements ran the complete `scripts/run_regression.py` gate before a fresh Gowin synthesis and PnR (`UART_BUILD_FLOW=all`, no cached-project reuse). The independent reference model agrees with both organizer classes for 1,509 packets across 15 sessions. All six HDL checks pass: RX 260 bytes, TX 256 bytes, original top 3 packets, isolated engines 1,509 packets including internal state, integrated top 1,509 packets, and integrated top 221 packets at 27 MHz / 115200 baud. The isolated engine test exercises the separate parallel reference RTL; the integrated top tests exercise the changed `trade_pair`. Existing vectors cover unsigned extremes, equality/floor boundaries, crossings at index 16, held actions, slot swaps, and index-zero resets between sessions without resetting the board model.

Tool: Gowin V1.9.11.03 Education; part `GW2AR-LV18QN88C8/I7`, device version C. All six routed pins match the unchanged CST. PR1014 and the digit-address truncation warning EX3791 remain in the build logs; the full regression covers digit-address wrap and comparison offset behavior. No new board programming occurred.

- `baseline/`: source and verification-input snapshot, regression logs, fresh build reports and `.fs`, and `summary.json` with source/bitstream SHA-256 hashes.
- `digit_width_2/`: the rejected source and its corresponding reports, regression logs, `.fs`, and hashes. Do not substitute this bitstream for the restored design.
- `../optimization_log.csv`: the measurement tool's complete comparison history. The initial INVALID row reflects missing Icarus on PATH; it is excluded from ranking. A subsequent fully gated baseline and experiment were recorded. A further attempted baseline passed regression but encountered read-only build outputs before logging a row.
- The freeze is also at `.build/opt/baseline_20261003`; frozen source fingerprint is `f90016e33d1c` (the tool's 12-character combined SHA-256 prefix).

The optimizer's ALU regex leaves the CSV ALU field blank for this report format. The tables and both `summary.json` files use the synthesis module XML to recover **4 ALUs**, and cross-check Logic = LUT + ALU + RAM16. The existing optimizer was not edited.

Icarus was already bundled at `.build/tools/icarus/app/bin`; no installation was needed. Add that directory to PATH for reproduction. Gowin needed access to its external cache. Read-only attributes on generated build files were cleared after verifying the deletion target and rejecting reparse points; no source directory was used for fresh-build cleanup.

`results/software_validation.json` and `results/simulation.log` were rewritten by regression. After restoring source, they were restored from the passing baseline evidence, so they describe the current source. The rejected experiment logs remain in its evidence directory. `.build/gowin_trade` still contains the last, rejected W=2 build and has an explicit rejection marker; use the preserved baseline `.fs` or rebuild restored source for W=1.

`bitstream/trade_core.fs` was not changed; its current SHA-256 is `cd708e137d143bdf52ca2ea6fe5ede4e09f18ba7849cd643ac7a7b0d5641c6e2`. The older physical evidence at `results/board_20261003T064213338565Z/` is for the saved `programmed.fs` with hash `e0b5bdc80f568ba7e7036693b6aa08fe2e0708843aa295db5cc83fca105afce7`. Its reported 13.718 / 31.265 ms mean/max must not be assigned to either new measurement. Both new builds require SRAM programming and saved quick, robust, and full-range physical results before release use. The skill calls for `22_robust_uart_test_fullrange.py`, which is absent from this checkout; obtaining that test is a TODO.

## Human review commands

Existing changes in scripts, vectors, the untracked skill/tool, and the ZIP review output predate this session. The commands below stage only the new optimization evidence, current baseline regression evidence, and project status update.

```powershell
git status --short
git diff --check
git diff -- PROJECT_BRIEF.md results/simulation.log results/software_validation.json
Get-Content results/optimization_20261003/README.md
git add PROJECT_BRIEF.md results/simulation.log results/software_validation.json results/optimization_log.csv results/optimization_20261003
git commit -m "Record FPGA baseline and digit-width experiment"
git push
```
