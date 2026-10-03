Experimental branch codex/logic-312-blockram: active source and bitstream are the block-RAM candidate, 312 synthesis Logic / 179 registers / one B-SRAM. Physical validation is pending. CANDIDATE.md identifies this build. Historical release measurements below describe the archived 365-LUT baseline.

Recovery note (2026-10-03): the active repository is `C:/Users/Lenovo/Downloads/QuizletFPGA`. Exact source/build files were restored, but some later physical logs and original simulation logs from Ubuntu are missing. Fresh recovery results are separate. See [recovery inventory](docs/repository_recovery.md).

# Silicon Trade Core

Gator Quant Hacks 2026 Hardware Track trading core for the Tang Nano 20K,
Gowin GW2AR-18. All UART parsing, item routing, moving-average state, crossing
decisions and response generation run on the FPGA. Host scripts are local
verification tools and are not required during judging.

**Current status: native Windows software regressions, synthesis, Place & Route, SRAM programming, the organizer quick test, and three repeated robust sessions pass. The matching tested bitstream is `bitstream/trade_core.fs`.**

Team members/contact: TODO — human team must supply names and contact details.
Board asset tag: TODO — confirm against the borrowed board.
Repository and Devpost URLs: TODO — human team must supply submission links.

## Design and protocol

Five Verilog modules separate UART RX, UART TX, packet control, top-level reset,
and per-item strategy. The controller instantiates two independent engines for
IDs `0x11` and `0x22`. Each keeps sixteen unsigned 16-bit prices, a 20-bit rolling
sum, a circular pointer, previous price, sample count and last action.

Index zero clears both histories **before** its prices are ingested. Indices
0–15 fill histories, update previous prices and return NONE. Later decisions use
floor averages (`sum >> 4`): BUY if previous price <= old average and current
price > new average; SELL if previous price >= old average and current price <
new average. With no crossing, the last action repeats. Item state follows the
ID and response order follows request slots.

```text
UART: 115200 baud, 8N1, LSB first within each byte
Multi-byte fields: big-endian; packets: exactly eight bytes
Request:  [index16][item1_8][price1_16][item2_8][price2_16]
Response: [index16][item1_8][action1_8][item2_8][action2_8][reserved16]
IDs: A=0x11, B=0x22; actions: NONE=0x00, SELL=0x01, BUY=0x02
reserved=0x0000
```

One complete request produces one response; no unsolicited bytes. Stop-and-wait
is required. Response frames retain a 1 ms idle gap, plus handshake cycles,
after each complete stop bit. This gap passed simulation and the physical quick
plus three robust runs. Its minimum acceptable value remains unmeasured.

## Hardware and sources

Target: `GW2AR-LV18QN88C8/I7`, device version C, QFN88; clock 27 MHz;
top-level module `top`. The unchanged organizer
[`constraints/19_tang_nano_20k.cst`](constraints/19_tang_nano_20k.cst) is used
directly. Do not recreate pin assignments in FloorPlanner.

| Port | Pin | Direction / behavior |
| --- | --- | --- |
| sys_clk | 4 | Input, 27 MHz |
| reset_btn | 87 | Input, KEY2/S2, pull-down; treated as active high |
| uart_rx_i | 70 | Input, BL616 to FPGA |
| uart_tx_o | 69 | Output, FPGA to BL616 |
| led0_n | 15 | Output, active low, driven high |
| led1_n | 16 | Output, active low, driven high |

`src/` contains synthesizable HDL; `testbench/` contains simulation benches and
regression vectors; `scripts/` contains independent Python tooling and unchanged
organizer tests. `gowin/` contains build Tcl and the clock SDC. `docs/official/`
contains organizer references. `results/` holds simulation, build, programming
and physical measurements. `bitstream/` contains the matching tested `.fs`.
Temporary tools, project files and caches under `.build/` are ignored.

No external HDL IP cores are used. Pre-existing organizer guide/CST/Python tests
are preserved; Python standard library builds the model and vectors, Icarus
Verilog runs simulations, Gowin builds hardware, and organizer serial tests use
pyserial. No host service participates in the decision path.

