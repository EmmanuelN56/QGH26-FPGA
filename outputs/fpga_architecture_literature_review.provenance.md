# Provenance: FPGA Architecture Literature Review

## Retrieval date

2026-10-02, America/New_York.

## Sources consulted

| Source | Type | Role in synthesis |
|---|---|---|
| https://www.gqhacks.com/tracks/hardware | Official competition page | Protocol, algorithm, scoring, board and submission requirements |
| https://www.gowinsemi.com/en/document/main/database/1846/ | FPGA vendor documentation index | Target device and current GW2AR documentation |
| https://www.gowinsemi.com/upload/database_doc/6/document/5b5852bfdb1b1.pdf | FPGA vendor guide | B-SRAM capabilities and target support |
| https://wiki.sipeed.com/hardware/en/tang/tang-nano-20k/nano-20k.html | Board vendor documentation | BL616 bridge, board resources and troubleshooting |
| https://doi.org/10.1109/FCCM.2011.50 | Peer-reviewed conference paper | Streaming financial parsing and deterministic latency |
| https://doi.org/10.1109/RECONFIG.2017.8279781 | Peer-reviewed conference paper | Modular end-to-end FPGA trading architecture |
| https://doi.org/10.1109/TII.2022.3182242 | Peer-reviewed journal paper | FSM-coordinated fixed-format financial parsing |
| https://doi.org/10.1007/978-3-319-97277-0_15 | Peer-reviewed book chapter | Recursive moving-average FPGA implementation |
| https://doi.org/10.1109/FPT.2017.8280128 | Peer-reviewed conference paper | Windowed stream aggregation architecture |
| https://arxiv.org/abs/2212.13977 | Research preprint | Streaming quantitative-finance dataflow and platform comparison |
| https://docs.amd.com/r/en-US/ug585-zynq-7000-SoC-TRM/Receiver-Data-Capture | FPGA vendor documentation | UART receiver synchronization and sampling principles |
| https://community.altera.com/t5/s/jgyke29768/attachments/jgyke29768/fpga-device/49242/1/wp-01082-quartus-ii-metastability.pdf | FPGA vendor white paper | Metastability and synchronizer rationale |
| https://openstax.org/books/principles-data-science/pages/5-3-time-series-forecasting-methods | Open textbook | Simple moving-average definition |
| https://doi.org/10.1111/j.1540-6261.1992.tb04681.x | Peer-reviewed journal paper | Historical moving-average trading-rule context |
| https://doi.org/10.1111/0022-1082.00163 | Peer-reviewed journal paper | Data-snooping limitations of technical-rule evidence |

## Source selection notes

- Primary and official sources were preferred.
- Absolute performance numbers from large Xilinx/Intel accelerator systems were not transferred to the Tang Nano 20K design.
- Vendor documentation was treated as more authoritative for device-specific memory, programming, and board behavior.
- Competition behavior remains subject to the organizer guide, supplied tests, and announcements.

## Claims requiring local verification

- Exact contents and port names of the supplied `.cst` file, because it was not present locally.
- Exact implementation of the organizer's Python reference model, because the scripts were not present locally.
- Actual LUT, register, B-SRAM, timing, and UART reliability results, because no HDL, Gowin installation, connected board, or test CSV existed when this review was written.
- Whether inferred HDL arrays map to B-SRAM under Gowin EDA V1.9.11.03; this must be checked in the final synthesis report.
