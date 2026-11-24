from copy import deepcopy
from hashlib import sha256
import unittest

from r5_f3.reference_audit import InputError, audit, validate_request
from r5_f3.reference_audit.build_examples import observation, simple_case, toy_request
from r5_f3.reference_audit.canonical import canonical_bytes, digest, load_file, loads
from r5_f3.reference_audit.provenance import HERE
from r5_f3.reference_audit.tests.helpers import reseal, tiny


class ContractTests(unittest.TestCase):
    def test_canonical_domain_and_duplicate_keys(self):
        self.assertEqual(canonical_bytes({"z": 2, "a": "é"}), b'{"a":"\xc3\xa9","z":2}')
        self.assertEqual(digest({"z": 2, "a": "é"}), sha256(b'{"a":"\xc3\xa9","z":2}').hexdigest())
        self.assertNotEqual(digest([1, 2]), digest([2, 1]))
        for text in ('{"a":1,"a":2}', '{"a":1.0}', '{"a":NaN}', '{"a":Infinity}'):
            with self.subTest(text=text), self.assertRaises(InputError):
                loads(text)

    def test_budget_and_rational_types(self):
        for bad in (True, -1, "1", 1.5):
            request = tiny()
            request["budget"] = bad
            with self.subTest(budget=bad), self.assertRaises(InputError):
                validate_request(request)
        for bad in (1, True, "-1", "1/0", "0.5", "nan", " 1", "01"):
            request = tiny()
            request["threshold"] = bad
            with self.subTest(threshold=bad), self.assertRaises(InputError):
                validate_request(request)
        for bad in ("-1", "1/0", 0, True):
            request = tiny()
            request["matrix"]["payload"]["cases"][0]["weight"] = bad
            with self.subTest(weight=bad), self.assertRaises(InputError):
                validate_request(reseal(request))

    def test_matrix_hash_and_closed_fields(self):
        request = tiny()
        request["matrix"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(InputError, "digest"):
            validate_request(request)
        for target, key in (("root", "extra"), ("case", "unknown")):
            request = tiny()
            if target == "root":
                request[key] = 1
            else:
                request["matrix"]["payload"]["cases"][0][key] = 1
                reseal(request)
            with self.assertRaises(InputError):
                validate_request(request)

    def test_case_identity_and_prediction_coverage(self):
        mutations = []
        request = tiny(); request["matrix"]["payload"]["cases"][1]["case_id"] = "a"; mutations.append(request)
        request = tiny(); del request["matrix"]["payload"]["conventions"][0]["predictions"]["b"]; mutations.append(request)
        request = tiny(); request["matrix"]["payload"]["centres"][0]["convention_by_case"]["b"] = "unknown"; mutations.append(request)
        request = tiny(); request["matrix"]["payload"]["conventions"][0]["version"] = ""; mutations.append(request)
        request = tiny(); request["matrix"]["payload"]["conventions"][0]["predictions"]["a"] = "NA"; mutations.append(request)
        request = tiny(); request["matrix"]["payload"]["cases"][0]["case_id"] = "a\n"; mutations.append(request)
        for i, request in enumerate(mutations):
            with self.subTest(mutation=i), self.assertRaises(InputError):
                validate_request(reseal(request))

    def test_admissibility_and_eligibility_are_explicit(self):
        for change in ("empty", "duplicate", "missing-flag", "integer-flag"):
            request = tiny()
            case = request["matrix"]["payload"]["cases"][0]
            if change == "empty": case["allowed_labels"] = []
            if change == "duplicate": case["allowed_labels"] = ["S", "S"]
            if change == "missing-flag": del case["exception_eligible"]
            if change == "integer-flag": case["exception_eligible"] = 1
            with self.subTest(change=change), self.assertRaises(InputError):
                validate_request(reseal(request))

    def test_observation_id_hash_label_and_contradictions(self):
        request = tiny()
        request["observations"] = [observation("a", "S", "ev-a", "Exact constructed observation")]
        variants = []
        bad = deepcopy(request); bad["observations"][0]["evidence"]["sha256"] = "f" * 64; variants.append(bad)
        bad = deepcopy(request); bad["observations"][0]["label"] = "V"; variants.append(bad)
        bad = deepcopy(request); bad["observations"][0] = observation("missing", "S", "ev-missing", "Unknown case"); variants.append(bad)
        bad = deepcopy(request); bad["observations"].append(observation("a", "V", "ev-other", "Conflicting duplicate")); variants.append(bad)
        bad = deepcopy(request); bad["observations"].append(deepcopy(bad["observations"][0])); variants.append(bad)
        bad = deepcopy(request); bad["observations"].append(observation("b", "V", "ev-a", "Duplicate evidence ID")); variants.append(bad)
        for i, bad in enumerate(variants):
            with self.subTest(mutation=i), self.assertRaises(InputError):
                validate_request(bad)
        # One well-formed exact observation outside S_i is a valid empty model.
        request = toy_request([simple_case("a", allowed=("V",))], {"g": {"a": "V"}},
                              observations=[observation("a", "S", "ev", "Contradicts declared admissibility")])
        self.assertEqual(audit(request)["status"], "OUT_OF_MODEL")

    def test_external_null_labels_require_zero_weight(self):
        request = load_file(HERE / "examples/mirror_S_external_eligible_k1.json")
        validate_request(request)
        external = next(c for c in request["matrix"]["payload"]["cases"] if c["role"] == "external_query")
        external["weight"] = "1"
        with self.assertRaises(InputError): validate_request(reseal(request))
        external["weight"] = "0"; external["checker_labels"]["t"] = "S"
        with self.assertRaises(InputError): validate_request(reseal(request))
        request = tiny(); request["matrix"]["payload"]["cases"][0]["checker_labels"] = {"t": None, "b": None}
        with self.assertRaises(InputError): validate_request(reseal(request))

    def test_scope_assignment_and_explicit_subset(self):
        request = load_file(HERE / "examples/contextwise_explicit_subset.json")
        report = audit(request)
        self.assertFalse(report["model_scope"]["complete_cartesian_product_certified"])
        self.assertEqual(report["model_scope"]["joint_centres_supplied"], 2)
        request["matrix"]["payload"]["centres"][0]["convention_by_case"]["A2"] = "all-V"
        with self.assertRaises(InputError): validate_request(reseal(request))
        request = load_file(HERE / "examples/casewise_explicit_subset.json")
        validate_request(request)
        request["model_scope"]["kind"] = "global"
        with self.assertRaises(InputError): validate_request(request)
        request = tiny(); request["model_scope"]["budget_scope"] = "per_context"
        with self.assertRaises(InputError): validate_request(request)


if __name__ == "__main__":
    unittest.main()
