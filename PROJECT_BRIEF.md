# Silicon Trade Core — Agent Project Brief

## Purpose

Build a synthesizable FPGA trading core for the Gator Quant Hacks 2026 Hardware Track. The target is a Sipeed Tang Nano 20K containing a Gowin GW2AR-18 FPGA. The design receives fixed-format UART packets, maintains an independent 16-price moving-average state for two items, emits the required trading actions, and is judged on correctness, latency, and LUT usage.

This file is the implementation contract for humans and coding agents. Do not change protocol or strategy semantics to make implementation easier. If an organizer-supplied guide, test, or announcement conflicts with this file, the organizer source wins and this file must be corrected.

## Current repository state

Organizer tests and constraints remain unchanged. Current source fingerprint
`cc8a88c20782` measures **186 synthesis Logic (186 LUT, 0 ALU, 0 RAM16),
92 registers, 4 B-SRAM and 186 routed Logic**. A fresh Gowin V1.9.11.03 Education
build reproduced the result at the unchanged 27 MHz target. Routed Fmax is
108.334 MHz, setup/hold slack +27.806/+0.074 ns, with zero reported violations.

The current top uses the shared one-bit digit-serial trade_pair, direct price-bit
selection from request B-SRAM, held item actions, a pointer/window-full flag,
shared packet byte count and a shared UART baud timer. The independent parallel
trade_engine remains separately testable. The seven-check standard regression
passes 1,609 session packets and 221 transactions at 27 MHz / 115200 baud.
The extensive suite passes 8,785 packets in both isolated-engine and full UART
simulation, with agreement between the independent model and organizer class.

The connected board was programmed with the exact final rebuilt file in SRAM.
Quick, five normal → full-range practice pairs (1,000 correct responses), and
8,785 extensive physical packets all passed without manual reset or reprogramming
between sessions. All five normal runs estimate 100/100 locally. Their mean
latencies span 16.527–18.948 ms; aggregate mean/max is 17.152/145.233 ms and median
of five run means is 16.740 ms. The extensive board run checked 17,570 item
actions, with no timeouts, mismatches or extra bytes; mean/median/max is
16.967/16.938/204.767 ms. Logs, every CSV row, hashes, source and per-module
breakdowns are in `results/logic_search_20261003/README.md`.

The lowest locally qualifying candidate tested removes 50 Logic and 79 registers
from the 236/171 baseline, using one extra B-SRAM. No accepted change lost the
local rubric; no global minimum or qualification-failure boundary is established.
Official judge and hidden-seed qualification remain pending. The tested file is
`results/logic_search_20261003/physical_final_best_five_runs/programmed.fs`, SHA-256
`6fbefe4697c714b18f78830088c826b2f7cc1e2823de0070a688c84f3f6a6e23`.
The selected submission copy `bitstream/trade_core.fs` contains this exact
186-Logic release. Fresh October 4 verification passed five normal runs (500
packets), five full-range runs (500), the modified full-range corpus (2,492),
and all 13 attached variant modes plus two additional random seeds (1,500).
Every one of the 4,992 robust packets and 9,984 actions, including warm-up,
matched the independent reference model, with zero timeouts or mismatches.
The board was programmed once and was not manually reset between these runs.
All five normal runs estimate 100/100 locally; the median of their means is
16.739245 ms. Source-matched simulation also passed these stimuli, including
200 normal/full-range packets at actual 27 MHz / 115200 baud timing.
Local verification artifacts are in `outputs/logic186_verification_20261004/`;
they are intentionally excluded from the selected submission commit.

Historical trading-core synthesis/PnR passed natively on Windows with Gowin V1.9.11.03 Education: 412 LUTs, 328 registers, zero B-SRAM, eight SSRAM blocks, routed Fmax 77.985 MHz, setup/hold +24.214/+0.425 ns and zero reported setup/hold violations. All six routed pins matched the unchanged CST; PR1014 remained. Build/source evidence is in `results/build_windows_20261003/`. That preserved design passed authorized SRAM programming, physical quick and three robust sessions; each robust run received 100 packets with 84/84 scored packets, 168/168 actions and zero timeouts. Every CSV row was independently checked. Combined physical mean/max latency was 13.718/31.265 ms on the local PC. Evidence and the matching tested `programmed.fs` are in `results/board_20261003T064213338565Z/`; these results do not validate the current source or current `bitstream/trade_core.fs`. The earlier UART-only Windows build at `edc3fae` reported 177 LUTs, 166 registers, zero B-SRAM, and PR1014. See `docs/board_bringup.md` for historical environment detection and release blockers.

