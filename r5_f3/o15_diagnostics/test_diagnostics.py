"""Risk-oriented known-answer tests; no historic checker invocation."""
import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from .evidence import InputError, canonical, encoded, parse, p5_custody, profile_custody, read_tree, seal_profile
from .frozen import native_context
from .native import fresh_seed, seed_variant
from .operators import transform
from .reference import POLICIES, RECORDS, evaluate_files

REPO = Path(__file__).resolve().parents[2]


def example():
    meta = {"unit": "units", "denominator": 1, "scope": "cohort-a"}
    result = {"result_id": "F3-DOC-RESULT", "values": {"x": 73, "y": 73, "~1": 17, "/": 99, "a~b": 18,
              "arr": [10, 11], "01": 11}}
    pointers = ["/values/x", "/values/y", "/values/~01", "/values/~1", "/values/a~0b", "/values/arr/1",
                "/values/arr/01", "/values/arr/٠", "/values/arr/999999999999999999999999", "/values/01", "/values/a~2b"]
    fields = {p: dict(meta) for p in pointers}
    fields["/values/y"]["scope"] = "cohort-b"
    docs = {RECORDS["result"]: result,
            RECORDS["claims"]: {"claims": [{"claim_id": "F3-DOC-CLAIM", "source_pointer": "/values/x", "value": 73, **meta}]},
            RECORDS["edges"]: {"result_id": "F3-DOC-RESULT", "aliases": {"primary": "/values/x"}, "field_metadata": fields}}
    return docs


def files(docs):
    return {p: encoded(v) for p, v in docs.items()}


def verdicts(data):
    r = evaluate_files(data, "F3-TEST")
    return r, "".join(r.get("policies", {}).get(p, {}).get("verdict", "-") for p in POLICIES)


class ReferenceRisks(unittest.TestCase):
    def test_original_valid_and_missing(self):
        self.assertEqual(verdicts(files(example()))[1], "SSSSS")
        d = example(); del d[RECORDS["result"]]
        self.assertEqual(verdicts(files(d))[1], "UUUUU")

    def test_five_alias_conventions(self):
        for aliases, expected in [({"primary": "/values/x"}, "VSSSS"),
                                  ({"alias:primary": "/values/x"}, "SVSSS"),
                                  ({"alias:primary": "/values/x", "primary": "/values/y"}, "SVVSV")]:
            with self.subTest(aliases=aliases):
                d = example(); d[RECORDS["claims"]]["claims"][0]["source_pointer"] = "alias:primary"
                d[RECORDS["edges"]]["aliases"] = aliases
                self.assertEqual(verdicts(files(d))[1], expected)

    def test_rfc_escape_order_and_object_array_distinction(self):
        for pointer, value, expected in [("/values/~01", 17, "S"), ("/values/~1", 99, "S"),
                                         ("/values/a~0b", 18, "S"), ("/values/arr/1", 11, "S"),
                                         ("/values/arr/01", 11, "V"), ("/values/01", 11, "S"),
                                         ("/values/arr/٠", 10, "V"), ("/values/a~2b", 18, "V"),
                                         ("/values/arr/999999999999999999999999", 11, "V")]:
            with self.subTest(pointer=pointer):
                d = example(); d[RECORDS["claims"]]["claims"][0].update(source_pointer=pointer, value=value)
                self.assertEqual(verdicts(files(d))[1], expected * 5)

    def test_identity_and_metadata_are_not_numeric_equality(self):
        d = example(); d[RECORDS["edges"]]["result_id"] = "WRONG"
        self.assertEqual(verdicts(files(d))[1], "VVVVV")
        d = example(); d[RECORDS["claims"]]["claims"][0]["source_pointer"] = "/values/y"
        self.assertEqual(verdicts(files(d))[1], "VVVVV")

    def test_claim_ids_and_exact_types(self):
        d = example(); d[RECORDS["claims"]]["claims"] *= 2
        self.assertEqual(verdicts(files(d))[1], "VVVVV")
        for key, value in [("denominator", True), ("value", True), ("value", "73"), ("unit", "")]:
            with self.subTest(key=key, value=value):
                d = example(); d[RECORDS["claims"]]["claims"][0][key] = value
                self.assertEqual(verdicts(files(d))[1], "VVVVV")

    def test_rational_equivalence_and_positive_denominator(self):
        d = example(); d[RECORDS["result"]]["values"]["x"] = {"numerator": 1, "denominator": 2}
        d[RECORDS["claims"]]["claims"][0]["value"] = {"numerator": 2, "denominator": 4}
        self.assertEqual(verdicts(files(d))[1], "SSSSS")
        d[RECORDS["claims"]]["claims"][0]["value"]["denominator"] = 0
        self.assertEqual(verdicts(files(d))[1], "VVVVV")

    def test_parse_failures_have_no_semantic_label(self):
        for raw in [b'{"claims":[],"claims":[]}', b'{"x":NaN}', b'{"x":1.5}', b'[]', b'\xff']:
            with self.subTest(raw=raw):
                data = files(example()); data[RECORDS["claims"]] = raw
                r = evaluate_files(data, "F3-TEST")
                self.assertEqual(r["status"], "INPUT_ERROR")
                self.assertEqual(r["policies"], {})
                self.assertFalse(r["semantic_verdict_assigned"])

    def test_execution_fault_is_not_caught_as_violation(self):
        with patch("r5_f3.o15_diagnostics.reference.resolve", side_effect=RuntimeError("deliberate test failure")):
            with self.assertRaises(RuntimeError):
                evaluate_files(files(example()), "F3-TEST")

    def test_symlink_input_is_not_read(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("NSC_O15_TEST_TMP")) as root:
            p = Path(root); (p / "target").mkdir(); (p / "link").symlink_to(p / "target", target_is_directory=True)
            with self.assertRaises(InputError):
                read_tree(p / "link")


