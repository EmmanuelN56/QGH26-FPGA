# Full-range regression corpus

These frozen vectors were recovered from the previously saved local full-range
verification package. `scripts/run_extensive_regression.py` independently checks
every response and internal state against this repository's model, and every
response against the unchanged organizer full-range reference class before RTL
simulation. No organizer serial loop is executed during simulation.

| Corpus | Packets | Purpose |
| --- | ---: | --- |
| qualification_sequence | 400 | Normal, full range, normal repeat, full-range repeat without reset |
| fullrange_edges | 3,776 | Maximum/zero/signed-boundary prices, equality and floor cases, 32 random seeds |
| original | 1,509 | Existing quick, normal, boundary and random sessions |
| expanded | 3,100 | Long wraps, ramps, impulses, carry/borrow bits, every floor residue, partial warm-up restarts |

Total: 8,785 packets. Every corpus starts at index zero; simulation resets once
per corpus but retains state between its sessions. The physical stress runner
sends the concatenated corpus without resetting or reprogramming the board.
Coverage and SHA-256 identities are recomputed and saved with each run.

`actual_uart_*` preserves the first 200 normal-to-full-range practice packets;
the standard regression separately exercises the quick, normal and full-range
sequence at the actual 27 MHz / 115200 baud settings.