Preserved organizer copies are located at:

- `constraints/19_tang_nano_20k.cst`
- `scripts/21_quick_uart_test.py`
- `scripts/22_robust_uart_test.py`
- `scripts/22_robust_uart_test_fullrange.py`
- `docs/official/SCORING_AND_RANKING_CLARIFICATION.md`
- `docs/official/GQH_Hardware_Track_Participant_Guide.pdf`
- `docs/official/21_quick_uart_test_REFERENCE.md`
- `docs/official/22_robust_uart_test_REFERENCE.md`
- `docs/official/JUDGING_AND_TESTING.md`
- `docs/official/REPOSITORY_STRUCTURE.md`
- `docs/official/SUBMISSION_CHECKLIST.md`
- `docs/official/TEAM_README_TEMPLATE.md`

Do not modify the protocol or expected-result logic in the organizer tests. Only change the configured serial port when required.

## Fixed hardware and tool target

- Board: Sipeed Tang Nano 20K
- FPGA: Gowin GW2AR-18, part `GW2AR-LV18QN88C8/I7`
- Clock: 27 MHz on `sys_clk`
- UART: 115200 baud, 8 data bits, no parity, 1 stop bit, LSB first
- Suggested reproducible tool version: Gowin EDA V1.9.11.03 Education
- Programming for local tests and judging: volatile SRAM mode using the generated `.fs` file

The top-level port names must match the supplied constraint file exactly. The published names are:

```text
sys_clk
reset_btn
uart_rx_i
uart_tx_o
led0_n
led1_n
```

Confirm these names against the actual supplied `.cst` before coding the top-level module.

## External protocol

### Request: judge PC to FPGA

Every request is exactly eight bytes:

```text
Byte 0  index[15:8]
Byte 1  index[7:0]
Byte 2  slot 1 item ID
Byte 3  slot 1 price[15:8]
Byte 4  slot 1 price[7:0]
Byte 5  slot 2 item ID
Byte 6  slot 2 price[15:8]
Byte 7  slot 2 price[7:0]
```

Packet fields use most-significant byte first. Bits within each UART byte are transmitted least-significant bit first.

### Response: FPGA to judge PC

Every response is exactly eight bytes:

```text
Byte 0  echoed index[15:8]
Byte 1  echoed index[7:0]
Byte 2  echoed slot 1 item ID
Byte 3  slot 1 action
Byte 4  echoed slot 2 item ID
Byte 5  slot 2 action
Byte 6  0x00
Byte 7  0x00
```

Exactly one response is allowed for each request. Do not transmit unsolicited bytes. Do not begin a response before all eight request bytes have arrived.

### Fixed identifiers

```text
Item A = 0x11
Item B = 0x22

NONE = 0x00
SELL = 0x01
BUY  = 0x02
```

The tester may place either item in either slot. State follows the item ID, while response ordering follows the request slots.

## Exact strategy semantics

Maintain the following state independently for Item A and Item B:

- Sixteen 16-bit unsigned prices
- A 4-bit circular write pointer
- A 20-bit unsigned rolling sum
- Previous 16-bit price plus a validity flag
- Last action
- Sample count or window-full flag

Packets with indices 0 through 15 warm up the windows and must return `NONE` for both items.

For index 16 and later, process each item using this order:

```text
oldest      = prices[write_pointer]
old_sum     = rolling_sum
old_average = floor(old_sum / 16) = old_sum >> 4

new_sum     = old_sum - oldest + current_price
new_average = floor(new_sum / 16) = new_sum >> 4

BUY  if previous_price <= old_average and current_price > new_average
SELL if previous_price >= old_average and current_price < new_average
else repeat last_action
```

