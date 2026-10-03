"""Offline tests of golden answers, coverage, fault detection, and capture checks."""

import csv
import itertools
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from reference_model import BUY, SELL, NONE, ITEM_A, ITEM_B, RESPONSE, ItemReference, PacketReference, Request
from stress_suite import OrganizerOracle, RollingItem, cases, generate, organizer_class, session
from verify_stress_responses import verify
from check_stress_metrics import evaluate


class FaultyItem:
    """Intentionally wrong algorithms: ensure vectors discriminate common bugs."""
    def __init__(self, fault):
        self.fault, self.window, self.prev, self.action = fault, [], None, NONE

    def process(self, price):
        if self.fault == "signed_price" and price >= 32768:
            price -= 65536
        if len(self.window) < 16:
            self.window.append(price)
            self.prev = 0 if self.fault == "stale_warmup_previous" else price
            return None
        old = sum(self.window)
        updated = (self.window[:-1] if self.fault == "replace_newest" else self.window[1:]) + [price]
        new = sum(updated)
        if self.fault in ("sum16", "sum19"):
            mask = (1 << (16 if self.fault == "sum16" else 19)) - 1
            old, new = old & mask, new & mask
        average = lambda value: value // 16
        if self.fault == "rounded_average":
            average = lambda value: (value + 8) // 16
        elif self.fault == "float_average":
            average = lambda value: value / 16
        before, after = average(old), average(new)
        if self.fault == "compare_both_to_old":
            after = before
        if self.fault == "compare_both_to_new":
            before = after
        buy = self.prev < before if self.fault == "strict_previous" else self.prev <= before
        sell = self.prev > before if self.fault == "strict_previous" else self.prev >= before
        buy_now = price >= after if self.fault == "inclusive_current" else price > after
        sell_now = price <= after if self.fault == "inclusive_current" else price < after
        if buy and buy_now:
            self.action = BUY
        elif sell and sell_now:
            self.action = SELL
        elif self.fault == "hold_returns_none":
            self.action = NONE
        self.window, self.prev = updated, price
        return self.action


