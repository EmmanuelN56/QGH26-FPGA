# Submission bitstream

[`trade_core.fs`](trade_core.fs) is the selected **236 synthesis Logic / 171
register / 3 B-SRAM** candidate's exact, physically tested programming file.

| Build setting | Value |
| --- | --- |
| Board / FPGA | Tang Nano 20K / `GW2AR-LV18QN88C8/I7`, device version C |
| Tool | Gowin EDA V1.9.11.03 Education |
| Top module / clock | `top` / 27 MHz |
| Programming mode | Volatile SRAM |
| Synthesis summary | Logic 236 (232 LUT, 4 ALU); registers 171; B-SRAM 3 |

SHA-256:

```text
cd708e137d143bdf52ca2ea6fe5ede4e09f18ba7849cd643ac7a7b0d5641c6e2
```

Verify from the repository root:

```powershell
Get-FileHash .\bitstream\trade_core.fs -Algorithm SHA256
```

The matching build inputs are the five files under `src/`, the unchanged
organizer `constraints/19_tang_nano_20k.cst`, `gowin/build_uart.tcl`, and
`gowin/uart.sdc`. The build generates
`.build/gowin_trade/trade_core/impl/pnr/trade_core.fs`. See the
[root README](../README.md) for build and SRAM programming instructions.

This exact file passed physical validation on October 3, 2026:

- Organizer quick test: PASS.
- Five normal → full-range practice pairs: all 1,000 replies correct, including
  warm-up; each run 84/84 scored packets and 168/168 scored actions; zero timeouts.
- Fresh edge-case test: 2,492/2,492 packets and 4,984/4,984 actions correct across
  41 sessions; zero timeouts, mismatches, or extra bytes. Mean/maximum physical
  round-trip latency: 16.734/32.346 ms on the local Windows PC.

There was no reset or reprogramming between sessions within each capture.
These are local practice results; official judge and hidden-seed qualification
remain pending. EX3791 address truncation and PR1014 generic clock-routing
warnings are documented in the root README.

Do not replace this file with an older candidate or an untested rebuild. After
source changes, rebuild and physically validate the replacement file, then
update the SHA-256 in both README files. Test captures are optional submission
material and are not needed to program this bitstream.
