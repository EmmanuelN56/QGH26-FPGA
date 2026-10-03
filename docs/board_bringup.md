# Tang Nano 20K bring-up and verification

## Current trading core — 2026-10-03

The FPGA strategy and integration pass software simulation and physical tests.
The authorized trading-core bitstream was programmed into volatile SRAM; quick
and three consecutive robust sessions passed, with saved logs and CSVs.
Trading-core synthesis/PnR now pass natively on Windows. The reviewed candidate
SHA-256 is `e0b5bdc80f568ba7e7036693b6aa08fe2e0708843aa295db5cc83fca105afce7`.
See `results/build_windows_20261003/` for source snapshots and build reports.

| Check | Current result |
| --- | --- |
| Independent Python model | 1,509 packets / 15 sessions agree byte-for-byte with both organizer reference classes |
| UART RX | PASS, 260 bytes, +/-2% baud, start glitch, bad stop/break, reset |
| UART TX | PASS, 256 byte values, exact frame duration, busy-start rejection, reset |
| Existing top test | PASS, three packets, slot order, partial-packet reset, no early/extra output, 1 ms gaps |
| Isolated engines | PASS, 1,509 packets; actions, sums, previous prices, pointers, counts, clear priority and valid pulses |
| Full-system sessions | PASS, 1,509 packets / 12,072 response bytes at accelerated UART timing |
| Board-default simulation | PASS, 221 packets / 1,768 bytes at 27 MHz / 115200 baud / 1 ms gaps; quick + two robust sessions without reset |
| Trading-core synthesis / timing / resources | PASS; 412 LUTs, 328 registers, 0 B-SRAM, 8 SSRAM; routed Fmax 77.985 MHz; setup/hold +24.214/+0.425 ns |
| Physical quick / robust / latency | PASS quick + 3 robust runs; 100% scored packets/actions; aggregate mean/max 13.718/31.265 ms |
| Final submission bitstream | Matching tested `bitstream/trade_core.fs`; SHA-256 below |

Evidence: `results/simulation.log`, `results/software_validation.json`, and
`testbench/vectors/vectors.json`. Simulation warnings about unspecified RTL
time units are benign because the RTL has no simulation delays; all bench time
units are explicit. The model executes only allowlisted organizer AST nodes;
no organizer serial or scoring code is executed during software checks.

## Latest native Windows session — 2026-10-03

All six software regressions were reproduced using native Windows Icarus 12.0
(devel) and Python 3.14.5. `scripts/run_regression.py` now supplies absolute
compiler input paths because Windows Icarus invokes cmd.exe, which rejects a
UNC working directory. Organizer files and RTL are unchanged in this session.

USB now enumerates healthy FTDI converter A/B and COM3/COM4, serial 2025030317;
FTDI driver 2.12.36.20 is already installed. No driver or debugger firmware was
changed. Native pyserial enumeration confirms both ports. Read-only Gowin cable
scan detects locations 562 and 561; location 561 reads one GW2AR-family FPGA,
ID 0x0000081B. COM4/interface B passed the organizer physical tests.
Evidence: `results/windows_detection.json`, `results/jtag_cables.log`,
`results/jtag_scan.log`, and `results/windows_model_validation.json`.

Authorized development tools were installed under
`C:/Users/Lenovo/AppData/Local/GatorFPGA/`: Icarus, an isolated Python environment
with pyserial/pypdf, and an archive helper used to extract Gowin without running
bundled driver installers. Gowin V1.9.11.03 Education was downloaded from its
vendor CDN. Launching Gowin from UNC stalled before Tcl execution; the successful
build used a native Windows copy at `trade_build_20261003`, with both a local
working directory and local source files. Every build source hash matches the
workspace. The generated project/output was copied back to `.build/gowin_trade/`.