After deciding the action:

```text
prices[write_pointer] = current_price
rolling_sum           = new_sum
previous_price        = current_price
write_pointer         = write_pointer + 1 modulo 16
last_action           = selected action
```

On a request with index zero, clear both item engines before ingesting that request's two prices. The physical board is not necessarily reset or reprogrammed between judging runs.

Do not replace the required floor averages with rounded averages. Do not use packet slot as the state key. Do not substitute a different trading strategy.

## Proposed module architecture

Keep transport, packet handling, and strategy logic separate:

```text
uart_rx_i
   |
   v
+----------+   byte/valid   +-------------------+
| UART RX  | -------------> | packet_controller |
+----------+                +-------------------+
                                    |
                             decoded request
                                    |
                                    v
                         +-----------------------+
                         | item router / control |
                         +-----------------------+
                              |             |
                              v             v
                       +------------+  +------------+
                       | item A     |  | item B     |
                       | state      |  | state      |
                       +------------+  +------------+
                              \             /
                               response actions
                                      |
                                      v
                         +-----------------------+
                         | response byte builder |
                         +-----------------------+
                                      |
                                byte/start
                                      v
                                 +---------+
                                 | UART TX |
                                 +---------+
                                      |
                                  uart_tx_o
```

Suggested files:

```text
src/top.v
src/uart_rx.v
src/uart_tx.v
src/packet_controller.v
src/trade_engine.v
constraints/19_tang_nano_20k.cst
testbench/uart_rx_tb.v
testbench/uart_tx_tb.v
testbench/trade_engine_tb.v
testbench/top_tb.v
scripts/reference_model.py
```

Start with two `trade_engine` instances because that is easiest to verify. Consider sharing one arithmetic datapath only after a correct synthesis shows that LUT usage needs improvement.

## Internal interface contract

Use one-clock `valid`, `start`, and `done` pulses unless a ready/valid handshake is explicitly documented.

Recommended UART receiver interface:

```text
Inputs:  clk, reset, uart_rx_i
Outputs: rx_byte[7:0], rx_valid, framing_error
```

Recommended UART transmitter interface:

```text
Inputs:  clk, reset, tx_byte[7:0], tx_start
Outputs: uart_tx_o, tx_busy, tx_done
```

Recommended trade-engine transaction interface:

```text
Inputs:  clk, reset, session_clear, sample_valid,
         price[15:0], warmup
Outputs: action[7:0], action_valid
```

Document any change to these interfaces before two teammates implement dependent modules.

The request-price RAM experiment replaces `trade_pair.price1/price2` with
`price_word[15:0]` and `price_read_slot`. The controller stores each completed
price in synchronous B-SRAM. The pair prefetches slot zero while idle and requests
slot one during its first FINISH cycle. Direct bit selection eliminates the
additional price register and its FETCH_SLOT cycle. Reads and writes never share a cycle; session clear still precedes the
one-clock sample pulse. This interface passed measured builds and board tests.

The shared UART timer adds optional `SHARE_TIMER`, `shared_timer`,
`timer_reload`, and `timer_reload_value` connections to RX and TX. RX also takes
`timer_pause`, preventing a new receive start while TX owns the timer. Standalone
modules default to their local timers. The top shares a counter for the protocol's
receive-then-respond transactions, with TX reload taking priority. UART framing,
start confirmation, synchronizers and full stop periods remain required.

The request RAM stores the complete 16-bit index in word two
of the existing request RAM. Index-zero and warm-up flags are latched while its
low byte arrives. During response transmission the RAM read address selects the
index; before sample acceptance it selects slot zero. The SEND handshake provides
the synchronous read cycle before the transmitter accepts the first index byte.

Direct price bit selection keeps the request RAM price stable throughout
each strategy operation and selects its arithmetic digit using `digit*W`. Digits
above the 16-bit price width return zero; the rolling sum retains all 20 bits.
Slot-one prefetch remains separate from computation, and response RAM indexing
begins only after pair completion.

