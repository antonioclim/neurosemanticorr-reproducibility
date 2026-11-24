from contextlib import redirect_stdout
from copy import deepcopy
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from r5_f3.reference_audit import audit
from r5_f3.reference_audit.canonical import digest, display_json, file_digest, load_file, loads
from r5_f3.reference_audit.cli import main
from r5_f3.reference_audit.provenance import HERE, code_identity
from r5_f3.reference_audit.qualify import prepare_output
from r5_f3.reference_audit.tests.helpers import tiny


class CLITests(unittest.TestCase):
    def command(self, *arguments, stdin=None, cwd=None):
        run = subprocess.run([sys.executable, "-B", "-m", "r5_f3.reference_audit", *map(str, arguments)],
                             cwd=cwd or HERE.parents[1], input=stdin, text=True,
                             encoding="utf-8", capture_output=True, check=False)
        self.assertEqual(run.stderr, "")
        return run.returncode, loads(run.stdout)

    def test_audit_verify_digest_stdin_and_exit_semantics(self):
        with tempfile.TemporaryDirectory(prefix="cli-", dir=os.environ.get("NSC_REFERENCE_AUDIT_TEST_TMP")) as temporary:
            directory = Path(temporary)
            request_path, report_path = directory / "input.json", directory / "report.json"
            request = tiny()
            request_path.write_text(display_json(request), encoding="utf-8")
            before = file_digest(request_path)
            code, report = self.command("audit", request_path)
            self.assertEqual((code, report["status"]), (0, "AT_OR_BELOW"))
            report_path.write_text(display_json(report), encoding="utf-8")
            code, receipt = self.command("verify", request_path, report_path)
            self.assertEqual((code, receipt["status"]), (0, "VERIFIED"))
            self.assertEqual(file_digest(request_path), before)
            code, hashed = self.command("digest", "-", stdin=display_json({"é": "value", "a": [1, 2]}))
            self.assertEqual((code, hashed["sha256"]), (0, digest({"é": "value", "a": [1, 2]})))
            code, stdin_report = self.command("audit", "-", stdin=display_json(request))
            self.assertEqual((code, stdin_report), (0, report))
            code, invalid = self.command("audit", "-", stdin='{"budget":true}')
            self.assertEqual((code, invalid["status"]), (2, "INPUT_ERROR"))
            code, invalid = self.command("digest", "-", stdin=r'{"\ud800":1,"\ud800":2}')
            self.assertEqual((code, invalid["status"]), (2, "INPUT_ERROR"))
            report["status"] = "ABOVE"
            report_path.write_text(display_json(report), encoding="utf-8")
            code, rejected = self.command("verify", request_path, report_path)
            self.assertEqual((code, rejected["status"]), (3, "VERIFICATION_FAILED"))
        code, valid_empty = self.command("audit", HERE / "examples/valid_out_of_model.json")
        self.assertEqual((code, valid_empty["status"]), (0, "OUT_OF_MODEL"))
        unsupported = load_file(HERE / "examples/canonical_broad_k8.json")
        unsupported["threshold"] = "23"
        code, report = self.command("q-min", "-", stdin=display_json(unsupported))
        self.assertEqual((code, report["status"], report["threshold"]), (0, "NOT_APPLICABLE", "23"))

    def test_execution_failure_is_not_a_semantic_verdict(self):
        stdout = io.StringIO()
        with patch("r5_f3.reference_audit.cli._input", return_value=tiny()), \
             patch("r5_f3.reference_audit.cli.audit", side_effect=RuntimeError("Deliberate execution failure")), \
             redirect_stdout(stdout):
            code = main(["audit", "unused.json"])
        result = loads(stdout.getvalue())
        self.assertEqual((code, result["status"]), (4, "EXECUTION_ERROR"))

    def test_runtime_is_relocatable_without_f2_or_other_repository_sources(self):
        with tempfile.TemporaryDirectory(prefix="standalone-", dir=os.environ.get("NSC_REFERENCE_AUDIT_TEST_TMP")) as temporary:
            root = Path(temporary)
            component = root / "r5_f3/reference_audit"
            component.mkdir(parents=True)
            for filename in code_identity()["files_sha256"]:
                shutil.copyfile(HERE / filename, component / filename)
            (component / "inputs").mkdir()
            shutil.copyfile(HERE / "inputs/o15_archived_reference_matrix_192.csv",
                            component / "inputs/o15_archived_reference_matrix_192.csv")
            request = load_file(HERE / "examples/canonical_broad_k8.json")
            code, report = self.command("audit", "-", stdin=display_json(request), cwd=root)
            self.assertEqual(code, 0)
            self.assertEqual(report["producer"], code_identity())
            code, certificate = self.command("q-min", "-", stdin=display_json(request), cwd=root)
            self.assertEqual((code, certificate["minimum_query_count"]), (0, 33))

    def test_qualification_output_is_new_and_external(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            prepare_output(HERE / "must-not-be-created")
        self.assertFalse((HERE / "must-not-be-created").exists())
        with tempfile.TemporaryDirectory(prefix="output-guard-", dir=os.environ.get("NSC_REFERENCE_AUDIT_TEST_TMP")) as temporary:
            parent = Path(temporary)
            with self.assertRaisesRegex(ValueError, "existing"):
                prepare_output(parent)
            new = prepare_output(parent / "new")
            self.assertTrue(new.is_dir())
            with self.assertRaisesRegex(ValueError, "existing"):
                prepare_output(new)


if __name__ == "__main__":
    unittest.main()
