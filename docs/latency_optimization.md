Recovery note: historical results below predate deletion of the Ubuntu working folder. Exact builds were recovered; some original logs are missing. See [recovery inventory](repository_recovery.md) and fresh recovery validation files.

# Latency audit and candidate review



The selected release is `bitstream/trade_core.fs` with zero configured gap. Seven isolated candidates passed simulation, synthesis/PnR, authorized SRAM programming, the organizer quick test, three robust runs, and 1,509 supplementary packets each. Final release validation passed; organizer mean/max is 13.178/17.982 ms. The full stop bit and three handshake idle clocks remain.



## Audit findings



- The seven 1 ms response gaps add 7 ms per transaction. The engine/controller takes five clocks (185.190 ns) from acceptance of request byte eight to the first TX start. Removing every remaining TX handshake would save under 0.8 us per response; USB/host timing needs physical measurement.

- The original full-system benches forced the 1 ms gap. They now accept a parameter and enforce both minimum and maximum frame spacing. Zero, one and ten cycle configurations each passed all 1,509 regression packets at accelerated timing.

- The cached Gowin project could refer to an old absolute source directory. A guard now refuses stale, incomplete or disabled source lists before reopening it. All candidates below used fresh native projects and were unaffected.

- Physical capture now checks every CSV field against the independent model, including warm-up, and ties a custom candidate to its build/source hashes. A supplementary capture checks all 1,509 packets across 15 sessions, including transport errors and unsolicited bytes.

- The former 100/100 estimate is conditional: saved runs support full local correctness, and 412 LUTs qualify for the full LUT allocation if the correctness gate is met. Official latency points use a reference run on the same judging PC; no guaranteed official score is claimed.



## Before and after



All builds target GW2AR-LV18QN88C8/I7 version C at 27 MHz. All use the unchanged organizer CST, pass the six-pin check, and have zero reported setup/hold violations. All use 0 B-SRAM and 8 SSRAM blocks. PR1014 remains.



| Configured gap | LUTs | Registers | Fmax MHz | Setup/hold ns | Simulated transaction ms | Physical mean/max ms |

| --- | ---: | ---: | ---: | --- | ---: | --- |

| Baseline 1000 us | 412 | 328 | 77.985 | +24.214 / +0.425 | 8.397770 | 13.718 / 31.265 |

| 500 us (13500 clocks) | 390 | 311 | 81.792 | +24.811 / +0.425 | 4.897679 | 13.460 / 23.130 |

| 250 us (6750 clocks) | 386 | 309 | 78.192 | +24.248 / +0.425 | 3.147634 | 14.332 / 23.779 |

| 100 us (2700 clocks) | 384 | 308 | 76.775 | +24.012 / +0.425 | 2.097606 | 13.621 / 60.618 |

| 10 us (270 clocks) | 377 | 305 | 75.032 | +23.709 / +0.329 | 1.467590 | 14.772 / 114.608 |

| 1 us (27 clocks) | 374 | 302 | 73.884 | +23.502 / +0.340 | 1.404588 | 14.388 / 24.211 |

| 0.037037 us (1 clocks) | 385 | 313 | 78.190 | +24.248 / +0.425 | 1.397847 | 13.480 / 18.222 |

| 0 us (0 clocks) | 365 | 296 | 75.176 | +23.735 / +0.425 | 1.397588 | 13.466 / 19.403 |



Each candidate passed the three-packet reset/transport test and 221 complete transactions at 27 MHz / 115200 baud. The accelerated 1,509-packet boundary runs complement these tests; they do not model the USB bridge. Simulated transaction time starts at the first request start edge and ends at the final response stop-bit center. It includes a deliberate two-bit pause before request byte eight (17.361111 us at 115200 baud), and excludes USB/host overhead. Gap zero still leaves three controller clocks (about 111 ns) of idle beyond the complete stop bit. The organizer requires idle/buffering and warns that too little spacing can drop bytes.



## Exact candidate identities



Baseline / rollback: `e0b5bdc80f568ba7e7036693b6aa08fe2e0708843aa295db5cc83fca105afce7`.



| Candidate | SHA-256 |

| --- | --- |
