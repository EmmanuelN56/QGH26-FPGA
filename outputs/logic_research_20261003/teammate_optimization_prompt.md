# Handoff: minimize total Logic while preserving qualification

Work on the native Windows Tang Nano 20K trading-core repository. Read AGENTS.md and PROJECT_BRIEF.md completely, then the organizer guide, scoring clarification, normal test, and full-range test. Organizer artifacts override conflicting repository prose. Inspect the actual checkout and teammate's latest evidence before choosing a baseline; some older status paragraphs describe superseded implementations.

Implement and measure the optimization experiments below. The objective is the best competition-ready design we can demonstrate, not the smallest standalone LUT number. Do not claim a global minimum or guaranteed win. Preserve the best known-good candidate throughout.

## 1. Objective, baseline, and ownership

Qualification requires 100/100 on the official judge run, followed immediately by a hidden unsigned-16-bit full-range run with every packet/action correct and no timeouts, without reprogramming. Qualifiers rank lexicographically by total synthesis Logic, total registers, then median latency over five runs; latency differences within 5% are tied. BSRAM is permitted and excluded from Logic. The judges rebuild using Gowin V1.9.11.03 and committed project settings.

Use exactly GW2AR-LV18QN88C8/I7, the supplied CST, 27 MHz, and 115200-baud 8N1. Preserve the existing documented device version and timing constraints. Do not remove constraints, ports, or required behavior to improve the report.

The archived context_ram baseline is at results/area_20261003T192105403559Z/context_ram/source/. Its synthesis summary is Logic 312 (272 LUT, 40 ALU), Register 179, one BSRAM, zero SSRAM. Its primitive LUT count is 271; routed Logic is 316. Fmax is 102.750 MHz, with setup/hold +27.305/+0.425 ns. Archived bitstream SHA-256: 825bf4d70b30f3ed7f01a09e725d65304f37f7b26c551289ea06fd13b947ef8d.

The 234-LUT candidate actually has 354 Logic; the 230-LUT candidate has 382. Existing reports establish that their distributed RAM contributes to Logic. Do not repeat the previously incorrect totals 314/342 or add one Logic unit per RAM16. Read the complete Resource Usage Summary row directly, saving both synthesis and routed totals separately.

First determine whether the teammate already has a better validated version. Preserve that version and the archived 312 baseline. Reproduce baseline tests and synthesis before optimizing. If a baseline discrepancy appears, resolve its source/settings identity before comparing experiments. Work in isolated experiment directories; do not overwrite archived results or unrelated edits.

All Git history and remote actions belong to the humans. Never execute git add/commit/push/tag/merge/rebase or create a PR. At completion provide explicit human review/stage/commit/push commands. Do not add attribution notices or signatures. For new board programming, follow the team's authorization requirements for the specific candidate; authorization of an old bitstream is not authorization to program every new one.

## 2. Invariants that every implementation must preserve

Prices are unsigned 16-bit values, 0 through 65535. A full sixteen-price sum needs 20 bits; its maximum is 1,048,560. Preserve all bits regardless of the current practice seed.

Request bytes are [index_hi,index_lo,id1,price1_hi,price1_lo,id2,price2_hi,price2_lo]. Response bytes are [index_hi,index_lo,id1,action1,id2,action2,0,0]. Exactly one complete response follows each complete request. No unsolicited bytes, partial responses, or response before the eighth request byte. UART bits are LSB first; multibyte fields are big-endian.

Items 0x11 and 0x22 have independent histories and held actions; response order follows input slots. An index-zero packet logically clears both items before ingesting either new price. Warm-up indices 0 through 15 return NONE. New sessions must work without reprogramming or physical reset.

For each later sample: old_average = old_sum >> 4; new_sum = old_sum - oldest + current_price; new_average = new_sum >> 4. BUY when previous_price <= old_average AND current_price > new_average; SELL when previous_price >= old_average AND current_price < new_average; otherwise retain the last action. NONE=0, SELL=1, BUY=2. Update history, sum, previous price, and pointer exactly once. Do not substitute rounded averages, signed comparisons, or truncated sums.

## 3. Arithmetic experiments: highest priority

The existing context candidate already shares one strategy engine across both items and stores history, sums, and previous prices in BSRAM. It still has parallel sum arithmetic and a separate comparison path. Inspect the mapped hierarchy to confirm current costs.

A. Implement a scheduled shared parallel arithmetic/comparison variant. Reuse one add/subtract network for old-price comparison, removal of oldest, addition of current, and new-price comparison. Store only the comparison flags needed later. Compare the saved arithmetic against additional operand muxes, preservation registers, and control. Retain this as an independent candidate even if serial arithmetic wins.

