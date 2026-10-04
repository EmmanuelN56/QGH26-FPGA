# Tang Nano 20K bring-up for the 186-Logic release

The selected core is **186 total Logic / 92 registers / 4 B-SRAM**. Its
source, build settings, and physically tested programming file are identified
in the [root README](../README.md). This page describes that selected release.

## Hardware and build

- Board: Sipeed Tang Nano 20K; `GW2AR-LV18QN88C8/I7`, device version C.
- Top: `top`; clock: 27 MHz; UART: 115200 baud, 8N1.
- Toolchain: Gowin EDA V1.9.11.03 Education and Gowin Programmer.
- Programming: volatile SRAM; reload after power loss.

Use the unchanged [organizer CST](../constraints/19_tang_nano_20k.cst).

| Port | Pin | Meaning |
| --- | --- | --- |
| `sys_clk` | 4 | 27 MHz onboard oscillator |
| `reset_btn` | 87 | KEY2/S2, active-high reset input, pull-down |
| `uart_rx_i` | 70 | BL616 to FPGA |
| `uart_tx_o` | 69 | FPGA to BL616 |
| `led0_n` / `led1_n` | 15 / 16 | Active-low LEDs; unused, driven high |

Follow the [Gowin build instructions](../gowin/README.md). The measured result
is 186 synthesis/routed Logic, 186 LUT, zero ALU/RAM16, 92 registers, 4 B-SRAM,
and zero distributed SSRAM. Routed Fmax is 108.334 MHz, setup/hold slack is
+27.806/+0.074 ns, and reported violations are zero. EX3791 and PR1014 remain.

## Program and run the demo

1. Connect the board with a data-capable USB-C cable.
2. Open Gowin Programmer, scan the device, and select `GW2AR-18C`.
3. Select **SRAM Mode / SRAM Program** and `bitstream/trade_core.fs`, then program.
4. Close Programmer and any serial terminal holding the UART port.
5. Detect the UART port. The October 4 test setup used FTDI serial `2025030317`,
   interface B / COM4; this can differ on another computer.
6. Change only PORT in the organizer quick, normal, and full-range scripts.
   Run them consecutively without manual reset or reprogramming.

The selected file's SHA-256 is:

```text
6fbefe4697c714b18f78830088c826b2f7cc1e2823de0070a688c84f3f6a6e23
```

Check with `Get-FileHash .\bitstream\trade_core.fs -Algorithm SHA256`.
The fresh source rebuild has identical configuration data; its creation-time
comment differs. The submitted hash identifies the exact physically tested file.

## Physical verification on October 4, 2026

The selected file was programmed once before all checks. No manual reset,
reprogramming, or host USB/UART setting change occurred between sessions.

| Test | Correct packets | Correct actions including warm-up |
| --- | --- | --- |
| Organizer quick | PASS | PASS |
| Normal, five runs | 500/500 | 1,000/1,000 |
| Full range, five runs | 500/500 | 1,000/1,000 |
| Modified full range, 41 sessions | 2,492/2,492 | 4,984/4,984 |
| Attached variants, 13 modes plus two extra random seeds | 1,500/1,500 | 3,000/3,000 |
| Total robust checks | **4,992/4,992** | **9,984/9,984** |

Every response was independently rechecked, including warm-up. Timeouts and
mismatches were zero. Five normal runs estimate 100/100 locally; their aggregate
mean/max latency is 16.739/29.604 ms and median of five run means is 16.739245 ms.
Official judge-run and hidden-seed qualification remain pending.

Source-matched simulation also passed the normal/full-range sequence, modified
full-range corpus, and attached variants. Normal/full-range was additionally
checked for 200 packets at actual 27 MHz / 115200 timing, including complete
response bytes, stop bits, gaps, and absence of early or extra responses.
Logs and CSVs were saved during testing; historical tracked reports should not
be treated as measurements of the current source.

## Protocol and recovery

Each request and response is eight bytes with big-endian multi-byte fields.
State follows item ID `0x11`/`0x22`; response order follows request slots.
One shared digit-serial `trade_pair` processes both items while keeping their
histories, sums, previous prices, and held actions independent. Index zero
clears session state before its prices are ingested. Warm-up returns NONE;
later crossings use floor averages (`sum >> 4`).

RX and TX share a baud counter. The selected top has `TX_GAP_CYCLES=0`;
complete UART stop bits and controller-handshake idle clocks are retained.
Send one request and wait for its response. Pipelined requests and invalid or
duplicate item IDs are unsupported. A framing error discards a partial packet.
There is no byte timeout or delimiter; press/release KEY2 after an interrupted
stream. Index zero clears strategy state and does not realign corrupted bytes.
Physical KEY2 polarity was not measured in the recorded test sequence.

If cable detection fails, follow the
[participant guide](https://www.gqhacks.com/hardware/GQH_Hardware_Track_Participant_Guide.pdf).
Close competing programs and use a direct data-capable cable. Ask an organizer
before changing USB drivers or BL616 firmware.
