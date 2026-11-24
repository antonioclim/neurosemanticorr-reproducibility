from copy import deepcopy
from fractions import Fraction
import unittest

from r5_f3.reference_audit import canonical_query_minimum
from r5_f3.reference_audit.build_examples import canonical_request, observation
from r5_f3.reference_audit.canonical import digest
from r5_f3.reference_audit.canonical_query import POLICIES, canonical_rows
from r5_f3.reference_audit.tests.helpers import reseal


class CanonicalQueryTests(unittest.TestCase):
    def test_verified_budgets_and_cross_region_distance(self):
        rows = canonical_rows()
        by_id = {r["case_id"]: r for r in rows}
        for broad in (False, True):
            for budget in range(9):
                report = canonical_query_minimum(canonical_request(budget, broad))
                self.assertEqual(report["status"], "VERIFIED_CANONICAL_MINIMUM")
                self.assertEqual(report["minimum_query_count"], 2 * budget + 1 if budget <= 7 else 33)
                self.assertEqual(len(set(report["case_ids"])), report["minimum_query_count"])
                self.assertEqual(report["certificate_sha256"], digest({k: v for k, v in report.items() if k != "certificate_sha256"}))
                if budget <= 7:
                    self.assertTrue(all(by_id[cid]["probe"] == "dual_alias_conflict" for cid in report["case_ids"]))
                    for pair in report["proof"]["opposing_pairs"]:
                        g, h = pair["centres"]
                        self.assertEqual(sum(by_id[cid][g] != by_id[cid][h] for cid in report["case_ids"]), 2 * budget + 1)
                    # Counts cannot cross 24 within the allowed local budget.
                    for count in report["proof"]["centre_counts"].values():
                        self.assertTrue(count + budget <= 24 if count <= 24 else count - budget > 24)

    def test_k8_constructive_necessity_for_all_32_ids_and_extra_query(self):
        request = canonical_request(8, True)
        report = canonical_query_minimum(request)
        rows = canonical_rows()
        by_id = {r["case_id"]: r for r in rows}
        predictions = {p: {r["case_id"]: r[p] for r in rows} for p in POLICIES}
        correct = {r["case_id"]: r["archived_paired_o15_agreement"] for r in rows}

        def score(vector):
            return sum(vector[cid] != label for cid, label in correct.items())

        proof = report["proof"]
        indispensable = set(proof["necessary_case_ids"])
        self.assertEqual(len(indispensable), 32)
        self.assertEqual({by_id[cid]["probe"] for cid in indispensable}, {"suffix_alias_clean", "dual_alias_conflict"})
        self.assertEqual(len(proof["necessity_witnesses"]), 32)
        for witness in proof["necessity_witnesses"]:
            first = predictions[witness["centre_id"]].copy()
            for cid in witness["common_repairs"]:
                first[cid] = correct[cid]
            second = first.copy()
            second[witness["additional_repair"]] = correct[witness["additional_repair"]]
            self.assertEqual([score(first), score(second)], [25, 24])
            self.assertEqual([sum(v[cid] != predictions["either_unique"][cid] for cid in correct) for v in (first, second)], [7, 8])
            self.assertEqual([cid for cid in correct if first[cid] != second[cid]], [witness["indispensable_case_id"]])
        obstruction = proof["obstruction_with_32_queries"]
        vectors = []
        for policy in obstruction["centres"]:
            vector = predictions[policy].copy()
            for cid in obstruction["common_repairs"]:
                vector[cid] = correct[cid]
            self.assertEqual(sum(vector[cid] != predictions[policy][cid] for cid in correct), 8)
            vectors.append(vector)
        self.assertEqual([score(v) for v in vectors], [24, 40])
        self.assertTrue(all(vectors[0][cid] == vectors[1][cid] for cid in indispensable))
        extra = proof["additional_case_id"]
        self.assertEqual(by_id[extra]["probe"], "exact_alias_clean")
        self.assertNotEqual(vectors[0][extra], vectors[1][extra])
        self.assertEqual(set(report["case_ids"]), indispensable | {extra})
        self.assertTrue(proof["sufficiency_rule"]["compatibility_check_required_first"])

    def test_scope_guards_and_actual_request_metadata(self):
        original = canonical_request(8, True)
        cases = []
        wrong = deepcopy(original); wrong["threshold"] = "23"; cases.append((wrong, "THRESHOLD_MUST_EQUAL_24"))
        wrong = deepcopy(original); wrong["budget"] = 9; cases.append((wrong, "ONLY_BUDGETS_0_TO_8_VERIFIED"))
        wrong = deepcopy(original); wrong["model_scope"]["kind"] = "contextwise"; cases.append((wrong, "GLOBAL_SCOPE_REQUIRED"))
        wrong = deepcopy(original); wrong["frame_id"] = "other-frame"; cases.append((wrong, "UNVERIFIED_FRAME_ID"))
        wrong = deepcopy(original); wrong["matrix"]["payload"]["cases"][0]["weight"] = "2"; reseal(wrong); cases.append((wrong, "UNIT_WEIGHT_ELIGIBLE_FRAME_COORDINATES_REQUIRED"))
        wrong = deepcopy(original); wrong["matrix"]["payload"]["cases"][0]["exception_eligible"] = False; reseal(wrong); cases.append((wrong, "UNIT_WEIGHT_ELIGIBLE_FRAME_COORDINATES_REQUIRED"))
        wrong = deepcopy(original); wrong["matrix"]["payload"]["cases"][0]["allowed_labels"] = ["S", "V"]; reseal(wrong); cases.append((wrong, "ADMISSIBILITY_IS_NOT_ONE_OF_THE_TWO_VERIFIED_CHOICES"))
        wrong = deepcopy(original); wrong["matrix"]["payload"]["conventions"][0]["version"] = "other-version"; reseal(wrong); cases.append((wrong, "CONVENTION_VERSION_OR_PREDICTIONS_DIFFER"))
        wrong = deepcopy(original); wrong["matrix"]["payload"]["conventions"][0]["predictions"][wrong["matrix"]["payload"]["cases"][0]["case_id"]] = "U"; reseal(wrong); cases.append((wrong, "CONVENTION_VERSION_OR_PREDICTIONS_DIFFER"))
        wrong = deepcopy(original); wrong["observations"] = [observation(wrong["matrix"]["payload"]["cases"][0]["case_id"], "S", "already-queried", "Constructed existing observation")]; cases.append((wrong, "FIXED_QUERY_MINIMUM_STARTS_WITH_NO_OBSERVATIONS"))
        for request, reason in cases:
            report = canonical_query_minimum(request)
            self.assertEqual(report["status"], "NOT_APPLICABLE")
            self.assertIsNone(report["minimum_query_count"])
            self.assertIsNone(report["case_ids"])
            self.assertIn(reason, report["reasons"])
            self.assertEqual(report["threshold"], str(Fraction(request["threshold"])))
            self.assertEqual(report["budget"], request["budget"])
            self.assertEqual(report["request_sha256"], digest(request))


if __name__ == "__main__":
    unittest.main()
