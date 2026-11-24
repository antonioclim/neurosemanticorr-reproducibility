import unittest

from r5_f3.reference_audit.regression_phase2 import run


class Phase2RegressionTests(unittest.TestCase):
    def test_actual_documentary_evaluator_and_every_original_transcript(self):
        result = run()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["original_checker_invocations"], 0)
        self.assertEqual(set(result["transcripts"]), {
            "direct_controls_underdetermined", "mirror_suffix_identifies_set",
            "differing_local_rules_out_of_model", "empty_transcript", "single_conflict_S", "single_conflict_V"})


if __name__ == "__main__":
    unittest.main()
