# Submission bitstream

`trade_core.fs` is the physically tested **186 Logic / 92 registers / 4 B-SRAM**
candidate for Tang Nano 20K, `GW2AR-LV18QN88C8/I7` version C, top `top`, 27 MHz.
Toolchain: Gowin EDA V1.9.11.03 Education; programming: volatile SRAM.

SHA-256: `6fbefe4697c714b18f78830088c826b2f7cc1e2823de0070a688c84f3f6a6e23`.

```powershell
Get-FileHash .\bitstream\trade_core.fs -Algorithm SHA256
```

Fresh October 4, 2026 physical validation: quick PASS; five normal/full-range
pairs (1,000 packets); modified full-range (2,492 packets); attached variants
(1,500 packets). Every robust packet and all 9,984 actions, including warm-up,
matched the independent model, with zero timeouts or mismatches. The board was
programmed once, with no manual reset or reprogramming between sessions.
All five normal runs estimate 100/100 locally; median of their run means is
16.739 ms. Official judge and hidden-seed qualification remain pending.

The fresh source rebuild reproduces 186 Logic, 92 registers, and 4 B-SRAM.
Its configuration data is identical to this file; its creation-time comment
differs. Exact inputs: the five `src/` HDL files, organizer CST, build Tcl, and
clock SDC. EX3791 and PR1014 remain disclosed. See the
[root README](../README.md) for reproduction and limitations.

After source changes, rebuild and physically test the replacement programming
file before updating its hash. Saved test logs and CSVs are optional material.
