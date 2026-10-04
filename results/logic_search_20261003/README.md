# Logic search and full-range validation — October 4, 2026

Lowest locally qualifying candidate tested: **186 synthesis Logic (186 LUT, 0 ALU,
0 RAM16), 92 registers, 4 B-SRAM**. The fresh final rebuild reproduced these
counts. Compared with the frozen baseline: **50 fewer Logic (21.2%) and 79 fewer
registers (46.2%)**, with one additional B-SRAM block.

Every accepted candidate passed physical quick → normal → full-range practice
tests. The final candidate passed five consecutive normal/full-range pairs and
the 8,785-packet extensive board corpus. No accepted reduction lost the local
100-point rubric. The qualification-failure boundary was not established; this
is a measured search result, not a proof of the global minimum.

## Reproducible evidence

- [Final source, fresh build and regression](final_best/summary.json)
- [Final programming log, organizer CSVs and five-run manifest](physical_final_best_five_runs/manifest.json)
- [Exact tested programming file](physical_final_best_five_runs/programmed.fs)
- [Extensive physical results](physical_final_best_five_runs/extensive_8785/summary.json)
- [All 8,785 observed board transactions](physical_final_best_five_runs/extensive_8785/transactions.csv)
- [Extensive RTL checks and independently recomputed coverage](extensive_final_best/validation.json)
- [Human release and Git commands](REVIEW.md)

Board serial `2025030317`, COM4, JTAG location 561, volatile SRAM. The final board
was programmed once; quick, all ten robust sessions and the extensive stress run
followed without manual reset or reprogramming. Organizer originals are unchanged;
executed copies differ only in PORT. All 100 CSV rows per robust run, including
warm-up, were independently checked. Full-range organizer SHA-256:
`73295ff02aa06bac869f2c9c5c6ad6f244084b514f697846c176bc4c2ff2fc9c`.

Tested .fs SHA-256: `6fbefe4697c714b18f78830088c826b2f7cc1e2823de0070a688c84f3f6a6e23`. Source fingerprint: `cc8a88c20782`.

## Search measurements

All rows passed the reference/RTL gate and fresh Gowin V1.9.11.03 Education
synthesis/PnR for `GW2AR-LV18QN88C8/I7`, version C, at 27 MHz. All report zero
setup/hold violations and zero distributed SSRAM. Tables use the complete
synthesis Logic row; routed final Logic is also 186. Each named directory saves
its own source, build reports, bitstream, hashes and software evidence.

