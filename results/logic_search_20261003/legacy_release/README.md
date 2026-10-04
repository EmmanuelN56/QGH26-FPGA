# Silicon Trade Core

Gator Quant Hacks 2026 Hardware Track trading core for the Sipeed Tang Nano 20K.
The selected design uses **236 synthesis Logic, 171 registers, and 3 B-SRAM
blocks**. The matching, physically tested programming file is
[`bitstream/trade_core.fs`](bitstream/trade_core.fs).

All UART parsing, item routing, moving-average state, trading decisions, and
response generation run on the FPGA. Host software is used only for local
testing; the design does not require team-supplied host software during judging.

- Team members: Emmanuel Nwosu and Hao Tran.
- Repository: [EmmanuelN56/QuizletFPGA](https://github.com/EmmanuelN56/QuizletFPGA).
- Submission portal: [GQH Devpost](https://gqhacks.devpost.com).

## FPGA implementation

The packet controller uses one shared `trade_pair` strategy engine with a
one-bit arithmetic cell (`W=1`). It processes both request slots sequentially
while keeping independent price histories, rolling sums, previous prices, and
held actions for item IDs `0x11` and `0x22`. Three narrow synchronous block RAMs
store the rolling sums, previous prices, and sixteen-price histories. The
circular pointer and sample count advance once per complete pair of prices.

Prices are unsigned 16-bit values; rolling sums are unsigned 20-bit values.
Index zero logically clears both items before its prices are ingested. Old RAM
contents are ignored until overwritten. Indices 0–15 fill the windows and
return NONE. Later decisions use floor averages (`sum >> 4`):

```text
old_average = old_sum >> 4
new_sum     = old_sum - oldest_price + current_price
new_average = new_sum >> 4

BUY  if previous_price <= old_average and current_price > new_average
SELL if previous_price >= old_average and current_price < new_average
otherwise repeat the item's last action
```

State follows the item ID; response ordering follows the request slots.

## Hardware and toolchain

- Board: Sipeed Tang Nano 20K; FPGA `GW2AR-LV18QN88C8/I7`, device version C.
- Clock: 27 MHz; top-level module: **`top`**.
- HDL: Verilog. Local testing: Python, pyserial, and Icarus Verilog.
- Build/programming tools: **Gowin EDA V1.9.11.03 Education** and Gowin Programmer.
- Physical validation platform: Windows, board USB serial `2025030317`, COM4.
  COM4 is this test setup's port; determine the port on another computer.
- Additional hardware: a data-capable USB-C cable; no external peripherals.

The unchanged organizer-supplied
[`constraints/19_tang_nano_20k.cst`](constraints/19_tang_nano_20k.cst) provides
the physical constraints. Do not recreate pin assignments in FloorPlanner.

| Port | Pin | Behavior |
| --- | --- | --- |
| `sys_clk` | 4 | 27 MHz clock input |
| `reset_btn` | 87 | KEY2/S2 reset input, active high, pull-down |
| `uart_rx_i` | 70 | BL616 to FPGA |
| `uart_tx_o` | 69 | FPGA to BL616 |
| `led0_n` | 15 | Active-low LED output, driven high |
| `led1_n` | 16 | Active-low LED output, driven high |

## Submission files

| File | Purpose |
| --- | --- |
| `src/top.v` | Top-level wiring, reset, UART parameters |
| `src/uart_rx.v` | UART receiver |
| `src/uart_tx.v` | UART transmitter |
| `src/packet_controller.v` | Eight-byte requests, strategy handshake, responses |
| `src/trade_engine.v` | Shared strategy engine and arithmetic cell |
| `constraints/19_tang_nano_20k.cst` | Organizer pin constraints |
| `gowin/build_uart.tcl` | Reproducible project creation and build |
| `gowin/uart.sdc` | 27 MHz clock timing constraint |
| `bitstream/trade_core.fs` | Final tested SRAM programming file |
| `testbench/top_tb.v` | Board-timing UART smoke test, reset and byte-gap checks |
| `testbench/top_sessions_tb.v` | Complete-session UART simulation |
| `scripts/run_regression.py` | Local model and HDL regression runner |

These are the selected design's build inputs and programming file. Historical
experiments, test scripts, and reports elsewhere in the repository are not
included in the synthesis project. The Tcl script creates generated project
files and caches under `.build/`; those generated files are not needed in the
submission. Local test code and simulation files are retained for reproduction;
test logs and CSVs are optional submission material.

## Build instructions

Install Gowin EDA V1.9.11.03 Education. From the repository root in PowerShell,
set the shell path to the installed location and run:

```powershell
$gowinShell = 'C:\Gowin\Gowin_V1.9.11.03_Education_x64\IDE\bin\gw_sh.exe'
$buildScript = (Resolve-Path '.\gowin\build_uart.tcl').Path
$env:UART_BUILD_FLOW = 'all'
try {
    & $gowinShell $buildScript
    if ($LASTEXITCODE -ne 0) { throw 'Gowin build failed.' }
}
finally { Remove-Item Env:UART_BUILD_FLOW }
```

The script selects the exact FPGA part/version, `top`, and 27 MHz. It adds only
the five HDL files, the supplied CST, and the SDC, then runs synthesis and Place
& Route. The generated project is
`.build/gowin_trade/trade_core/trade_core.gprj`; the generated bitstream is
`.build/gowin_trade/trade_core/impl/pnr/trade_core.fs`. The script does not
program hardware. Its default flow is synthesis only; `UART_BUILD_FLOW=all`
is required to generate the programming file.

Alternatively, create a Gowin GUI project for `GW2AR-LV18QN88C8/I7`, version C,
add those same seven inputs, set `top` as the top module and 27 MHz as the
target frequency, then run synthesis and Place & Route. Do not add testbenches.
If a cached project refers to another checkout, use a fresh project directory
with the submitted inputs and no copied `.build/` directory.

Review the synthesis resource summary and routed timing. The submitted `.fs`
has the following SHA-256:

```text
cd708e137d143bdf52ca2ea6fe5ede4e09f18ba7849cd643ac7a7b0d5641c6e2
```

Check it with `Get-FileHash .\bitstream\trade_core.fs -Algorithm SHA256`.
If producing a replacement bitstream, physically test that generated file
before copying it to `bitstream/trade_core.fs` and updating its hash here and
in `bitstream/README.md`.

## Programming and reproducing the demo

1. Connect the Tang Nano 20K with a data-capable USB-C cable.
2. Open Gowin Programmer and scan the connected device. Select `GW2AR-18C`.
3. Open Device Configuration, select **SRAM Mode / SRAM Program**, and choose
   `bitstream/trade_core.fs`. Save the configuration and run Program/Configure.
   SRAM configuration is volatile; reload it after power loss.
4. Close Programmer and any serial terminal that holds the UART port. Find
   the board's serial port in Device Manager.
5. Obtain the organizer's `21_quick_uart_test.py`, `22_robust_uart_test.py`, and
   `22_robust_uart_test_fullrange.py`. With Python and pyserial installed, change
   only their `PORT` setting to the detected port. Run the quick test, then the
   normal robust test, then the full-range practice test:

```powershell
# Run from the directory containing the organizer's test scripts.
python 21_quick_uart_test.py
python 22_robust_uart_test.py
python 22_robust_uart_test_fullrange.py
```

The quick test should print PASS. Each robust test should receive all 100
responses, with 84/84 scored packets, 168/168 scored actions, and zero timeouts.
Review its CSV. Run normal and full-range tests consecutively without resetting
or reprogramming the board; index zero begins each new session. Organizer tests
are distributed separately and need not be included in the team repository.

## UART input and output

```text
UART: 115200 baud, 8N1, LSB first within each byte
Multi-byte fields: big-endian; packet length: exactly eight bytes

Request:  [index16][item1_8][price1_16][item2_8][price2_16]
Response: [index16][item1_8][action1_8][item2_8][action2_8][reserved16]

ITEM_A=0x11, ITEM_B=0x22
NONE=0x00, SELL=0x01, BUY=0x02
reserved=0x0000
```

For example, request `00 00 11 00 64 22 00 C8` begins a session with prices
100 and 200, and returns `00 00 11 00 22 00 00 00`.

Send one complete request and wait for its response before sending the next.
The FPGA responds only after all eight request bytes arrive and sends no
unsolicited bytes. Each transmitted byte includes a complete stop bit, followed
by three controller-handshake idle clocks. The selected top-level configuration
uses `TX_GAP_CYCLES=0`; it does not add a millisecond delay between bytes.

## Verification and measured results

For software verification, install Python 3 and Icarus Verilog, with `iverilog`
and `vvp` available on PATH. From the repository root, run:

```powershell
python scripts/run_regression.py
```

The runner checks the independent model against the organizer's reference
classes, regenerates simulation vectors, and runs UART, strategy, and complete
session tests. It never opens a serial port or programs the board. Its generated
logs and summaries are local outputs. The selected UART testbenches use the
final design's zero additional response-gap setting.

Local validation on October 3, 2026 used the exact submitted bitstream:

| Check | Result |
| --- | --- |
| Organizer quick UART test | PASS |
| Five consecutive normal → full-range practice pairs | 1,000/1,000 responses correct, including warm-up; zero timeouts |
| Each 100-packet practice run | 84/84 scored packets and 168/168 scored actions |
| Fresh full-range edge-case board test, 41 sessions | 2,492/2,492 packets and 4,984/4,984 actions correct; zero timeouts, mismatches, or extra bytes |
| Matching edge-case RTL/UART simulation, accelerated UART | 2,492 packets / 19,936 response bytes, PASS |
| Earlier selected-candidate strategy / UART regressions | 4,176 packets each, PASS; 200 packets at actual UART timing, PASS |

The fresh edge-case test uses new values and seed `0x236171EC`. Expected
responses agree between the organizer's extracted strategy model and an
independent model that recomputes history sums. It checks zero/max prices,
20-bit sum limits, unsigned and byte-order boundaries, carry/borrow, equality,
held BUY/SELL, all sixteen floor-division remainders, independent item state,
slot swaps, window wraparound, and repeated/early index-zero resets. The board
was programmed once before those 41 sessions, with no manual reset or
reprogramming between them.

| Resource / timing metric | Selected candidate |
| --- | --- |
| Synthesis total Logic | **236 (232 LUT, 4 ALU)** |
| LUT2 / LUT3 / LUT4 primitives | 27 / 98 / 106 |
| LUT primitive total | 231; the synthesis LUT summary also includes one INV |
| Registers | **171** |
| B-SRAM / distributed SSRAM | **3 / 0** |
| Routed total Logic | 237 |
| Routed Fmax | 118.135 MHz |
| Worst setup / hold slack | +28.572 / +0.425 ns |
| Setup / hold violations | 0 / 0 |

Use the complete synthesis Resource Usage Summary for the organizer's total
Logic ranking. The routed count and LUT primitive count are separate metrics.

| Physical latency on the local Windows PC | Result |
| --- | --- |
| Five normal practice runs, 500 packets: mean / maximum | 16.718 / 32.786 ms |
| Median of the five normal run means | 16.695 ms |
| Five full-range practice runs, 500 packets: mean / maximum | 16.713 / 28.665 ms |
| Fresh edge-case test, 2,492 packets: mean / median / maximum | 16.734 / 16.731 / 32.346 ms |

These are local practice measurements. Official judge-run and hidden-seed
qualification remain pending; the judging PC and USB/UART path can change
round-trip latency. Saved local captures were checked against expected replies;
they are not required to build or program the design.

## External resources

The design follows the organizer's protocol, participant guide, fixed CST,
and reference strategy/test scripts. Gowin provides synthesis, Place & Route,
programming, and inferred FPGA block RAM. Python standard-library tooling,
pyserial, and Icarus Verilog support local verification. No third-party HDL IP
cores are used, and no external service participates in trading decisions.

## Known limitations

Requests must contain one of each supported item ID and follow the organizer's
sequential, stop-and-wait protocol. Unknown/duplicate IDs and pipelined requests
are unsupported. An incomplete packet has no byte timeout or delimiter;
press/release KEY2 to recover after an interrupted byte stream. A framing error
discards a partial packet. Index-zero strategy clearing does not realign bytes.

The build reports EX3791 for address-expression truncation in `trade_engine.v`
and PR1014 for generic clock routing. The recorded build has positive timing
slack and passed the local tests described above; the warnings remain disclosed.
Power loss clears the SRAM configuration and requires reprogramming.

## Final submission

These instructions follow Part 3 of the
[organizer participant guide](https://www.gqhacks.com/hardware/GQH_Hardware_Track_Participant_Guide.pdf#page=13).
Complete the team member names above, make the repository public, and keep it
available through judging. Commit and push the selected source, constraints,
build inputs, README files, local test code, and matching `.fs`. Obtain the full final commit SHA
with `git rev-parse HEAD` and enter it with the repository URL on Devpost. Do not
put the Git commit SHA in this README.

Submit through Devpost before **Sunday, October 4, 2026, 11:00 am EDT**, then
return the board and all borrowed accessories to **Reitz Room 2345** by that
same deadline. The submitted commit identifies the version judged.
