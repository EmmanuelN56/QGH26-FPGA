# Submission bitstream

`trade_core.fs` is the exact physically tested **186 Logic / 92 registers /
4 B-SRAM** candidate. Build: Gowin V1.9.11.03 Education, Tang Nano 20K,
`GW2AR-LV18QN88C8/I7` version C, top `top`, 27 MHz, volatile SRAM mode.

SHA-256: `6fbefe4697c714b18f78830088c826b2f7cc1e2823de0070a688c84f3f6a6e23`.

```powershell
Get-FileHash .\bitstream\trade_core.fs -Algorithm SHA256
```

This file passed quick, five normal/full-range pairs (1,000 correct replies),
and the extensive 8,785-packet physical corpus on October 4, 2026. All responses
including warm-up matched; there were no timeouts, mismatches or extra bytes.
One SRAM programming operation covered that sequence, with no manual reset or
reprogramming between sessions. All five normal runs estimated 100/100 locally.
Median of the five normal run means: 16.740 ms.

The current five src files, original CST, gowin/build_uart.tcl and gowin/uart.sdc
are the matching inputs. Fresh synthesis/PnR reproduced 186 Logic and 92 registers,
with Fmax 108.334 MHz and +27.806/+0.074 ns setup/hold slack; zero violations.
EX3791 and PR1014 remain disclosed. See the [root README](../README.md) and
[saved evidence](../results/logic_search_20261003/README.md).

Official judge and hidden-seed qualification remain pending. After any source
change, rebuild and physically test the replacement before updating this file.
