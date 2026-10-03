"""Generate deterministic requests, answers, and coverage without an FPGA.

python scripts/stress_suite.py --output tests/vectors/stress
"""

import argparse
import ast
from collections import Counter, deque
import csv
import hashlib
import itertools
import json
from pathlib import Path
import random

from reference_model import ACTION_NAMES, BUY, ITEM_A, ITEM_B, NONE, SELL, PacketReference, Request

ROOT = Path(__file__).resolve().parents[1]
BOUNDARIES = (0, 1, 2, 15, 16, 17, 255, 256, 257, 4095, 4096,
              32767, 32768, 32769, 65534, 65535)
TRACE_FIELDS = ("old_sum", "new_sum", "old_average", "new_average", "oldest",
                "previous", "pointer", "last_action", "reason")
CSV_FIELDS = ("sequence", "session", "case", "index", "tx_item1", "tx_price1", "tx_item2",
              "tx_price2", "expected_action1", "expected_action2", "request_hex",
              "response_hex") + tuple(f"slot{s}_{f}" for s in (1, 2) for f in TRACE_FIELDS)


def organizer_class(path, class_name):
    """Load ONLY literal constants + reference class, never run UART script body."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            nodes.append(node)
        elif isinstance(node, ast.ClassDef) and node.name == class_name:
            nodes.append(node)
    namespace = {"deque": deque}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace[class_name]


class OrganizerOracle:
    def __init__(self, factory):
        self.factory = factory
        self.items = {}

    def process(self, request):
        if request.index == 0:
            self.items = {ITEM_A: self.factory(), ITEM_B: self.factory()}
        a1 = self.items[request.item1].process(request.price1)
        a2 = self.items[request.item2].process(request.price2)
        # Organizer classes return None during warm-up; wire protocol requires 0.
        from reference_model import RESPONSE
        return RESPONSE.pack(request.index, request.item1, a1 or NONE,
                             request.item2, a2 or NONE, 0)


class RollingItem:
    """Second local implementation: circular storage and a rolling 20-bit sum."""
    def __init__(self):
        self.ring = [0] * 16
        self.pointer = self.count = self.total = self.action = 0
        self.previous = None

    def process(self, price):
        if self.count < 16:
            self.total += price
            self.count += 1
            result = None
        else:
            before = self.total >> 4
            updated = self.total - self.ring[self.pointer] + price
            after = updated >> 4
            if self.previous <= before and price > after:
                self.action = BUY
            elif self.previous >= before and price < after:
                self.action = SELL
            self.total = updated
            result = self.action
        self.ring[self.pointer] = price
        self.pointer = (self.pointer + 1) % 16
        self.previous = price
        if not 0 <= self.total <= 16 * 65535:
            raise AssertionError("sum escaped the 20-bit range")
        return result


def session(name, a, b, placement="alternate", seed=0):
    """Yield one valid sequential session, including slot swaps during warm-up."""
    rng = random.Random(seed)
    sentinel = object()
    for index, (pa, pb) in enumerate(itertools.zip_longest(a, b, fillvalue=sentinel)):
        if pa is sentinel or pb is sentinel:
            raise ValueError("item sequences must have the same length")
        swap = placement == "ba" or (placement == "alternate" and index % 2 == 1)
        if placement == "random":
            swap = rng.getrandbits(1) == 1
        elif placement not in ("ab", "ba", "alternate"):
            raise ValueError("unknown slot placement")
        request = Request(index, ITEM_B, pb, ITEM_A, pa) if swap else Request(index, ITEM_A, pa, ITEM_B, pb)
        yield name, request


def cases(profile="stress", seed=0x57214720):
    # Exact official quick example and robust practice sequence.
    a = [50] * 16 + [80, 85, 85, 20, 15]
    b = [100] * 16 + [60, 55, 55, 130, 140]
    for i, (pa, pb) in enumerate(zip(a, b)):
        swap = i in (16, 19, 20)
        yield "official_quick", Request(i, ITEM_B if swap else ITEM_A,
                                       pb if swap else pa, ITEM_A if swap else ITEM_B,
                                       pa if swap else pb)
    rng = random.Random(0x57214720)
    a = [rng.randint(0, 100) for _ in range(100)]
    b = [rng.randint(0, 100) for _ in range(100)]
    slots = random.Random(0x57214720 ^ 0xA5A5A5A5)
    for i in range(100):
        swap = i >= 16 and slots.random() < 0.5
        yield "official_robust", Request(i, ITEM_B if swap else ITEM_A,
                                        b[i] if swap else a[i], ITEM_A if swap else ITEM_B,
                                        a[i] if swap else b[i])

    for base in BOUNDARIES:
        for placement in ("ab", "ba", "alternate"):
            yield from session(f"constant_{base}_{placement}", [base] * 64, [65535 - base] * 64, placement)
    for left, right in itertools.product(BOUNDARIES, repeat=2):
        yield from session(f"boundary_pair_{left}_{right}",
                           [left] * 16 + [right] * 17 + [left] * 17,
                           [right] * 16 + [left] * 17 + [right] * 17)
    # Full Cartesian product for four-sample motifs over {0,1,2}, then every
    # next price in the same alphabet. Repeated motifs fill all 16 positions.
    for motif in itertools.product(range(3), repeat=4):
        for current in range(3):
            yield from session("small_motif_" + "".join(map(str, motif)) + f"_{current}",
                               list(motif) * 4 + [current],
                               [2 - p for p in motif] * 4 + [2 - current])
    # All discarded fraction values, low/mid/high baselines, strict and
    # inclusive comparisons; both sides of floor(new_sum/16).
    for base, remainder, delta in itertools.product((0, 100, 32768, 65520), range(16), (-1, 0, 1)):
        current = max(0, min(65535, base + delta))
        window = [base + remainder] + [base] * 15
        yield from session(f"floor_{base}_{remainder}_{delta}", window + [current] * 18,
                           [65535 - p for p in window] + [65535 - current] * 18)
    yield from session("rounding_buy", [1] * 15 + [0, 1], [0] + [1] * 15 + [0])
    yield from session("held_actions", [50] * 16 + [80, 85, 85, 20, 15, 15] * 12,
                       [100] * 16 + [60, 55, 55, 130, 140, 140] * 12)
    # Walking bits, asymmetric byte patterns, signed boundary, maximum sum.
    patterns = [0, 65535, 0xAA55, 0x55AA, 0xFF00, 0x00FF] + [1 << bit for bit in range(16)]
    yield from session("walking_bits", patterns * 32, list(reversed(patterns)) * 32)
    yield from session("pointer_extremes", [65535] * 16 + [0, 65535] * 256,
                       [0] * 16 + [65535, 0] * 256)
    # Abort partially filled sessions and reset after an active SELL/BUY state.
    for length in (1, 1, 2, 7, 15, 16, 17, 33):
        yield from session(f"short_reset_{length}", [65535] * min(16, length) + [0] * max(0, length - 16),
                           [0] * min(16, length) + [65535] * max(0, length - 16), "ba")
    yield from session("reset_recovery", [7] * 16 + [8, 8, 0], [65000] * 16 + [0, 0, 65535])

    random_count = 512 if profile == "smoke" else 8192
    for distribution in ("practice_range", "full_range", "boundary_bias"):
        rng = random.Random(seed ^ {"practice_range": 1, "full_range": 2, "boundary_bias": 3}[distribution])
        def draw():
            if distribution == "practice_range":
                return rng.randint(0, 100)
            if distribution == "boundary_bias" and rng.random() < 0.8:
                return rng.choice(BOUNDARIES)
            return rng.randint(0, 65535)
        a = [draw() for _ in range(random_count)]
        b = [draw() for _ in range(random_count)]
        yield from session(f"random_{distribution}", a, b, "random", seed ^ 0xA5A5A5A5)
    if profile == "stress":
        # Every uint16 price AND every uint16 index, no accidental index wrap.
        yield from session("uint16_sweep", range(65536), range(65535, -1, -1))


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate(output, profile="stress", seed=0x57214720):
    output.mkdir(parents=True, exist_ok=True)
    sources = ((ROOT / "scripts/21_quick_uart_test.py", "Reference"),
               (ROOT / "scripts/22_robust_uart_test.py", "MovingAverageReference"))
    oracles = [OrganizerOracle(organizer_class(path, name)) for path, name in sources]
    oracles.append(OrganizerOracle(RollingItem))
    reference = PacketReference()
    counts, reasons, transitions, action_pairs = Counter(), Counter(), Counter(), Counter()
    residues, pointers, prices, indices, comparisons = set(), set(), set(), set(), set()
    sessions = warmup = swaps = 0
    min_sum, max_sum = 16 * 65535, 0
    with (output / "answers.csv").open("w", newline="", encoding="utf-8") as answers, \
            (output / "requests.mem").open("w", encoding="ascii", newline="\n") as requests, \
            (output / "responses.mem").open("w", encoding="ascii", newline="\n") as responses:
        writer = csv.DictWriter(answers, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for sequence, (name, request) in enumerate(cases(profile, seed)):
            expected, traces = reference.process(request)
            for oracle in oracles:
                if oracle.process(request) != expected:
                    raise AssertionError(f"oracle disagreement: {name}, index {request.index}")
            counts[name] += 1
            sessions += request.index == 0
            warmup += request.index < 16
            swaps += request.item1 == ITEM_B
            indices.add(request.index)
            prices.update((request.price1, request.price2))
            a1, a2 = (t["action"] for t in traces)
            action_pairs[f"{ACTION_NAMES[a1]}/{ACTION_NAMES[a2]}"] += 1
            row = dict(sequence=sequence, session=sessions - 1, case=name, index=request.index,
                       tx_item1=f"0x{request.item1:02X}", tx_price1=request.price1,
                       tx_item2=f"0x{request.item2:02X}", tx_price2=request.price2,
                       expected_action1=ACTION_NAMES[a1], expected_action2=ACTION_NAMES[a2],
                       request_hex=request.pack().hex(), response_hex=expected.hex())
            for slot, trace in enumerate(traces, 1):
                row.update({f"slot{slot}_{f}": trace[f] for f in TRACE_FIELDS})
                reasons[trace["reason"]] += 1
                min_sum = min(min_sum, trace["new_sum"])
                max_sum = max(max_sum, trace["new_sum"])
                if trace["reason"] != "WARMUP":
                    residues.update((trace["old_sum"] % 16, trace["new_sum"] % 16))
                    pointers.add(trace["pointer"])
                    transitions[f"{ACTION_NAMES[trace['last_action']]}->{ACTION_NAMES[trace['action']]}"] += 1
                    relation = lambda x, y: "<" if x < y else ">" if x > y else "="
                    price = request.price1 if slot == 1 else request.price2
                    comparisons.add(relation(trace["previous"], trace["old_average"]) + "/" +
                                    relation(price, trace["new_average"]))
            writer.writerow(row)
            requests.write(request.pack().hex() + "\n")
            responses.write(expected.hex() + "\n")
    manifest = dict(schema_version=1, profile=profile, seed=seed,
                    packets=sum(counts.values()), sessions=sessions, warmup_packets=warmup,
                    decision_packets=sum(counts.values()) - warmup, swapped_packets=swaps,
                    cases=dict(counts), oracle_checks=["chronological full re-sum", "circular rolling sum",
                                                     "organizer quick Reference", "organizer robust MovingAverageReference"],
                    organizer_sources={p.relative_to(ROOT).as_posix(): sha256(p) for p, _ in sources},
                    suite_sources={f"scripts/{f}": sha256(ROOT / "scripts" / f)
                                   for f in ("reference_model.py", "stress_suite.py")},
                    coverage=dict(unique_prices=len(prices), unique_indices=len(indices),
                                  min_sum=min_sum, max_sum=max_sum, sum_remainders=sorted(residues),
                                  replacement_pointers=sorted(pointers), comparisons=sorted(comparisons),
                                  reasons=dict(reasons), transitions=dict(transitions), action_pairs=dict(action_pairs)),
                    files={f: sha256(output / f) for f in ("answers.csv", "requests.mem", "responses.mem")},
                    implementation_validation="NOT RUN; golden answers only",
                    resource_and_latency_validation="NOT MEASURED; requires MVP/build/physical board")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "tests/vectors/stress")
    parser.add_argument("--profile", choices=("smoke", "stress"), default="stress")
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=0x57214720)
    args = parser.parse_args()
    manifest = generate(args.output, args.profile, args.seed)
    print(f"PASS: {manifest['packets']:,} requests + answers, {manifest['sessions']:,} sessions; four models agree.")
    print(f"Files: {args.output.resolve()}")


if __name__ == "__main__":
    main()
