# Literature Review: Practical FPGA Architecture for the Silicon Trade Core

## Scope

This review focuses on sources that can materially improve the implementation or optimization of a small UART-connected, streaming moving-average engine on a Gowin GW2AR-18 FPGA. It is not a general survey of quantitative trading.

## What to read first

### 1. Official competition specification

The project is primarily a conformance problem. The official hardware-track page fixes the UART packet format, item routing, moving-average update order, session reset behavior, and scoring. Treat the organizer's robust Python test as the executable specification.

Practical implication: do not copy a published trading architecture until a small reference model reproduces the organizer's exact byte-level behavior.

Source: [Gator Quant Hacks Hardware Track](https://www.gqhacks.com/tracks/hardware)

### 2. Gowin device and memory documentation

The GW2AR-18 documentation and Gowin B-SRAM guide describe the resources actually available in the target device. The B-SRAM guide is more relevant to LUT optimization than a paper implemented on a large Xilinx or Intel accelerator card.

Practical implications:

- Measure whether the two 16x16-bit histories infer registers, distributed logic, or B-SRAM.
- Compare total scored LUT count with and without explicit memory inference.
- Check synchronous-read behavior before changing a verified register-array implementation to B-SRAM.
- Use the actual synthesis report rather than assuming that shorter HDL produces smaller hardware.

Sources:

- [GW2AR documentation database](https://www.gowinsemi.com/en/document/main/database/1846/?order=DESC&page=1&support_search=&type=version)
- [Gowin B-SRAM User Guide](https://www.gowinsemi.com/upload/database_doc/6/document/5b5852bfdb1b1.pdf)

### 3. Sipeed Tang Nano 20K documentation

Sipeed documents the onboard BL616 bridge, FPGA resources, JTAG programming, USB-to-UART function, and common detection failures.

Practical implications:

- Treat USB/UART reliability as part of the system architecture.
- Validate with the exact board and bridge; RTL simulation cannot expose USB buffering behavior.
- Keep a stable, deterministic transmitter and empirically determine the minimum reliable inter-byte spacing.

Source: [Sipeed Tang Nano 20K documentation](https://wiki.sipeed.com/hardware/en/tang/tang-nano-20k/nano-20k.html)

## Architecture papers worth using

### Design and Implementation of Moving-Average Calculations with an FPGA

Ivanov and Stoilov compare FPGA approaches to moving-average calculation and identify the recursive form as the resource-efficient structure. This is the paper most directly connected to the contest arithmetic.

Use here:

- Maintain an incremental rolling sum instead of rebuilding the sum from all 16 samples.
- Store only what is required to identify the departing sample.
- Treat the fixed power-of-two window as an opportunity to replace division with a right shift.

Limit: the organizer's old-average/new-average crossing order remains the governing specification; the paper supplies an implementation principle, not contest semantics.

Source: Ivanov and Stoilov, “Design and Implementation of Moving Average Calculations with Hardware FPGA Device,” [DOI: 10.1007/978-3-319-97277-0_15](https://doi.org/10.1007/978-3-319-97277-0_15)

### Single Window Stream Aggregation Using Reconfigurable Hardware

This work treats windowed aggregates as streaming hardware and analyzes throughput/resource tradeoffs.

Use here:

- View each item as a keyed stream with local state.
- Perform an incremental update when a sample enters and the oldest sample leaves.
- Keep state update and input acceptance as an explicit transaction.

Limit: its larger stream-processing machinery is unnecessary for only two item keys and sixteen samples per item.

Source: Geethakumari et al., “Single Window Stream Aggregation Using Reconfigurable Hardware,” FPT 2017, [DOI: 10.1109/FPT.2017.8280128](https://doi.org/10.1109/FPT.2017.8280128)

### Low-Latency FPGA Based Financial Data Feed Handler

Morris et al. describe an FPGA feed handler that parses financial messages with low and deterministic latency. The most relevant principle is moving parsing and stateful processing into a streaming hardware path rather than involving a host operating system in the critical path.

Use here:

- Keep UART parsing, packet state, strategy state, and response formation entirely on the FPGA.
- Use a deterministic FSM pipeline with explicit message boundaries.
- Report latency distribution and repeatability, not only a best-case number.

Limit: the paper targets a much faster and larger financial-feed system. Its absolute latency and architecture should not be copied directly into a 115200-baud contest design.

Source: Morris et al., “Low-Latency FPGA Based Financial Data Feed Handler,” FCCM 2011, [DOI: 10.1109/FCCM.2011.50](https://doi.org/10.1109/FCCM.2011.50)

### Build Fast, Trade Fast: FPGA-Based High-Frequency Trading Using HLS

The paper presents a complete low-latency trading pipeline and emphasizes composable system components: protocol parsing, state handling, strategy logic, and packet generation.

Use here:

- Preserve clean boundaries between UART, packet, strategy, and response modules.
- Define module interfaces before parallel development.
- Optimize an end-to-end measured system rather than one isolated arithmetic block.

Limit: it uses HLS and a high-end Xilinx Kintex UltraScale at 156 MHz. This project uses RTL on a small Gowin device at 27 MHz.

Source: Cong et al., “Build fast, trade fast: FPGA-based high-frequency trading using high-level synthesis,” ReConFig 2017, [DOI: 10.1109/RECONFIG.2017.8279781](https://doi.org/10.1109/RECONFIG.2017.8279781)

### A Domain-Specific Accelerator for Ultralow Latency Market Data Distribution

This work uses finite-state-machine coordinated parsing and parallel field decoding for a financial protocol.

Use here:

- Decode fields as soon as packet bytes make them valid, but do not respond before the complete eight-byte request.
- Prefer direct, fixed-format decoding over a general parser.
- Make message sequence and field validity explicit in the controller.

Limit: the paper's FAST protocol, Ethernet, PCIe, and parallel 16-field decoder are far beyond the contest's needs.

Source: “A Domain-Specific Accelerator for Ultralow Latency Market Data Distribution System,” IEEE Transactions on Industrial Informatics, [DOI: 10.1109/TII.2022.3182242](https://doi.org/10.1109/TII.2022.3182242)

### Fast and Energy-Efficient Derivatives Risk Analysis: Streaming Option Greeks

This work compares streaming FPGA implementations across architectures and shows why a continuous dataflow structure can improve throughput and energy efficiency.

Use here:

- Think in terms of a streaming transaction from input bytes through state update to output bytes.
- Keep host software outside the judged critical path.
- Separate architecture-independent arithmetic from board-specific I/O.

Limit: option-Greeks computation and accelerator-card bandwidth are not directly comparable to a small rolling-average core.

Source: Brown, “Fast and energy-efficient derivatives risk analysis: Streaming option Greeks on Xilinx and Intel FPGAs,” [arXiv:2212.13977](https://arxiv.org/abs/2212.13977)

## UART reliability references

The UART input is asynchronous to the FPGA clock. Use a two-register synchronizer before edge detection, qualify the start bit, and sample data near the center of each bit. At 27 MHz and 115200 baud, a 234-clock integer bit period has only about 0.16% error; a fractional 234/235 tick can be evaluated later but is not a substitute for correct synchronization and sampling.

Useful primary/vendor material:

- [AMD Zynq UART Receiver Data Capture](https://docs.amd.com/r/en-US/ug585-zynq-7000-SoC-TRM/Receiver-Data-Capture), for start qualification, oversampling, resynchronization, and midpoint sampling principles.
- [Intel/Altera Metastability in FPGAs](https://community.altera.com/t5/s/jgyke29768/attachments/jgyke29768/fpga-device/49242/1/wp-01082-quartus-ii-metastability.pdf), for the rationale behind synchronizer chains.

These sources describe general digital-design principles. Verify the actual receiver against phase-offset and long-stream simulations and against the Tang Nano 20K board.

## Mathematical background

OpenStax gives a clear definition of a simple moving average as the arithmetic mean of a fixed window of consecutive values. It supports the explanation of why the design stores the latest 16 samples and maintains a rolling sum.

Practical implication: the direct formula establishes correctness, while the rolling recurrence is the hardware optimization:

```text
sum_new = sum_old - oldest + newest
average = floor(sum / 16)
```

Source: [OpenStax, Principles of Data Science, §5.3](https://openstax.org/books/principles-data-science/pages/5-3-time-series-forecasting-methods)

For the finance narrative, Brock, Lakonishok, and LeBaron studied moving-average trading rules historically. Sullivan, Timmermann, and White subsequently emphasized data-snooping risk. These sources justify describing the strategy as historically studied, but they do not prove that the contest rule is profitable or help synthesize the circuit.

Sources:

- Brock, Lakonishok, and LeBaron, “Simple Technical Trading Rules and the Stochastic Properties of Stock Returns,” [DOI: 10.1111/j.1540-6261.1992.tb04681.x](https://doi.org/10.1111/j.1540-6261.1992.tb04681.x)
- Sullivan, Timmermann, and White, “Data-Snooping, Technical Trading Rule Performance, and the Bootstrap,” [DOI: 10.1111/0022-1082.00163](https://doi.org/10.1111/0022-1082.00163)

## Where to search

Use sources in this order:

1. Organizer guide and executable tests — exact required behavior.
2. Gowin documentation database — primitives, memory, synthesis, timing, programming, and device-specific behavior.
3. Sipeed wiki and schematics — board bridge, clock, pins, and physical troubleshooting.
4. IEEE Xplore and ACM Digital Library — peer-reviewed FPGA architectures.
5. arXiv — accessible preprints, ideally cross-checked against a published version.
6. Google Scholar or Semantic Scholar — citation discovery, not the final authority.
7. GitHub/OpenCores — implementation examples only; inspect license, test coverage, target clock assumptions, and synthesis portability before reuse.

Useful search queries:

```text
FPGA streaming sliding window rolling sum architecture
FPGA moving average resource efficient RTL
FPGA UART receiver fractional baud clock recovery
FPGA financial feed handler deterministic latency
FPGA time multiplexed datapath resource sharing
GW2AR-18 B-SRAM inference Verilog
Gowin synthesis resource sharing FSM
```

## Evidence-driven optimization plan

Papers suggest architectural principles, but this contest is decided by the organizers' test and Gowin report. Maintain a table for every candidate:

```text
variant | commit | correctness | actions | mean latency | max latency | LUTs | FFs | B-SRAM | timing slack
```

Benchmark these variants in order:

1. Baseline: two independent register-array engines.
2. Logical reset: retain array bits and reset only validity/count/pointer/sum.
3. Exact-width arithmetic and simplified controller.
4. Inferred or explicit B-SRAM history.
5. Shared arithmetic engine for both items.
6. Empirically tuned UART response gap.

Keep an optimization only after simulation, synthesis, and repeated board tests all pass. The fastest published architecture is not automatically the best contest architecture because the measured round trip is dominated by UART, BL616, USB, and the judge PC.

## Bottom line

The most reliable design is likely a small deterministic FSM system with a center-sampling UART, fixed packet decoder, two independent item states, rolling sums, circular windows, exact-width unsigned arithmetic, and a conservatively spaced UART transmitter. Optimize storage mapping and arithmetic sharing only after the baseline repeatedly passes the robust physical test.
