from copy import deepcopy
import unittest

from r5_f3.reference_audit import VerificationError, audit, verify_report, verify_witness
from r5_f3.reference_audit.build_examples import observation
from r5_f3.reference_audit.tests.helpers import resign, tiny


class VerificationTests(unittest.TestCase):
    def test_coordinated_endpoint_budget_label_distance_score_attack(self):
        request = tiny(budget=0)
        report = audit(request)
        certificate = deepcopy(report["endpoint_certificates"]["upper"])
        certificate.update(budget=1, distance=1, score="1", changed_case_ids=["a"])
        certificate["labels"]["a"] = "V"
        # The witness is internally consistent at k=1 but is not an endpoint of
        # the bound request at k=0. Hash identity alone cannot legitimise it.
        with self.assertRaisesRegex(VerificationError, "request budget"):
            verify_witness(request, certificate)
        report["endpoint_certificates"]["upper"] = certificate
        report["interval"]["upper"] = "1"
        report["status"] = "UNDETERMINED"
        with self.assertRaises(VerificationError):
            verify_report(request, resign(report))

    def test_endpoint_sharpness_and_first_region_minimality(self):
        request = tiny(budget=1)
        report = audit(request)
        certificate = deepcopy(report["endpoint_certificates"]["upper"])
        certificate.update(distance=0, score="0", changed_case_ids=[])
        certificate["labels"] = {"a": "S", "b": "S"}
        with self.assertRaisesRegex(VerificationError, "exact endpoint"):
            verify_witness(request, certificate)
        radius = report["region_certificates"]["above"]
        self.assertEqual(verify_witness(request, radius)["certificate_domain"], "first_region_budget")
        bad = deepcopy(radius); bad["budget"] = 2
        with self.assertRaisesRegex(VerificationError, "first feasible budget"):
            verify_witness(request, bad)
        endpoint = report["endpoint_certificates"]["upper"]
        self.assertEqual(verify_witness(request, endpoint)["certificate_domain"], "requested_budget_endpoint")

    def test_coordinated_protected_and_observed_label_attacks(self):
        request = tiny(budget=1, eligible=False)
        certificate = deepcopy(audit(request)["endpoint_certificates"]["upper"])
        certificate.update(distance=1, score="1", changed_case_ids=["a"])
        certificate["labels"]["a"] = "V"
        with self.assertRaisesRegex(VerificationError, "protected"):
            verify_witness(request, certificate)
        request = tiny(budget=1)
        request["observations"] = [observation("a", "S", "binding", "Fixed exact observation")]
        certificate = deepcopy(audit(request)["endpoint_certificates"]["lower"])
        certificate.update(distance=1, score="1", changed_case_ids=["a"])
        certificate["labels"]["a"] = "V"
        with self.assertRaisesRegex(VerificationError, "admissibility|adjudicated"):
            verify_witness(request, certificate)

    def test_rehashed_report_mutations_are_rejected(self):
        request = tiny(budget=1)
        original = audit(request)
        mutations = []
        bad = deepcopy(original); bad["producer"]["version"] = "changed"; mutations.append(bad)
        bad = deepcopy(original); bad["request_sha256"] = "0" * 64; mutations.append(bad)
        bad = deepcopy(original); bad["matrix_sha256"] = "0" * 64; mutations.append(bad)
        bad = deepcopy(original); bad["budget"] = True; mutations.append(bad)
        bad = deepcopy(original); bad["threshold"] = "0/2"; mutations.append(bad)
        bad = deepcopy(original); bad["feasible_centres"] = []; mutations.append(bad)
        bad = deepcopy(original); bad["centres"][0]["minimum_required_departures"] = 1; mutations.append(bad)
        bad = deepcopy(original); bad["radii"]["first_above"] = 2; mutations.append(bad)
        bad = deepcopy(original); bad["nesting"]["opposite_unanimous_reversal_possible"] = True; mutations.append(bad)
        bad = deepcopy(original); bad["execution_scope"]["original_checker_invocations"] = 1; mutations.append(bad)
        bad = deepcopy(original); bad["endpoint_certificates"]["upper"]["labels"]["a"] = "U"; mutations.append(bad)
        bad = deepcopy(original); bad["endpoint_certificates"]["upper"]["labels"]["foreign"] = "S"; mutations.append(bad)
        bad = deepcopy(original); bad["endpoint_certificates"]["upper"]["changed_case_ids"] = []; mutations.append(bad)
        bad = deepcopy(original); bad["endpoint_certificates"]["upper"]["centre_id"] = "unknown"; mutations.append(bad)
        for i, bad in enumerate(mutations):
            with self.subTest(mutation=i), self.assertRaises(VerificationError):
                verify_report(request, resign(bad))
        bad = deepcopy(original); bad["report_sha256"] = "f" * 64
        with self.assertRaisesRegex(VerificationError, "digest"):
            verify_report(request, bad)

    def test_input_identity_prevents_reuse_under_different_request(self):
        request = tiny()
        report = audit(request)
        different = deepcopy(request); different["budget"] = 1
        with self.assertRaises(VerificationError): verify_report(different, report)
        with self.assertRaises(VerificationError): verify_witness(different, report["endpoint_certificates"]["upper"])


if __name__ == "__main__":
    unittest.main()