## Software verification

Requires Python 3.10+ and installed Icarus Verilog (`iverilog`, `vvp`). Do not
install new tools without authorization. From the repository root:

```powershell
python scripts/run_regression.py
```

The independent model uses a chronological list and direct integer arithmetic.
The vector generator extracts only reference classes and their constants from
both organizer scripts using an AST allowlist. It never imports their modules,
opens a port, runs scoring code, or modifies organizer files.

The regression regenerates checked-in vectors, compares all expected responses
to both organizer classes, and runs UART RX/TX, original top, isolated engines,
and complete-session top tests. It saves a transcript and SHA-256 source/vector
identities in `results/`. The latest full regression passed natively on Windows with Icarus 12.0 (devel)
and Python 3.14.5; the earlier Linux/WSL run used Icarus 12.0 and Python 3.14.4. The approved workspace-local Icarus package lives in
`.build/tools/`; the runner also accepts normal PATH installations.

| Simulated check | Result |
| --- | --- |
| Independent model vs both organizer classes | 1,509 packets / 15 sessions, byte-exact |
| RX / TX unit tests | 260 / 256 bytes, PASS |
| Existing top smoke test | Three packets, partial-request reset, PASS |
| Engines | 1,509 packets; actions and internal state, PASS |
| Full sessions, accelerated UART timing | 1,509 packets / 12,072 response bytes, PASS |
| Full sessions, 27 MHz / 115200 baud / 1 ms gaps | 221 packets: quick + two robust sessions without reset, PASS |

Coverage includes equality comparisons, floor rounding, held BUY/SELL actions,
zero and maximum prices, circular replacement, index values above 255, repeated
sessions and slot swaps during warm-up and trading. Board-default UART simulations
drive the nominal host baud independently of the FPGA divider. Accelerated
session tests are marked separately in the evidence manifest.

## Build

Use Gowin EDA `V1.9.11.03 Education`, as used for the historical UART scaffold.
The trading-core build passed natively on Windows; see `results/build_windows_20261003/build_summary.json`. With Gowin already installed
on Windows, set the actual shell path and run:

```powershell
$gowinShell = 'C:\Gowin\Gowin_V1.9.11.03_Education_x64\IDE\bin\gw_sh.exe'
$env:UART_BUILD_FLOW = 'all'
try { & $gowinShell .\gowin\build_uart.tcl }
finally { Remove-Item Env:UART_BUILD_FLOW }
```

The script creates/reopens `.build/gowin_trade/trade_core/trade_core.gprj` with
all five HDL sources, unchanged CST and `gowin/uart.sdc`. It selects the exact
part/version and `top`, runs synthesis plus Place & Route, and writes
`.build/gowin_trade/trade_core/impl/pnr/trade_core.fs`. It never programs a board.
For GUI steps and Linux invocation, see [gowin/README.md](gowin/README.md).

Save and review synthesis logs/resources, PnR logs, routed pins, setup/hold,
Fmax and clock warnings. The old UART build reported PR1014 for generic clock
routing; this remains an open review item. Preserve the organizer clock pin.
Do not use an old generated project or UART-only `.fs` for this design.

## Programming and physical demo

**Explicit authorization is required before programming any board.** Once the
identified `.fs` has passed build review and programming is authorized:

1. Connect the Tang Nano 20K with a data-capable USB-C cable. Detect the current
   JTAG cable/location and serial port; old COM4/location 561 are historical.
2. In Gowin Programmer, Scan Device, select GW2AR-18C, open Device Configuration,
   set **SRAM Mode / SRAM Program**, select the matching built `.fs`, Save, then
   Program/Configure. Save console evidence. SRAM contents disappear on power loss.
3. Press/release KEY2. Close Programmer and other serial terminals. Confirm
   pyserial is installed; ask before installing it if absent.
4. Run the capture tool with the actual port, board identity, and exact file
   programmed (example values below must be replaced):

```powershell
python scripts/capture_board_tests.py --port COM4 --board '<asset-tag>' --bitstream .build/gowin_trade/trade_core/impl/pnr/trade_core.fs --runs 3
```

