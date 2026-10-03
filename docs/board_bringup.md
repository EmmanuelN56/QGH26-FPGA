# Tang Nano 20K UART bring-up

Checked on 2026-10-03 on Windows build 10.0.26200.0. The board is detected over
USB and JTAG. The UART milestone synthesizes and completes Place & Route.
The board was **not programmed**, no serial port was opened for a hardware test,
and neither organizer test was run.

## Organizer contract

Sources: [participant guide](official/GQH_Hardware_Track_Participant_Guide.pdf),
sections 2, 5, 6, 9, 10, and 12; [constraint file](../constraints/19_tang_nano_20k.cst);
[quick test](../scripts/21_quick_uart_test.py);
[robust test](../scripts/22_robust_uart_test.py); and their
[quick](official/21_quick_uart_test_REFERENCE.md) and
[robust](official/22_robust_uart_test_REFERENCE.md) references.

| Setting | Confirmed value |
| --- | --- |
| Board | Sipeed Tang Nano 20K |
| FPGA | GW2AR-18, version C, `GW2AR-LV18QN88C8/I7`, QFN88 |
| Clock | 27 MHz onboard oscillator; `sys_clk`, pin 4 |
| UART | 115200 baud, 8 data bits, no parity, one stop bit, LSB first |
| FPGA RX | `uart_rx_i`, pin 70, bridge to FPGA |
| FPGA TX | `uart_tx_o`, pin 69, FPGA to bridge |
| Reset | `reset_btn`, pin 87, S2/KEY2, pull-down, optional |
| LEDs | `led0_n` pin 15, `led1_n` pin 16, active low |
| Programming | Volatile SRAM mode using a Gowin `.fs` file |

The pull-down and the guide's active-high button examples support treating KEY2
as active high. This is the scaffold's reset assumption; button polarity has not
been measured on the physical board. It asserts the internal reset immediately
and releases it after two clock edges. The initialized reset synchronizer also
provides a reset at configuration startup; Gowin synthesized its initialization.
After any future programming, press and release KEY2 before the first smoke test.

The organizer tests do not toggle a hardware reset between sessions. In the
future strategy implementation, **index zero must clear both item histories
before ingesting that request's prices**. The UART milestone has no item history.

Both scripts use `COM6` as a placeholder, a one-second serial timeout, and
stop-and-wait: send one request and read its entire response before the next.
Every request and response is eight raw binary bytes, with no delimiter or text.
Multi-byte fields are big-endian; UART bits within a byte are LSB first.

| Byte | Request: `>HBHBH` | Response: `>HBBBBH` |
| --- | --- | --- |
| 0 | index high byte | echoed index high byte |
| 1 | index low byte | echoed index low byte |
| 2 | slot 1 item ID | echoed slot 1 item ID |
| 3 | slot 1 price high byte | slot 1 action |
| 4 | slot 1 price low byte | echoed slot 2 item ID |
| 5 | slot 2 item ID | slot 2 action |
| 6 | slot 2 price high byte | `00` |
| 7 | slot 2 price low byte | `00` |

Item IDs are `11` and `22`; actions are NONE=`00`, SELL=`01`, BUY=`02`.
Only one response is allowed per complete request. The organizer guide warns
that the BL616 bridge can lose response bytes without idle time between them.
It does not specify a minimum reliable gap.

## Tools found

| Tool | Exact version / discovery result |
| --- | --- |
| Gowin EDA / synthesis / PnR | `V1.9.11.03 Education`, confirmed in build reports |
| Gowin Programmer CLI | `V1.9.11.03 Education (64-bit) build(2536)`, from `--help` |
| openFPGALoader | Not found on PATH or in the inspected common tool/MSYS2 directories; no version available |
| Verilog simulators | Icarus (`iverilog`, `vvp`), Verilator, and Questa (`vsim`) not found in the inspected paths |
| Yosys | Not found in the inspected paths |
| Default Python | `3.14.7`; pyserial absent |
| Bundled Python used to read PDFs | `3.12.14`; existing `pypdf` available |
| Bundled Poppler | `26.07.0`, from `pdfinfo -v` |

Gowin is installed but is not on PATH. Executables:

```text
C:\Gowin\Gowin_V1.9.11.03_Education_x64\IDE\bin\gw_ide.exe
C:\Gowin\Gowin_V1.9.11.03_Education_x64\IDE\bin\gw_sh.exe
C:\Gowin\Gowin_V1.9.11.03_Education_x64\Programmer\bin\programmer.exe
C:\Gowin\Gowin_V1.9.11.03_Education_x64\Programmer\bin\programmer_cli.exe
```

No tools, Python packages, drivers, or firmware were installed or changed.
Windows device queries and Gowin's local cache access needed elevated execution
outside the restricted workspace environment.

## USB, JTAG, and COM detection

Windows reported the following present devices with status `OK`:

| Device | Identity | Result |
| --- | --- | --- |
| USB composite device | `VID_0403`, `PID_6010`, serial `2025030317` | Present |
| USB Serial Converter A | interface `MI_00` | Present |
| USB Serial Converter B | interface `MI_01` | Present |
| USB Serial Port (COM3) | `FTDIBUS\VID_0403+PID_6010+2025030317A\0000` | Present |
| USB Serial Port (COM4) | `FTDIBUS\VID_0403+PID_6010+2025030317B\0000` | Present |

`.NET SerialPort.GetPortNames()` returned `COM3` and `COM4`.
The installed FTDI library's read-only device enumeration associated serial
`2025030317A` with USB location **561**, description `USB Debugger A`, and
`2025030317B` with location **562**, description `USB Debugger B`.

Gowin `--scan-cables F` initially displayed both interfaces as `USB Debugger A`:

```text
Cable found: USB Debugger A/0/562/null (USB location:562)
Cable found: USB Debugger A/1/561/null (USB location:561)
```

Channel-only scans stalled or could not open a cable. Those stalled scan
processes were stopped. An explicit location scan was successful:

```powershell
$programmer = 'C:\Gowin\Gowin_V1.9.11.03_Education_x64\Programmer\bin\programmer_cli.exe'
& $programmer --scan --cable-index 4 --location 561
```

```text
Target Cable: USB Debugger A/0/561/null@2.5MHz
Device Info:
    Family: GW2AR
    Name: GW2A-18C GW2AR-18C (One of them)
    ID: 0x0000081B
1 device(s) found!
```

Location 562 returned `Cable failed to open via the location` and
`No Gowin devices found`. This is not evidence of a broken UART interface.
The successful scan confirms a reachable FPGA consistent with the target; its
exact package and board asset tag still need visual confirmation.

**Likely UART port: COM4**, the B interface. **Confirmed JTAG path: USB Debugger
A at location 561**, the A interface also exposed as COM3. The UART assignment
remains a candidate until a programmed design returns the expected bytes.
COM numbers and USB locations can change after reconnecting.

For future manual programming, use Gowin Programmer's detected GW2AR-18C row,
SRAM Mode, and SRAM Program, as specified by the guide. Select the interface
corresponding to the successful location scan. Do not rely on whichever cable
Gowin selects first. No programming operation was executed in this session.

## UART milestone behavior

`src/top.v` connects independently testable `uart_rx`, `packet_controller`, and
`uart_tx` modules. It keeps both LEDs off. RX checks the start-bit center,
samples eight data-bit centers, and rejects a low stop bit with a one-clock
`framing_error`. It waits for a held-low line to return high before accepting
another start edge. `rx_valid`, `tx_start`, and `tx_done` are one-clock pulses.
TX ignores `tx_start` while busy and stays busy for the entire stop bit.

At 27 MHz, the rounded divider is **234 clocks per bit**, producing about
115384.6 baud (+0.1603% relative to 115200). Parameters default to the actual
board settings; only use combinations with at least four clocks per UART bit.

The controller collects eight bytes and then returns the organizer's response
layout with echoed index/slot IDs and **both actions fixed to NONE**. Prices are
ignored at this milestone. Example:

```text
Request:  12 34 22 AB CD 11 FE DC
Response: 12 34 22 00 11 00 00 00
```