| Candidate | Parent | Logic | LUT / ALU | Registers | B-SRAM | Fmax MHz | Setup / hold ns |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | — | 236 | 232 / 4 | 171 | 3 | 118.135 | +28.572 / +0.425 |
| digit_width_2 | baseline | 248 | 244 / 4 | 170 | 3 | 120.636 | +28.748 / +0.341 |
| pointer_full_flag | baseline | 233 | 233 / 0 | 167 | 3 | 118.017 | +28.564 / +0.425 |
| explicit_bit_carry | pointer_full_flag | 235 | 235 / 0 | 167 | 3 | 132.573 | +29.494 / +0.425 |
| held_action_outputs | pointer_full_flag | 230 | 230 / 0 | 163 | 3 | 133.025 | +29.520 / +0.425 |
| price_shift_16 | held_action_outputs | 229 | 229 / 0 | 159 | 3 | 153.353 | +30.516 / +0.327 |
| shared_ram_read_enable | price_shift_16 | 231 | 231 / 0 | 159 | 3 | 147.990 | +30.280 / +0.353 |
| rx_single_byte_register | price_shift_16 | 230 | 230 / 0 | 151 | 3 | 154.854 | +30.579 / +0.425 |
| tx_stop_marker | price_shift_16 | 224 | 224 / 0 | 156 | 3 | 128.933 | +29.281 / +0.322 |
| shared_packet_byte_count | tx_stop_marker | 221 | 221 / 0 | 153 | 3 | 137.916 | +29.786 / +0.425 |
| packet_handoff_fsm | shared_packet_byte_count | 217 | 217 / 0 | 153 | 3 | 132.659 | +29.499 / +0.425 |
| request_price_bsram | packet_handoff_fsm | 206 | 206 / 0 | 129 | 4 | 129.297 | +29.303 / +0.202 |
| phase_bit_decode | request_price_bsram | 205 | 205 / 0 | 129 | 4 | 128.114 | +29.232 / +0.202 |
| shared_uart_baud_timer | phase_bit_decode | 199 | 199 / 0 | 121 | 4 | 126.136 | +29.109 / +0.074 |
| index_in_request_ram | shared_uart_baud_timer | 197 | 197 / 0 | 108 | 4 | 139.885 | +29.888 / +0.074 |
| strategy_onehot | index_in_request_ram | 197 | 197 / 0 | 108 | 4 | 139.885 | +29.888 / +0.074 |
| held_byte_uart_tx | index_in_request_ram | 200 | 200 / 0 | 104 | 4 | 130.574 | +29.379 / +0.077 |
| direct_price_ram_bits | index_in_request_ram | 188 | 188 / 0 | 92 | 4 | 113.159 | +28.200 / +0.074 |
| remove_price_fetch_state | direct_price_ram_bits | 186 | 186 / 0 | 92 | 4 | 108.334 | +27.806 / +0.074 |
| shared_timer_rx_single_byte | remove_price_fetch_state | 191 | 191 / 0 | 84 | 4 | 104.817 | +27.497 / +0.198 |
| final_best | remove_price_fetch_state | 186 | 186 / 0 | 92 | 4 | 108.334 | +27.806 / +0.074 |

Rejected resource trials were not programmed: W=2, explicit carry, shared read
enable, either single-byte RX trial, held-byte TX, and the unchanged one-hot
attribute trial. Their physical latency is unmeasured. `final_197` is a preserved
fresh rebuild of an intermediate candidate; `final_best` supersedes it.

Accepted changes replace fill count with pointer/full flag, expose held actions
directly, keep exact-width prices, use a TX stop marker, share packet byte count,
simplify packet handoff, store request prices/index in B-SRAM, share UART baud
timing, simplify phase decode, select price bits directly, and remove the now
unused fetch state. The legacy parallel trade_engine remains separately tested.
The final design preserves full unsigned prices, 20-bit sums, floor averages,
item-keyed histories, held actions, index-zero clear-before-ingest, and eight-byte
framing. No RTL state name or state count is required by the rubric; guide section
10 allows the internal HDL organization to vary while requiring exact protocol.

## Per-module breakdown

These are own cells, with arithmetic shown separately. Do not add a subtree
aggregate to its descendants. The strategy subtree fell from 122 to 77 Logic.

| Own module cells | Baseline Logic | Final Logic | Baseline registers | Final registers | Final B-SRAM |
| --- | ---: | ---: | ---: | ---: | ---: |
| top | 0 | 21 | 2 | 10 | 0 |
| top/receiver | 31 | 17 | 35 | 27 | 0 |
| top/packets | 35 | 32 | 59 | 19 | 1 |
| top/packets/strategy | 112 | 67 | 52 | 24 | 3 |
| top/packets/strategy/arithmetic | 10 | 10 | 0 | 0 | 0 |
| top/transmitter | 48 | 39 | 23 | 12 | 0 |
| Total | 236 | 186 | 171 | 92 | 4 |

## Physical before/after measurements

Each non-final row is one normal/full-range pair; final_best_five_runs is five
pairs. Mean/max include all received packets. Build summaries intentionally have
physical_validation=false; the separate physical manifests establish board tests.

