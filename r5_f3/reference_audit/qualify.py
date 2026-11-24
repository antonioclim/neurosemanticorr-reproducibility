"""Reproduce qualification into a new external output directory."""

import argparse
from datetime import datetime, timezone
import io
import os
from pathlib import Path
import platform
import sys
import tempfile
import traceback
import unittest

from .canonical import digest, display_json, file_digest, load_file
from .canonical_query import canonical_query_minimum
from .engine import audit
from .integration_scope_comparison import run as scope_comparison
from .provenance import HERE, code_identity
from .regression_phase2 import run as phase2_regression
from .verification import verify_report


def now():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(display_json(value), encoding="utf-8")


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = {}

    def startTest(self, test):
        self.records[test.id()] = {"status": "RUNNING"}
        super().startTest(test)

    def addSuccess(self, test):
        self.records[test.id()]["status"] = "PASS"
        super().addSuccess(test)

    def addFailure(self, test, error):
        self.records[test.id()]["status"] = "FAIL"
        super().addFailure(test, error)

    def addError(self, test, error):
        self.records[test.id()]["status"] = "ERROR"
        super().addError(test, error)

    def addSubTest(self, test, subtest, error):
        if error is not None:
            self.records[test.id()]["status"] = "FAIL"
        super().addSubTest(test, subtest, error)


def retained_identities():
    manifest = load_file(HERE / "inputs/SOURCE_IDENTITIES.json")
    identities = {}
    for item in manifest["sources"]:
        path = HERE / item["local"]
        identity = file_digest(path)
        if identity != item["sha256"] or path.stat().st_size != item["bytes"]:
            raise AssertionError("Retained source identity mismatch: " + item["local"])
        identities[item["local"]] = identity
    return identities