It inserts 27000 clock cycles (1 ms), plus handshake cycles, between response
bytes after each complete stop bit. This adds roughly 7 ms per response.
That initial gap is an implementation choice, not an organizer-specified or
physically validated minimum. Keep it until hardware tests provide evidence.

Only stop-and-wait is supported: bytes sent while a response is in progress
are not buffered. A framing error clears the partial request. There is no
packet delimiter or partial-packet timeout; after an interrupted/corrupted
request, use KEY2 and resend a complete request to restore byte alignment.
Button reset cancels a partial request or response.

This is **not the full trading core**. It cannot pass the scored strategy checks:
the quick test's five scored packets require BUY/SELL actions, not fixed NONE.
Floor averages, per-item history, index-zero strategy clearing, and held actions
are deliberately not implemented yet. The organizer files were left unchanged.

## Local verification

The final `UART_BUILD_FLOW=all` build completed on 2026-10-03 at 01:04:23 local
time using the checked-in build script and all four HDL sources.

| Check | Result |
| --- | --- |
| Gowin parsing and synthesis | Passed, target `GW2AR-LV18QN88C8/I7`, version C |
| Place & Route and bitstream generation | Passed |
| Pins | All six ports match the supplied `.cst` |
| LUTs | 177 total: LUT2=43, LUT3=56, LUT4=78 |
| Registers | 166; no latches |
| B-SRAM | 0 |
| Clock timing | 27 MHz constraint; reported Fmax 218.934 MHz |
| Setup | 0 violations; worst reported slack +32.469 ns |
| Hold | 0 violations; worst reported slack +0.425 ns |
| Simulation | Testbenches written, **not run**; simulator unavailable |
| Board programming | Not performed |
| Organizer quick/robust tests | Not run |
| Physical UART latency | Not measured |

PnR warning `PR1014` says generic routing is used to connect `sys_clk_d` to
clock resources and may cause delay/skew. The supplied clock pin was preserved.
The reported internal setup/hold checks pass, but these numbers do not validate
asynchronous UART inputs, button timing, or physical-board operation. Review
the clock warning before treating this build as a submission candidate.

Generated files are under the ignored directory
`.build/gowin_uart/uart_milestone/impl/`:

- `gwsynthesis/uart_milestone.log` and `uart_milestone_syn.rpt.html`
- `pnr/uart_milestone.log`, `.rpt.txt`, `.pin.html`, and `.tr.html`
- `pnr/uart_milestone_tr_content.html` (actual timing data)
- `pnr/uart_milestone.fs`

Detection scan stdout/stderr are retained in `.build/board_detection/`.
The generated `.fs` is a local milestone artifact, not a validated final
submission bitstream. Its SHA-256 for this build is:

```text
DF3E0001E78C4D64810396922219668A7DFBA757F9D8CDEC63B8CD4708278292
```

## Next manual steps

1. Confirm the physical board label/asset tag and that reconnecting that board
   removes/restores these USB interfaces. Recheck the current COM numbers.
2. Use an existing simulator or approve installing one, then run the commands
   in [Gowin project notes](../gowin/README.md). No simulator was installed here.
3. Explicitly authorize board programming before loading the milestone `.fs`.
   Use SRAM mode. Press/release KEY2, close Programmer and any serial terminal,
   then test an eight-byte request/response on likely COM4 and save the log.
4. Implement and verify the strategy separately before expecting either
   organizer script to pass. When ready, install pyserial with human approval,
   change **only PORT** in both scripts, run quick then robust, and retain every
   CSV/summary with the source and bitstream identities.

If detection fails on reconnect, follow guide section 12: close competing
programs, connect directly with a known data-capable USB-C cable, and retry each
reported debugger location. In Device Manager, inspect any unknown USB device
or non-OK converter/port. Ask an organizer before changing Windows USB drivers
or BL616 firmware. The installed Gowin Programmer includes driver installers
under its `driver/` directory, but driver selection must match the actual
device. The present interfaces are healthy; no driver installation is currently
indicated. The guide's MSYS2 UCRT64/openFPGALoader flow is an optional fallback
if Gowin programming later fails, and requires separate installation approval.

TODO: physical reset polarity, confirmed UART port, simulated test results,
physical milestone response/log, and ultimately full organizer passes with CSVs.
