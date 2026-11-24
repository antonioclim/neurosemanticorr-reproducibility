"""Adversarial tests for the decision engine; cases are abstract, not survey data."""

from itertools import combinations, product
import unittest

from decision_audit import compatible, decision, minimum_witness


class DecisionAuditTests(unittest.TestCase):
    def test_empty_model_never_certifies_zero(self):
        labels = {"global_s": {"left": "S", "right": "S"}, "global_v": {"left": "V", "right": "V"}}
        counts = {"global_s": 0, "global_v": 6}
        self.assertEqual(decision(labels, counts, {"left": "S", "right": "V"}, 1),
                         {"status": "OUT_OF_MODEL", "retained_policies": [],
                          "attainable_counts": [], "interval": None})
        self.assertEqual(decision(labels, counts, {"left": "S"}, 1)["interval"], [0, 0])
        self.assertEqual(decision(labels, counts, {}, 1)["attainable_counts"], [0, 6])

    def test_unknown_adjudication_requires_an_explicit_label(self):
        labels = {"unknown": {"case": "U"}, "satisfied": {"case": "S"}}
        self.assertEqual(compatible(labels, {}), ("unknown", "satisfied"))
        self.assertEqual(compatible(labels, {"case": "U"}), ("unknown",))
        with self.assertRaises(ValueError):
            compatible(labels, {"case": None})
        with self.assertRaises(ValueError):
            compatible(labels, {"missing_case": "U"})

    def test_impossibility_and_triviality(self):
        labels = {"a": {"sample": "S"}, "b": {"sample": "S"}}
        result = minimum_witness(labels, {"a": 1, "b": 2}, 1)
        self.assertEqual(result["status"], "INSUFFICIENT_DISTINGUISHING_CASES")
        self.assertIsNone(result["case_ids"])
        self.assertEqual(minimum_witness(labels, {"a": 1, "b": 2}, 2)["case_ids"], [])

    def test_minimum_and_ties_against_exhaustive_subsets(self):
        cases = ("x", "y", "z")
        vectors = tuple(product("SV", repeat=3))
        policies = ("a", "b", "c", "d")
        # Counts can be computed on a larger finite frame than the available queries.
        counts = dict(zip(policies, (0, 3, 8, 9)))
        opposing = tuple((a, b) for a, b in combinations(policies, 2) if (counts[a] <= 4) != (counts[b] <= 4))
        for choice in product(vectors, repeat=len(policies)):
            labels = {p: dict(zip(cases, v)) for p, v in zip(policies, choice)}
            expected = next((list(selection) for n in range(4) for selection in combinations(cases, n)
                             if all(any(labels[a][i] != labels[b][i] for i in selection) for a, b in opposing)), None)
            self.assertEqual(minimum_witness(labels, counts, 4)["case_ids"], expected)


if __name__ == "__main__":
    unittest.main()