The controller holds `tx_byte` stable throughout WAIT_DONE; the integrated
recovery bench checks this as well as one-clock handshake pulses. A held-input
transmitter experiment grew Logic and was rejected; TX retains its stop-marker
shift register and captures the complete input byte on its start pulse.

## Realistic implementation sequence

### Phase 0 — establish ground truth

1. Obtain the official guide, `.cst`, and two Python tests.
2. Commit their unmodified originals.
3. Confirm the exact top-level pin names and active level of optional reset/LED signals.
4. Read the software reference logic inside the robust test.
5. Write at least five hand-calculated examples covering warm-up, BUY, SELL, HOLD, and slot swapping.

Exit criterion: both teammates agree on byte order, update order, reset semantics, and expected examples.

### Phase 1 — software reference model

1. Implement a small bit-exact Python model independent of the organizer test.
2. Represent Item A and Item B with separate state objects.
3. Generate deterministic sequences for warm-up and crossings.
4. Compare the model against the organizer reference model when available.

Exit criterion: generated expected responses agree byte-for-byte with the organizer model.

### Phase 2 — strategy engine in isolation

1. Implement one `trade_engine` using explicit unsigned widths.
2. Test window fill, circular replacement, rolling-sum arithmetic, equality boundaries, held actions, and session clear.
3. Instantiate it twice or run the same testbench for both item identities.

Exit criterion: all reference vectors pass without any UART logic.

### Phase 3 — UART modules in isolation

1. Implement the receiver with start-bit detection and center-of-bit sampling.
2. Implement the transmitter with start, eight data, and stop bits.
3. Use a 27 MHz to 115200 baud timing scheme with acceptable error.
4. Test back-to-back bytes, idle gaps, malformed start/stop timing, and reset during idle.

Exit criterion: UART testbenches reconstruct every byte exactly and expose no duplicate `valid` or `done` pulses.

### Phase 4 — packet controller and integration

1. Collect exactly eight request bytes.
2. Decode the two slots.
3. If index is zero, clear both engines before accepting the new samples.
4. Route each slot to the correct item engine by ID.
5. Preserve request slot order when building the response.
6. Send exactly eight response bytes and then return to receive state.

Exit criterion: top-level simulation passes multiple complete sessions, including a slot swap on every packet.

### Phase 5 — synthesis and board bring-up

1. Create the Gowin project for `GW2AR-LV18QN88C8/I7`.
2. Add synthesizable HDL only; do not add testbenches as synthesis sources.
3. Add the official `.cst` and select the real top module.
4. Synthesize and complete Place & Route.
5. Review warnings, timing, total LUTs, flip-flops, and block RAM usage.
6. Generate the `.fs` bitstream.
7. Program SRAM mode and run a minimal physical UART test.

Exit criterion: the board enumerates, programs successfully, and returns one correctly formatted response.

### Phase 6 — organizer tests

1. Run `21_quick_uart_test.py`.
2. Fix transport and formatting failures before continuing.
3. Run `22_robust_uart_test.py` repeatedly.
4. Preserve every CSV with the source commit and bitstream identity.
5. Test multiple sessions without power cycling.

Exit criterion: repeatable 100-packet passes, not a single lucky pass.

### Phase 7 — optimization

Optimize only after correctness is repeatable.

1. Record a baseline: packet accuracy, action accuracy, mean/max latency, LUTs, registers, RAMs, and timing slack.
2. Change one architectural feature at a time.
3. Re-run simulation, synthesis, and physical robust tests after each change.
4. Keep a change only if measured evidence improves the target without reducing reliability.

Promising changes:

- Rolling sum instead of re-summing 16 values
- Exact 20-bit sum and 16-bit price widths rather than generic 32-bit integers
- Circular buffer rather than shifting all 16 entries
- Logical invalidation on session reset rather than clearing every price register
- Block SRAM inference or explicit Gowin B-SRAM only if it lowers scored LUT usage
- Time-multiplexed arithmetic across the two items if duplicated arithmetic is expensive
- Minimal response construction and control logic
- The shortest empirically reliable UART inter-byte spacing

Do not optimize by changing externally visible behavior.

### Phase 8 — release

