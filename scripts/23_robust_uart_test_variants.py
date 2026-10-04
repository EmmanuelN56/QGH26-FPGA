"""
GQH Hardware Track - UART test, variant stimulus modes

Same packet protocol, reference model, and scoring as the practice script.
Only the price stimulus changes, so you can check that your design still
matches the reference on inputs other than the one practice seed.

Examples:
    python 23_robust_uart_test_variants.py --list
    python 23_robust_uart_test_variants.py --dry-run --mode all
    python 23_robust_uart_test_variants.py --port COM6 --mode random --seed 12345
    python 23_robust_uart_test_variants.py --port COM6 --mode boundary --seed 7

IMPORTANT: reset the board before every run. The FPGA keeps its window and
last-price state between runs, so a second run without a reset will not
start from a clean warm-up.

Requires: Python 3 and pyserial  (pip install pyserial). Dry-run does not.
"""

import argparse
import csv
import random
import struct
import sys
import time
from collections import deque

# ============================================================
# FIXED SETTINGS (same as the practice script)
# ============================================================

BAUD = 115200
PACKET_COUNT = 100
WINDOW_SIZE = 16
PRICE_MIN = 0
PRICE_MAX = 65535
ITEM_A = 0x11
ITEM_B = 0x22
TIMEOUT_S = 1.0

ACTION_NONE = 0x00
ACTION_SELL = 0x01
ACTION_BUY = 0x02

SCORED_PACKETS_TOTAL = PACKET_COUNT - WINDOW_SIZE
SCORED_ACTIONS_TOTAL = SCORED_PACKETS_TOTAL * 2

INPUT_STRUCT = struct.Struct(">HBHBH")
OUTPUT_STRUCT = struct.Struct(">HBBBBH")


def action_name(v):
    return {ACTION_NONE: "NONE", ACTION_SELL: "SELL",
            ACTION_BUY: "BUY"}.get(v, f"0x{v:02X}")


# ============================================================
# REFERENCE MODEL (unchanged)
# ============================================================

class MovingAverageReference:
    def __init__(self):
        self.window = deque(maxlen=WINDOW_SIZE)
        self.running_sum = 0
        self.last_price = None
        self.action = ACTION_NONE

    def process(self, price):
        if len(self.window) < WINDOW_SIZE:
            self.window.append(price)
            self.running_sum += price
            self.last_price = price
            return None

        old_avg = self.running_sum >> 4
        oldest = self.window[0]
        new_sum = self.running_sum - oldest + price
        new_avg = new_sum >> 4

        if self.last_price <= old_avg and price > new_avg:
            self.action = ACTION_BUY
        elif self.last_price >= old_avg and price < new_avg:
            self.action = ACTION_SELL

        self.window.append(price)
        self.running_sum = new_sum
        self.last_price = price
        return self.action


# ============================================================
# STIMULUS MODES
# Each generator returns PACKET_COUNT prices in [0, 65535].
# `stream` is 0 for item A and 1 for item B so the two items differ.
# ============================================================

def clamp(v):
    return max(PRICE_MIN, min(PRICE_MAX, v))


def gen_random(rng, stream):
    return [rng.randint(PRICE_MIN, PRICE_MAX) for _ in range(PACKET_COUNT)]


def gen_low(rng, stream):
    return [rng.randint(0, 255) for _ in range(PACKET_COUNT)]


def gen_high(rng, stream):
    return [rng.randint(PRICE_MAX - 255, PRICE_MAX) for _ in range(PACKET_COUNT)]


def gen_narrow(rng, stream):
    base = rng.randint(1000, 60000)
    return [base + rng.randint(0, 10) for _ in range(PACKET_COUNT)]


def gen_const(rng, stream):
    v = rng.randint(PRICE_MIN, PRICE_MAX)
    return [v] * PACKET_COUNT


def gen_zeros(rng, stream):
    return [0] * PACKET_COUNT


def gen_max(rng, stream):
    return [PRICE_MAX] * PACKET_COUNT


def gen_alternate(rng, stream):
    lo, hi = (PRICE_MIN, PRICE_MAX) if stream == 0 else (PRICE_MAX, PRICE_MIN)
    return [lo if i % 2 == 0 else hi for i in range(PACKET_COUNT)]


def gen_ramp(rng, stream):
    up = [round(i * PRICE_MAX / (PACKET_COUNT - 1)) for i in range(PACKET_COUNT)]
    return up if stream == 0 else up[::-1]