B. Implement reusable arithmetic with digit widths W=1,2,4,8. Use a small W-bit addition/subtraction unit, carry/borrow state, digit counter, and operation sequencing. Share across both items and across compatible arithmetic/comparison operations. Compile-time width selection must remove unused alternatives; do not synthesize four engines together. Document handling of the partial final digit for widths that do not divide 20, especially W=8.

For LSB-first subtraction A + ~B + carry, initialize carry to 1; for addition initialize it to 0. Mask widths explicitly. Final carry means no borrow for equal-width unsigned subtraction. Accumulate equality over every valid bit. Derive unsigned comparisons correctly: A<B iff no-borrow carry is 0; A>=B iff it is 1; A<=B iff borrow or equality. On the final cycle use the just-computed carry/equality, not the previous clock's registers. Exhaustively verify the small digit cell and verify complete 16-/20-bit operations against an independent model.

Compare previous_price with old_sum[19:4] before destroying information needed for that comparison. Compare current_price with new_sum[19:4] only after the new sum is correct. Floor division discards bits [3:0]; no rounding. A streamed comparison must align bit zero of the price with bit four of the sum. Prefer separate passes initially. Fusing sum arithmetic and comparison requires independent carry state and may require additional hardware; do not assume one adder performs both simultaneously for free.

Treat W=4 as a serious contender, not a fallback. W=1 minimizes the arithmetic slice but may lose to counters, selectors, and storage. Choose by complete top-level Logic, then registers, with qualification preserved.

## 4. Memory and operand movement: optimize with the arithmetic

Keep the circular histories in BSRAM and preserve logical invalidation. On a new session, stale sum/history/previous-price data must be masked until valid. Do not introduce a whole-history reset loop that converts RAM into registers or distributed RAM.

For the best serial/digit variants, compare two operand organizations:

- Existing word-wide BSRAM with fixed-distance shifting of short temporary registers.
- Digit-organized BSRAM supplying 1/2/4/8 bits per step, with address fields formed by concatenating item, field/sample, and digit where practical.

Avoid wide variable-index bit selection, variable barrel shifts, and arithmetic address calculations when simple wiring suffices. Measure rather than assuming a shorter RTL expression maps smaller. Include every temporary register, mux, write-enable decoder, and address counter in the comparison. More BSRAM blocks are acceptable if their interface reduces total Logic; do not minimize the block count as an independent objective.

Consult Gowin UG285 and installed device libraries for exact primitive parameters, supported port widths, read latency, and collision behavior. The vendor documents narrow ports, but GW2A dual-port BSRAM does not support read-before-write. Capture outgoing history explicitly before replacing it; never depend on an unsupported same-address collision. Match simulation to the selected primitive/mode and verify inferred memory types after synthesis.

Do not replace the complete history with flip-flop shift registers merely because an ASIC SERV example used a small shift-register file.

## 5. Remove control and packet redundancies

Run isolated experiments and combine only measured winners:

- Replace a duplicate fill counter with circular pointer plus window-full/empty state where equivalent. Distinguish an empty session from a full window whose pointer wrapped to zero. Do not assume packet index can replace sample-history state without proving the organizer's behavior permits it.
- Simplify RAM field/address decoding and repeated read/write phases. Reuse counters only when their lifetimes cannot overlap. Derive a cycle schedule before folding states.
- Inspect packet storage. The current shared request/response buffer is already reused. Consider storing only variable fields and a slot-order flag, reconstructing fixed IDs/reserved bytes, but only when the organizer contract guarantees those IDs and all valid slot permutations remain exact. Measure the added decode logic; fewer registers alone do not justify greater Logic.
- Remove redundant scratch copies and reset muxes only where every read is preceded by a guaranteed write. Prove that physical reset, index-zero reset, partial packets, and warm-up cannot expose stale or unknown data.
- Compare binary, one-hot, and output-oriented/manual phase encodings on the surviving architecture. Verify the actual synthesis encoding rather than relying on an RTL attribute being honored. Published Xilinx FSM percentages are not Gowin predictions.

UART changes are lower priority: the archived RX/TX already use about 32/33 LUTs. BasicUART's approximately 40 LUTs per module on iCE40 does not establish savings. Retain RX synchronization, start/stop validation, framing recovery, full stop-bit duration, and one-clock handshakes. If measuring registered terminal counts, smaller counters, or buffer elimination, run transport-specific tests. A ready-to-queue indication during a stop bit is not tx_done. Do not shorten a stop bit to reduce latency.

## 6. Timing budget and measurement