1. Produce a clean build from the documented tool version.
2. Run final simulation and physical quick/robust tests.
3. Commit source, constraints, reproducible project files, test evidence, and the matching `.fs`.
4. Record the final full Git commit SHA.
5. Verify the repository is accessible to judges.

## Scoring-aware priorities

Correctness dominates. According to the published track page, latency and LUT points are zero when packet correctness is below 95%.

- Packet correctness: 50 points
- Individual action correctness: 20 points
- Average round-trip latency: 15 points
- Total LUT usage: 15 points

Published reference targets:

- Reference latency: 16.626 ms
- Full latency points within 1.25x, approximately 20.8 ms
- Partial latency points within 2x, approximately 33.3 ms
- Reference size: 542 LUTs
- LUT score: `15 * min(1, 542 / implementation_LUTs)`

The supplied organizer scoring/ranking clarification adds qualification and placement rules. Qualification requires 100/100 on the official run, followed immediately without reprogramming by a hidden full-range unsigned 16-bit run with every packet/action correct and no timeouts. Qualified teams rank by lowest total synthesis Logic (LUT, ALU and other logic types combined), then fewest registers, then lower median latency over five runs; latency within 5% ties. B-SRAM is allowed and excluded from Logic. Judges rebuild committed source using Gowin V1.9.11.03 and the submitted project settings, and check that rebuilt behavior matches the submitted .fs.

Reducing below 542 LUTs does not improve the capped rubric score, but reducing total Logic does improve qualified placement. Optimize total Logic while retaining the 100-point rubric and perfect full-range correctness. Local practice results can estimate qualification; they cannot certify the official run or hidden seed on the judging PC. The UART/USB path dominates physical latency, so measure it on the board for accepted candidates.

## Two-person ownership plan

### Teammate A — transport and physical build

- `uart_rx.v`
- `uart_tx.v`
- Gowin project and constraints
- Board detection and programming
- Physical serial tests
- Synthesis and timing/resource reports

### Teammate B — model and strategy verification

- `reference_model.py`
- `trade_engine.v`
- Unit-level HDL testbenches
- Boundary, reset, and slot-swap vectors
- CSV analysis and evidence documentation

### Shared integration

- `packet_controller.v`
- `top.v`
- Full-system testbench
- Robust-test debugging
- Final optimization decisions
- README and release checklist

Humans own branch and history actions. Assign a single temporary owner to shared files during each integration session; coding work stops after edits, tests, and review commands.

## Git authorship and agent restrictions

All Git history and remote actions are human-owned. Coding agents may edit files, run tests, and use read-only Git inspection commands, but must never execute:

```text
git add
git commit
git push
git tag
git merge
git rebase
```

Agents must not create pull requests or add AI attribution, bot signatures, generated-by notices, or `Co-authored-by` trailers. After completing work, an agent should report the changed files and provide explicit review/stage/commit/push commands for a teammate to run manually.

Humans should inspect every change before staging it. Prefer explicit paths rather than `git add .` so unrelated work is not included accidentally.

## Definition of done

The project is complete only when all of the following are true:

- HDL synthesizes and Place & Route completes for the exact target part.
- Top-level ports match the organizer `.cst`.
- The `.fs` programs successfully in SRAM mode.
- Every request receives exactly one eight-byte response.
- Warm-up, crossings, held actions, slot swaps, and repeated sessions match the reference model.
- Quick and robust organizer tests pass repeatedly on the physical board.
- Latency and total LUT count are recorded from the final build.
- Source, project files, constraints, tests, results, README, and matching `.fs` are committed.
- The final commit SHA is recorded for submission.

## Historical optimization measurement — 2026-10-03

Frozen source fingerprint: `f90016e33d1c`; snapshot `.build/opt/baseline_20261003`, with durable source, hashes, reports and matching bitstream in `results/optimization_20261003/baseline/`. Fresh Gowin V1.9.11.03 Education synthesis/PnR passes for the exact part: 236 synthesis Logic, 237 routed Logic, 232 LUT, 4 ALU, 171 registers, 0 SSRAM, 3 B-SRAM; routed Fmax 118.135 MHz, setup/hold +28.572/+0.425 ns, zero reported violations. PR1014 remains.

