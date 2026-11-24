"""Risk-based regression and independent finite sampling checks."""

from collections import Counter
from copy import deepcopy
from fractions import Fraction
from itertools import combinations
import json
from math import comb
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

if __package__:
    from . import cli
    from .screening import InputError, make_plan, score_plan, upper_count, zero_hit_upper
else:
    import cli
    from screening import InputError, make_plan, score_plan, upper_count, zero_hit_upper


def request():
    ids = [f"case-{i}" for i in range(6)]
    return {"schema": "nsc-screening-request/1", "plan_input": {
        "case_ids": ids, "flagged_ids": [ids[0]], "budget": 3,
        "permutation": ids, "design_id": "synthetic-edge-controls-v1"},
        "checker_outputs": {case: ["S", "S"] for case in ids},
        "observations": {case: "S" for case in ids[:3]}, "alpha": "1/20",
        "sampling_basis": "Synthetic control of the conditional calculation; no empirical coverage claim"}


class ScreeningTests(unittest.TestCase):
    def test_no_flags_draws_from_whole_frame_and_precision_is_undefined(self):
        r = request(); r["plan_input"]["flagged_ids"] = []
        result = cli.run_bytes(json.dumps(r).encode())
        self.assertEqual(result["plan"]["selection"]["residual_frame"], r["plan_input"]["case_ids"])
        self.assertEqual(result["result"]["residual_sample"], 3)
        self.assertIsNone(result["result"]["flag_precision"])
        self.assertEqual(result["result"]["flag_precision_reason"], "UNDEFINED_EMPTY_FLAG_PANEL")

    def test_flags_equal_budget_produces_no_residual_sample(self):
        r = request(); r["plan_input"]["flagged_ids"] = r["plan_input"]["case_ids"][:3]
        r["observations"]["case-0"] = "V"
        result = cli.run_bytes(json.dumps(r).encode())["result"]
        self.assertEqual(result["residual_sample"], 0)
        self.assertEqual(result["conditional_upper"], 4)
        self.assertEqual(result["interval"], [1, 4])

    def test_overflow_rejects_design_without_partial_selection(self):
        r = request(); r["plan_input"]["flagged_ids"] = r["plan_input"]["case_ids"][:4]
        result = cli.run_bytes(json.dumps(r).encode())
        self.assertEqual(result["result"]["status"], "INVALID_DESIGN")
        self.assertIsNone(result["plan"]["selection"])
        self.assertIsNone(result["result"]["conditional_upper"])
        self.assertEqual(result["plan"]["shortfall"], 1)

    def test_empty_frame_and_complete_census(self):
        p = make_plan([], [], 0, [], "empty")
        s = score_plan(p, {}, {}, alpha="1/20", sampling_basis="empty frame")
        self.assertEqual(s["interval"], [0, 0]); self.assertEqual(s["conditional_upper"], 0)
        r = request(); r["plan_input"]["budget"] = 6
        r["observations"] = {case: "V" for case in r["plan_input"]["case_ids"]}
        s = cli.run_bytes(json.dumps(r).encode())["result"]
        self.assertEqual(s["interval"], [6, 6]); self.assertEqual(s["conditional_upper"], 6)

    def test_positive_hits_are_never_zero_hits(self):
        with self.assertRaisesRegex(InputError, "ZERO_HIT_PRECONDITION_FAILED"):
            zero_hit_upper(32, 12, 1, "1/80")
        r = request(); r["observations"]["case-1"] = "U"
        s = cli.run_bytes(json.dumps(r).encode())["result"]
        self.assertEqual(s["residual_errors_observed"], 1)
        self.assertFalse(s["zero_hit_precondition"])
        self.assertEqual(s["bound_method"], "GENERAL_HYPERGEOMETRIC_EXACT")

    def test_strict_boundary_alpha(self):
        # N=2, n=1, x=0: a population with one error has P(X=0)=1/2.
        self.assertEqual(upper_count(2, 1, 0, "1/2"), 0)
        self.assertEqual(upper_count(32, 12, 0, "1/80"), 7)

    def test_invalid_configuration_has_no_scientific_verdict(self):
        base = request()
        mutations = []
        for field, value in (("budget", True), ("budget", -1), ("budget", 7),
                             ("case_ids", ["x", "x"]), ("flagged_ids", ["outside"]),
                             ("permutation", ["case-0"]), ("design_id", "")):
            r = deepcopy(base); r["plan_input"][field] = value; mutations.append(r)
        for value in ("0", "1", "NaN", 0.05, True):
            r = deepcopy(base); r["alpha"] = value; mutations.append(r)
        for value in ({}, {"case-0": "S"}, {"case-0": "X", "case-1": "S", "case-2": "S"}):
            r = deepcopy(base); r["observations"] = value; mutations.append(r)
        for value in (["S", "V"], ["S"], [None, None], [True, True]):
            r = deepcopy(base); r["checker_outputs"]["case-0"] = value; mutations.append(r)
        for r in mutations:
            with self.subTest(r=r), self.assertRaises(InputError):
                cli.run_bytes(json.dumps(r).encode())
        with self.assertRaises(InputError):
            cli.run_bytes(b'{"schema":"a","schema":"b"}')
        with self.assertRaises(InputError):
            cli.run_bytes(json.dumps(base).encode(), "0" * 64)

    def test_tampered_plan_is_rejected(self):
        r = request(); p = make_plan(**r["plan_input"])
        p["selection"]["residual_draw"][0] = "case-5"
        with self.assertRaises(InputError):
            score_plan(p, r["checker_outputs"], r["observations"],
                       alpha=r["alpha"], sampling_basis=r["sampling_basis"])

    def test_derived_plan_fields_are_type_sensitive(self):
        r = request()
        for key, value in (("flag_count", True), ("frame_size", 6.0), ("shortfall", False)):
            p = make_plan(**r["plan_input"]); p[key] = value
            with self.subTest(key=key), self.assertRaises(InputError):
                score_plan(p, r["checker_outputs"], r["observations"],
                           alpha=r["alpha"], sampling_basis=r["sampling_basis"])

    def test_utf8_contract_rejects_utf16_bytes(self):
        with self.assertRaises(InputError):
            cli.run_bytes(json.dumps(request()).encode("utf-16"))

    def test_cli_success_input_error_execution_error_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); p = root / "request.json"; out = root / "report.json"
            p.write_text(json.dumps(request()))
            args = [sys.executable, "-B", str(Path(cli.__file__).resolve()), str(p), "--out", str(out)]
            good = subprocess.run(args, capture_output=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            original = out.read_bytes()
            duplicate = subprocess.run(args, capture_output=True)
            self.assertEqual(duplicate.returncode, 3)
            self.assertEqual(out.read_bytes(), original)
            bad = subprocess.run(args[:4] + ["--expect-sha256", "0"*64], capture_output=True)
            self.assertEqual(bad.returncode, 2)
            self.assertEqual(json.loads(bad.stderr)["status"], "INPUT_ERROR")
            repository = Path(__file__).resolve().parents[2]
            module_out = root / "module_report.json"
            packaged = subprocess.run(
                [sys.executable, "-B", "-m", "r5_f3.screening.cli", str(p), "--out", str(module_out)],
                cwd=repository, capture_output=True, timeout=30)
            self.assertEqual(packaged.returncode, 0, packaged.stderr)
            self.assertEqual(module_out.read_bytes(), original)
            replay_out = root / "packaged_replay"
            replay = subprocess.run(
                [sys.executable, "-B", "-m", "r5_f3.screening.replay_archived", "--out", str(replay_out)],
                cwd=repository, capture_output=True, timeout=30)
            self.assertEqual(replay.returncode, 0, replay.stderr)
            replay_result = json.loads((replay_out / "REPLAY_RESULTS.json").read_bytes())
            self.assertEqual(replay_result["field_comparisons"], 72)
            self.assertEqual(replay_result["pooled"]["screen_bonferroni_upper"], 60)

    def test_exact_bounds_and_coverage_by_direct_subset_enumeration(self):
        # Independent oracle: list every sample, rather than reuse the formula.
        comparisons = coverage_checks = 0
        for population in range(10):
            for sample in range(population + 1):
                histograms = []
                for total in range(population + 1):
                    histogram = Counter(sum(i < total for i in draw)
                                        for draw in combinations(range(population), sample))
                    self.assertEqual(sum(histogram.values()), comb(population, sample))
                    histograms.append(histogram)
                for alpha in ("1/20", "1/4", "1/2"):
                    calculated = {x: upper_count(population, sample, x, alpha) for x in range(sample + 1)}
                    for x, bound in calculated.items():
                        possible = [total for total, histogram in enumerate(histograms)
                                    if Fraction(sum(n for hit, n in histogram.items() if hit <= x),
                                                comb(population, sample)) > Fraction(alpha)]
                        self.assertEqual(bound, max(possible)); comparisons += 1
                    for total, histogram in enumerate(histograms):
                        missed = sum(n for hit, n in histogram.items() if calculated[hit] < total)
                        self.assertLessEqual(Fraction(missed, comb(population, sample)), Fraction(alpha))
                        coverage_checks += 1
        type(self).enumerated_bound_comparisons = comparisons
        type(self).enumerated_coverage_checks = coverage_checks


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ScreeningTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"schema": "nsc-screening-tests/1", "status": "PASS" if result.wasSuccessful() else "FAIL",
                      "test_methods": result.testsRun,
                      "direct_subset_bound_comparisons": getattr(ScreeningTests, "enumerated_bound_comparisons", 0),
                      "direct_subset_coverage_checks": getattr(ScreeningTests, "enumerated_coverage_checks", 0),
                      "scope": "Conditional exact arithmetic and local software validation, not field validation"}, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