def gen_sawtooth(rng, stream):
    period = rng.choice([4, 6, 8, 12, 20])
    mid = rng.randint(20000, 45000)
    amp = rng.randint(100, 15000)
    out = []
    for i in range(PACKET_COUNT):
        phase = (i + stream * (period // 2)) % period
        out.append(clamp(mid - amp + (2 * amp * phase) // max(1, period - 1)))
    return out


def gen_extremes(rng, stream):
    pool = [0, 1, 2, 255, 256, 32767, 32768, 65534, 65535]
    return [rng.choice(pool) for _ in range(PACKET_COUNT)]


def gen_boundary(rng, stream):
    """After warm-up, land within a few counts of the current average so the
    <= and >= comparisons and the floor from >>4 are exercised constantly."""
    window = deque(maxlen=WINDOW_SIZE)
    out = []
    for i in range(PACKET_COUNT):
        if i < WINDOW_SIZE:
            p = rng.randint(20000, 40000)
        else:
            avg = sum(window) >> 4
            p = clamp(avg + rng.choice([-2, -1, 0, 0, 1, 2, 3]))
        window.append(p)
        out.append(p)
    return out


def gen_wide_swing(rng, stream):
    """Slow big drift with noise, so the average lags and crossings are real."""
    out = []
    v = rng.randint(10000, 55000)
    for _ in range(PACKET_COUNT):
        v = clamp(v + rng.randint(-9000, 9000))
        out.append(v)
    return out


MODES = {
    "random":     (gen_random,     "uniform over the full 16-bit range"),
    "low":        (gen_low,        "values 0 to 255 only"),
    "high":       (gen_high,       "values 65280 to 65535 only"),
    "narrow":     (gen_narrow,     "10-count band, many equalities with the average"),
    "const":      (gen_const,      "one constant price per item, never crosses"),
    "zeros":      (gen_zeros,      "all zeros"),
    "max":        (gen_max,        "all 65535, checks sum width"),
    "alternate":  (gen_alternate,  "0 and 65535 alternating, items in antiphase"),
    "ramp":       (gen_ramp,       "A ramps up, B ramps down across the run"),
    "sawtooth":   (gen_sawtooth,   "periodic wave around a midpoint"),
    "extremes":   (gen_extremes,   "random picks from 0,1,2,255,256,32767,32768,65534,65535"),
    "boundary":   (gen_boundary,   "prices within +-3 of the running average"),
    "swing":      (gen_wide_swing, "random walk with large steps"),
}


# ============================================================
# BUILD VECTORS
# ============================================================

def build(mode, seed):
    gen = MODES[mode][0]
    rng = random.Random(seed)
    prices_a = gen(rng, 0)
    prices_b = gen(rng, 1)

    slot_rng = random.Random(seed ^ 0xA5A5A5A5)
    swap = [(i >= WINDOW_SIZE and slot_rng.random() < 0.5)
            for i in range(PACKET_COUNT)]

    ref_a, ref_b = MovingAverageReference(), MovingAverageReference()
    exp_a = [ref_a.process(p) for p in prices_a]
    exp_b = [ref_b.process(p) for p in prices_b]
    return prices_a, prices_b, swap, exp_a, exp_b


def describe(mode, seed):
    prices_a, prices_b, swap, exp_a, exp_b = build(mode, seed)
    lines = [f"mode={mode:9s} seed=0x{seed:08X}"]
    for name, prices, exp in (("A", prices_a, exp_a), ("B", prices_b, exp_b)):
        scored = exp[WINDOW_SIZE:]
        buys = sum(1 for x in scored if x == ACTION_BUY)
        sells = sum(1 for x in scored if x == ACTION_SELL)
        nones = sum(1 for x in scored if x == ACTION_NONE)
        changes = sum(1 for a, b in zip(scored, scored[1:]) if a != b)
        lines.append(
            f"   item {name}: min={min(prices):5d} max={max(prices):5d} | "
            f"BUY={buys:2d} SELL={sells:2d} NONE={nones:2d} | "
            f"action changes={changes:2d}"
        )
    lines.append(f"   slot swaps={sum(swap)}/{SCORED_PACKETS_TOTAL}")
    return "\n".join(lines)


# ============================================================
# HARDWARE RUN
# ============================================================

def run_hardware(port, mode, seed, tag):
    import serial  # imported here so --dry-run works without pyserial

    prices_a, prices_b, swap_slots, expected_a, expected_b = build(mode, seed)

    csv_file = f"trade_results_{tag}.csv"
    summary_file = f"trade_summary_{tag}.txt"

    rows = []
    successful_latencies = []
    correct_packets = 0
    correct_actions = 0
    timeout_count = 0

    print()
    print(f"Mode: {mode} | seed 0x{seed:08X}")
    print(f"Generated {PACKET_COUNT} packets "
          f"({SCORED_PACKETS_TOTAL} scored, {SCORED_ACTIONS_TOTAL} scored actions).")
    print(f"Opening {port} at {BAUD} baud...")
    print()

    with serial.Serial(port, BAUD, timeout=TIMEOUT_S) as ser:
        time.sleep(0.2)
        ser.reset_input_buffer()

        for index in range(PACKET_COUNT):
            pa, pb = prices_a[index], prices_b[index]
            exp_a, exp_b = expected_a[index], expected_b[index]

            if swap_slots[index]:
                item1, price1, expected1 = ITEM_B, pb, exp_b
                item2, price2, expected2 = ITEM_A, pa, exp_a
            else:
                item1, price1, expected1 = ITEM_A, pa, exp_a
                item2, price2, expected2 = ITEM_B, pb, exp_b

            tx = INPUT_STRUCT.pack(index, item1, price1, item2, price2)

            t0 = time.perf_counter_ns()
            ser.write(tx)
            rx = ser.read(8)
            t1 = time.perf_counter_ns()
            latency_us = (t1 - t0) / 1000.0

            base = {
                "index": index,
                "tx_item1": f"0x{item1:02X}",
                "tx_price1": price1,
                "tx_item2": f"0x{item2:02X}",
                "tx_price2": price2,
                "expected_action1": "IGNORED" if expected1 is None else action_name(expected1),
                "expected_action2": "IGNORED" if expected2 is None else action_name(expected2),
            }

            if len(rx) != 8:
                timeout_count += 1
                partial_hex = rx.hex(" ").upper() if rx else "NONE"
                print(f"[{index:02d}] TIMEOUT: received {len(rx)}/8 bytes: {partial_hex}")
                rows.append({
                    **base,
                    "rx_index": "", "rx_item1": "", "rx_action1": "",
                    "rx_item2": "", "rx_action2": "", "rx_reserved": partial_hex,
                    "action1_correct": "", "action2_correct": "", "packet_correct": "",
                    "status": "TIMEOUT",
                    "latency_us": f"{latency_us:.2f}",
                })
                break

            rx_index, rx_item1, rx_action1, rx_item2, rx_action2, reserved = \
                OUTPUT_STRUCT.unpack(rx)
            successful_latencies.append(latency_us)

            if index < WINDOW_SIZE:
                status = "IGNORED_WARMUP"
                action1_correct = action2_correct = packet_correct = ""
                expected1_text = expected2_text = "---"
            else:
                index_ok = rx_index == index
                item1_ok = rx_item1 == item1
                item2_ok = rx_item2 == item2
                action1_ok = rx_action1 == expected1
                action2_ok = rx_action2 == expected2
                reserved_ok = reserved == 0x0000

                correct_actions += int(action1_ok) + int(action2_ok)
                packet_ok = (index_ok and item1_ok and item2_ok
                             and action1_ok and action2_ok and reserved_ok)

                if packet_ok:
                    correct_packets += 1
                    status = "CORRECT"
                else:
                    failed = []
                    if not index_ok:
                        failed.append("INDEX")
                    if not item1_ok:
                        failed.append("ITEM1")
                    if not action1_ok:
                        failed.append("ACTION1")
                    if not item2_ok:
                        failed.append("ITEM2")
                    if not action2_ok:
                        failed.append("ACTION2")
                    if not reserved_ok:
                        failed.append("RESERVED")
                    status = "WRONG_" + "_".join(failed)

                action1_correct = "YES" if action1_ok else "NO"
                action2_correct = "YES" if action2_ok else "NO"
                packet_correct = "YES" if packet_ok else "NO"
                expected1_text = action_name(expected1)
                expected2_text = action_name(expected2)

            rows.append({
                **base,
                "rx_index": rx_index,
                "rx_item1": f"0x{rx_item1:02X}",
                "rx_action1": action_name(rx_action1),
                "rx_item2": f"0x{rx_item2:02X}",
                "rx_action2": action_name(rx_action2),
                "rx_reserved": f"0x{reserved:04X}",
                "action1_correct": action1_correct,
                "action2_correct": action2_correct,
                "packet_correct": packet_correct,
                "status": status,
                "latency_us": f"{latency_us:.2f}",
            })

            print(
                f"[{index:02d}] TX: 0x{item1:02X}:{price1:5d}, 0x{item2:02X}:{price2:5d} | "
                f"EXPECTED: {expected1_text:4s}, {expected2_text:4s} | "
                f"RX: 0x{rx_item1:02X}:{action_name(rx_action1):4s}, "
                f"0x{rx_item2:02X}:{action_name(rx_action2):4s} | "
                f"{status:16s} | {latency_us:9.2f} us"
            )

    csv_fields = [
        "index", "tx_item1", "tx_price1", "tx_item2", "tx_price2",
        "expected_action1", "expected_action2",
        "rx_index", "rx_item1", "rx_action1", "rx_item2", "rx_action2", "rx_reserved",
        "action1_correct", "action2_correct", "packet_correct",
        "status", "latency_us",
    ]
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        w.writeheader()
        w.writerows(rows)

    packet_correctness = correct_packets / SCORED_PACKETS_TOTAL * 100.0
    action_correctness = correct_actions / SCORED_ACTIONS_TOTAL * 100.0
    packet_points = 50.0 * correct_packets / SCORED_PACKETS_TOTAL
    action_points = 20.0 * correct_actions / SCORED_ACTIONS_TOTAL
    avg_us = (sum(successful_latencies) / len(successful_latencies)
              if successful_latencies else 0.0)

    lines = [
        "FPGA Dual-Item Trade Signal Test (variant)",
        "==========================================",
        "",
        f"Mode: {mode}",
        f"Seed: 0x{seed:08X}",
        f"Requested packets: {PACKET_COUNT}",
        f"Packets successfully received: {len(successful_latencies)}",
        f"Warm-up packets ignored: {WINDOW_SIZE}",
        f"Scored packets (fixed): {SCORED_PACKETS_TOTAL}",
        f"Correct packets: {correct_packets}",
        f"Packet correctness: {packet_correctness:.2f}%",
        f"Correct individual actions: {correct_actions}/{SCORED_ACTIONS_TOTAL}",
        f"Action correctness: {action_correctness:.2f}%",
        f"Timeouts: {timeout_count}",
        "",
        f"Estimated correctness points: {packet_points + action_points:.1f} / 70",
        "",
        f"Average successful round-trip latency: {avg_us:.2f} us",
        f"Average successful round-trip latency: {avg_us / 1000.0:.3f} ms",
        "",
        f"UART port: {port}",
        f"UART baud rate: {BAUD}",
        "",
    ]
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print()
    print("=" * 40)
    print(f"FINAL TEST RESULTS ({mode}, seed 0x{seed:08X})")
    print("=" * 40)
    for ln in lines[5:-1]:
        if ln:
            print(ln)
    print(f"CSV output: {csv_file}")
    print(f"Summary output: {summary_file}")
    print("=" * 40)
    print()


# ============================================================
# MAIN
# ============================================================

def main():
    ap = argparse.ArgumentParser(description="Variant UART test for the trade-signal FPGA")
    ap.add_argument("--port", default="COM6", help="serial port (default COM6)")
    ap.add_argument("--mode", default="random",
                    help="stimulus mode, or 'all' with --dry-run (see --list)")
    ap.add_argument("--seed", type=lambda s: int(s, 0), default=0x1F00D16B,
                    help="integer seed, decimal or 0x hex")
    ap.add_argument("--dry-run", action="store_true",
                    help="no hardware; print what each mode would exercise")
    ap.add_argument("--list", action="store_true", help="list modes and exit")
    args = ap.parse_args()

    if args.list:
        for name, (_, desc) in MODES.items():
            print(f"{name:10s} {desc}")
        return

    if args.mode != "all" and args.mode not in MODES:
        sys.exit(f"Unknown mode '{args.mode}'. Use --list.")

    if args.dry_run:
        names = list(MODES) if args.mode == "all" else [args.mode]
        for n in names:
            print(describe(n, args.seed))
            print()
        return

    if args.mode == "all":
        sys.exit("--mode all is dry-run only. Reset the board between hardware runs.")

    tag = f"{args.mode}_{args.seed:08X}"
    run_hardware(args.port, args.mode, args.seed, tag)


if __name__ == "__main__":
    main()
