# Total-logic optimization

The organizer's final ranking order is total synthesis Logic, registers, then
five-run median latency (within 5% tied), after full official qualification.
B-SRAM is permitted and excluded from Logic. Reduce the complete Resource Usage
Summary Logic row; count ALUs and distributed RAM costs even if LUTs fall.

## Frozen comparison baseline

context_ram: 312 synthesis Logic, 179 registers, 271 primitive LUTs / 272 summary
LUTs, 40 ALUs, one B-SRAM, zero SSRAM. Routed Logic 316; Fmax 102.750 MHz;
setup/hold +27.305/+0.425 ns. Original source/.fs identities remain unchanged.
Physical latency is unknown; physical qualification is pending. The separate
codex/logic-312-blockram branch is for testing this identified candidate.

The previous two candidates have 354 and 382 synthesis Logic. A smaller LUT
number alone is not an improvement under the new ranking. The synthesis report's
complete Logic row is the comparison metric; routed totals are saved separately.

## Next isolated experiments

1. Share the existing accumulator arithmetic with the price/average comparisons.
   The current strategy has a 20-bit add/subtract network plus a separate unsigned
   comparison subtractor. Test whether one scheduled arithmetic network costs
   less than the extra operand selection and FSM control. Preserve full 16-bit
   prices, 20-bit sums, unsigned carry/borrow and equality boundaries.
2. Replace the duplicate fill counter with the shared circular pointer and a
   full flag. Distinguish a new empty session from a full window wrapping at zero.
   Preserve logical RAM invalidation before every old-sum/history access.
3. Simplify RAM address, read-enable and write-enable decoding. Check whether
   encoding changes reduce actual mapped Logic without increasing control logic
   elsewhere. Synchronous RAM reads still require their documented latency.
4. Compare narrower context transfers and scheduling changes. Removing stored
   state is beneficial only if RAM/control/selectors cost less than what is
   removed. B-SRAM capacity is available; added address decoding can still lose.

Make one change per isolated experiment; preserve the frozen source/bitstream.
Record reference-model and strategy/UART correctness, synthesis Logic, registers,
LUTs, ALUs, B-SRAM/SSRAM, routed Logic, Fmax and setup/hold before and after.
Record physical latency as pending until the identified experiment is programmed
and saved logs/CSVs exist. Do not claim an optimum or physical improvement from
source changes or simulation alone.

Run the unchanged organizer full-range practice vectors, exact normal->full-range
sequence without reset, multiple additional seeds, zero/65535/max-sum cases,
unsigned-boundary transitions, floor-average edges and swapped slots. Physical
comparison using the new organizer suite is scheduled after candidate selection;
no board programming is performed by publication or optimization preparation.
