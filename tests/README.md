# Extended trading-core stress suite

This suite contains **118,212 request/answer pairs**, **758 sequential sessions**,
and **106,138 packets after warm-up**. The organizer robust practice test has
100 packets. The official tests are preserved unchanged.

The delivered CSV contains the answers already; no MVP, FPGA, serial port,
pyserial, network connection, or additional Python package is needed to read or
regenerate them. Python 3.10+ is sufficient. Validation here checks the answer
key and test tooling. **No MVP, synthesis, HDL simulation, or physical board was
tested by this suite. LUTs, hardware redundancy, timing, and board latency are
unmeasured.**

## Files and commands

Run from the repository root in PowerShell:

```powershell
python -m unittest discover -s tests -v
python scripts/stress_suite.py --output tests/vectors/stress
```

The full stress files are saved in the repository as reviewable artifacts:

| File | Purpose |
|---|---|
| `vectors/stress/answers.csv` | Requests, expected actions, exact response bytes, and internal arithmetic traces |
| `vectors/stress/requests.mem` | One 64-bit request per line, 16 hex digits, suitable for HDL `$readmemh` |
| `vectors/stress/responses.mem` | Corresponding 64-bit golden response per line |
| `vectors/stress/manifest.json` | Counts, coverage, seed, source hashes, and artifact SHA-256 hashes |
| `performance_measurements.template.json` | Empty fields for real baseline/candidate measurements |
| `test_stress_suite.py` | Offline regression tests and deliberate-fault detection |

`answers.csv` has a global zero-based `sequence` and a zero-based `session`.
`index` restarts at zero each session. Case labels describe the generator's
intent; repeated case labels can represent multiple resets. Route samples by
`tx_item1`/`tx_item2`; the `slot1_` and `slot2_` traces follow request slots.
`pointer` is the write/replacement pointer **before** ingesting the sample.
Empty `oldest`/`previous` fields mean no prior value exists during warm-up.
Sums and averages are decimal; packet strings are big-endian hexadecimal.
The final sweep ends at index 65535; it does not accidentally wrap into a reset.

For a smaller 29,636-packet corpus or new random data:

```powershell
python scripts/stress_suite.py --profile smoke --output .build/stress_smoke
python scripts/stress_suite.py --seed 0x12345678 --output .build/stress_other_seed
```

The seed changes the three additional random sessions and their slot placement.
The exact organizer practice replay, directed cases, and full sweep remain fixed.
The complete files total approximately 26 MB. They are for local verification;
host reference computation never belongs in the official decision path.
`.gitattributes` preserves their exact bytes across Git checkouts so Windows
line-ending conversion cannot invalidate the saved SHA-256 hashes.

## Coverage and expected behavior

| Family | Coverage | Required answer |
|---|---|---|
| Organizer replay | Exact 21-packet quick and 100-packet robust practice sequences | Same actions/bytes as the organizer models; warm-up wire actions NONE |
| Constants | 16 boundary prices, both fixed orders and alternating slots, 64 packets each | NONE throughout each session |
| Boundary pairs | All 256 ordered pairs from the 16-price boundary set; plateau, change, change back | Cross or retain action according to the 16-sample history |
| Small alphabet | All 81 four-sample motifs over `{0,1,2}`, repeated four times; all three next prices | Exact answer for each of the 243 motif/current combinations |
| Floor arithmetic | All 16 sum remainders, four baselines including high unsigned prices, three next-price deltas | Floor both averages; strict current-price and inclusive previous-price comparisons |
| Action retention | Multiple BUY/SELL crossings followed by non-crossings | Repeat BUY/SELL, never substitute NONE for a hold |
| Bit/byte boundaries | Walking 1 bits, `AA55`, `55AA`, `FF00`, `00FF`, 32767/32768, 65534/65535 | Unsigned arithmetic and exact wire byte order |
| Extreme replacement | Zero/max windows, repeated circular wraps, alternating endpoints | Sum range 0..1,048,560; replace the oldest sample |
| Session reset | Index-zero after 1/2/7/15/16/17/33 samples; repeated zero; reset after active actions | Clear both histories/actions before ingesting the new index-zero prices |
| Random | 8,192 packets each: 0..100, full uint16 range, 80% boundary-biased | Reference actions; independent item state under random slot swaps |
| Full sweep | 65,536 packets; A increases 0..65535 while B decreases 65535..0 | Every valid price for each item and every index echoed correctly |

The boundary set is
`0, 1, 2, 15, 16, 17, 255, 256, 257, 4095, 4096, 32767, 32768, 32769, 65534, 65535`.
The manifest verifies all 16 replacement pointers, all 16 floor remainders, all
nine previous/current comparison combinations (`<`, `=`, `>` relative to their
respective averages), and all nine slot-action pairs. It records the seven
reachable action transitions; BUY/SELL never transition back to NONE without a
session clear.

