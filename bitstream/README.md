# Submission bitstream

`trade_core.fs` is the exact trading-core bitstream built with Gowin
V1.9.11.03 Education for GW2AR-LV18QN88C8/I7, device version C, top `top`.
SHA-256: `e0b5bdc80f568ba7e7036693b6aa08fe2e0708843aa295db5cc83fca105afce7`.

It was programmed into volatile SRAM after explicit authorization. The organizer
quick test and three consecutive robust sessions passed on COM4 without reset
or reprogramming between sessions. Each robust run received all 100 packets,
with 84/84 scored packets, 168/168 actions and zero timeouts. Independent CSV
review checked every row, including warm-up, against the reference model.

Matching source snapshots, build reports, programming evidence and CSVs are in
`results/board_20261003T064213338565Z/`. Build summary is in
`results/build_windows_20261003/build_summary.json`. PR1014 remains documented.
Physical mean/max latency over the 300 robust packets was 13.718/31.265 ms on
the local Windows PC. Official judging uses a different seed and PC.

Human review, metadata completion and Git/submission freeze remain pending.
See the root README for reproduction instructions.
