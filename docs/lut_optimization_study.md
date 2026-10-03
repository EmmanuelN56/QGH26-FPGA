Recovery note: historical results below predate deletion of the Ubuntu working folder. Exact builds were recovered; some original logs are missing. See [recovery inventory](repository_recovery.md) and fresh recovery validation files.

# LUT optimization study

The lowest measured complete design is **230 LUTs**, compared
with 365 in the physically tested release: **135 fewer LUTs
(36.986%)**. This establishes a feasible synthesis
result, not a mathematical global minimum. No candidate has been programmed
onto the board. The tested release source and bitstream are unchanged.

The human team clarified that the organizer rubric is the minimum eligibility
bar. The development objective is to reduce LUTs substantially below 300,
remove avoidable duplication, and pass larger datasets with different patterns.
The published score caps are retained as facts, not optimization stopping criteria.

## Measured candidates

All successful candidates passed the original 1,509-packet independent-model
and applicable item-state tests, accelerated complete UART transactions,
three board-timing smoke packets and 221 full-speed packets. The smallest
candidate also passed the additional/full-speed checks below. All synthesize
and route for GW2AR-LV18QN88C8/I7 version C, at 27 MHz, with the unchanged
organizer CST and all six matching pins. PR1014 remains; no setup/hold
violations were reported. Physical latency after optimization is pending.

| Candidate | LUTs | Registers | ALUs | B-SRAM / SSRAM | Fmax MHz | Setup / hold ns |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Tested release | 365 | 296 | 152 | 0 / 8 | 75.176 | +23.735 / +0.425 |
| response_mux | 311 | 226 | 152 | 0 / 8 | 83.063 | +24.998 / +0.323 |
| compact_logical_v2 | 306 | 226 | 152 | 0 / 8 | 95.055 | +26.517 / +0.325 |
| uart_shift | 355 | 295 | 152 | 0 / 8 | 75.316 | +23.760 / +0.323 |
| context_ram | 271 | 179 | 40 | 1 / 0 | 102.750 | +27.305 / +0.425 |
| shared_uart_shift | 297 | 226 | 44 | 0 / 8 | 62.318 | +20.991 / +0.425 |
| dual_sequential | 315 | 231 | 152 | 0 / 8 | 84.315 | +25.177 / +0.319 |
| carry_uart | 236 | 226 | 76 | 0 / 8 | 73.845 | +23.495 / +0.425 |
| shared_response_mux | 311 | 227 | 44 | 0 / 8 | 64.897 | +21.628 / +0.425 |
| carry_flags_only | 231 | 222 | 102 | 0 / 8 | 76.858 | +24.026 / +0.425 |
| shared_block_ram | 315 | 228 | 44 | 1 / 0 | 71.663 | +23.083 / +0.346 |
| memory_previous | 245 | 193 | 72 | 0 / 8 | 72.634 | +23.269 / +0.425 |
| shared_parallel | 302 | 227 | 44 | 0 / 8 | 70.904 | +22.934 / +0.336 |
| carry_uart_pointer | 234 | 222 | 72 | 0 / 8 | 72.098 | +23.167 / +0.425 |
| logical_clear | 325 | 276 | 152 | 0 / 8 | 82.115 | +24.859 / +0.425 |
| carry_direct_equality | 230 | 222 | 104 | 0 / 8 | 75.331 | +23.762 / +0.323 |
| shared_carry_compare | 248 | 227 | 76 | 0 / 8 | 72.243 | +23.195 / +0.425 |
| compact_packet_v2 | 359 | 246 | 152 | 0 / 8 | 74.484 | +23.611 / +0.323 |

The two first compact-buffer attempts failed to compile because a missing
space next to a hexadecimal literal changed Verilog tokenization; their logs
remain saved and the corrected v2 builds are shown. The block-RAM build
initially failed report extraction because Gowin omits an unused SSRAM row.
Its simulations and vendor build had passed; the validated parser recovery
and original logs are saved. These failures are not claimed as passing builds.

## What actually reduced LUTs

1. **Logical history clear.** Mask old entries until sixteen current-session
   values have overwritten them. Removing physical RAM clearing alone
   reduced 365 to 325 LUTs without leaking state between sessions.
2. **One request/response buffer.** Receive into a shift register, then
   reuse it after computation for the eight-byte response. Request and
   response storage no longer coexist. Combining this with logical clear
   reached 306 LUTs and 226 registers.
3. **One strategy datapath for two contexts.** Process the slots on
   successive clocks. Histories, sums, previous prices and held actions
   remain per item; metadata may be shared because each valid request
   always includes both fixed IDs exactly once. Full-width context
   selectors offset much of the initial arithmetic saving.
4. **Explicit unsigned carry-based comparisons.** Use zero-extended
   17-bit subtraction and its borrow bit, preserving equality and strict
   BUY/SELL boundaries. Equivalent RTL forms mapped very differently:
   the initial shared design was 302 LUTs; carry comparisons reached 248.
5. **Shift UART data rather than indexing individual bits.** Preserve
   start confirmation, center sampling, framing errors, complete stop
   bits and one-clock valid/done pulses. Combining the shifts with the
   carry design reached 236 LUTs.
6. **Remove the duplicated fill counter.** Before full, the circular
   pointer supplies the sample count; afterward a single full flag
   represents saturation at sixteen. That reached 234 LUTs. Direct
   operand equality alongside carry comparisons reduced it to 230.

