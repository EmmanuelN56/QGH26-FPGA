# Gowin build for the 186-Logic release

The selected trading core uses **186 total Logic (186 LUT, 0 ALU, 0 RAM16),
92 registers, and 4 B-SRAM blocks**. Target: `GW2AR-LV18QN88C8/I7`, device
version C, top `top`, 27 MHz. Toolchain: Gowin EDA V1.9.11.03 Education.

## Build from the submitted source

From the repository root in PowerShell, using the installed Gowin shell:

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

Change the executable path if needed. The script defaults to synthesis only;
`UART_BUILD_FLOW=all` runs synthesis and Place & Route. It does not program
the board. On Linux, set `UART_BUILD_FLOW=all` when invoking the installed
Gowin shell with `gowin/build_uart.tcl`.

The project contains exactly these seven inputs:

```text
src/top.v
src/uart_rx.v
src/uart_tx.v
src/packet_controller.v
src/trade_engine.v
constraints/19_tang_nano_20k.cst
gowin/uart.sdc
```

Keep the organizer CST unchanged. The SDC defines a 37.037037 ns clock period.
The script selects the exact part/version, `top`, and 27 MHz. Do not add
testbenches to synthesis. The GUI equivalent uses those same settings and inputs.

Generated project: `.build/gowin_trade/trade_core/trade_core.gprj`.
Generated programming file: `.build/gowin_trade/trade_core/impl/pnr/trade_core.fs`.
Generated caches are ignored and are not submission inputs. A cached project
that points to another checkout is rejected; build in a fresh native Windows
directory containing `src/`, `constraints/`, and `gowin/`, without copied caches.

## Verified resources, timing, and programming file

| Metric | Selected release |
| --- | --- |
| Synthesis / routed total Logic | 186 / 186 |
| LUT / ALU / RAM16 | 186 / 0 / 0 |
| Registers | 92 |
| B-SRAM / distributed SSRAM | 4 / 0 |
| Routed Fmax | 108.334 MHz |
| Worst setup / hold slack | +27.806 / +0.074 ns |
| Reported setup / hold violations | 0 / 0 |

A fresh build reproduced these metrics. The submitted file is
[`bitstream/trade_core.fs`](../bitstream/trade_core.fs), SHA-256:

```text
6fbefe4697c714b18f78830088c826b2f7cc1e2823de0070a688c84f3f6a6e23
```

That exact file passed the October 4 physical quick, normal, full-range,
modified full-range, and attached variant tests. The fresh rebuild contains
identical configuration data; its creation-time comment differs.
EX3791 (address-expression truncation) and PR1014 (generic clock routing)
remain disclosed. Preserve the organizer clock pin and review the generated
resource, pin, and timing reports after rebuilding.

## Local tests and SRAM programming

Run `python scripts/run_regression.py` with Python and Icarus Verilog installed.
The runner checks the independent model against all three organizer reference
classes and runs seven configurations across six testbenches. Board timing
covers quick, normal, and full-range sessions; accelerated timing covers the
complete vector set. Generated logs are local verification material.

Program `bitstream/trade_core.fs` with Gowin Programmer **SRAM Mode / SRAM
Program**, selecting `GW2AR-18C`. Detect the debugger and UART port on the
connected computer. Then run the organizer quick, normal, and full-range tests;
change only their PORT setting. Run normal and full-range consecutively without
manual reset or reprogramming. Only a physically tested file should replace
the submitted `.fs`.

See the [root README](../README.md), [bitstream description](../bitstream/README.md),
and [board verification](../docs/board_bringup.md) for the selected release.