At 27 MHz one cycle is approximately 37.04 ns. A twenty-bit operation takes twenty arithmetic cycles at W=1 or five at W=4, before memory/control overhead. Two sum operations plus two sixteen-bit comparisons per item would total 144 W=1 arithmetic cycles for both items, about 5.33 microseconds, if one digit is processed per cycle. That is a scheduling estimate, not a measured implementation.

An ideal eight-byte 115200-baud 8N1 transfer takes about 694.44 microseconds in one direction. This suggests room for additional internal cycles, but host/USB timing and qualification must be measured. Record last-request-byte to first-response-bit cycles separately from complete host round-trip latency. Check the actual organizer latency formula and threshold; do not assume historical PC measurements establish the judging score. Maintain positive setup/hold margins for the fixed 27 MHz clock and document warnings.

## 7. Correctness and expanded regression gate

Before changes, confirm that the independent reference model agrees with the organizer model. Keep organizer files unchanged except PORT. Test the active strategy module used by top, including trade_pair when applicable, rather than only a legacy trade_engine module.

Use scripts/verify_fullrange_candidates.py and the existing test infrastructure after inspecting their options and source. Reproduce the saved 4,176 strategy and accelerated-UART packets plus the exact 200-packet normal-then-full-range sequence at real 27 MHz/115200 timing, without an intervening reset. Re-run relevant original regressions as well. These counts are a minimum comparison baseline, not a substitute for new coverage.

Expand the independent corpus with deterministic seeds and directed cases covering:

- 0, 65535, constant extrema, maximum rolling sum, alternating extrema, monotonic ramps, sawtooth sequences, impulses, and repeated prices.
- 32767/32768 and every power-of-two carry/borrow boundary; floor-average residues 0 through 15; exact equality and one above/below old/new averages.
- BUY/SELL transitions, held BUY/SELL, warm-up boundary indices 15/16/17, all history-pointer wraps, long runs, swapped slots on every packet, and independent item activity.
- Normal/full-range/normal/full-range sessions back-to-back, repeated index-zero restarts, restart after a partial warm-up, and physical reset behavior where specified.
- UART 0x00/0xFF/0x55/0xAA, complete byte coverage, legal back-to-back frames, permitted inter-byte gaps, invalid start/stop recovery, partial-packet behavior, and no duplicate/lost response pulses.

Keep expected values independent of the optimized arithmetic. Compare every returned byte, including warm-up actions and reserved zero bytes. Add assertions for sum/history consistency, carry sequencing, RAM read latency, and single update/response per request. Adapt bench connections for changed interfaces without weakening the oracle.

## 8. Evidence, selection, and physical handoff

For every experiment record source hash, tool version/settings, correctness, total synthesis Logic, summary/primitive LUTs, ALUs, registers, BSRAM/SSRAM, routed Logic, timing, warnings, internal cycle latency, and physical latency status. Save raw reports and logs in new directories. Explain failed experiments and why they lost. Use full builds of promising survivors; reject resource gains caused by pruned or disconnected functionality.

Physical-board results may remain pending during implementation. Do not claim qualification from simulation. Once the team authorizes the selected bitstream, run the unchanged quick test and official normal test followed immediately by full-range practice without reprogramming; also run the expanded suite. For finalists, collect five repeatable normal/full-range pairs and compute the specified median consistently. Hold board/host/USB settings constant, save raw CSVs/logs, and associate them with source and bitstream SHA-256. The hidden judge run remains untested.

Deliver: a baseline-versus-candidate table; the smallest correct candidate and close alternatives; explanation of each retained change; reproducible clean-build/test commands; source/report/bitstream identities; qualification evidence or explicit pending status; and exact human Git commands with explicit file paths. Finish the finite experiment matrix or document concrete blockers. Do not stop at proposing changes, and do not replace a working baseline with an unverified area result.

## Primary references

Use these for implementation principles, not portable area predictions:

- SERV README and ALU: https://github.com/olofk/serv and https://github.com/olofk/serv/blob/main/rtl/serv_alu.v
- Isshiki/Dai serial synthesis: https://www.ece.iastate.edu/~zambreno/classes/cpre583/documents/IssDai95A.pdf
- ZipCPU running sum: https://zipcpu.com/dsp/2017/10/16/boxcar.html
- Gowin memory guide: https://cdn.gowinsemi.com.cn/UG285E.pdf
- BasicUART source: https://github.com/STjurny/BasicUART
- FSM study: https://www.researchgate.net/publication/378930206_Hardware_reduction_for_FSMs_with_extended_state_codes

Read research_findings.md beside this prompt for the complete source audit and access limitations. Andraka's full PDF and the supplied CORDIC page were unavailable; no quantitative claim here depends on them.
