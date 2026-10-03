# Gowin trading-core build

Target `GW2AR-LV18QN88C8/I7`, device version C, top `top`; organizer reference
toolchain Gowin EDA `V1.9.11.03 Education`. This version built the historical
UART scaffold on Windows. **The trading-core synthesis and PnR passed natively on Windows.**

From the repository root on Windows with Gowin already installed:

```powershell
$gowinShell = 'C:\Gowin\Gowin_V1.9.11.03_Education_x64\IDE\bin\gw_sh.exe'
$env:UART_BUILD_FLOW = 'all'
try { & $gowinShell .\gowin\build_uart.tcl }
finally { Remove-Item Env:UART_BUILD_FLOW }
```

Use the actual executable path on your machine. On Linux, with an installed
Gowin shell, use `UART_BUILD_FLOW=all /path/to/gw_sh gowin/build_uart.tcl`.
The script never invokes a programmer. It defaults to synthesis; `syn`, `pnr`,
and `all` are accepted. Always use `all` after changing HDL.

The script creates a separate trading-core project, so an old UART milestone
project cannot silently omit the new engine. It creates/reopens
`.build/gowin_trade/trade_core/trade_core.gprj`, and generates
`.build/gowin_trade/trade_core/impl/pnr/trade_core.fs`. Generated caches are
ignored. Do not submit a stale UART milestone `.fs`.

GUI equivalent: create an FPGA Design Project named `trade_core`, select
GW2AR-18 version C / QFN88 / the exact part above, set Top Module to `top`, and add:

```text
src/top.v
src/uart_rx.v
src/uart_tx.v
src/packet_controller.v
src/trade_engine.v
constraints/19_tang_nano_20k.cst
gowin/uart.sdc
```

Use the organizer CST unchanged. The SDC supplies a 37.037037 ns clock period.
Do not add simulation files. If the source list changes later, update existing
generated projects as well as this Tcl script.

After synthesis and PnR, save the synthesis log/resource report and PnR log,
resource, pin, and timing reports from `impl/gwsynthesis/` and `impl/pnr/`.
Record Total LUT, LUT2/3/4, registers, B-SRAM, Fmax, worst setup/hold slack and
violations. Check all six pins against the CST. Review PR1014 on the actual
trading build: historical internal timing did pass, but generic clock routing
can introduce delay/skew. Do not alter the organizer clock pin to silence it.
The routed report shows Fmax 77.985 MHz, setup/hold +24.214/+0.425 ns and
zero reported setup/hold violations; PR1014 remains. Authorized SRAM programming
and physical quick plus three robust sessions subsequently passed.

Software regression (Python 3 and already installed Icarus Verilog):

```powershell
python scripts/run_regression.py
```

The runner compares the Python model against extracted organizer reference
classes without executing their serial test bodies, generates vectors, compiles
five testbenches, and runs six simulation configurations. It saves transcripts
and source SHA-256 identities in `results/`. Board-default UART timing includes
quick and two robust sessions; accelerated timing covers every boundary and
random session. See the root README and bring-up notes for results and limits.

Programming requires explicit authorization. After a reviewed build, use the
participant guide's Gowin Programmer **SRAM Mode / SRAM Program** procedure.
Re-detect the cable/location and UART port; do not assume the old location 561
or COM4 applies. Save programming evidence, then run the physical capture script.
Only a matching physically tested `.fs` should become the final submission file.

## Verified Windows build in the WSL-hosted workspace

The successful build used a native copy at
`C:/Users/Lenovo/AppData/Local/GatorFPGA/trade_build_20261003`, because launching
Gowin from the UNC workspace stalled before Tcl execution. Copy `src/`,
`constraints/` and `gowin/` to a native Windows directory, set that directory as
the working directory, then run the same Tcl with `UART_BUILD_FLOW=all`.
Verify source hashes before using the result. Generated project paths refer to
this local snapshot; rebuild from Tcl rather than reopening copied projects.

The tools were extracted at
`C:/Users/Lenovo/AppData/Local/GatorFPGA/gowin/extracted/Gowin_V1.9.11.03_Education_x64/`.
No bundled driver installer was run. Build reports/source snapshots are archived
in `results/build_windows_20261003/`; outputs are copied to `.build/gowin_trade/`.
Candidate SHA-256:
`e0b5bdc80f568ba7e7036693b6aa08fe2e0708843aa295db5cc83fca105afce7`.
The same file was subsequently programmed in authorized volatile SRAM, passed
quick plus three robust sessions, and copied to `bitstream/trade_core.fs`.
Evidence: `results/board_20261003T064213338565Z/`. Human Git/submission freeze is pending.
The CLI programmer rejected a UNC `.fs` path; use a hash-verified native Windows
copy when reproducing SRAM programming.