class GoldenTests(unittest.TestCase):
    def test_literal_quick_answers(self):
        reference = PacketReference()
        answers = []
        for name, request in cases("smoke"):
            if name != "official_quick":
                break
            answer, _ = reference.process(request)
            answers.append(answer.hex())
        self.assertEqual(answers[16:], ["0010220111020000", "0011110222010000",
                                       "0012110222010000", "0013220211010000", "0014220211010000"])
        self.assertEqual(answers[0], "0000110022000000")

    def test_hand_calculated_floor_answers(self):
        ref = PacketReference()
        for name, request in session("floor", [1] * 15 + [0, 1], [0] + [1] * 15 + [0], "ab"):
            answer, traces = ref.process(request)
        self.assertEqual(answer.hex(), "0010110222000000")
        self.assertEqual((traces[0]["old_sum"], traces[0]["new_sum"]), (15, 15))
        self.assertEqual((traces[1]["old_average"], traces[1]["new_average"]), (0, 0))

    def test_extreme_sum_and_downward_cross(self):
        ref = ItemReference()
        for _ in range(16):
            ref.process(65535)
        action, trace = ref.process(0)
        self.assertEqual(action, SELL)
        self.assertEqual(trace["old_sum"], 1048560)
        self.assertEqual(trace["new_sum"], 983025)
        self.assertEqual(trace["new_average"], 61439)

    def test_warmup_then_first_decision(self):
        ref = ItemReference()
        for price in [50] * 15 + [0]:
            self.assertEqual(ref.process(price)[0], NONE)
        self.assertEqual(ref.process(100)[0], BUY)

    def test_held_buy_and_sell(self):
        for initial, next_prices, expected in ((50, [80, 85, 85], BUY), (100, [60, 55, 55], SELL)):
            ref = ItemReference()
            for _ in range(16):
                ref.process(initial)
            self.assertEqual([ref.process(p)[0] for p in next_prices], [expected] * 3)

    def test_reset_clears_both_actions_before_ingest(self):
        ref = PacketReference()
        for _, request in session("old", [65535] * 16 + [0], [0] * 16 + [65535]):
            ref.process(request)
        answer, traces = ref.process(Request(0, ITEM_B, 123, ITEM_A, 456))
        self.assertEqual(answer.hex(), "0000220011000000")
        self.assertEqual([trace["new_sum"] for trace in traces], [123, 456])
        self.assertEqual([trace["last_action"] for trace in traces], [NONE, NONE])

    def test_swap_preserves_item_histories(self):
        fixed, swapped = PacketReference(), PacketReference()
        a, b = [50] * 16 + [80, 85, 20], [100] * 16 + [60, 55, 130]
        for (_, r1), (_, r2) in zip(session("ab", a, b, "ab"), session("alt", a, b)):
            out1, _ = fixed.process(r1)
            out2, _ = swapped.process(r2)
            v1, v2 = RESPONSE.unpack(out1), RESPONSE.unpack(out2)
            self.assertEqual({v1[1]: v1[2], v1[3]: v1[4]}, {v2[1]: v2[2], v2[3]: v2[4]})
        self.assertEqual(fixed.items[ITEM_A].prices, swapped.items[ITEM_A].prices)

    def test_byte_order_literal(self):
        request = Request(0x1234, ITEM_B, 0xABCD, ITEM_A, 0xFEDC)
        self.assertEqual(request.pack().hex(), "123422abcd11fedc")
        self.assertEqual(Request.unpack(request.pack()), request)

    def test_reject_undefined_host_data_types(self):
        for value in (-1, 65536, 1.5, "7", True, None, float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Request(0, ITEM_A, value, ITEM_B, 0)
                with self.assertRaises(ValueError):
                    Request(value, ITEM_A, 0, ITEM_B, 0)

    def test_reject_undefined_identifiers_and_indices(self):
        for ids in ((ITEM_A, ITEM_A), (ITEM_B, ITEM_B), (0, ITEM_B), (17.0, ITEM_B)):
            with self.assertRaises(ValueError):
                Request(0, ids[0], 0, ids[1], 0)
        with self.assertRaises(ValueError):
            PacketReference().process(Request(16, ITEM_A, 0, ITEM_B, 0))
        ref = PacketReference()
        ref.process(Request(0, ITEM_A, 0, ITEM_B, 0))
        with self.assertRaises(ValueError):
            ref.process(Request(2, ITEM_A, 0, ITEM_B, 0))
        with self.assertRaises(ValueError):
            Request.unpack(b"\x00" * 7)

    def test_all_smoke_packets_match_official_and_rolling(self):
        ref = PacketReference()
        oracles = [OrganizerOracle(RollingItem)]
        for file, name in (("21_quick_uart_test.py", "Reference"), ("22_robust_uart_test.py", "MovingAverageReference")):
            oracles.append(OrganizerOracle(organizer_class(ROOT / "scripts" / file, name)))
        count = 0
        for name, request in cases("smoke"):
            expected, _ = ref.process(request)
            for oracle in oracles:
                self.assertEqual(oracle.process(request), expected, (name, request.index))
            count += 1
        self.assertGreater(count, 10000)

    def test_stress_has_full_uint16_price_and_index_sweep(self):
        sweep = (request for name, request in cases("stress") if name == "uint16_sweep")
        count = 0
        for index, request in enumerate(sweep):
            self.assertEqual(request.index, index)
            self.assertEqual({request.item1: request.price1, request.item2: request.price2},
                             {ITEM_A: index, ITEM_B: 65535 - index})
            count += 1
        self.assertEqual(count, 65536)

    def test_motifs_cover_the_declared_cartesian_product(self):
        starts = {name for name, request in cases("smoke") if name.startswith("small_motif") and request.index == 0}
        self.assertEqual(len(starts), 3 ** 4 * 3)

    def test_price_translation_preserves_actions(self):
        low, high = PacketReference(), PacketReference()
        for _, request in itertools.islice(cases("smoke"), 121):
            moved = Request(request.index, request.item1, request.price1 + 32000,
                            request.item2, request.price2 + 32000)
            self.assertEqual(low.process(request)[0], high.process(moved)[0])

    def test_common_algorithm_mutations_are_detected(self):
        faults = ("signed_price", "stale_warmup_previous", "replace_newest", "sum16", "sum19",
                  "rounded_average", "float_average", "compare_both_to_old", "compare_both_to_new",
                  "strict_previous", "inclusive_current", "hold_returns_none")
        pending = {fault: OrganizerOracle(lambda f=fault: FaultyItem(f)) for fault in faults}
        ref = PacketReference()
        for name, request in cases("smoke"):
            expected, _ = ref.process(request)
            for fault, oracle in list(pending.items()):
                if oracle.process(request) != expected:
                    del pending[fault]
            if not pending:
                break
        self.assertEqual(list(pending), [], "vectors failed to kill these wrong algorithms")

    def test_incorrect_slot_order_and_no_session_clear_are_detected(self):
        reference, stale = PacketReference(), {ITEM_A: RollingItem(), ITEM_B: RollingItem()}
        order_caught = reset_caught = False
        for _, request in cases("smoke"):
            expected, _ = reference.process(request)
            a1 = stale[request.item1].process(request.price1) or NONE
            a2 = stale[request.item2].process(request.price2) or NONE
            wrong = RESPONSE.pack(request.index, request.item1, a1, request.item2, a2, 0)
            reset_caught |= wrong != expected
            if request.item1 == ITEM_B:
                v = RESPONSE.unpack(expected)
                wrong_order = RESPONSE.pack(v[0], v[3], v[4], v[1], v[2], 0)
                order_caught |= wrong_order != expected
            if order_caught and reset_caught:
                break
        self.assertTrue(order_caught)
        self.assertTrue(reset_caught)


class ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temp.name)
        cls.vectors = cls.directory / "vectors"
        cls.manifest = generate(cls.vectors, "smoke")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def capture(self, lines):
        path = self.directory / "capture.mem"
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="ascii")
        return path

    def golden_lines(self):
        return (self.vectors / "responses.mem").read_text(encoding="ascii").splitlines()

    def test_answer_key_round_trip_and_unmeasured_resources(self):
        summary = verify(self.vectors, self.vectors / "responses.mem")
        self.assertTrue(summary["pass_all"])
        self.assertIsNone(summary["latency_us"])
        self.assertIsNone(summary["lut_count"])

    def test_coverage(self):
        coverage = self.manifest["coverage"]
        self.assertEqual(coverage["sum_remainders"], list(range(16)))
        self.assertEqual(coverage["replacement_pointers"], list(range(16)))
        self.assertEqual(coverage["max_sum"], 1048560)
        self.assertEqual(len(coverage["comparisons"]), 9)
        self.assertEqual(len(coverage["action_pairs"]), 9)
        for reason in ("BUY_CROSS", "SELL_CROSS", "HOLD_NONE", "HOLD_BUY", "HOLD_SELL"):
            self.assertGreater(coverage["reasons"][reason], 0)

    def test_deterministic_artifacts(self):
        again = self.directory / "again"
        second = generate(again, "smoke")
        self.assertEqual(self.manifest, second)

    def test_missing_response_keeps_fixed_denominators(self):
        summary = verify(self.vectors, self.capture(self.golden_lines()[:20]))
        self.assertFalse(summary["pass_all"])
        self.assertEqual(summary["requested_packets"], self.manifest["packets"])
        self.assertEqual(summary["correct_packets"], 20)
        self.assertEqual(summary["failures"]["MISSING_RESPONSE"], self.manifest["packets"] - 20)

    def test_all_response_fields_checked_including_warmup(self):
        original = self.golden_lines()
        for byte_number, field in ((0, "INDEX"), (2, "ITEM1"), (3, "ACTION1"),
                                   (4, "ITEM2"), (5, "ACTION2"), (7, "RESERVED")):
            changed = original.copy()
            raw = bytearray.fromhex(changed[0])
            raw[byte_number] ^= 1
            changed[0] = raw.hex()
            summary = verify(self.vectors, self.capture(changed))
            self.assertFalse(summary["pass_all"])
            self.assertEqual(summary["failures"], {field: 1})

    def test_duplicate_unsolicited_and_partial_responses_fail(self):
        original = self.golden_lines()
        for lines, field in ((original + [original[-1]], "EXTRA_RESPONSE"),
                             ([original[0][:-2]] + original[1:], "LENGTH"),
                             (["debug"] + original[1:], "INVALID_HEX"),
                             ([original[0] + "00"] + original[1:], "LENGTH")):
            summary = verify(self.vectors, self.capture(lines))
            self.assertFalse(summary["pass_all"])
            self.assertIn(field, summary["failures"])

    def test_optional_latency_statistics(self):
        capture = self.capture(self.golden_lines()[:4])
        latency = self.directory / "latency.csv"
        latency.write_text("sequence,latency_us\n0,10\n1,20\n2,30\n3,100\n", encoding="ascii")
        summary = verify(self.vectors, capture, latency)
        self.assertEqual(summary["latency_us"], dict(samples=4, mean=40, p50=20, p95=100, p99=100, maximum=100))
        self.assertFalse(summary["pass_all"])

    def test_invalid_latencies_fail(self):
        capture = self.capture(self.golden_lines()[:1])
        latency = self.directory / "invalid_latency.csv"
        for data in ("sequence,latency_us\n0,nan\n", "sequence,latency_us\n0,-1\n",
                     "sequence,latency_us\n1,10\n", "sequence,latency_us\n"):
            latency.write_text(data, encoding="ascii")
            with self.assertRaises(ValueError):
                verify(self.vectors, capture, latency)

    def test_tampered_answer_key_rejected(self):
        path = self.vectors / "responses.mem"
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"0000000000000000\n")
            with self.assertRaisesRegex(ValueError, "integrity"):
                verify(self.vectors, path)
        finally:
            path.write_bytes(original)


