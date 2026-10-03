# Hardware Track: Scoring and Ranking Clarification

Source: organizer clarification supplied by the team on 2026-10-03.
The following announcement supplements the Participant Guide.

This supplements the Participant Guide. Nothing in the guide changes. Since the LUT and latency points are capped, many teams can reach 100/100, so here is how placement works.

## Stage 1: Qualification

You must pass both of these to compete for placement:

- 100/100 on the official judge run. If you miss the latency tier, judges may rerun once.
- A second hidden run with full-range 16-bit prices (0 to 65535). The spec says prices are unsigned 16-bit, so don't shrink your datapath to fit the practice range. To pass, you need every packet and action correct with no timeouts. Latency and LUTs are not re-scored on this run. It runs right after the official run without reprogramming.

Practice with large prices before the deadline using the attached 22_robust_uart_test_fullrange.py. Change only PORT, same as the normal test.

Teams that don't qualify are ranked below all qualifiers, ordered by rubric score.

## Stage 2: Ranking (qualified teams only)

- Lowest total logic count
- If tied, fewer registers
- If still tied, lower median latency over 5 runs (within 5% counts as a tie)

## How logic is measured

Judges re-synthesize your submitted source with Gowin V1.9.11.03 using the project settings in your commit.
The number is the total logic count in the Resource Usage Summary, with LUTs, ALUs, and other logic types combined, so moving math into ALUs won't lower your count. Registers means the total register count in the same summary.
Self-reported counts are not used. Qualification still uses the normal scoring from the guide. Only the ranking uses this total.
Judges will rebuild your design from your committed source and confirm it behaves the same as your submitted .fs.
BSRAM use is allowed and is not counted as logic.

The ranking order above is final.