Synthesis: 412 LUTs (49 LUT2, 123 LUT3, 240 LUT4), 328 registers, 152 ALUs,
eight RAM16S4 SSRAM blocks, zero B-SRAM and zero latches. PnR: 412 LUTs,
166 ALUs, 328 registers, eight SSRAM blocks. Routed clock constraint is 27 MHz;
Fmax 77.985 MHz, worst setup +24.214 ns, hold +0.425 ns, zero reported violations.
All six routed pins match the supplied CST. PR1014 remains for sys_clk_d generic
routing into the primary clock network. Timing reports do not validate physical
clock skew or asynchronous UART/reset input behavior. Preserve the organizer pin;
physical quick/robust validation passed with this warning retained. No
response-gap/resource optimization ran.

## Earlier environment detection

This workspace is Linux/WSL, not the original Windows build environment.
Python 3.14.4 and pyserial are available. Neither Linux serial-port enumeration
nor `/dev/ttyUSB*` / `/dev/ttyACM*` found a port. Earlier Windows host discovery failed through WSL interop. A subsequent
read-only PowerShell query outside the sandbox succeeded on host
`DESKTOP-JLOM0UA`: no COM ports, no matching FPGA/debugger identity, and one
**Unknown USB Device (Device Descriptor Request Failed)**. Its reported identity
is `USB\VID_0000&PID_0002`; this does not identify the FPGA. Confirm whether this
entry disappears when the board is unplugged before attributing the error to
the board. Enumeration evidence is in `results/usb_detection.json`. No serial
port was opened and no board was programmed.

Gowin, Icarus and Verilator were initially absent from PATH and inspected tool
locations; no `gw_sh.exe`, `iverilog.exe` or `vvp.exe` was found in the mounted
Windows drive search. Installing Icarus was approved. System installation failed
because sudo required a password. The approved Ubuntu `iverilog 12.0-3` package
was downloaded and extracted into ignored `.build/tools/`; no system files were
changed. The regression runner discovers this local tool or an installed Icarus.
At that earlier stage, Gowin installation/download and programming were not authorized;
the later Windows session received both authorizations.

## Fixed board interface and behavior

Sources: unchanged [guide](official/GQH_Hardware_Track_Participant_Guide.pdf),
[organizer CST](../constraints/19_tang_nano_20k.cst), and organizer quick/robust
scripts. Target GW2AR-18, version C, `GW2AR-LV18QN88C8/I7`, QFN88.

| Port | Pin | Meaning |
| --- | --- | --- |
| sys_clk | 4 | 27 MHz onboard oscillator |
| reset_btn | 87 | KEY2 / S2, pull-down; treated as active high |
| uart_rx_i | 70 | BL616 to FPGA |
| uart_tx_o | 69 | FPGA to BL616 |
| led0_n / led1_n | 15 / 16 | Active low; unused, driven high |

All six routed pin assignments match the unchanged CST. Physical reset polarity remains unmeasured.
`reset_pipe` asserts reset immediately and releases after two clock edges;
configuration initialization provides startup reset as in the original scaffold.

UART is 115200 baud / 8N1 / LSB first. The rounded divider is 234 clocks per bit,
115384.6 baud (+0.1603%). Request and response are eight bytes, big-endian fields:
`>HBHBH` request and `>HBBBBH` response, with reserved 0000. Item IDs are 11/22;
NONE/SELL/BUY are 00/01/02. State follows item ID; responses preserve slot order.

Two `trade_engine` instances maintain 16 unsigned prices, 20-bit sums,
previous prices, circular pointers, sample counts and held actions. Index zero
clears both engines in PREPARE; SAMPLE ingests the prices on the next clock.
BUILD consumes both valid actions on the following clock. Warm-up updates
history and previous price but returns NONE. Crossings use old/new `sum >> 4`.
The count guards an empty or incomplete history; only official sequential
sessions with one of each item per packet are specified and regression-scored.