class MetricTests(unittest.TestCase):
    # Synthetic values test the gate only; these are not project measurements.
    def setUp(self):
        self.correctness = dict(pass_all=True, correct_packets=100, requested_packets=100,
                                latency_us=dict(samples=100, mean=16000, p99=20000))
        self.metrics = dict(source_revision="test_fixture", bitstream_sha256="test_fixture",
                            resource_report="fixture", timing_report="fixture", board_capture="fixture",
                            capture_kind="physical_board", luts=542, registers=300, bsram_blocks=2,
                            timing_slack_ns=1)

    def test_complete_values_pass_and_boundaries_are_inclusive(self):
        self.correctness["latency_us"].update(mean=20782.5, p99=33300)
        self.assertEqual(evaluate(self.correctness, self.metrics)["status"], "PASS")

    def test_unmeasured_template_cannot_pass(self):
        metrics = json.loads((ROOT / "tests/performance_measurements.template.json").read_text())
        self.assertEqual(evaluate(self.correctness, metrics)["status"], "INCOMPLETE")

    def test_luts_timing_and_latency_budgets_fail(self):
        self.metrics.update(luts=543, timing_slack_ns=-0.1)
        self.correctness["latency_us"].update(mean=20783, p99=33301)
        result = evaluate(self.correctness, self.metrics)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(len(result["failures"]), 4)

    def test_imperfect_correctness_fails_even_with_small_fast_design(self):
        self.correctness.update(pass_all=False, correct_packets=99)
        self.assertEqual(evaluate(self.correctness, self.metrics)["status"], "FAIL")

    def test_simulated_or_absent_latency_cannot_pass(self):
        self.metrics["capture_kind"] = "simulation"
        self.assertEqual(evaluate(self.correctness, self.metrics)["status"], "INCOMPLETE")
        self.metrics["capture_kind"] = "physical_board"
        self.correctness["latency_us"] = None
        self.assertEqual(evaluate(self.correctness, self.metrics)["status"], "INCOMPLETE")

    def test_invalid_resource_types_fail(self):
        for value in (-1, True, float("nan"), 1.5):
            self.metrics["luts"] = value
            self.assertEqual(evaluate(self.correctness, self.metrics)["status"], "FAIL")

    def test_before_after_deltas(self):
        baseline = dict(luts=600, registers=310, bsram_blocks=1, timing_slack_ns=0.5,
                        latency_us=dict(mean=18000, p99=21000))
        result = evaluate(self.correctness, self.metrics, baseline=baseline)
        self.assertEqual(result["candidate_minus_baseline"], dict(luts=-58, registers=-10,
                        bsram_blocks=1, timing_slack_ns=0.5, latency_mean_us=-2000, latency_p99_us=-1000))


if __name__ == "__main__":
    unittest.main()
