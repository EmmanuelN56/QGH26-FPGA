# Research for reducing total FPGA logic

> Historical research from October 3. These archived experiment
> descriptions and baseline counts do not identify the active submission.
> The selected release is **186 total Logic / 92 registers / 4 B-SRAM**;
> see the [current README](../../README.md).

Research date: 2026-10-03. Scope: literature and existing source/report inspection only. No project RTL, tests, constraints, settings, or bitstreams changed; no synthesis or physical test was run for this research.

## Recommendation

The strongest next experiment is a shared, narrower arithmetic datapath with memory access designed around it. Compare 1-, 2-, 4-, and 8-bit arithmetic against a shared parallel implementation. Choose the smallest complete synthesized design that preserves qualification; a 1-bit adder does not automatically produce the smallest system.

The existing block-RAM candidate already uses a running sum, logical history invalidation, and one strategy datapath scheduled across both items. Repeating those changes is not a new optimization. The remaining opportunities are arithmetic/comparison sharing, operand selection, temporary storage, memory addressing, packet storage, and control decoding.

These are engineering hypotheses for this design, not savings promised by the papers. No source establishes a global minimum or guarantees competition placement.

## Correct baseline and ranking metric

The organizer announcement makes qualification mandatory: 100/100 on the official run, then every packet/action correct with no timeout on the hidden full-range run, without reprogramming. Qualifiers rank by total synthesis Logic, then registers, then five-run median latency (within 5% tied). BSRAM is excluded from Logic. The judges' rebuild is authoritative.

| Frozen candidate | Synthesis Logic | Registers | LUTs in summary | ALUs | RAM16 | BSRAM | Routed Logic |
|---|---:|---:|---:|---:|---:|---:|---:|
| context_ram | 312 | 179 | 272 | 40 | 0 | 1 | 316 |
| carry_uart_pointer, called 234-LUT | 354 | 222 | 234 | 72 | 8 | 0 | 360 |
| carry_direct_equality, called 230-LUT | 382 | 222 | 230 | 104 | 8 | 0 | 392 |

The context candidate has 271 primitive LUTs but 272 in the summary's LUT category. Use the complete Logic row. For the two distributed-RAM candidates, the totals exceed LUT+ALU by 48. Their eight RAM16 blocks therefore contribute six Logic units each in these reports. This settles the immediate SSRAM question from existing evidence; it is not a universal formula for every memory configuration.

Evidence: `results/fullrange_20261003_ranking/ranking_audit.json`, the referenced original synthesis reports, and `validation.json`. The latter records 4,176 strategy transactions, 4,176 accelerated UART transactions, and 200 actual-clock/baud transactions per candidate. These are simulations. New physical results from the teammate, if any, must be attached separately.

## Source review

### Bit-serial arithmetic and storage

**SERV README and ALU source — inspected.** The README's 198, 239, and 125 LUT figures correspond to iCE40, Cyclone 10 LP, and Artix-7 respectively. They are not three comparable Gowin configurations. The ALU demonstrates a narrow addition/subtraction path with retained carry and accumulated comparison information. Borrow the arithmetic scheduling principle; adding a RISC-V processor would introduce unrelated hardware. The best contest width must include selectors, storage, counters, and control. [SERV repository](https://github.com/olofk/serv), [ALU source](https://github.com/olofk/serv/blob/main/rtl/serv_alu.v).