The final module costs are RX 32, TX 33, packet/control 59 and strategy 106
LUTs. The history RAM already uses dedicated distributed storage. Reducing
window depth, price width or rolling-sum precision would change behavior
and was not used. Response slot order, exact reserved zeros, index-zero
clear-before-ingestion, floor averages and held actions are preserved.

## LUT minimum versus total resources

The 230-LUT design uses 104 ALU cells. The 234-LUT alternative uses 72 ALU
cells with the same 222 registers and 0 B-SRAM / 8 SSRAM. Gowin reports
342 logic units for 230 LUTs, versus 314 for 234 LUTs and 525 for the
release. Thus 230 wins on LUT count; 234 uses less total logic. The
difference is four LUTs traded for 32 additional carry/ALU cells. Both
remain substantially smaller than the current release.

Moving only history storage to block RAM measured 315 LUTs. Putting
history and item context into one synchronous RAM address space measured
271 LUTs, 179 registers and one B-SRAM. It reduced registers and improved
Fmax, but its address/microsequence control added LUTs. Removing the
previous-price registers, deriving them from the preceding history entry,
measured 245 LUTs and 193 registers. A logical redundancy can be cheaper
than the multiplexers/control needed to remove it.

## Larger test data and full-speed checks

The additional corpus has 13,508 packets across 31 sessions and 16 new
deterministic random seeds. It includes constant extremes/midpoint,
ascending/descending prices, sixteen-sample square waves, impulses,
sawtooth waves, held-action plateaus, floor boundaries and noise around
the midpoint. Prices cover the entire unsigned 16-bit domain, including
65535 and rolling sums approaching 1,048,560. Echo indices include 255,
256, 32767, 32768, 65534 and 65535. Short repeated sessions exercise
index-zero clearing after previously full/nonzero histories. Both
organizer reference classes agree with the independent model byte-for-byte.
The original release and 234-LUT design passed all additional packets in
their item-state and complete-UART benches; the 230-LUT design passed
the same 13,508 additional packets in its two benches. The corpus was
batched only to respect testbench capacity; no reset occurs between
sessions inside a batch. The official unpublished seed was not tested.

Both 230- and 234-LUT candidates passed all original 1,509 packets at
actual 27 MHz / 115200-baud timing, as well as RX 260-byte / TX 256-byte
unit tests. Candidate timing starts before the first request bit and
ends at the final response stop-bit center; it includes a deliberate
two-bit request pause, and excludes USB/host overhead.
The 230-LUT simulated turnaround is 259.266 ns;
transaction time is 1.397662 ms, versus
185.190 ns / 1.397588 ms for the current release. Sharing adds only two
processing clocks; the complete stop bit and three inter-byte handshake
idle clocks remain. This is a simulation cost, not measured board latency.
Saved physical baseline mean/max is 14.105513/16.9418 ms;
after-candidate measurements are unavailable because no new candidate
has been programmed. No physical reliability or host-latency gain is claimed.

## What to test next to go lower

Reaching below 200 requires at least 31 more LUTs beyond the measured 230.
There is no evidence yet that 200 is an achievable minimum or a hard floor.
Prioritize these experiments, with correctness and synthesis after each:

1. **Packet/control logic (59 LUTs):** compare fixed-field capture and
   staged response selection against the reused 64-bit buffer. Direct
   response selection already measured worse in this study; a new layout
   must improve the selector/write-enable network, not merely remove registers.
2. **Item-context selectors (within 106 LUTs):** try narrower byte/nibble
   transfers and a carefully scheduled shared datapath. Keep the efficient
   carry comparison form. More computation clocks can fit inside UART
   transport time, but the new microcontrol must cost less than the muxes.
3. **Recompute versus cache:** previous prices and rolling sums are
   derivable from the history. Recomputing can remove stored state at the
   cost of more RAM reads and controls. The previous-price experiment
   showed a LUT increase; benchmark a complete schedule before choosing it.
4. **Synthesis encoding/placement:** examine actual FSM and critical-path
   reports after structural changes. Treat small improvements as mapping
   results, with exact tool/source identities, rather than assumed guarantees.

Integrate only after reviewing a selected candidate and measuring it on
the physical board against the preserved release. Experimental files
retain the old standalone engine for baseline/unit-test compatibility;
it is unreachable from the candidate synthesis top and contributes no
LUTs. Integration should migrate the unit interface and remove that source
duplication. Larger protocol/item/window changes need a new contract; the
current study does not change the fixed UART format or item set.

## Evidence and reproduction

Experiment root: `results/area_20261003T192105403559Z/`.
Smallest build/source/reports/file: `results/area_20261003T192105403559Z/carry_direct_equality/`.
Candidate SHA-256: `f33a5f114d87616951c13435718ed73c124a23b2a02452ec93f26593e1278bf8`.
Per-candidate build summaries, native source snapshots, compiler/model/UART
logs and resource/timing reports are preserved, along with the release
baseline, larger corpus, generator and validation tools. `study_summary.json`
contains the full comparison and source/file identities. Before rerunning
preparation, use a fresh experiment root; existing evidence is not overwritten.
Native Windows Gowin V1.9.11.03 Education and Icarus 12 were used; no
tools, drivers or host settings were changed.

[Gowin Synthesis guide](https://cdn.gowinsemi.com.cn/SUG550E.pdf)
(RAM templates and memory attributes, sections 4.2 and 5.16) informed the
RAM experiments. Actual installed-tool reports determine the counts here.
Use [human review commands](human_review.md) to inspect/stage any results.