Each generated answer agrees with four computations:

1. A chronological list model that recomputes both sums from all prices.
2. A circular-buffer rolling-sum model.
3. The unchanged organizer quick-test `Reference` class.
4. The unchanged organizer robust-test `MovingAverageReference` class.

Only literal settings and the reference class are extracted from organizer
scripts using Python AST; their serial imports and transmission code are never
executed. Organizer classes return Python `None` during warm-up; the saved wire
answer uses the specified NONE byte (`00`). The test suite intentionally checks
warm-up response formatting/actions too, even though official correctness
scoring excludes warm-up.

Deliberate faults are detected for signed prices, stale warm-up previous prices,
replacement of the newest sample, 16/19-bit sums, rounded/floating averages,
comparison against the wrong average, strict previous-price comparisons,
inclusive current-price comparisons, and NONE on hold. Separate checks detect
fixed response slot order and missing session clearing. This shows the vectors
distinguish those faults; it does not constitute a test of absent hardware.

## Hand-calculated answers

After 16 samples of A=50 and B=100, the quick-test decisions are:

| Index | Request order and prices | Expected response hex |
|---|---|---|
| 16 | B=60, A=80 | `0010220111020000` |
| 17 | A=85, B=55 | `0011110222010000` |
| 18 | A=85, B=55 | `0012110222010000` |
| 19 | B=130, A=20 | `0013220211010000` |
| 20 | B=140, A=15 | `0014220211010000` |

At index 16, A's old sum is 800 and new sum is `800 - 50 + 80 = 830`.
The old/new averages are 50/51, so previous 50 <= 50 and current 80 > 51 means
BUY. B's old/new sums are 1600/1560 and averages 100/97, so previous 100 >= 100
and current 60 < 97 means SELL. At index 17, neither item crosses again, so
the last actions persist. Warm-up index 0 with A=50/B=100 returns
`0000110022000000`.

A floor-sensitive example starts with A's window `[1]*15 + [0]` and B's window
`[0] + [1]*15`. At index 16 send A=1 and B=0. Both old and new sums are 15,
so both old and new floor averages are zero. A buys; B holds NONE. The response
is `0010110222000000`. Rounded averaging misses A's BUY; floating-point
averaging incorrectly makes B SELL.

A window of sixteen 65535 prices has sum **1,048,560**. Replacing one with zero
gives sum **983,025** and new floor average **61,439**. Previous 65535 is at the
old average and zero is below the new average, so the answer is SELL. This
requires the full 20-bit sum and unsigned 16-bit prices.

## Checking a future implementation

Capture one complete response per request, in order, as a line of 16 hex digits.
A partial response may be saved as a shorter line and must end the real
stop-and-wait run. Do not insert blank/comment lines. Use the entire corpus in
order, without a physical reset between sessions; index zero performs the reset.
Use `sequence`, rather than the restarting index, to label capture rows.

```powershell
python scripts/verify_stress_responses.py --vectors tests/vectors/stress --responses .build/dut_responses.mem --report .build/dut_correctness.json
```

This checks echoed index, both item IDs/actions, reserved zero, and exact length.
Missing, partial, invalid-hex, and extra responses fail. Unreceived packets remain
in the denominator. All 118,212 packets must match for a local PASS. The report
also retains separate totals for the 106,138 decision packets and 212,276
decision actions. These larger local totals are not official judging scores.
Exit codes: 0=PASS, 1=mismatch/incomplete capture, 2=invalid key/input.

For board round-trip latency, save a separate CSV with columns
`sequence,latency_us`, one row per captured response attempt. Measure from
immediately before writing the request until its response is completely read,
using `time.perf_counter_ns()` as the organizer tests do. Include warm-up. Do
not supply time spent running the Python oracle or simulation time as board
latency. Add `--latencies .build/board_latency.csv` to the command above; the
report gives mean, p50, p95, p99, and maximum for complete responses. Percentiles
use nearest rank. Incomplete runs cannot pass the performance gate.

The following self-check exercises the checker with its own golden answers. It
must not be reported as an MVP or physical-board test:

```powershell
python scripts/verify_stress_responses.py --vectors tests/vectors/stress --responses tests/vectors/stress/responses.mem --report .build/answer_key_selfcheck.json
```

## LUT, latency, and redundancy acceptance

