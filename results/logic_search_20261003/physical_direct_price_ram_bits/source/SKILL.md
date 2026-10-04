---
name: gowin-logic-optimizer
description: Reduce total synthesis Logic (LUT + ALU + RAM16 combined) and register count of the Tang Nano 20K UART trading core built with Gowin EDA V1.9.11.03. Use whenever the task is to shrink, optimize, or measure FPGA area in this repo, to try a datapath, FSM, UART, packet-buffer, or memory change, to compare experiments, or to check why a build got bigger. Runs a fresh judge-style Gowin build, gates every change on the reference-model regression, logs results, and keeps a fallback snapshot.
---

# Gowin logic optimizer

Goal: lowest total Logic, then fewest registers, with zero loss of correctness. The judges rank qualified teams on the complete Logic row of the synthesis Resource Usage Summary. LUTs, ALUs, and RAM16 all count together. BSRAM is free. A smaller LUT line is worthless if Logic did not drop.

Read `AGENTS.md` and `PROJECT_BRIEF.md` first. Their rules win over this file. In particular: never run git add, commit, push, tag, merge, or rebase; never add AI attribution to source or docs; organizer artifacts override repo prose.

## Tool

All commands run from the repo root:

```
python <skill-dir>/scripts/fpgaopt.py <command>
```

| Command | What it does |
| --- | --- |
| `freeze [--name N]` | Snapshot `src/`, `gowin/`, `constraints/` to `.build/opt/N` (default `baseline`) |
| `restore [--name N]` | Copy a snapshot back. Use after a failed experiment |
| `gate` | Run `scripts/run_regression.py`; pass only if exit code 0 and `all_passed` is true |
| `measure --label "text"` | Gate, fresh Gowin build (`UART_BUILD_FLOW=all`), parse reports, append a row to `results/optimization_log.csv`, print per-module breakdown and a verdict against the best gated result |
| `compare` | Print the log sorted best first |
| `parse --reports DIR` | Parse existing Gowin report files without building |

Gowin shell path: pass `--gw-sh PATH`, set `GOWIN_SH`, or rely on the default `C:\Gowin\Gowin_V1.9.11.03_Education_x64\IDE\bin\gw_sh.exe`. If the path is wrong, ask the human; do not guess.

`measure` deletes `.build/gowin_trade` first because judges rebuild from scratch and a cached project can silently omit a new source file. Pass `--reuse-project` only for quick synthesis-only checks (`--flow syn`), never for a recorded result.

## Workflow

1. **Baseline.** Run `freeze`, then `measure --label "baseline"`. Record Logic, registers, BSRAM. If the baseline gate fails, stop and report; do not optimize a broken design.
2. **Read the breakdown.** The per-module table shows where cells go. Pick the largest cost center, not the most interesting idea.
3. **One change per experiment.** Edit `src/` only. State the hypothesis in one line before editing.
4. **Measure.** `measure --label "short description of change"`. The gate runs first; a failing gate marks the row INVALID.
5. **Decide.** BETTER: `freeze --name best` and continue from there. SAME or WORSE: `restore --name best` (or `baseline`) and try something else. Do not stack untested changes.
6. **Repeat**, then `compare` and report the table.

Tie-break order is Logic, then registers. A change that lowers Logic by 1 but adds 20 registers still wins on Logic, but report it. Compare synthesis Logic against routed Logic in the `measure` output; the judges use the re-synthesized number.

## Correctness rules that must never regress

These are what disqualify a team, so treat any weakening as a failed experiment.

- Prices are full-range unsigned 16-bit (0 to 65535). Sum needs 20 bits. Never narrow the datapath.
- Averages use floor (`sum >> 4`), not rounding. BUY and SELL comparisons use `<=` and `>=` against the old average and `>` and `<` against the new average, exactly as in the guide.
- Previous price is compared with the old average; the current price with the new average that already includes it.
- Index 0 clears all state (windows, sums, previous prices, held actions) before its prices are ingested, with no board reset.
- Route by item ID (0x11 A, 0x22 B), never by slot. Respond in request slot order. Held action repeats when no crossing occurs. NONE only before the first crossing.
- Exactly 8 response bytes per request, reserved bytes 0x0000, nothing sent early or unsolicited.
- BL616 bridge: back-to-back response bytes can be dropped. Do not remove `TX_GAP_CYCLES` or idle time without a physical test.
- Do not add testbenches to the synthesis sources. Keep the `top` port names and the supplied `.cst` unchanged.

If the regression vectors do not already cover a new corner you are touching (0 and 65535 prices, prices exactly at the average, first crossing right at index 16, item swapped between slots, index 0 mid-session), add a vector to `scripts/generate_vectors.py` before relying on the gate.

## Ideas to try, in rough order of expected payoff

Use the per-module table to choose. These are hypotheses; keep only what `measure` confirms.

- UART RX and TX: share one baud counter, shrink the oversampling and stop-bit logic, drop unused framing-error paths.
- Packet storage: hold the 8 request bytes in one shift register or BSRAM, echo index and item bytes instead of storing separate copies.
- Merge small state machines so decode logic is paid once. Sweep FSM encoding (binary, one-hot, Gray) and inspect the mapped result.
- Arithmetic: share one subtract/compare unit across both items and both comparisons; test 1, 2, 4, and 8 bit digit-serial variants against the whole design, not the adder alone.
- Memory: BSRAM is excluded from Logic, so move window history, sums, and previous prices there when addressing and control cost less than the logic they replace. Gowin GW2A BSRAM has no read-before-write mode, so keep explicit old-data capture and collision-free scheduling.
- Remove duplicated counters (fill count versus pointer), reset terms on datapath registers that do not need them, and unused ports or LEDs.
- Synthesis options in `gowin/build_uart.tcl` (resource sharing, retiming, RAM style attributes). Judges use the project settings in the commit, so these count.

## Reporting

After each session give: the compare table, the best candidate's Logic, registers, and BSRAM, which files changed, and the exact review commands from `AGENTS.md` for the human to stage and commit with explicit paths.

## What this skill does not do

- It does not program the board. A candidate is not release-ready until a human programs the generated `.fs` in SRAM mode and runs `21_quick_uart_test.py`, `22_robust_uart_test.py`, and `22_robust_uart_test_fullrange.py` back to back, saving the CSVs.
- It does not write `bitstream/trade_core.fs`. If a better candidate is physically validated, the human copies the `.fs` and updates the hash in `README.md` and `bitstream/README.md`.
- Simulation results are never to be described as physical validation.
- `run_regression.py` rewrites `results/software_validation.json` and `results/simulation.log`; mention this in the report.