The capture tool runs the unchanged organizer quick test and three robust tests,
changing only PORT in run-local copies. There is no reset/reprogram between
sessions. It preserves console logs, all CSVs/summaries, source snapshot/hashes,
base commit/worktree status and a copy/hash of the programmed `.fs` under
`results/board_<UTC>/`. It does not itself program hardware. Confirm its recorded
source snapshot matches the build; archive the matching build/programming logs
in that evidence directory.

Expected physical result: quick prints PASS; every robust run receives 100
packets with 84/84 correct scored packets, 168/168 actions, and zero timeouts.
Check every CSV and retain failures as well as successes. Record average and
maximum latency from successful response rows; simulation cannot measure USB
or PC latency.

After successful physical tests, copy the **same tested** bitstream for submission:

```powershell
Copy-Item .build/gowin_trade/trade_core/impl/pnr/trade_core.fs bitstream/trade_core.fs
Get-FileHash bitstream/trade_core.fs -Algorithm SHA256
```

## Measured results and release limits

| Metric | Current trading core | Historical UART-only scaffold |
| --- | --- | --- |
| Physical scored packet/action correctness | 100% in each of three robust runs (84/84 packets; 168/168 actions) | Not measured |
| Physical mean/max round-trip latency | 13.718 / 31.265 ms across 300 received robust packets | Not measured |
| Total LUT (judging metric) | 412: LUT2=49, LUT3=123, LUT4=240 | 177: LUT2=43, LUT3=56, LUT4=78 |
| Registers / B-SRAM | 328 / 0; eight distributed SSRAM blocks | 166 / 0 |
| Fmax | 77.985 MHz (routed) | 218.934 MHz |
| Worst setup / hold slack | +24.214 / +0.425 ns; zero reported violations | +32.469 / +0.425 ns |
| Synthesis / PnR | Passed natively on Windows | Passed on original Windows machine |

The historical scaffold ignored prices and returned NONE. Its resource/timing
figures cannot be used as trading-core metrics. No optimization was performed.
Before any optimization, record correctness, LUTs/registers/B-SRAM, timing and
physical latency before and after.

Physical validation on 2026-10-03 used explicit SRAM authorization, Gowin CLI
operation 2 at JTAG location 561, and COM4 on the local Windows PC. Quick passed;
all three robust runs received 100 packets with no timeouts. Independent review
checked every CSV row, including warm-up, against the model. Mean/max latency
per run was 14.076/31.265 ms, 13.616/23.797 ms and 13.462/30.494 ms.
Evidence: [`results/board_20261003T064213338565Z/csv_review.json`](results/board_20261003T064213338565Z/csv_review.json),
including programming log, source snapshots, matching build reports and all CSVs.
There was no reset or reprogram between sessions. The programmer rejected a UNC
bitstream path before programming; the successful command used a hash-identical
native Windows copy. No KEY2 press was required or claimed.

Final tested SHA-256: `e0b5bdc80f568ba7e7036693b6aa08fe2e0708843aa295db5cc83fca105afce7`.
Remaining release tasks are human team/asset/submission metadata, Git review,
commit/push, public repository check and Devpost submission. PR1014 remains;
the local tests passed with this routing but do not exhaustively validate clock
skew. Latency is specific to this PC; the official seed and judging PC differ.
Optional button polarity is unmeasured. No optimization was performed.
Unsupported input cases include unknown/duplicate item IDs, pipelined requests,
and nonsequential/incomplete judging sessions. Framing errors discard a partial
packet; reset KEY2 after an interrupted stream because no delimiter or partial
packet timeout is defined. Index-zero strategy clearing does not realign bytes.

Humans must supply team/asset/submission metadata, keep the repository public
through judging, review and commit the final source/evidence/bitstream, push, and
enter the full final SHA on Devpost. Do not place that SHA in this README.
See [PROJECT_BRIEF.md](PROJECT_BRIEF.md), [bring-up notes](docs/board_bringup.md),
and the [organizer checklist](docs/official/SUBMISSION_CHECKLIST.md).
