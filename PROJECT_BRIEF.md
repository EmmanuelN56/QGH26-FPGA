Experimental branch codex/lut-234: active src/ and bitstream/trade_core.fs are the 234-LUT candidate. Physical validation is pending. CANDIDATE.md identifies the build; historical release measurements below describe the archived 365-LUT baseline.

Recovery note (2026-10-03): the active repository is `C:/Users/Lenovo/Downloads/QuizletFPGA`. Exact source/build files were restored, but some later physical logs and original simulation logs from Ubuntu are missing. Fresh recovery results are separate. See [recovery inventory](docs/repository_recovery.md).

# Silicon Trade Core — Agent Project Brief

## Purpose

Build a synthesizable FPGA trading core for the Gator Quant Hacks 2026 Hardware Track. The target is a Sipeed Tang Nano 20K containing a Gowin GW2AR-18 FPGA. The design receives fixed-format UART packets, maintains an independent 16-price moving-average state for two items, emits the required trading actions, and is judged on correctness, latency, and LUT usage.

This file is the implementation contract for humans and coding agents. Do not change protocol or strategy semantics to make implementation easier. If an organizer-supplied guide, test, or announcement conflicts with this file, the organizer source wins and this file must be corrected.

## Current repository state

Organizer resources remain unchanged. The trading core now has independent per-item engines, an independent Python model, deterministic regression vectors, and packet integration. Icarus Verilog 12.0 simulations pass: RX/TX/top scaffold tests, 1,509 engine and full-system packets across 15 sessions, and 1,509 complete transactions at the actual 27 MHz / 115200-baud timing across all 15 expanded sessions. Software evidence is in `results/`.

The minimum configured response-gap release passed native Windows Gowin V1.9.11.03 Education synthesis and PnR: 365 LUTs, 296 registers, zero B-SRAM, eight SSRAM blocks, routed Fmax 75.176 MHz, setup/hold +23.735/+0.425 ns, and no reported setup/hold violations. All six pins match the unchanged CST; PR1014 remains. `top.TX_GAP_CYCLES=0` leaves three handshake idle clocks after each full UART stop bit. Seven candidate gaps passed authorized SRAM programming, organizer quick plus three robust runs, and 1,509 supplementary packets each. The selected release's final quick/three robust/stress capture passed with every returned field checked, including warm-up. Final organizer mean/max is 13.178/17.982 ms on the local PC; supplementary stress statistics are separate. The original COM4 receive timer was restored to 16 ms after authorized 2/1 ms experiments showed no repeatable benefit. Matching tested file: `bitstream/trade_core.fs`, SHA-256 `bc7edc25e995168772989e199c9cd43252f6120bec68e21fba034c8a35d4313d`. Evidence: `results/release_zero_gap_20261003T180901633856Z/`, `results/board_20261003T181026986060Z/`, `results/stress_20261003T181041984828Z/`, and `docs/latency_optimization.md`. The original 1 ms baseline (412 LUTs, 328 registers, 13.718/31.265 ms) remains archived under `results/build_windows_20261003/` and `results/board_20261003T064213338565Z/`. See `docs/board_bringup.md` for limitations and human release tasks.

Preserved organizer copies are located at:

- `constraints/19_tang_nano_20k.cst`
- `scripts/21_quick_uart_test.py`
- `scripts/22_robust_uart_test.py`
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

Reducing below 542 LUTs does not produce more than 15 LUT points. The UART/USB path dominates measured latency, so a reliable transport usually matters more than saving a few internal clock cycles.

## Optimization objective beyond the rubric

The human team clarified on 2026-10-03 that the rubric is the minimum eligibility bar. The active objective is LUT usage substantially below 300, removal of avoidable state/control duplication, and larger deterministic data suites. The lowest measured isolated candidate is 230 LUTs / 222 registers / 104 ALUs / 0 B-SRAM / 8 SSRAM; the 234-LUT alternative uses 72 ALUs and less total logic. Both passed original and additional simulations, including all 1,509 original packets at actual UART timing. The extra corpus has 13,508 packets across 31 sessions. The live source and bc7 release bitstream remain the physically validated 365-LUT design; new candidates are unprogrammed. See docs/lut_optimization_study.md and results/area_20261003T192105403559Z/study_summary.json. There is no proof of a global LUT minimum.

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

## Current status

Update this section at the end of each meaningful work session:

```text
Last known-good commit: edc3fae is the historical UART scaffold; current trading/latency changes are uncommitted, simulation- and physically validated
Last matching bitstream: bitstream/trade_core.fs; SHA-256 bc7edc25e995168772989e199c9cd43252f6120bec68e21fba034c8a35d4313d; authorized SRAM and final physical tests passed
Board detected: native Windows USB Debugger A, serial 2025030317, VID_0403/PID_6010; location 561, FPGA ID 0x0000081B
COM port: COM4 (interface B); host receive timer restored to original 16 ms and final capture passed
Simulation status: native Windows Icarus12 RX260/TX256/top3/engine1509/accelerated top1509/27MHz top1509 all PASS with release gap0; gap0/1/10 parameter boundary suite PASS
Reference model: byte-exact agreement with both unchanged organizer classes across1509 packets /15 sessions
Synthesis/PnR status: PASS, exact part/version;365 LUTs (42 LUT2/119 LUT3/204 LUT4),296 registers,0 B-SRAM,8 SSRAM; all pins match CST
Quick UART test: final physical PASS; programming/console/source evidence saved
Robust UART test: final3 runs PASS without reset/reprogram;84/84 scored packets and168/168 actions each; all300 CSV rows independently verified
Supplementary physical test:1509 exact replies /15 sessions, no timeout/extra bytes; separate latency statistics
Timing / physical latency: Fmax75.176 MHz; setup/hold+23.735/+0.425 ns; no reported violations; latest organizer mean/max14.105513/16.9418 ms on local PC; prior optimized capture13.177649/17.9824 ms
Optimization: configured gap1000us ->0clocks; simulated transaction8.397770 ->1.397588ms; internal delay removed; fresh mean host latency is higher than prior run, and system latency is PC-dependent; cached-project input guard fixed
Fresh organizer-rubric revalidation: quick + three robust runs PASS, all300 CSV rows verified, organizer mean/max14.105513/16.9418 ms; expanded physical1509/1509 across15 sessions PASS; COM4 timer16ms unchanged; local evidence supports85 points plus conditional0/8/15 latency points; see docs/grading_report.md and results/regrade_20261003T183908493740Z/
Known blockers: human metadata/Git review/commit/push/public repository/Devpost freeze; PR1014 retained; official latency score depends on judging-PC reference
Next smallest task: review 230-LUT versus 234-LUT area candidates and validate a selected identified bitstream physically before integration; continue LUT reduction experiments listed in docs/lut_optimization_study.md; human metadata/Git/submission freeze remains pending
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
