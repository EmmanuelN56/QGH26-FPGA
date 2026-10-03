# UART milestone project

The installed and locally exercised toolchain is Gowin EDA
`V1.9.11.03 Education`. Target `GW2AR-LV18QN88C8/I7`, device version C,
top module `top`. Board detection and limits are in
[board bring-up notes](../docs/board_bringup.md).

## Build from the repository root

The Tcl script uses commands documented in the installed Gowin Software User
Guide, SUG100-4.4.2E, section 8. It creates or reopens a project under `.build/`.
It defaults to synthesis; it never invokes a programmer.

```powershell
$gowinShell = 'C:\Gowin\Gowin_V1.9.11.03_Education_x64\IDE\bin\gw_sh.exe'
& $gowinShell .\gowin\build_uart.tcl
```

For synthesis plus Place & Route and bitstream generation:

```powershell
$env:UART_BUILD_FLOW = 'all'
try {
    & $gowinShell .\gowin\build_uart.tcl
} finally {
    Remove-Item Env:UART_BUILD_FLOW
}
```

`UART_BUILD_FLOW` also accepts `pnr` to route an existing synthesized netlist.
Use `all` after any HDL change so the bitstream includes the latest source.
The local build was verified from this repository path, including its space.

Generated project:
`.build/gowin_uart/uart_milestone/uart_milestone.gprj`.
Generated `.fs`:
`.build/gowin_uart/uart_milestone/impl/pnr/uart_milestone.fs`.
These generated files are ignored by Git. They are reproducible build output,
not the final submitted bitstream.

## GUI equivalent

Create an FPGA Design Project named `uart_milestone`, select GW2AR-18 version C,
QFN88, part `GW2AR-LV18QN88C8/I7`, and add:

```text
src/top.v
src/uart_rx.v
src/uart_tx.v
src/packet_controller.v
constraints/19_tang_nano_20k.cst
gowin/uart.sdc
```

Set Top Module/Entity to `top`. The `.sdc` supplies the 27 MHz clock constraint.
Use the organizer `.cst` directly. Do not add `testbench/` files to synthesis.
Run Synthesize, then Place & Route; review resource, timing, pin, and warning
reports. The current `PR1014` clock-routing warning is documented in the bring-up
notes. A generated `.fs` is not proof that the design works on the board.

If a future task changes the source-file list, update the Tcl creation block
and add the new files to any existing generated project through the GUI.

## Simulation when a simulator is available

No simulator was found locally, so these testbenches have not run. The following
commands are for an already installed Icarus Verilog; they do not install tools:

```powershell
New-Item -ItemType Directory -Force .build\sim | Out-Null
iverilog -g2012 -s uart_rx_tb -o .build/sim/uart_rx_tb.vvp src/uart_rx.v testbench/uart_rx_tb.v
vvp .build/sim/uart_rx_tb.vvp
iverilog -g2012 -s uart_tx_tb -o .build/sim/uart_tx_tb.vvp src/uart_tx.v testbench/uart_tx_tb.v
vvp .build/sim/uart_tx_tb.vvp
iverilog -g2012 -s top_tb -o .build/sim/top_tb.vvp src/top.v src/uart_rx.v src/uart_tx.v src/packet_controller.v testbench/top_tb.v
vvp .build/sim/top_tb.vvp
```

RX exercises all 256 byte values, contiguous frames, idle gaps, nominal host
baud and +/-2% baud offsets, a short start glitch, bad stop/break, and reset.
TX independently checks all 256 bytes, idle-high/start/data/stop timing, full
2340-clock frames, one-clock completion, ignored starts while busy, and reset.
The top-level test exercises three full packets, slot order, fixed NONE actions,
reserved zeros, no early/extra replies, 1 ms byte gaps, and a partial-request reset.

## Programming boundary

No programming was performed. Only after explicit authorization, follow the
participant guide's SRAM Mode / SRAM Program procedure using the successful
USB Debugger A location (561 in the recorded session). Re-scan on reconnect.
The generated milestone returns fixed NONE actions and cannot pass the full
organizer strategy tests. A final submission will need the complete strategy,
physical test evidence, and the matching `.fs` in `bitstream/`.
