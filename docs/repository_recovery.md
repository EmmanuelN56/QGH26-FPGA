# Native Windows repository recovery

Active working folder: `C:/Users/Lenovo/Downloads/QuizletFPGA`.
Commands and edits now use this path explicitly. The former Ubuntu working
folder was deleted; it is no longer the source of working files.

Recovered files came from the published GitHub snapshot
`b068c5ee6f8b80e26a4262c1fcce36e1e6063ed4`, surviving native Windows build
folders, and complete source bodies in saved execution records. Recovery did
not change Git branches, history, remote references, or the index.

- Exact 365-LUT release source and bitstream, SHA-256
  `bc7edc25e995168772989e199c9cd43252f6120bec68e21fba034c8a35d4313d`.
- All 17 successful area candidates: eight build inputs, matching bitstreams,
  resource/timing/pin reports, and verification benches.
- Exact 230-LUT candidate: `results/area_20261003T192105403559Z/carry_direct_equality/`.
- Exact 234-LUT candidate: `results/area_20261003T192105403559Z/carry_uart_pointer/`.
- Independent model, organizer tests, regression vectors, preserved expanded
  corpus (13,508 packets / 31 sessions), recovered scripts and research notes.
- Earlier 412-LUT physical-board logs and CSVs already published on GitHub.

Both organizer models regenerated the expanded corpus byte-for-byte, including
all state files and the full manifest. Source and bitstream hashes match the
surviving vendor builds. Fresh software-only regression results are stored in
`results/software_validation.json`, `results/recovery_corpus_checks.json`, and
`results/recovery_candidate_validation.json`. No serial port was opened and no
FPGA was programmed during recovery.

Some later physical-board CSVs, console logs, aggregate grading JSON and original
area simulation logs existed only in the deleted Ubuntu results directory.
They have not been recovered. Historical documents retain the earlier reported
results; missing evidence must not be treated as a new physical validation.
Fresh candidate recovery simulations are saved separately under each candidate's
`recovery_simulation/`. Full-speed simulation packet counts are recorded there;
these runs are not physical-board measurements.

The exact older local working files were preserved before replacement under
`.build/recovery_20261003/before/`. The published archive and extraction staging
files remain under `.build/recovery_20261003/`; private execution records were
not copied into the repository. The recovery inventory is
`results/area_20261003T192105403559Z/recovery_manifest.json`.

To publish the comparison branches, review and run
`scripts/publish_lut_candidate_branches.ps1`. It prepares a separate native
checkout from the latest fetched `origin/main`, installs exact identified
candidates, and publishes sibling `codex/lut-230` and `codex/lut-234` branches
when run manually. The original checkout stays on its existing branch. It does
not merge a candidate into main. Physical comparison and selection remain pending.

Fresh recovery validation passed for the 365-LUT baseline and both candidate
sources. Each candidate passed RX 260-byte and TX 256-byte unit tests, three
packet smoke tests, all 1,509 original regression packets and 13,508 expanded
packets in both strategy-state and complete UART benches, plus three packets
at actual 27 MHz / 115200-baud simulation timing. The original full-speed
1,509-packet run remains a historical result whose original console log is
missing. No physical board test was performed during recovery.

`.gitattributes` preserves checksum-tracked source, bitstream, vectors and
saved evidence bytes across Windows Git checkouts. This avoids CRLF conversion
changing hashes when a teammate clones the comparison branches.
