# Verification records and the selected 186-Logic release

The active submission is **186 total Logic / 92 registers / 4 B-SRAM**,
with [`bitstream/trade_core.fs`](../bitstream/trade_core.fs). The
[root README](../README.md) contains its source/build identity, tested bitstream
hash, resource/timing measurements, and October 4 physical test results.

The existing tracked files in this directory are **historical verification
snapshots**. Their source hashes and recorded configuration define their scope;
they should not be reported as results for the current source. Preserve their
original contents rather than rewriting recorded measurements to match a release.

The selected file passed quick, five normal runs, five full-range runs, the
modified full-range test, and all attached variant modes plus two additional
random seeds: 4,992 correct robust packets and 9,984 correct actions including
warm-up, with zero timeouts or mismatches. Detailed logs/CSVs were saved during
verification and retained with local work; they are optional submission material.

For current software-only checks, run `python scripts/run_regression.py`.
The runner regenerates vectors and writes `software_validation.json` and
`simulation.log` here with the tested source identities. These files describe
simulation only; the runner does not program the board or open a serial port.

For physical checks, program the selected `.fs` in SRAM mode and preserve
programming logs and each UART test's CSV/summary, including source and bitstream
hashes. Do not substitute software simulation for physical-board results.
See the [board instructions](../docs/board_bringup.md) for this release.