Response gaps remain 27000 clocks (1 ms), plus existing handshake cycles,
between complete UART frames. This is not a measured minimum for the BL616.
Only stop-and-wait is supported. Bytes arriving during a response are not
buffered. Framing errors discard a partial request; there is no partial-request
timeout or delimiter. After an interrupted request, reset KEY2 to realign bytes.
Index zero clears strategy state; it cannot realign a corrupted byte stream.

## Historical UART-only Windows build (edc3fae)

These observations belong to another machine and do not validate the current
strategy. Windows build 10.0.26200.0 on 2026-10-03 used Gowin EDA
V1.9.11.03 Education, target part/version above. Synthesis and PnR passed for a
controller returning fixed NONE actions and ignoring prices:

| Historical measurement | Value |
| --- | --- |
| Total LUT | 177 (LUT2 43, LUT3 56, LUT4 78) |
| Registers / B-SRAM | 166 / 0; no latches |
| Clock constraint / Fmax | 27 MHz / 218.934 MHz |
| Worst setup / hold slack | +32.469 ns / +0.425 ns, zero reported violations |
| Warning | PR1014: generic routing connecting sys_clk_d to clock resources |
| Programming / UART tests | Never performed |

PR1014 was not resolved. Positive internal timing does not prove clock skew,
asynchronous pin behavior, or physical operation. Recheck the actual new build
reports and vendor clock-routing guidance while preserving organizer CST.

Historical USB VID_0403/PID_6010, serial 2025030317: A interface COM3/location
561, B interface COM4/location 562. JTAG at 561 reported family GW2AR and ID
0x0000081B. Location 562 could not open. COM4 was a UART candidate, never tested.
These are not current detected ports. Re-scan after connecting the board.

Historical `.fs` path:
`.build/gowin_uart/uart_milestone/impl/pnr/uart_milestone.fs`, SHA-256
`DF3E0001E78C4D64810396922219668A7DFBA757F9D8CDEC63B8CD4708278292`.
The file/logs were ignored and did not arrive here; never substitute that file
for a trading-core submission bitstream.

## Completed physical validation and release tasks

Explicit SRAM authorization was received for SHA-256 `e0b5bdc80f568ba7e7036693b6aa08fe2e0708843aa295db5cc83fca105afce7`.
Gowin CLI `--device GW2AR-18C --operation_index 2 --cable-index 4 --location 561
--frequency 2.5MHz` programmed the hash-identical native Windows file successfully.
The UNC file attempt was rejected before programming; both logs are retained.
The programmer exited before the capture script opened COM4. KEY2 was not pressed.

Saved evidence: `results/board_20261003T064213338565Z/`, including `programming.log`, `manifest.json`,
`csv_review.json`, `programmed.fs`, source snapshots, build reports, quick console
and three robust CSV/summary/console sets. The three runs each received 100
packets, scored 84/84 packets and 168/168 actions, and had no timeouts. Every CSV
row, including all warm-up fields, independently matches the Python model.
No reset, power cycle or reprogram occurred between sessions. Physical latency:

| Run | Mean (ms) | Maximum (ms) |
| --- | --- | --- |
| robust_1 | 14.076 | 31.265 |
| robust_2 | 13.616 | 23.797 |
| robust_3 | 13.462 | 30.494 |
| Combined 300 packets | 13.718 | 31.265 |

The tested file was copied to `bitstream/trade_core.fs` and its hash rechecked.
PR1014 remains; local correctness is demonstrated, while exhaustive physical
clock-skew validation and KEY2 polarity remain unmeasured. Official tests use
a different seed and judging PC. These results do not claim an official score.

Humans must supply team/asset/submission metadata, inspect and commit explicit
source/evidence/bitstream paths, push, verify public access, and record the full
final SHA in Devpost. No Git history or remote actions were performed here.

If cable detection fails, follow guide section 12: close competing programs,
use a direct data-capable cable, and retry detected debugger locations. Ask an
organizer before changing USB drivers or BL616 firmware. No such changes were
made here. Do not optimize resources or shorten response gaps without matching
before/after correctness, resources, timing and physical latency evidence.