The sole experiment in that earlier session changed `trade_pair` default `W=1` to `W=2`. It passed all six regression checks and routing, but measured 248 synthesis Logic, 249 routed Logic, 244 LUT, 4 ALU, 170 registers, 0 SSRAM, 3 B-SRAM; routed Fmax 120.636 MHz, setup/hold +28.748/+0.341 ns, zero reported violations. It was rejected under Logic-first ranking. Exact frozen `src/`, `gowin/`, and `constraints/` were restored for that session, along with matching baseline software evidence. Saved experiment files remain available locally for comparison; generated `.build/` caches are not submitted build inputs.

Simulated final-byte-to-response turnaround was 10.926210 Âµs before and 5.592738 Âµs during the experiment. Physical mean/max latency is **unmeasured for both source snapshots**. The historical physical test evidence below describes its preserved source and `results/board_20261003T064213338565Z/programmed.fs`, not the current baseline. The current untouched `bitstream/trade_core.fs` hashes to `cd708e137d143bdf52ca2ea6fe5ede4e09f18ba7849cd643ac7a7b0d5641c6e2`, which differs from that historical programmed file. At the end of that initial measurement session, zero-gap physical validation and the full-range script were still pending. The October 4 search described above supersedes that status and supplies both the recovered unchanged full-range test and current physical evidence.

## Current status

```text
Verified candidate branch/commit: codex/logic-186 at 343217213e21871eab12bd07e7c4edc024e0df0d; eight synthesis/build inputs match the measured source
Matching tested bitstream: SHA-256 6fbefe4697c714b18f78830088c826b2f7cc1e2823de0070a688c84f3f6a6e23; outputs/logic186_verification_20261004/candidate.fs
Fresh build: Gowin V1.9.11.03 Education; 186 synthesis/routed Logic, 186 LUT, 0 ALU/RAM16, 92 registers, 4 B-SRAM; configuration equals archived candidate except creation-time comment
Fresh physical validation: quick PASS; normal500/500; fullrange500/500; modified2492/2492; attached variants1500/1500; all9984 robust actions correct including warmup; zero timeouts/mismatches
Fresh simulation: accelerated normal/fullrange200, modified2492, variants1500 PASS; actual27MHz/115200 normal/fullrange200 PASS
Board: USB serial2025030317, COM4, volatile SRAM; programmed once for entire sequence; no manual reset/reprogramming between sessions
Normal local rubric: all five runs estimate100/100; median of five means16.739245ms; official judge/hidden-seed qualification pending
Publication: selected release files are the186 candidate; README and bitstream README identify its tested hash; human Git/submission freeze remains required
Existing capture_board_tests.py modifications, SKILL.md, and zip review outputs remain separate; no Git history/remote actions performed by verification
Next step: human promotes selected source/tests and exact186 .fs to main, verifies public repository, pushes, and submits final commit SHA on Devpost
```

## Common failure modes

- Byte 8 is decoded from an old request-buffer value on the same clock it arrives.
- Item histories follow slot 1/2 rather than item ID 0x11/0x22.
- Index-zero clearing happens after, rather than before, ingesting the new samples.
- The first trading decision occurs one packet too early or late.
- Old and new sums are confused because clocked HDL assignments update together.
- Arithmetic silently becomes signed or the rolling sum is narrower than 20 bits.
- Reset loops prevent RAM inference or create excess reset logic.
- B-SRAM is treated as asynchronous even though the chosen mode has synchronous reads.
- `tx_start` remains asserted and transmits the same byte more than once.
- Response bytes follow engine order rather than original request-slot order.
- Debug text or unsolicited status bytes contaminate the binary UART protocol.
- The recorded `.fs`, resource report, and source commit come from different builds.

## Research guidance

Implementation-focused references and an annotated reading order are maintained in:

- `outputs/fpga_architecture_literature_review.md`
- `outputs/fpga_architecture_literature_review.provenance.md`

For this project, vendor documentation and measured synthesis reports are more directly actionable than papers about large exchange-grade FPGA systems. Use papers for architectural principles; use Gowin documentation and experiments for decisions about this specific FPGA.