def component_files():
    result = {}
    for path in sorted(HERE.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(HERE)
        result[str(relative)] = {"bytes": path.stat().st_size, "sha256": file_digest(path)}
    return result


def prepare_output(value):
    output = Path(value).expanduser().resolve()
    if output == HERE or output.is_relative_to(HERE):
        raise ValueError("The qualification output must be outside the component")
    if output.exists():
        raise ValueError("Refusing to overwrite an existing qualification directory")
    output.mkdir(parents=True, exist_ok=False)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m r5_f3.reference_audit.qualify")
    parser.add_argument("--out", required=True, help="New output directory outside the component; existing paths are refused")
    arguments = parser.parse_args(argv)
    try:
        output = prepare_output(arguments.out)
    except (ValueError, OSError) as error:
        print(display_json({"status": "QUALIFICATION_INPUT_ERROR", "message": str(error)}), end="")
        return 2
    command = {"schema": "nsc.reference-audit.command-log/1", "started_utc": now(),
               "command": [sys.executable, "-B", "-m", "r5_f3.reference_audit.qualify", "--out", str(output)],
               "working_directory": str(Path.cwd()), "output_directory": str(output), "operations": [],
               "original_checker_invocations": 0, "prospective_experiments": 0}
    result = {"schema": "nsc.reference-audit.qualification/1", "status": "RUNNING",
              "producer": code_identity(), "driver_sha256": file_digest(HERE / "qualify.py"),
              "environment": {"python": sys.version, "implementation": platform.python_implementation(),
                              "platform": platform.platform()},
              "original_checker_invocations": 0, "prospective_experiments": 0}
    exit_code = 1
    try:
        originals = retained_identities()
        source_files = component_files()
        result["source_files"] = source_files
        command["operations"].append({"kind": "identity_check", "status": "PASS", "retained_files": len(originals)})
        stream = io.StringIO()
        suite = unittest.defaultTestLoader.discover(str(HERE / "tests"), top_level_dir=str(HERE.parents[1]))
        # All transient test files are created inside the selected output, not
        # inside the source component. The environment value is task-specific.
        with tempfile.TemporaryDirectory(prefix="test-work-", dir=output) as test_work:
            previous_test_directory = os.environ.get("NSC_REFERENCE_AUDIT_TEST_TMP")
            os.environ["NSC_REFERENCE_AUDIT_TEST_TMP"] = test_work
            try:
                tests = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordedResult).run(suite)
            finally:
                if previous_test_directory is None:
                    del os.environ["NSC_REFERENCE_AUDIT_TEST_TMP"]
                else:
                    os.environ["NSC_REFERENCE_AUDIT_TEST_TMP"] = previous_test_directory
        (output / "unittest.txt").write_text(stream.getvalue(), encoding="utf-8")
        result["unit_tests"] = {"status": "PASS" if tests.wasSuccessful() else "FAIL", "tests_run": tests.testsRun,
                                "failures": len(tests.failures), "errors": len(tests.errors), "skipped": len(tests.skipped),
                                "test_results": tests.records, "log": "unittest.txt"}
        command["operations"].append({"kind": "in_process", "operation": "unittest discovery and execution", "status": result["unit_tests"]["status"]})
        if not tests.wasSuccessful():
            raise AssertionError("The component test suite did not pass")
        example_ids = load_file(HERE / "examples/EXAMPLE_IDENTITIES.json")
        examples = {}
        for name, identity in sorted(example_ids.items()):
            path = HERE / "examples" / (name + ".json")
            request = load_file(path)
            if file_digest(path) != identity["file_sha256"] or digest(request) != identity["request_sha256"]:
                raise AssertionError("Packaged example identity mismatch: " + name)
            report = audit(request)
            receipt = verify_report(request, report)
            write(output / "example_reports" / (name + ".report.json"), report)
            write(output / "example_reports" / (name + ".verification.json"), receipt)
            examples[name] = {"status": report["status"], "interval": report["interval"],
                              "request_sha256": digest(request), "report_sha256": report["report_sha256"],
                              "verification_sha256": receipt["verification_sha256"], "verified": True}
        result["examples"] = examples
        command["operations"].append({"kind": "in_process", "operation": "audit and independent verify_report for every packaged example", "status": "PASS"})
        query_results = {}
        for budget in (7, 8):
            request = load_file(HERE / f"examples/canonical_broad_k{budget}.json")
            certificate = canonical_query_minimum(request)
            write(output / f"CANONICAL_QUERY_K{budget}.json", certificate)
            query_results[str(budget)] = {"minimum": certificate["minimum_query_count"],
                                         "certificate_sha256": certificate["certificate_sha256"], "case_ids": certificate["case_ids"]}
        result["canonical_query_certificates"] = query_results
        command["operations"].append({"kind": "in_process", "operation": "canonical q-min certificates for budgets 7 and 8", "status": "PASS"})
        phase2 = phase2_regression()
        write(output / "PHASE2_REGRESSION.json", phase2)
        result["phase2_regression"] = {"status": phase2["status"], "result_sha256": phase2["result_sha256"],
                                        "scope": phase2["scope"]}
        command["operations"].append({"kind": "in_process", "operation": "exact retained phase2 documentary evaluator and all original transcripts", "status": "PASS"})
        comparison = scope_comparison()
        write(output / "SCOPE_COMPARISON.json", comparison)
        result["scope_comparison"] = {"status": comparison["status"], "result_sha256": comparison["result_sha256"],
                                       "scope": comparison["scope"]}
        command["operations"].append({"kind": "in_process", "operation": "E05 global and 625-centre contextwise API results versus raw enumeration; separate full casewise product comparator", "status": "PASS"})
        if retained_identities() != originals:
            raise AssertionError("Retained inputs changed during qualification")
        if component_files() != source_files:
            raise AssertionError("Component source or packaged inputs changed during qualification")
        result["retained_input_immutability"] = "PASS"
        result["coverage"] = {
            "endpoint_and_radius_oracle": "All two-coordinate binary centres, common checker labels, nonempty binary admissibility sets and eligibility masks, under three rational/zero weight patterns and budgets 0..2; separate raw assignment enumeration",
            "additional_semantics": "Multicentre, U, checker disagreement, hard observations, zero-weight external queries, protection and noninteger exact scores",
            "adversarial_contract": "Duplicate IDs and JSON keys, missing or mismatched hashes, false types, coordinated budget/label/distance/score certificate mutation, rehashed report mutation, source identity binding",
            "regression": "Every original phase2 transcript and actual documentary probe evaluation; empty and single-conflict branches at k=0",
            "query_certificate": "Canonical k=0..8 scope guards, cross-region distances and reconstructed necessity witnesses for all 32 plus the extra query at k=8",
            "portability": "CLI round trips and execution from a relocated runtime-only component with packaged canonical CSV; no F2 path dependency"}
        result["limits"] = [
            "Observed adjudication truth and external authority are assumptions, not established by hashes.",
            "The engine covers only explicitly supplied joint centres; it does not certify complete Cartesian enumeration.",
            "The complete casewise 192-case product comparator is separate from the explicit-centre engine API.",
            "Canonical query minima are restricted to the verified frame, conventions, admissibility choices, threshold and budgets 0..8.",
            "No original T_FULL or B_ASSERT execution and no new prospective experiment occurred.",
            "These are exact finite-model sensitivity calculations, not sampling confidence bounds."]
        result["status"] = "PASS"
        exit_code = 0
    except Exception as error:
        result["status"] = "FAIL"
        result["error"] = {"type": type(error).__name__, "message": str(error)}
        (output / "failure_traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")
    result["completed_utc"] = now()
    result["result_sha256"] = digest(result)
    write(output / "RESULT.json", result)
    command["completed_utc"] = result["completed_utc"]
    command["exit_code"] = exit_code
    command["result_sha256"] = result["result_sha256"]
    command["log_sha256"] = digest(command)
    write(output / "COMMAND_LOG.json", command)
    generated_files = {str(path.relative_to(output)): {"bytes": path.stat().st_size, "sha256": file_digest(path)}
                       for path in sorted(output.rglob("*")) if path.is_file()}
    manifest = {"schema": "nsc.reference-audit.file-manifest/1", "component_files": component_files(),
                "generated_files": generated_files,
                "scope": "Component sources and input paths are relative to the component; generated paths are relative to this output directory. This manifest excludes itself and Python bytecode caches."}
    manifest["manifest_sha256"] = digest(manifest)
    write(output / "FILE_MANIFEST.json", manifest)
    print(display_json({"status": result["status"], "result": str(output / "RESULT.json"),
                        "result_sha256": result["result_sha256"], "exit_code": exit_code}), end="")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