**Isshiki and Dai, High-Level Bit-Serial Datapath Synthesis for Multi-FPGA Systems — full paper inspected.** Iowa State hosts the PDF; its authors were at UC Santa Cruz. The paper quantifies serial operator area and timing on old Xilinx XC4000 devices and explicitly discusses storage/control costs. Its CLB counts cannot predict Gowin Logic. It supports trying a narrow datapath when the available processing time exceeds the arithmetic work. [Primary PDF](https://www.ece.iastate.edu/~zambreno/classes/cpre583/documents/IssDai95A.pdf).

**Andraka, Building a High Performance Bit Serial Processor in an FPGA — partial verification only.** The author's PDF is indexed, and its abstract describes a radar vector-magnitude example, but repeated retrieval attempts failed. I did not read its full design or tables and use no numerical savings from it. The actionable serial-datapath recommendation is independently supported by the accessible Isshiki/Dai paper and SERV implementation. [Author PDF](https://fpga-guru.com/files/supercn.pdf).

**Lifetime-Aware Design for Item-Level Intelligence at the Extreme Edge — abstract inspected.** This work concerns flexible electronics and configurable narrow datapaths, not a Tang Nano implementation. Its energy and frequency results are not Gowin area estimates. The supplied LinkedIn Tang Nano 9K counts remain unverified and are excluded from the recommendation. [Paper](https://arxiv.org/abs/2509.08193).

**Tiny Tapeout underserved — project documentation inspected.** Its reduced SERV system has a five-register shift-register file. This is an ASIC-specific storage choice, not evidence that replacing free-to-ranking Gowin BSRAM with hundreds of flip-flops will help. Small temporary shifters remain worth measuring. [Project documentation](https://tinytapeout.com/chips/ttsky25b/tt_um_underserved).

**CNMAT CORDIC comparison — unavailable.** The supplied page could not be retrieved, so its quantitative area/latency claim remains unverified. CORDIC is not required by the trading algorithm. Serial arithmetic's cycle cost can be calculated directly for our own operations. [Supplied page](https://cnmat.org/~norbert/cordic/node9.html).

### Running sum and RAM

**ZipCPU boxcar — article inspected.** The recurrence replaces a repeated window sum with subtraction of the outgoing sample and addition of the incoming sample. RAM stores the history; validity handles startup without clearing every RAM location at runtime. Configuration initialization and clearing between sessions are different issues. Our context candidate already applies this architecture. Preserve unsigned prices and floor averages rather than copying the article's signed/rounding choices. [Article](https://zipcpu.com/dsp/2017/10/16/boxcar.html).

**Ljubljana lab — all seven pages inspected.** The 44-LUT/74-FF running-sum result is for an eight-sample signed-data example on a Xilinx Zynq device using Vivado. It is not a bound for our two-item, sixteen-sample Gowin system. The lab supports replacing a register delay line with RAM and a pointer; our baseline has already done so. [Lab PDF](https://lniv.fe.uni-lj.si/doc/HL_FPGA/HL_FPGA_Lab1.pdf).

**Austin Consultants example — original forum post inspected.** The first-person LabVIEW account supports RAM-backed delay storage in place of expensive averaging blocks. Its many-channel utilization numbers do not transfer to this core. [Original post](https://forums.ni.com/t5/London-LabVIEW-User-Group/Ever-needed-a-rolling-average-filter-for-FPGA-in-LabVIEW/td-p/3485563).

### FSM encoding

**Barkalov et al., 2024 — author-version methods and experimental sections inspected.** The reported 6.21% and 22.21% average LUT reductions compare mixed state assignment against composite and extended state-code methods. Experiments use 48 FSM benchmarks, Virtex-7 six-input LUTs, and Vivado 2019.1. The advantage increases with FSM complexity. These percentages are not forecasts for our small Gowin controllers. Try simpler encoding alternatives first; inspect the mapped result because synthesis may recode RTL states. [Author version, DOI 10.1109/ACCESS.2024.3376472](https://www.researchgate.net/publication/378930206_Hardware_reduction_for_FSMs_with_extended_state_codes).

**Barkalov et al., 2018 — publisher abstract inspected; full PDF unavailable.** It partitions states and gives each state two codes to reduce logic-function inputs. Its stated target is FSMs with more than fifteen states. This is lower priority for our existing small controllers. [Publisher record](https://reference-global.com/article/10.2478/amcs-2018-0046).

**Barkalov et al., 2020 — publisher abstract and bibliographic details inspected; full PDF unavailable.** The relevant journal article is Improving characteristics of LUT-based Mealy FSMs, DOI 10.34768/amcs-2020-0055. It partitions states into subsets and uses a three-level logic structure. A separate 2020 book chapter is titled Twofold State Assignment for Mealy FSMs; do not conflate these with the similarly titled 2021 article. There is insufficient direct evidence to prioritize this decomposition over a small encoding sweep here. [2020 publisher record](https://reference-global.com/article/10.34768/amcs-2020-0055).

**Sutter et al., 2002 — full paper inspected.** The study uses Xilinx XC4010E, FPGA Express/Foundation, and power measurements of benchmark FSMs. Its up-to-eight-state/beyond-sixteen-state recommendation is technology- and benchmark-dependent. Even its small-FSM area table has exceptions: bbara uses 11 binary CLBs versus 8 one-hot. Therefore, "binary always minimizes our tiny FSM" is too strong. Compare binary, one-hot, and output-oriented encodings on Gowin, ranking total Logic first. [University-hosted paper](https://repositorio.uam.es/bitstream/10486/667004/1/low-power_sutter_LNCS_2002_ps.pdf).

### UART and Gowin

**BasicUART — README plus complete RX/TX source inspected.** Approximately 40 LUTs per module is an iCE40 result. The source uses shift registers, bounded timers, registered terminal-count signals, RX synchronization, and stop-bit handling. TX ready permits queuing during the stop bit; it does not mean transmission has completed. Our current candidate's RX/TX already use roughly 32/33 LUTs, so the old 177-LUT UART-only build is not a useful like-for-like comparison. Replacing the current UART wholesale has no demonstrated benefit. [Repository and source](https://github.com/STjurny/BasicUART).

**Gowin UG285 — relevant memory sections inspected.** It documents 1/2/4/8-bit BSRAM configurations and wider options. Reads are clocked; the optional output pipeline adds a cycle. Crucially, GW2A-family dual-port BSRAM does not support read-before-write mode. Keep explicit old-data capture and collision-free scheduling. A narrow memory layout can remove wide operand selectors, but address/control logic must be measured. [Vendor guide](https://cdn.gowinsemi.com.cn/UG285E.pdf).

The official device table lists 46 blocks/828 Kbits for GW2A-18; our exact-target reports also show a 46-block capacity. Capacity is ample for the histories. Additional blocks can be worthwhile if they reduce surrounding Logic. [Vendor device family](https://www.gowinsemi.com/en/product/arora-ii-fpga/).

## Implementation order

1. Reproduce the actual best teammate baseline and existing 312-Logic reference.
2. Compare a shared parallel arithmetic/comparison unit with 1-, 2-, 4-, and 8-bit variants.
3. Couple the best narrow variants to inexpensive operand storage: fixed shifts versus digit-organized BSRAM.
4. Remove duplicate fill/pointer state; simplify address decoding and packet-field storage where proven redundant.
5. Sweep FSM encodings on the surviving architecture. Revisit UART only if its mapped report identifies a specific cost.
6. Keep only complete-design improvements that pass the expanded reference/UART suite; physical qualification remains mandatory before release.

The separate handoff prompt gives the exact semantic, measurement, and validation requirements.