class OperatorRisks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = parse((REPO / "p5/profiles/FIXED_PROFILE.json").read_bytes())

    def test_T01_raw_changes_logical_content_preserved(self):
        original = files(example())
        out, report = transform(original, "F3-TEST", "T01", {"order_independent": True})
        self.assertIsNotNone(out)
        self.assertNotEqual(report["input_binding"]["sha256"], report["output_binding"]["sha256"])
        self.assertTrue(all(x["result"] == "HOLDS" for x in report["relations"].values()))
        self.assertEqual(verdicts(out)[1], "SSSSS")

    def test_T01_duplicate_and_stale_inventory_rejected(self):
        data = files(example()); data[RECORDS["claims"]] = b'{"claims":[],"claims":[]}'
        out, report = transform(data, "F3-TEST", "T01", {"order_independent": True})
        self.assertIsNone(out); self.assertEqual(report["status"], "INPUT_ERROR")
        self.assertFalse(report["semantic_verdict_assigned"])
        self.assertEqual(report["reference_before"]["policies"], {})
        self.assertEqual(report["relations"], {})
        data = fresh_seed(REPO, "W1", "F3-TEST", self.profile); data["records/R02_aux.txt"] += b"changed"
        out, r = transform(data, "F3-TEST", "T01", {"order_independent": True}, profile=self.profile)
        self.assertIsNone(out); self.assertEqual(r["status"], "PRECONDITION_FAILED")

    def test_T02_collision_and_undeclared_policy_rejected(self):
        d = example(); d[RECORDS["claims"]]["claims"][0]["source_pointer"] = "alias:primary"
        d[RECORDS["edges"]]["aliases"]["occupied"] = "/values/y"
        out, _ = transform(files(d), "F3-TEST", "T02", {"renames": {"primary": "occupied"}, "invariance_conventions": ["suffix_only"]})
        self.assertIsNone(out)
        self.assertIsNone(transform(files(d), "F3-TEST", "T02", {"renames": {"primary": "new"}})[0])

    def test_T03_conflict_is_not_neutral_normalisation(self):
        d = example(); d[RECORDS["claims"]]["claims"][0]["source_pointer"] = "alias:primary"
        d[RECORDS["edges"]]["aliases"] = {"primary": "/values/x", "alias:primary": "/values/y"}
        outputs = []
        for selection in ("min", "max"):
            out, r = transform(files(d), "F3-TEST", "T03", {"selection": selection, "relation_mode": "contrast"})
            self.assertEqual(r["relation_type"], "SEMANTIC_CONTRAST")
            outputs.append(verdicts(out)[1])
        self.assertEqual(outputs, ["SVSSS", "VVVVV"])
        self.assertIsNone(transform(files(d), "F3-TEST", "T03", {"selection": "min", "relation_mode": "preserve", "invariance_conventions": ["either_unique"]})[0])

    def test_T04_convention_conditioned_and_collision(self):
        d = example(); d[RECORDS["claims"]]["claims"][0]["source_pointer"] = "alias:primary"
        d[RECORDS["edges"]]["aliases"] = {"alias:primary": "/values/x"}
        out, r = transform(files(d), "F3-TEST", "T04", {})
        self.assertEqual(verdicts(out)[1], "VSSSS")
        self.assertEqual(r["relations"]["literal_only"]["before"], "S")
        self.assertEqual(r["relations"]["literal_only"]["after"], "V")
        d[RECORDS["edges"]]["aliases"]["primary"] = "/values/y"
        self.assertIsNone(transform(files(d), "F3-TEST", "T04", {})[0])

    def test_T05_repair_cycles_and_unsupported_invariance(self):
        d = example(); d[RECORDS["claims"]]["claims"][0]["source_pointer"] = "alias:primary"
        d[RECORDS["edges"]]["aliases"] = {"primary": "alias:second", "second": "/values/x"}
        self.assertEqual(verdicts(files(d))[1], "VVVVV")
        out, r = transform(files(d), "F3-TEST", "T05", {"mode": "repair"})
        self.assertEqual(verdicts(out)[1], "VSSSS"); self.assertEqual(r["relation_type"], "REPAIR")
        self.assertIsNone(transform(files(d), "F3-TEST", "T05", {"mode": "invariance"})[0])
        d[RECORDS["edges"]]["aliases"]["second"] = "alias:primary"
        self.assertIsNone(transform(files(d), "F3-TEST", "T05", {"mode": "repair"})[0])

    def test_T07_requires_equal_values_but_different_metadata(self):
        out, r = transform(files(example()), "F3-TEST", "T07", {"claim_id": "F3-DOC-CLAIM", "target_pointer": "/values/y", "comparison_convention": "either_unique"})
        self.assertEqual(verdicts(out)[1], "VVVVV")
        d = example(); d[RECORDS["result"]]["values"]["y"] = 74
        self.assertIsNone(transform(files(d), "F3-TEST", "T07", {"claim_id": "F3-DOC-CLAIM", "target_pointer": "/values/y", "comparison_convention": "either_unique"})[0])

    def test_T08_permutation_and_scope(self):
        for w in ("W1", "W2"):
            with self.subTest(workflow=w):
                data = fresh_seed(REPO, w, "F3-TEST-" + w, self.profile)
                params = {"permutation": [2, 0, 1], "eligibility_model": "NSC-CORE-ROW-LOCAL-1"}
                out, r = transform(data, "F3-TEST", "T08", params, profile=self.profile)
                self.assertIsNotNone(out); self.assertEqual(p5_custody(out, self.profile)["status"], "PASS")
                self.assertEqual(verdicts(out)[1], "SSSSS")
                self.assertIsNone(transform(data, "F3-TEST", "T08", {**params, "permutation": [0, 0, 1]}, profile=self.profile)[0])
                self.assertIsNone(transform(data, "F3-TEST", "T08", {**params, "eligibility_model": "order_sensitive"}, profile=self.profile)[0])

    def test_bad_configuration_is_not_a_semantic_label(self):
        with self.assertRaises(InputError):
            transform(files(example()), "F3-TEST", "T99", {})
        with self.assertRaises(InputError):
            transform(files(example()), "F3-TEST", "T01", {"silent_option": True})

    def test_nested_parameter_types_are_controlled_precondition_failures(self):
        d = example(); d[RECORDS["claims"]]["claims"][0]["source_pointer"] = "alias:primary"
        for bad in ([[]], [{}], [True], ["suffix_only", "suffix_only"], None):
            with self.subTest(policies=bad):
                out, report = transform(files(d), "F3-TEST", "T02", {
                    "renames": {"primary": "renamed"}, "invariance_conventions": bad})
                self.assertIsNone(out); self.assertEqual(report["status"], "PRECONDITION_FAILED")
                self.assertEqual(report["relations"], {})
        original = fresh_seed(REPO, "W1", "F3-TEST", self.profile)
        for bad in ([[]], [{}], [True]):
            for field in ("ids", "local_to_source_positions"):
                with self.subTest(field=field, value=bad):
                    records = {p: parse(b) for p, b in original.items() if p.endswith(".json")}
                    records["records/R06_materialisation.json"]["populations"][0][field] = bad
                    data = dict(original)
                    for p, value in records.items(): data[p] = encoded(value)
                    data = seal_profile(data, self.profile)
                    out, report = transform(data, "F3-TEST", "T08", {
                        "permutation": [2, 0, 1], "eligibility_model": "NSC-CORE-ROW-LOCAL-1"}, profile=self.profile)
                    self.assertIsNone(out); self.assertEqual(report["status"], "PRECONDITION_FAILED")
                    self.assertEqual(report["relations"], {})

    def test_P4_frozen_sources_and_fresh_profile_custody(self):
        ctx = native_context(REPO, "P4")
        profile = parse(ctx["profile_path"].read_bytes())
        for workflow in ("W1", "W2"):
            data = fresh_seed(REPO, workflow, "F3-TEST-P4-" + workflow, profile)
            self.assertEqual(profile_custody(data, profile)["status"], "PASS")
            self.assertEqual(parse(data["bundle.json"])["profile_id"], "NSC-P3-CORE-RECOVERY-2")
            out, report = transform(data, "F3-TEST-P4", "T08", {
                "permutation": [2, 0, 1], "eligibility_model": "NSC-CORE-ROW-LOCAL-1"}, profile=profile)
            self.assertIsNotNone(out); self.assertEqual(report["custody"]["status"], "RECOMMITTED_P4")

    def test_changed_profile_cannot_redefine_row_local_eligibility(self):
        original = fresh_seed(REPO, "W1", "F3-TEST", self.profile)
        altered = copy.deepcopy(self.profile)
        altered["category_order"] = list(reversed(altered["category_order"]))
        out, report = transform(original, "F3-TEST", "T08", {
            "permutation": [2, 0, 1], "eligibility_model": "NSC-CORE-ROW-LOCAL-1"}, profile=altered)
        self.assertIsNone(out); self.assertEqual(report["status"], "INPUT_ERROR")
        self.assertIn("FROZEN_PROFILE_CONTENT_MISMATCH", report["failure"]["message"])

    def test_inventory_byte_count_boolean_cannot_impersonate_integer(self):
        data = fresh_seed(REPO, "W1", "F3-TYPED-INVENTORY", self.profile)
        data["records/R02_aux.txt"] = b"x"
        data = seal_profile(data, self.profile)
        inventory = parse(data["inventory.json"])
        member = next(m for m in inventory["members"] if m["path"] == "records/R02_aux.txt")
        self.assertEqual(member["bytes"], 1)
        member["bytes"] = True
        data["inventory.json"] = encoded(inventory)
        self.assertEqual(profile_custody(data, self.profile), {"status": "FAIL", "issues": ["RAW_INVENTORY"]})
        out, report = transform(data, "F3-TYPED-INVENTORY", "T01", {"order_independent": True}, profile=self.profile)
        self.assertIsNone(out); self.assertEqual(report["status"], "PRECONDITION_FAILED")
        self.assertEqual(report["relations"], {})

    def test_malformed_non_O15_record_remains_an_input_error(self):
        data = fresh_seed(REPO, "W1", "F3-BAD-RECORD", self.profile)
        data["inventory.json"] = b'{"members":[],"members":[]}'
        out, report = transform(data, "F3-BAD-RECORD", "T01", {"order_independent": True}, profile=self.profile)
        self.assertIsNone(out); self.assertEqual(report["status"], "INPUT_ERROR")
        self.assertFalse(report["semantic_verdict_assigned"])
        self.assertEqual(report["relations"], {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