| Candidate | Normal mean / max ms | Full-range mean / max ms | Correct / local score |
| --- | ---: | ---: | --- |
| baseline_236 | 16.958 / 32.034 | 16.997 / 31.101 | All / 100 |
| direct_price_ram_bits | 16.783 / 34.602 | 16.776 / 22.386 | All / 100 |
| final_best_five_runs | 17.152 / 145.233 | 16.829 / 53.164 | All / 100 |
| held_action_outputs | 16.592 / 27.868 | 17.178 / 44.282 | All / 100 |
| index_in_request_ram | 16.946 / 32.664 | 16.769 / 21.689 | All / 100 |
| packet_handoff_fsm | 17.738 / 51.462 | 19.207 / 153.352 | All / 100 |
| phase_bit_decode | 16.746 / 19.364 | 16.881 / 30.011 | All / 100 |
| pointer_full_flag | 17.176 / 31.727 | 16.548 / 21.634 | All / 100 |
| price_shift_16 | 16.811 / 26.049 | 16.712 / 28.976 | All / 100 |
| remove_price_fetch_state | 17.075 / 38.482 | 16.816 / 24.232 | All / 100 |
| request_price_bsram | 16.831 / 31.325 | 16.691 / 21.284 | All / 100 |
| shared_packet_byte_count | 16.757 / 38.071 | 20.118 / 210.871 | All / 100 |
| shared_uart_baud_timer | 16.589 / 24.403 | 16.844 / 29.924 | All / 100 |
| tx_stop_marker | 16.655 / 26.013 | 16.841 / 22.764 | All / 100 |

Final normal run means: 16.987, 16.527, 16.556, 16.740, 18.948 ms.
Each estimates **100/100** using 70 correctness points, 15 latency points at mean
≤20.7825 ms, and 15 LUT points at ≤542 LUTs. Median of five normal run means:
**16.740 ms**; median of five packet
medians: 16.836 ms. Aggregate
normal mean/max: 17.152/145.233 ms;
full-range mean/max: 16.829/53.164 ms.
The long-tail samples are included in these means; none caused a timeout.

## Extensive correctness

All **8,785 packets / 17,570 item actions** matched on the final physical board,
with no timeouts, mismatches or trailing unsolicited bytes. Stress mean/median/max:
16.967/16.938/204.767 ms.
This stress latency is recorded separately and is not the normal rubric run.

The same 8,785 packets passed isolated legacy-engine state/action checks and
complete active-pair UART simulation. The standard seven-check regression also
passed 1,609 session packets, 221 actual 27 MHz / 115200 baud packets, all-byte
RX/TX tests, malformed start/stop recovery, partial packets, inter-byte gaps,
physical-reset simulation, stable transmit bytes and single-cycle handshakes.

Recomputed corpus coverage: 101 index-zero restarts, 854 full history wraps, all
16 ring positions, all 16 old/new floor residues, all 256 request byte values,
9,302 distinct prices spanning 0–65535, maximum rolling sum 1,048,560, old/new
comparisons at equality and ±1, 2,819 BUY and 2,783 SELL transitions, and 3,789
held BUY / 4,043 held SELL cases. It includes 32 supplementary full-range seeds,
long sessions, carry/borrow bits, endpoint prices, unsigned boundaries and early
session resets. Expected replies agree with both the independent model and the
unchanged organizer full-range reference class before simulation.

## Limits and release

Official judge score and the hidden seed remain unverified. Qualification depends
on their run, their PC's latency and a rebuild of human-committed source. The final
Fmax is 108.334 MHz versus baseline 118.135; setup/hold slack is +27.806/+0.074 ns
versus +28.572/+0.425. Both pass the 27 MHz constraint, but the reduced hold margin
is disclosed. EX3791 bounded address truncation and PR1014 generic clock routing
remain in the saved logs. All six routed pins match the original CST.

The submission bitstream still contains the saved 236-Logic release. The optimizer
[skill](../../SKILL.md) says “the human copies the `.fs` and updates the hash in
`README.md` and `bitstream/README.md`.” Prepared replacement README files and
exact promotion/review/stage/commit/push commands are in REVIEW.md. No Git history
or remote action was performed. Ordinary regression regenerates
results/software_validation.json, results/simulation.log and session vectors.
