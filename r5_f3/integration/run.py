"""Run the complete qualification workflow from an unpacked software distribution.

Outputs must be new and outside the repository. Python 3.12 or later is
required. All subprocesses use the packaged sources and the standard library.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import sys
import tarfile
import time
import traceback


ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "r5_f3/integration/inputs/neurosemanticorr_prospective_evidence_1.0.0.tar.xz"
ARCHIVE_SHA256 = "55dc0a8bfd7a9aec272bf259b81b15a57e9fc41be9f3b38b75d3e1b20c0054d1"
PHASE2_RESULT_SHA256 = "259e8bd285373048e53fc5fedcfae0a221ffa310eb9e5b159843e7693363dbbb"
CASEWISE_RESULT_SHA256 = "5e8265375be3e1d112b670648588941e011bfec237813d093407009fbaf76464"


def stamp():
    return datetime.now(timezone.utc).isoformat()


def file_hash(path):
    return sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def snapshot():
    result = {}
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if ".git" in relative.parts:
            continue
        require(not path.is_symlink(), "Repository contains a symbolic link: " + str(relative))
        if path.is_file():
            result[relative.as_posix()] = {"bytes": path.stat().st_size, "sha256": file_hash(path)}
    return result


def extract_retained_archive(output):
    require(file_hash(ARCHIVE) == ARCHIVE_SHA256, "Retained archive SHA-256 mismatch")
    destination = output / "retained_archive"
    destination.mkdir()
    with tarfile.open(ARCHIVE, "r:xz") as archive:
        members = archive.getmembers()
        names = set()
        for member in members:
            path = PurePosixPath(member.name)
            require(not path.is_absolute() and ".." not in path.parts and "\\" not in member.name,
                    "Unsafe archive member: " + member.name)
            require(path.parts and path.parts[0] == "NSC_PROS_v1", "Unexpected archive root")
            require(member.isfile() or member.isdir(), "Non-regular archive member")
            require(path.as_posix() not in names, "Duplicate archive member")
            names.add(path.as_posix())
        archive.extractall(destination, filter="data")
    return destination / "NSC_PROS_v1", {"sha256": ARCHIVE_SHA256, "members": len(members),
                                          "uncompressed_file_bytes": sum(m.size for m in members if m.isfile())}


def run_command(output, name, arguments, *, isolated=False, timeout=600):
    logdir = output / "commands" / name
    logdir.mkdir(parents=True)
    command = [sys.executable, "-I" if isolated else "-B", *[str(x) for x in arguments]]
    started = stamp()
    clock = time.perf_counter()
    print("Running " + name, flush=True)
    receipt = {"command": command, "working_directory": str(ROOT), "started_utc": started,
               "timeout_seconds": timeout, "exit_code": None, "execution_status": "STARTED"}
    stdout, stderr, process = b"", b"", None
    try:
        process = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=timeout)
        stdout, stderr = process.stdout, process.stderr
        receipt.update(exit_code=process.returncode, execution_status="COMPLETED")
    except subprocess.TimeoutExpired as error:
        stdout, stderr = error.stdout or b"", error.stderr or b""
        receipt.update(execution_status="TIMEOUT", error={"type": type(error).__name__, "message": str(error)})
    except OSError as error:
        receipt.update(execution_status="EXECUTION_ERROR", error={"type": type(error).__name__, "message": str(error)})
    if isinstance(stdout, str):
        stdout = stdout.encode("utf-8")
    if isinstance(stderr, str):
        stderr = stderr.encode("utf-8")
    receipt.update(completed_utc=stamp(), duration_seconds=round(time.perf_counter() - clock, 6),
                   stdout_sha256=sha256(stdout).hexdigest(), stderr_sha256=sha256(stderr).hexdigest())
    (logdir / "stdout.bin").write_bytes(stdout)
    (logdir / "stderr.bin").write_bytes(stderr)
    write_json(logdir / "RECEIPT.json", receipt)
    require(process is not None, name + " " + receipt["execution_status"] + "; inspect " + str(logdir))
    require(process.returncode == 0, name + " exited " + str(process.returncode) + "; inspect " + str(logdir))
    return process, receipt


def unittest_count(process, expected):
    text = process.stderr.decode("utf-8", errors="replace")
    match = re.search(r"Ran (\d+) tests? in", text)
    require(match is not None and re.search(r"^OK$", text, re.M), "Missing successful unittest footer")
    count = int(match.group(1))
    require(count == expected, "Expected " + str(expected) + " unit tests, observed " + str(count))
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new directory outside the repository")
    args = parser.parse_args()
    output = args.out.resolve()
    if sys.version_info < (3, 12):
        parser.error("Python 3.12 or later is required")
    if output == ROOT or ROOT in output.parents:
        parser.error("--out must be outside the repository")
    if output.exists():
        parser.error("--out already exists; use a new directory")
    output.mkdir(parents=True)
    result = {"schema": "nsc-r5-f3-integrated-qualification/1", "status": "RUNNING", "started_utc": stamp(),
              "environment": {"python": sys.version, "platform": platform.platform()},
              "repository": str(ROOT), "runner_sha256": file_hash(Path(__file__)), "checks": {},
              "scope": "Local computational acceptance on synthetic fixtures and read-only historical records",
              "new_prospective_experiments": 0, "new_human_adjudications": 0,
              "historical_prospective_checker_invocations": 0}
    commands = {}
    code = 1
    initial = None
    try:
        initial = snapshot()
        write_json(output / "SOURCE_BEFORE.json", initial)
        process, commands["custody_before"] = run_command(output, "custody_before", ["tools/check_candidate.py"])
        result["checks"]["custody_before"] = json.loads(process.stdout)
        frozen, result["retained_archive"] = extract_retained_archive(output)

        _, commands["reference_audit"] = run_command(output, "reference_audit",
            ["-m", "r5_f3.reference_audit.qualify", "--out", output / "reference_audit"])
        reference = read_json(output / "reference_audit/RESULT.json")
        require(reference["status"] == "PASS" and reference["unit_tests"]["tests_run"] == 27
                and reference["unit_tests"]["failures"] == 0 and reference["unit_tests"]["errors"] == 0
                and reference["unit_tests"]["skipped"] == 0 and len(reference["examples"]) == 17
                and all(example["verified"] is True for example in reference["examples"].values()),
                "Reference-audit qualification did not pass or corpus changed")
        result["checks"]["reference_audit"] = {
            "status": reference["status"], "unit_tests": reference["unit_tests"]["tests_run"],
            "examples_audited_and_verified": len(reference["examples"]),
            "phase2_regression": reference["phase2_regression"], "scope_comparison": reference["scope_comparison"],
            "canonical_query_certificates": {k: v["minimum"] for k, v in reference["canonical_query_certificates"].items()},
            "receipt": "reference_audit/RESULT.json", "sha256": file_hash(output / "reference_audit/RESULT.json")}

        process, commands["o15_unit"] = run_command(output, "o15_unit",
            ["-m", "unittest", "r5_f3.o15_diagnostics.test_diagnostics", "-v"])
        result["checks"]["o15_unit"] = {"status": "PASS", "unit_tests": unittest_count(process, 23)}
        _, commands["o15_cli"] = run_command(output, "o15_cli",
            ["-m", "r5_f3.o15_diagnostics.qualify_cli", "--out", output / "o15_cli"])
        cli = read_json(output / "o15_cli/SUMMARY.json")
        require(cli["status"] == "PASS" and len(cli["checks"]) == 8
                and all(c["passed"] is True for c in cli["checks"]), "O15 CLI qualification failed or corpus changed")
        result["checks"]["o15_cli"] = {"status": "PASS", "checks": len(cli["checks"])}
        _, commands["o15_regression"] = run_command(output, "o15_regression",
            ["-m", "r5_f3.o15_diagnostics", "regression", "--archive", frozen, "--output", output / "O15_REGRESSION_202.json"])
        regression = read_json(output / "O15_REGRESSION_202.json")
        require(regression["status"] == "PASS" and regression["case_count"] == 202
                and regression["convention_comparisons"] == 1010, "O15 retained-reference regression failed")
        result["checks"]["o15_regression"] = {key: regression[key] for key in
            ("status", "case_count", "convention_comparisons", "original_checker_invocations")}
        for generation in ("P4", "P5"):
            name = "native_" + generation.lower()
            _, commands[name] = run_command(output, name,
                ["-m", "r5_f3.o15_diagnostics", "native-suite", "--generation", generation, "--out", output / name])
            native = read_json(output / name / "SUMMARY.json")
            require(native["status"] == "PASS" and native["candidate_invocations"] == 94
                    and native["expectations_met"] == 94 and native["semantic_reports"] == 92
                    and native["controlled_execution_errors"] == 2
                    and native["documentary_checks_passed"] == native["documentary_checks_total"] == 21
                    and native["native_full_vector_relation_checks"] == 12 and native["nonfocal_changes"] == [],
                    generation + " native qualification failed or corpus changed")
            result["checks"][name] = {key: native[key] for key in
                ("status", "run_id", "candidate_invocations", "semantic_reports", "controlled_execution_errors",
                 "expectations_met", "documentary_checks_passed", "documentary_checks_total",
                 "native_full_vector_relation_checks", "nonfocal_changes")}

        process, commands["screening_unit"] = run_command(output, "screening_unit",
            ["-m", "unittest", "r5_f3.screening.test_screening", "-v"])
        result["checks"]["screening_unit"] = {"status": "PASS", "unit_tests": unittest_count(process, 12)}
        _, commands["screening_replay"] = run_command(output, "screening_replay",
            ["-m", "r5_f3.screening.replay_archived", "--out", output / "screening"])
        screening = read_json(output / "screening/REPLAY_RESULTS.json")
        require(screening["status"] == "PASS_ARCHIVED_DESIGN_REPLAY" and screening["field_comparisons"] == 72
                and screening["pooled"]["screen_bonferroni_upper"] == 60, "Screening replay differs from retained design")
        result["checks"]["screening_replay"] = {key: screening[key] for key in
            ("status", "context_policy_reports", "field_comparisons", "pooled", "new_draws", "new_human_adjudications")}

        process, commands["legacy_decision_unit"] = run_command(output, "legacy_decision_unit", ["phase2/02_source/test_decision_audit.py"])
        result["checks"]["legacy_decision_unit"] = {"status": "PASS", "unit_tests": unittest_count(process, 4)}
        process, commands["legacy_phase2"] = run_command(output, "legacy_phase2",
            ["phase2/02_source/run_phase2.py", "--frozen-root", frozen])
        require(sha256(process.stdout).hexdigest() == PHASE2_RESULT_SHA256, "Retained phase2 result is not byte-identical")
        result["checks"]["legacy_phase2"] = {"status": "PASS_BYTE_IDENTICAL", "sha256": PHASE2_RESULT_SHA256}
        process, commands["legacy_casewise"] = run_command(output, "legacy_casewise", ["tools/recompute_casewise.py", frozen])
        require(sha256(process.stdout).hexdigest() == CASEWISE_RESULT_SHA256, "Retained casewise comparison is not byte-identical")
        result["checks"]["legacy_casewise"] = {"status": "PASS_BYTE_IDENTICAL", "stdout_sha256": CASEWISE_RESULT_SHA256}
        process, commands["software_example"] = run_command(output, "software_example",
            ["examples/software-report/check_build_report.py", "--source-dir", "phase2/02_source"])
        example = json.loads(process.stdout)
        require(example["status"] == "PASS_SYNTHETIC_INTERFACE_EXAMPLE" and example["comparisons"] == 20,
                "Software example failed or corpus changed")
        result["checks"]["software_example"] = example

        _, commands["p5_full"] = run_command(output, "p5_full",
            ["p5/tools/review.py", "--mode", "full", "--out", output / "p5_full"], isolated=True)
        p5 = read_json(output / "p5_full/SUMMARY.json")
        require(p5["status"] == "PASS_UNIT_REVIEW" and p5["candidate_invocations"] == 158
                and len(p5["checks"]) == 183 and all(c["ok"] is True for c in p5["checks"]), "P5 full review failed")
        result["checks"]["p5_full"] = {"status": p5["status"], "candidate_invocations": p5["candidate_invocations"],
                                         "checks": len(p5["checks"]), "checks_passed": sum(c["ok"] for c in p5["checks"])}

        process, commands["custody_after"] = run_command(output, "custody_after", ["tools/check_candidate.py"])
        result["checks"]["custody_after"] = json.loads(process.stdout)
        require(snapshot() == initial, "Repository contents changed during integration")
        result["source_immutability"] = "PASS"
        result["native_checker_invocations_new_synthetic_inputs"] = 94 + 94 + 158
        result["status"] = "PASS"
        code = 0
    except Exception as error:
        result["status"] = "FAIL"
        result["error"] = {"type": type(error).__name__, "message": str(error)}
        (output / "TRACEBACK.txt").write_text(traceback.format_exc(), encoding="utf-8")
    finally:
        result["completed_utc"] = stamp()
        # Include the receipt of a failed or timed-out command as well as every
        # successful one. The on-disk receipts precede any raised failure.
        result["commands"] = {p.parent.name: read_json(p) for p in sorted((output / "commands").glob("*/RECEIPT.json"))}
        if initial is not None:
            try:
                final = snapshot()
                write_json(output / "SOURCE_AFTER.json", final)
                result["source_immutability"] = "PASS" if final == initial else "FAIL"
                if final != initial:
                    result["status"] = "FAIL"
                    code = 1
            except Exception as error:
                result["source_immutability"] = "CHECK_ERROR: " + str(error)
                result["status"] = "FAIL"
                code = 1
        result["exit_code"] = code
        write_json(output / "SUMMARY.json", result)
        print(json.dumps({"status": result["status"], "summary": str(output / "SUMMARY.json"), "exit_code": code}), flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
