# Verification evidence

`software_validation.json` records the simulator/Python versions, test results,
source SHA-256 identities and vector manifest. `simulation.log` is the actual
compiler/runtime transcript. These are **software simulation evidence only**.

Validated: independent model agrees byte-for-byte with both organizer classes
for 1,509 packets / 15 sessions; RX (260 bytes), TX (256), original top (3),
engines (1,509), accelerated full sessions (1,509), board-default full sessions
(221: quick and two robust runs without reset). Golden request/response and
internal-state vectors are in `testbench/vectors/` and can be regenerated with
`python scripts/generate_vectors.py`. No serial port is opened by software checks.

Icarus reports unspecified RTL time-unit warnings; the RTL has no delays, and
the benches specify their time units. These do not affect the checked cycle
counts or serial stimulus. All pass/failure messages are retained.

No current trading-core synthesis, PnR, bitstream, programming logs, physical
CSV/summary, or latency measurement is available. Historical UART-only metrics
in the bring-up notes must not be reported as trading-core measurements.

After explicit SRAM-programming authorization and successful programming, use
`scripts/capture_board_tests.py` to preserve quick output and repeated robust
CSVs/summaries with source/bitstream identities under `results/board_<UTC>/`.
Archive the matching Gowin synthesis/resource/pin/timing reports and programming
console log there, and record physical correctness and mean/max latency.
Its manifest identifies programming mode as operator-reported; retain actual
programming evidence separately. Never label software simulation as a board pass.