Copy `performance_measurements.template.json` into `.build/baseline_metrics.json`
and `.build/candidate_metrics.json`. Populate real measurements and source /
bitstream identities after each build. `luts` means Gowin's **total LUT** resource
line; also record registers, B-SRAM blocks, and worst timing slack at 27 MHz.
`resource_report`, `timing_report`, and `board_capture` identify preserved evidence;
`capture_kind` must be `physical_board`. `bitstream_sha256` identifies the exact
programmed file. `source_revision` should include the commit and identify any
uncommitted diff saved with that build. The checker treats these fields as
reported evidence; a human must inspect the files and verify their identities.

```powershell
python scripts/check_stress_metrics.py --correctness .build/dut_correctness.json --metrics .build/candidate_metrics.json --baseline .build/baseline_metrics.json
```

The local default gate requires 100% stress correctness, LUTs <=542, nonnegative
timing slack, mean physical round-trip <=20,782.5 us (1.25 x 16.626 ms), and
p99 <=33,300 us. The p99 limit is an extra team reliability budget, **not an
organizer scoring rule**. Adjust `--max-luts`, `--max-mean-us`, or `--max-p99-us`
to an agreed stricter target. Fill the baseline's `latency_us.mean`/`p99` from
its separate verified board report to report latency deltas too. Exit codes:
0=PASS, 1=failed budget/correctness, 2=INCOMPLETE measurements. A template or a
simulation capture cannot pass. The template's null values are not zero usage.

For each proposed optimization, keep both the baseline and candidate
correctness reports, total LUTs, registers, B-SRAM, timing, mean/p99/max physical
latency, exact source diff, bitstream hash, and board logs/CSVs. Run the same
corpus and multiple organizer practice runs under the same board/host settings.
Change one architectural choice per comparison. Inspect the synthesis hierarchy
and warnings for unused or duplicated arithmetic, unnecessarily wide operators,
shifted copies of windows, excessive reset logic, and failed RAM inference.
Input/output tests cannot prove there is no redundant internal logic. Separate
item state is required; two datapaths may be a legitimate latency trade-off.
Retain optimizations only after correctness and measured evidence justify them.

## Transport tests to run when HDL/board is available

The hex corpus tests complete packet contents. It cannot observe UART edges.
Use the existing RX/TX/top benches as transport references, then run the following
scheduled checks alongside the corpus. Their behavioral answers are specified
here, but execution is deferred until a working implementation is available.

| Stimulus | Expected behavior |
|---|---|
| Split a valid request after each byte position 1..7; idle 0, 1, 10, or 100 bit periods before the remaining bytes | No response before byte 8; then exactly the corpus answer |
| Whole requests with zero/minimal host pause between completed response and next request | One correct 8-byte response each; stop-and-wait still applies |
| All 256 byte values in RX unit stimulus; walking bits in TX stimulus | Exact byte reconstruction, one valid/done pulse each, valid stop bit |
| Idle for a second before/after a session | UART remains high; no unsolicited data |
| Assert the documented physical reset during a partial packet, release, then send index zero | Partial packet discarded; fresh complete request gives its golden answer |
| Monitor one second after the last response | No duplicate response or debug bytes |
| Record each response start and final stop bit in simulation | Response starts after the full request; record compute cycles separately from UART wire time |

Wire transfer alone takes `16 * 10 / 115200 = 1.3889 ms` per request/response.
Physical latency includes the USB bridge and response spacing; sweep response
spacing only with recorded board evidence. Preserve reliable byte delivery while
reducing delays. A full 118,212-packet board run would take roughly 33 minutes at
16.626 ms average, longer with extra idle checks or host overhead.

## Limits and unresolved organizer details

Valid prices/indices are unsigned 16-bit integers. Negative values, floats,
NaN/Infinity, strings, booleans, values >65535, unknown/duplicate item IDs,
nonsequential indices, and truncated requests are **not assigned invented trading
answers**. Host validation tests reject unsupported types instead of silently
wrapping/coercing them. TODO: obtain organizer rules before adding expected board
behavior for alternate encodings, duplicate IDs, index gaps, malformed frames,
packet timeout recovery, or overlapping requests. The existing protocol does not
define such extensions; a new organizer source must override this suite if the
protocol changes.

This exhausts each scalar price/index, the declared small-alphabet motif domain,
and boundary-pair domain. It does not exhaust all possible two-item 16-price
histories or all UART schedules. Different seeds and additional formal checks
can extend confidence when the MVP becomes available.

## Recorded offline validation

On October 3, 2026, Python 3.14.7 ran all **32 unit tests successfully**. Full
stress generation checked every one of the **118,212 answers** against the four
models listed above. The complete answer-key/checker round-trip passed with
118,212 matching packets and zero extra responses. Re-generation determinism,
artifact integrity, truncated captures, field mismatches, duplicate responses,
invalid latency values, and incomplete performance measurements are included in
the unit tests. These results apply to the local verification tools and golden
answers, not an MVP or physical board.
