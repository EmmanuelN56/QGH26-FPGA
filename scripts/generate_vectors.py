"""Check independent model against organizer classes, then emit HDL vectors.

Only allowlisted AST nodes are executed. Neither organizer module is imported:
their module-level serial/test/file-writing code never runs.
"""

import ast
import hashlib
import json
from pathlib import Path
import random

from reference_model import BUY, SELL, NONE, ITEM_A, ITEM_B, REQUEST, RESPONSE, ReferenceModel

ROOT = Path(__file__).resolve().parents[1]


def organizer_reference(filename, classname):
    tree = ast.parse((ROOT / "scripts" / filename).read_text())
    names = {"WINDOW_SIZE", "ACTION_NONE", "ACTION_SELL", "ACTION_BUY"}
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "collections":
            nodes.append(node)
        elif isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id in names for t in node.targets
        ):
            ast.literal_eval(node.value)  # Reject executable settings expressions.
            nodes.append(node)
        elif isinstance(node, ast.ClassDef) and node.name == classname:
            nodes.append(node)
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), filename, "exec"), namespace)
    return namespace[classname]


def sessions():
    yield "quick", [50] * 16 + [80, 85, 85, 20, 15], [100] * 16 + [60, 55, 55, 130, 140], [i in (16, 19, 20) for i in range(21)]
    rng = random.Random(0x57214720)
    a = [rng.randint(0, 100) for _ in range(100)]
    b = [rng.randint(0, 100) for _ in range(100)]
    slots = random.Random(0x57214720 ^ 0xA5A5A5A5)
    swaps = [i >= 16 and slots.random() < 0.5 for i in range(100)]
    yield "robust_practice", a, b, swaps
    yield "robust_repeat_without_reset", a, b, swaps
    yield "equal_old_and_new", [10] * 16 + [10, 11, 10, 0, 0, 10, 10] * 8, [10] * 16 + [9, 10, 10, 11, 11, 0, 10] * 8, [bool(i % 2) for i in range(72)]
    yield "floor_boundary", [1] * 15 + [0] + [1, 0, 1, 2] * 16, [0] * 15 + [15] + [1, 0, 15, 16] * 16, [True] * 80
    yield "maximum_sum", [65535] * 32 + [0, 65535] * 32, [0] * 16 + [65535] * 32 + [0, 65535] * 24, [bool(i % 2) for i in range(96)]
    yield "all_zero_after_maximum", [0] * 40, [0] * 40, [True] * 40
    for seed in range(8):
        rng = random.Random(seed)
        n = 300 if seed == 0 else 100
        yield f"random_u16_{seed}", [rng.randrange(65536) for _ in range(n)], [rng.randrange(65536) for _ in range(n)], [bool(i % 2) for i in range(n)]


def hand_checks():
    model = ReferenceModel()
    for i in range(16):
        assert model.process(REQUEST.pack(i, ITEM_A, 50, ITEM_B, 100)) == RESPONSE.pack(i, ITEM_A, NONE, ITEM_B, NONE, 0)
    # A: sum 830 -> 51, prev 50 <= 50, 80 > 51 => BUY.
    # B: sum 1560 -> 97, prev 100 >= 100, 60 < 97 => SELL.
    assert model.process(REQUEST.pack(16, ITEM_B, 60, ITEM_A, 80)) == RESPONSE.pack(16, ITEM_B, SELL, ITEM_A, BUY, 0)
    # A: sum 865 -> 54, prev 80 > 51 => held BUY.
    # B: sum 1515 -> 94, prev 60 < 97 => held SELL.
    assert model.process(REQUEST.pack(17, ITEM_A, 85, ITEM_B, 55)) == RESPONSE.pack(17, ITEM_A, BUY, ITEM_B, SELL, 0)
    assert model.process(REQUEST.pack(0, ITEM_B, 65535, ITEM_A, 0)) == RESPONSE.pack(0, ITEM_B, NONE, ITEM_A, NONE, 0)
    assert model.items[ITEM_A].total == 0 and model.items[ITEM_B].total == 65535


def generate(output):
    hand_checks()
    references = [organizer_reference("21_quick_uart_test.py", "Reference"), organizer_reference("22_robust_uart_test.py", "MovingAverageReference")]
    model = ReferenceModel()  # Retained across sessions to exercise index-zero clearing.
    packets, states, ranges = [], [], []
    for name, pa, pb, swaps in sessions():
        start = len(packets)
        refs = [{ITEM_A: cls(), ITEM_B: cls()} for cls in references]
        assert len(pa) == len(pb) == len(swaps)
        for index, (a, b, swapped) in enumerate(zip(pa, pb, swaps)):
            slots = (ITEM_B, b, ITEM_A, a) if swapped else (ITEM_A, a, ITEM_B, b)
            request = REQUEST.pack(index, *slots)
            response = model.process(request)
            for reference in refs:
                aa, ab = reference[ITEM_A].process(a), reference[ITEM_B].process(b)
                aa, ab = NONE if aa is None else aa, NONE if ab is None else ab
                expected = RESPONSE.pack(index, slots[0], ab if swapped else aa, slots[2], aa if swapped else ab, 0)
                assert response == expected, (name, index, response.hex(), expected.hex())
            sa, sb = model.items[ITEM_A], model.items[ITEM_B]
            packets.append(request.hex() + response.hex())
            states.append(f"{sa.total:06x}{sb.total:06x}{sa.previous:04x}{sb.previous:04x}{sa.pointer:02x}{sb.pointer:02x}{len(sa.prices):02x}{len(sb.prices):02x}0000")
        ranges.append({"name": name, "start": start, "packets": len(pa)})
    output.mkdir(parents=True, exist_ok=True)
    (output / "packets.mem").write_text("\n".join(packets) + "\n")
    (output / "states.mem").write_text("\n".join(states) + "\n")
    manifest = {"packet_count": len(packets), "sessions": ranges, "organizer_sha256": {f: hashlib.sha256((ROOT / "scripts" / f).read_bytes()).hexdigest() for f in ("21_quick_uart_test.py", "22_robust_uart_test.py")}, "packets_sha256": hashlib.sha256((output / "packets.mem").read_bytes()).hexdigest(), "states_sha256": hashlib.sha256((output / "states.mem").read_bytes()).hexdigest()}
    (output / "vectors.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"PASS reference model: {len(packets)} packets / {len(ranges)} sessions agree byte-for-byte with both organizer classes; hand calculations pass")
    return manifest


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "testbench" / "vectors")
    generate(parser.parse_args().output)
