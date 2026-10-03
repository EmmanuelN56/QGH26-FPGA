# Block-RAM physical practice validation

On 2026-10-03 at approximately 18:28 EDT, the context_ram candidate was programmed
into volatile SRAM on Tang Nano 20K board serial 2025030317. Gowin V1.9.11.03
Education reported target GW2AR-18C, FPGA ID 0x0000081B, SRAM Program completion,
and programmer exit code zero. JTAG location was 561; UART was COM4 at 115200 baud.
The board was left running this candidate. No flash programming was performed.

Branch: `codex/logic-312-blockram`.
Source commit: `6f13a956336e90cc5f7c4fb9dba0a6f9ca68881f`.
Bitstream SHA-256: `825bf4d70b30f3ed7f01a09e725d65304f37f7b26c551289ea06fd13b947ef8d`.
Recorded build: 312 synthesis Logic (272 summary LUTs + 40 ALUs), 179 registers,
one B-SRAM, zero SSRAM. Routed Logic is 316. Existing routed Fmax is 102.750 MHz,
setup/hold slack +27.305/+0.425 ns with no reported violations. These resource
and timing figures come from the existing build; no new synthesis ran.

## Results

The quick test passed, followed by five normal/full-range pairs in this order:
normal_1, fullrange_1, normal_2, fullrange_2, through normal_5, fullrange_5.
There was no reprogramming, power cycle, or requested/manual reset between tests.
Each organizer test starts at index zero. The serial port is opened and closed
by each unmodified organizer test, as in the supplied scripts.

Every robust test received all 100 packets, scored 84/84 packets and 168/168
actions correctly, and reported zero timeouts. Independent model review checked
every returned field in all 1,000 robust packets, including the 160 warm-up
packets ignored by organizer scoring. Thus full-range alone passed 500/500
complete replies, 420/420 scored packets, and 840/840 scored actions.

| Pair | Normal mean ms | Normal median ms | Full-range mean ms | Full-range median ms | Full-range max ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 16.843306 | 16.841400 | 16.724885 | 16.833250 | 24.5360 |
| 2 | 16.673652 | 16.851700 | 16.671942 | 16.845900 | 19.1615 |
| 3 | 16.890694 | 16.867550 | 16.828641 | 16.873550 | 22.6568 |
| 4 | 16.673841 | 16.823250 | 16.596640 | 16.856150 | 24.3070 |
| 5 | 16.640075 | 16.845550 | 16.874118 | 16.871600 | 28.3334 |

Across 500 packets each, normal/full-range mean latency was
16.744314/16.739245 ms; maximum was 32.4375/28.3334 ms. The median of the five
run means was 16.673841/16.724885 ms. The median of the five run medians was
16.845550/16.856150 ms. Both aggregations are labeled because they describe
different quantities. Latency measures the supplied host write/read transaction,
including USB and operating-system effects; it is not FPGA computation latency.

## Insights and limits

- Correctness survives normal-to-full-range session changes on the physical
  board. Index-zero clearing correctly handles previously populated RAM in these
  sequences, and swapped slots pass (40 full-range swaps per run).
- Large unsigned prices work in the sampled practice data: the full-range seed
  generates prices from 1,417 through 64,932. It does not generate either exact
  endpoint, 0 or 65,535. Existing simulation edge checks remain separate evidence.
- Repeating the same seeds demonstrates repeatability across sessions, not
  coverage of five independent random datasets. The normal seed is 0x57214720;
  full-range is 0x1F00D16B. The hidden seed remains unknown.
- Normal mean latency is below the published approximate 20.8 ms full-points
  threshold on this PC. With perfect correctness and the existing resource
  count, this is consistent with the published 100-point practice target, not
  an official score. Judge reference timing and the hidden run remain authoritative.
- The block-RAM design has 42 fewer synthesis Logic units and 43 fewer registers
  than the 234-LUT alternative (354 Logic / 222 registers), and 70 fewer Logic
  units than the 230-LUT alternative (382 Logic / 222 registers). Earlier
  314/342 totals omitted distributed-memory costs and must not be used.
- Historical baseline captures came from different sessions/host conditions.
  These results do not establish a latency improvement over the baseline.

## Evidence and source integrity

`manifest.json` records the commit, source and script hashes, detected serial
identity, exact programmer command, per-run results, and latency aggregations.
`programming.log`, `programmed.fs`, `build_summary.json`, and `source/` preserve
the exact programmed build and verification scripts. Each test directory
contains the executed script, console log, CSV, and organizer summary.

The supplied Downloads full-range test and repository original share SHA-256
`73295ff02aa06bac869f2c9c5c6ad6f244084b514f697846c176bc4c2ff2fc9c`.
Only PORT was changed to COM4 in executed organizer copies; protocol, vectors,
reference model, timeouts, and scoring were left intact. Pyserial 3.5 was installed
locally under ignored `.build/python_deps`; no driver or host timer was changed.

Initial identity checking stopped before programming because checkout CST bytes
had different CRLF/LF line endings. All other build inputs matched their recorded
hashes. The runner verified that the CST contents are identical after normalizing
only line endings, then preserved and validated the exact archived build snapshot.
The organizer CST in the active checkout was not modified. Both hashes and the
line-ending difference are recorded in the manifest.
