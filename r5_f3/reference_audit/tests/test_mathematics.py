from copy import deepcopy
from fractions import Fraction
from itertools import product
import unittest

from r5_f3.reference_audit import audit, verify_report, verify_witness
from r5_f3.reference_audit.build_examples import observation, simple_case, toy_request
from r5_f3.reference_audit.canonical import load_file
from r5_f3.reference_audit.provenance import HERE
from r5_f3.reference_audit.tests.helpers import brute_force


class MathematicsTests(unittest.TestCase):
    def assert_oracle(self, request, verify=True):
        expected = brute_force(request)
        report = audit(request)
        self.assertEqual(report["interval"], expected["interval"])
        self.assertEqual(report["status"], expected["status"])
        self.assertEqual(report["radii"]["minimum_feasible_budget"], expected["fit"])
        self.assertEqual(report["radii"]["first_at_or_below"], expected["low_radius"])
        self.assertEqual(report["radii"]["first_above"], expected["high_radius"])
        if verify:
            self.assertEqual(verify_report(request, report)["status"], "VERIFIED")
        return report

    def test_exhaustive_binary_admissibility_protection_weights_and_nesting(self):
        # Direct enumeration of assignments is an oracle separate from both the
        # sorted-gain optimiser and the verifier's exact-cost recurrence.
        subsets = (("S",), ("V",), ("S", "V"))
        weights = (("1", "1"), ("0", "2/3"), ("3/2", "1/2"))
        for centre, checker, allowed, eligibility, weight in product(
                product("SV", repeat=2), product("SV", repeat=2),
                product(subsets, repeat=2), product((False, True), repeat=2), weights):
            cases = [simple_case(cid, t=checker[i], b=checker[i], allowed=allowed[i],
                                 weight=weight[i], eligible=eligibility[i])
                     for i, cid in enumerate(("a", "b"))]
            request = toy_request(cases, {"g": dict(zip(("a", "b"), centre))}, threshold="1/2")
            previous = None
            for budget in range(3):
                request["budget"] = budget
                with self.subTest(centre=centre, checker=checker, allowed=allowed,
                                  eligibility=eligibility, weight=weight, budget=budget):
                    report = self.assert_oracle(request)
                    if previous and previous["interval"] is not None:
                        self.assertIsNotNone(report["interval"])
                        self.assertLessEqual(Fraction(report["interval"]["lower"]), Fraction(previous["interval"]["lower"]))
                        self.assertGreaterEqual(Fraction(report["interval"]["upper"]), Fraction(previous["interval"]["upper"]))
                        if previous["status"] in ("ABOVE", "AT_OR_BELOW"):
                            opposite = "AT_OR_BELOW" if previous["status"] == "ABOVE" else "ABOVE"
                            self.assertNotEqual(report["status"], opposite)
                    previous = report

    def test_third_outcome_disagreements_observations_and_multiple_centres(self):
        cases = [simple_case("a", allowed=("S", "V", "U"), t="U", b="U", weight="5/7"),
                 simple_case("b", allowed=("S", "U"), t="S", b="V", weight="11/3"),
                 simple_case("c", allowed=("V", "U"), t="V", b="V", weight="0")]
        predictions = {"g": {"a": "S", "b": "V", "c": "S"},
                       "h": {"a": "U", "b": "S", "c": "V"}}
        for observed in ((), (observation("a", "U", "third-label", "Constructed exact U outcome"),),
                         (observation("b", "V", "empty-model", "Well-formed observation outside the declared local set"),)):
            for budget in range(4):
                request = toy_request(cases, predictions, observations=observed, budget=budget, threshold="1/3")
                self.assert_oracle(request)

    def test_exact_rationals_and_envelope_with_gaps(self):
        cases = [simple_case("a", allowed=("S", "V"), weight="9007199254740993/7"),
                 simple_case("b", allowed=("S", "V"), weight="1/3")]
        request = toy_request(cases, {"g": {"a": "S", "b": "S"}}, budget=1, threshold="1/2")
        report = self.assert_oracle(request)
        self.assertEqual(report["interval"]["upper"], "9007199254740993/7")
        self.assertTrue(report["interval_is_envelope"])
        # An interval does not assert that every interior real score is attainable.
        self.assertNotEqual(Fraction(report["interval"]["upper"]), Fraction(float(Fraction(report["interval"]["upper"]))))

    def test_external_zero_weight_can_spend_budget_and_protection_changes_radius(self):
        for name, first_low in (("mirror_S_external_eligible_k1", 1), ("mirror_S_external_protected_k1", 8)):
            request = load_file(HERE / ("examples/" + name + ".json"))
            report = audit(request)
            self.assertEqual(report["radii"]["first_at_or_below"], first_low)
            self.assertEqual(verify_report(request, report)["status"], "VERIFIED")
            certificate = report["region_certificates"]["at_or_below"]
            self.assertEqual(verify_witness(request, certificate)["certificate_domain"], "first_region_budget")
        request = load_file(HERE / "examples/weighted_protected_third_outcome.json")
        report = self.assert_oracle(request)
        centre = report["centres"][0]
        self.assertEqual(centre["minimum_required_departures"], 2)
        self.assertEqual(centre["mandatory_case_ids"], ["external-U", "weighted-mandatory"])

    def test_retained_f2_values_and_opposite_completion(self):
        expected = load_file(HERE / "examples/EXPECTED.json")["expected"]
        for name, values in expected.items():
            if name == "canonical_query_minima":
                continue
            request = load_file(HERE / ("examples/" + name + ".json"))
            report = audit(request)
            self.assertEqual(report["interval"], values["interval"], name)
            self.assertEqual(report["status"], values["status"], name)
            if "first_at_or_below" in values:
                self.assertEqual(report["radii"]["first_at_or_below"], values["first_at_or_below"])
            self.assertEqual(verify_report(request, report)["status"], "VERIFIED")
        for label, status in (("S", "AT_OR_BELOW"), ("V", "ABOVE")):
            request = load_file(HERE / f"examples/single_conflict_{label}_broad_k0.json")
            report = audit(request)
            self.assertEqual(report["status"], status)
            self.assertEqual(report["radii"]["first_opposite_completion"]["first_budget"], 1)
            enlarged = deepcopy(request); enlarged["budget"] = 1
            self.assertEqual(audit(enlarged)["status"], "UNDETERMINED")

    def test_nonmutation_and_deterministic_report(self):
        request = load_file(HERE / "examples/weighted_protected_third_outcome.json")
        original = deepcopy(request)
        report = audit(request)
        report_copy = deepcopy(report)
        self.assertEqual(report, audit(request))
        verify_report(request, report)
        self.assertEqual(request, original)
        self.assertEqual(report, report_copy)


if __name__ == "__main__":
    unittest.main()
