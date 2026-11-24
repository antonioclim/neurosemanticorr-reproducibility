"""Run unchanged native P4/P5 checkers on fresh, fully recommitted F3 inputs."""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import uuid

from .evidence import (InputError, binding, canonical, encoded, json_documents, parse,
                       read_tree, seal_profile, sha256, validate_fixed_profile,
                       write_new_json, write_new_tree)
from .frozen import native_context
from .operators import transform
from .reference import POLICIES, RECORDS, evaluate_files

ARMS = ("T_FULL", "B_ASSERT")
ALL_S = {f"O{i:02d}": "S" for i in range(1, 17)}


def utc():
    return datetime.now(timezone.utc).isoformat()


def replace_ids(value, replacements):
    if type(value) is str:
        return replacements.get(value, value)
    if type(value) is list:
        return [replace_ids(v, replacements) for v in value]
    if type(value) is dict:
        return {replacements.get(k, k): replace_ids(v, replacements) for k, v in value.items()}
    return value


def fresh_seed(repository, workflow, case_id, profile):
    files = read_tree(Path(repository) / "p5" / "examples" / workflow)
    docs = json_documents(files)
    rows = docs["data/rows.json"]["rows"]
    replacement = {row["id"]: case_id + "-ROW-" + str(i + 1) for i, row in enumerate(rows)}
    replacement[docs[RECORDS["result"]]["result_id"]] = case_id + "-RESULT"
    for i, claim in enumerate(docs[RECORDS["claims"]]["claims"]):
        replacement[claim["claim_id"]] = case_id + "-CLAIM-" + str(i + 1)
    for i, task in enumerate(docs["records/R13.json"]["tasks"]):
        replacement[task["task_id"]] = case_id + "-TASK-" + str(i + 1)
    docs = {p: replace_ids(v, replacement) for p, v in docs.items()}
    docs["bundle.json"]["profile_id"] = profile["profile_id"]
    docs["semantic_payload.json"] = {"study": case_id, "revision": 3, "active": True}
    for p, value in docs.items():
        files[p] = encoded(value)
    return seal_profile(files, profile)


def mutate_documents(files, mutate, profile):
    docs = json_documents(files)
    mutate(docs)
    result = dict(files)
    for p, value in docs.items():
        result[p] = encoded(value)
    return seal_profile(result, profile)


def seed_variant(files, workflow, variant, profile):
    def change(docs):
        claim = docs[RECORDS["claims"]]["claims"][0]
        edges = docs[RECORDS["edges"]]
        direct = claim["source_pointer"]
        if variant == "clean":
            return
        if variant in ("alias", "full_only", "chain", "conflict", "conflict_full_correct"):
            claim["source_pointer"] = "alias:primary"
            if variant == "alias":
                edges["aliases"] = {"primary": direct}
            elif variant == "full_only":
                edges["aliases"] = {"alias:primary": direct}
            elif variant == "chain":
                edges["aliases"] = {"primary": "alias:secondary", "secondary": direct}
            else:
                alternative = "/operands/display_codes/Fully ready" if workflow == "W1" else "/values/ratio"
                edges["aliases"] = {"primary": direct, "alias:primary": alternative}
                if variant == "conflict_full_correct":
                    edges["aliases"] = {"primary": alternative, "alias:primary": direct}
                edges["field_metadata"][alternative] = {"unit": "alternative", "denominator": 1, "scope": "different-quantity"}
        elif variant == "array":
            pointer = "/operands/rows/0/staff"
            claim.update(source_pointer=pointer, value=6, unit="persons", denominator=1, scope="first-retained-row")
            meta = {k: claim[k] for k in ("unit", "denominator", "scope")}
            for token in ("0", "00", "999"):
                edges["field_metadata"]["/operands/rows/" + token + "/staff"] = dict(meta)
        elif variant == "equal_metadata":
            edges["field_metadata"]["/operands/display_codes/Slightly ready"] = {
                "unit": "ordinal-code", "denominator": 5, "scope": "category-codebook"}
        else:
            raise InputError("UNKNOWN_SEED_VARIANT")
    return mutate_documents(files, change, profile)


def expected_vector(o15="S", **overrides):
    return {**ALL_S, "O15": o15, **overrides}


def policy_labels(sequence):
    return dict(zip(POLICIES, sequence))


def planned_specs(generation="P5"):
    """Literal known-answer expectations are fixed before native invocation."""
    specs = []
    for workflow in ("W1", "W2"):
        specs.extend([
            {"name": workflow + "-T01-order", "workflow": workflow, "seed": "clean", "operator": "T01",
             "parameters": {"order_independent": True}, "before": "S", "after": "S", "doc_before": "SSSSS", "doc_after": "SSSSS"},
            {"name": workflow + "-T02-rename", "workflow": workflow, "seed": "alias", "operator": "T02",
             "parameters": {"renames": {"primary": "renamed-Δ"}, "invariance_conventions": ["suffix_only", "either_unique"]},
             "before": "S", "after": "S", "doc_before": "VSSSS", "doc_after": "VSSSS"},
            {"name": workflow + "-T04-bare", "workflow": workflow, "seed": "full_only", "operator": "T04",
             "parameters": {}, "before": "V", "after": "S", "doc_before": "SVSSS", "doc_after": "VSSSS"},
            {"name": workflow + "-T05-repair", "workflow": workflow, "seed": "chain", "operator": "T05",
             "parameters": {"mode": "repair", "max_hops": 8}, "before": "V", "after": "S", "doc_before": "VVVVV", "doc_after": "VSSSS"},
            {"name": workflow + "-T08-permutation", "workflow": workflow, "seed": "clean", "operator": "T08",
             "parameters": {"permutation": [2, 0, 1], "eligibility_model": "NSC-CORE-ROW-LOCAL-1"},
             "before": "S", "after": "S", "doc_before": "SSSSS", "doc_after": "SSSSS"},
        ])
        for selection in ("min", "max"):
            good = (workflow == "W1" and selection == "max") or (workflow == "W2" and selection == "min")
            specs.append({"name": workflow + "-T03-" + selection, "workflow": workflow, "seed": "conflict", "operator": "T03",
                          "parameters": {"selection": selection, "relation_mode": "contrast"},
                          "before": "S", "after": "V", "doc_before": "VSVVS", "doc_after": "SVSSS" if good else "VVVVV"})
    for token in ("00", "999"):
        specs.append({"name": "W2-T06-array-" + token, "workflow": "W2", "seed": "array", "operator": "T06",
                      "parameters": {"target_pointer": "/operands/rows/" + token + "/staff"},
                      "before": "S", "after": "V", "doc_before": "SSSSS", "doc_after": "VVVVV"})
    specs.append({"name": "W1-T07-metadata", "workflow": "W1", "seed": "equal_metadata", "operator": "T07",
                  "parameters": {"target_pointer": "/operands/display_codes/Slightly ready", "comparison_convention": "suffix_only"},
                  "before": "S", "after": "V", "doc_before": "SSSSS", "doc_after": "VVVVV"})
    # Both orientations are needed: each native grammar can agree on S while
    # either_unique rejects conflicting targets. This is a conditional reference
    # disagreement, not an assertion that the native grammar is defective.
    for workflow in ("W1", "W2"):
        for selection in ("min", "max"):
            good = (workflow == "W1" and selection == "max") or (workflow == "W2" and selection == "min")
            specs.append({"name": workflow + "-T03-full-correct-" + selection, "workflow": workflow,
                          "seed": "conflict_full_correct", "operator": "T03",
                          "parameters": {"selection": selection, "relation_mode": "contrast"},
                          "before": "V", "after": "V", "doc_before": "SVVSV",
                          "doc_after": "SVSSS" if good else "VVVVV"})
    # These are fixed answers declared by case construction, before evaluation.
    # The P4 column applies only to this corpus (explicit alias: tokens and
    # canonical ASCII pointer probes), not to every accepted P4 source token.
    if generation == "P4":
        for spec in specs:
            if spec["operator"] == "T02":
                spec["seed"] = "full_only"
                spec["parameters"]["invariance_conventions"] = ["literal_only", "either_unique"]
                spec["doc_before"] = spec["doc_after"] = "SVSSS"
            spec["before"], spec["after"] = spec["doc_before"][0], spec["doc_after"][0]
    return specs


def validate_native_report(report, case_id, invocation_id, arm):
    if type(report) is not dict or report.get("schema") != "nsc-p4-checker-report/2":
        raise InputError("INVALID_NATIVE_REPORT_SCHEMA")
    if (report.get("case_id"), report.get("invocation_id"), report.get("arm_id")) != (case_id, invocation_id, arm):
        raise InputError("NATIVE_REPORT_IDENTITY_MISMATCH")
    vector, coverage = report.get("obligation_vector"), report.get("coverage_mask")
    if (type(vector) is not dict or set(vector) != set(ALL_S)
            or any(v not in ("S", "V", "U") for v in vector.values())
            or type(coverage) is not dict or set(coverage) != set(ALL_S)
            or any(type(v) is not bool or not v for v in coverage.values())):
        raise InputError("INVALID_NATIVE_VECTOR_OR_COVERAGE")
    aggregate = "REJECT" if "V" in vector.values() else "INDETERMINATE" if "U" in vector.values() else "ALLOW_WITHIN_SCOPE"
    if report.get("aggregate") != aggregate or type(report.get("diagnostics")) is not list:
        raise InputError("INVALID_NATIVE_AGGREGATION")


def invoke(repository, out, context, case, arm, counter, *, timeout=5.0):
    checker = context["checker_paths"][arm]
    profile = context["profile_path"]
    invocation_id = case["case_id"] + "__" + arm + "__" + str(counter).zfill(4)
    attempt = out / "attempts" / invocation_id
    attempt.mkdir(parents=True, exist_ok=False)
    output = attempt / "checker_report.json"
    input_dir = out / case["input_path"]
    input_before = binding(read_tree(input_dir))
    command = [sys.executable, "-I", "-B", str(checker), "--case-bundle", str(input_dir),
               "--profile", str(profile), "--case-id", case["case_id"],
               "--invocation-id", invocation_id, "--arm-id", case.get("arm_override", arm), "--output", str(output)]
    started = utc()
    clock = time.monotonic()
    operational = None
    try:
        process = subprocess.run(command, cwd=repository, capture_output=True, timeout=timeout, check=False)
        code, stdout, stderr = process.returncode, process.stdout, process.stderr
    except subprocess.TimeoutExpired as exc:
        code, stdout, stderr = None, exc.stdout or b"", exc.stderr or b""
        operational = "TIMEOUT"
    except OSError as exc:
        code, stdout, stderr = None, b"", (type(exc).__name__ + ":" + str(exc)).encode()
        operational = "PROCESS_START_ERROR"
    duration = time.monotonic() - clock
    (attempt / "stdout.bin").write_bytes(stdout)
    (attempt / "stderr.bin").write_bytes(stderr)
    report = None
    report_validation_error = None
    if operational is None and code == 0:
        try:
            report = parse(output.read_bytes(), "checker_report.json")
            validate_native_report(report, case["case_id"], invocation_id, arm)
            operational = "COMPLETED"
        except (OSError, InputError) as exc:
            operational = "INVALID_OR_MISSING_REPORT"
            report = None
            report_validation_error = {"type": type(exc).__name__, "message": str(exc)}
    elif operational is None:
        operational = "EXECUTION_ERROR"
    unchanged = binding(read_tree(input_dir)) == input_before
    instruments_unchanged = (sha256(checker.read_bytes()) == context["checker_hashes"][arm]
                             and sha256(profile.read_bytes()) == context["profile_sha256"])
    if case.get("expected_exit", 0) == 2:
        passed = code == 2 and not output.exists() and unchanged and instruments_unchanged
    else:
        passed = (operational == "COMPLETED" and unchanged and instruments_unchanged
                  and report["obligation_vector"] == case["expected_vector"])
    receipt = {"schema": "nsc-r5-f3-native-invocation/1", "case_id": case["case_id"], "invocation_id": invocation_id,
               "arm_id": arm, "generation": context["generation"],
               "checker_profile_scope": "Unchanged native " + context["generation"] + " checker on a new synthetic F3 dossier; not a historical replay.",
               "command": command, "cwd": str(repository), "started_utc": started, "finished_utc": utc(),
               "duration_seconds": duration, "exit_code": code, "execution_status": operational,
               "input_binding": input_before, "input_unchanged": unchanged, "instruments_unchanged": instruments_unchanged,
               "profile_path": profile.relative_to(repository).as_posix(), "profile_sha256": context["profile_sha256"],
               "checker_path": checker.relative_to(repository).as_posix(), "checker_sha256": context["checker_hashes"][arm],
               "stdout_path": "stdout.bin", "stderr_path": "stderr.bin", "stdout": stdout.decode("utf-8", errors="replace"),
               "stderr": stderr.decode("utf-8", errors="replace"), "expected_exit": case.get("expected_exit", 0),
               "expected_vector": case.get("expected_vector"), "observed_vector": report.get("obligation_vector") if report else None,
               "observed_aggregate": report.get("aggregate") if report else None,
               "report_validation_error": report_validation_error,
               "semantic_verdict_assigned": report is not None, "expectation_met": bool(passed)}
    if output.exists():
        receipt["report_sha256"] = sha256(output.read_bytes())
    write_new_json(attempt / "RECEIPT.json", receipt)
    return {"case_id": case["case_id"], "arm": arm, "invocation_id": invocation_id,
            "receipt_path": str((attempt / "RECEIPT.json").relative_to(out)),
            "execution_status": operational, "exit_code": code, "expectation_met": bool(passed),
            "generation": context["generation"], "expected_vector": case.get("expected_vector"),
            "observed_vector": report["obligation_vector"] if report else None,
            "aggregate": report["aggregate"] if report else None,
            "O15": report["obligation_vector"]["O15"] if report else None,
            "duration_seconds": duration}


def native_suite(repository, output, *, generation="P5", timeout=5.0):
    repository, out = Path(repository).resolve(), Path(output).resolve()
    if not 0 < timeout <= 60:
        raise InputError("native timeout must be in (0,60]")
    if out.exists() or out.is_symlink():
        raise InputError("NATIVE_OUTPUT_MUST_BE_NEW")
    context = native_context(repository, generation)
    profile_path = context["profile_path"]
    profile = parse(profile_path.read_bytes(), "FIXED_PROFILE.json")
    if validate_fixed_profile(profile) != generation:
        raise InputError("PROFILE_GENERATION_MISMATCH")
    out.mkdir(parents=True, exist_ok=False)
    run_id = "R5F3O15-" + generation + "-" + uuid.uuid4().hex[:12].upper()
    for source in sorted(Path(__file__).parent.glob("*.py")):
        target = out / "source_snapshot/o15_diagnostics" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    code_binding = binding({p.name: p.read_bytes() for p in sorted(Path(__file__).parent.glob("*.py"))})
    cases, transforms, documentary_checks = [], [], []

    def add_case(name, files, vector, *, expected_exit=0, arm_override=None):
        case_id = run_id + "-" + name
        relative = "dossiers/" + name
        write_new_tree(out / relative, files)
        item = {"case_id": case_id, "input_path": relative, "input_binding": binding(files),
                "expected_exit": expected_exit, "expected_vector": vector}
        if arm_override:
            item["arm_override"] = arm_override
        cases.append(item)
        return item

    # Original complete controls are first in the invocation order.
    for w in ("W1", "W2"):
        files = fresh_seed(repository, w, run_id + "-" + w + "-CONTROL", profile)
        add_case(w + "-CONTROL", files, expected_vector())
    for spec in planned_specs(generation):
        files = fresh_seed(repository, spec["workflow"], run_id + "-" + spec["name"], profile)
        files = seed_variant(files, spec["workflow"], spec["seed"], profile)
        params = copy.deepcopy(spec["parameters"])
        if spec["operator"] in ("T06", "T07"):
            params["claim_id"] = json_documents(files)[RECORDS["claims"]]["claims"][0]["claim_id"]
        altered, report = transform(files, run_id + "-" + spec["name"], spec["operator"], params, profile=profile)
        report_path = "transforms/" + spec["name"] + ".json"
        write_new_json(out / report_path, report)
        check = {"case": spec["name"], "operator": spec["operator"], "expected_before": policy_labels(spec["doc_before"]),
                 "expected_after": policy_labels(spec["doc_after"]), "transform_status": report["status"]}
        if altered is None:
            check["passed"] = False
        else:
            observed_before = {p: v["verdict"] for p, v in report["reference_before"]["policies"].items()}
            observed_after = {p: v["verdict"] for p, v in report["reference_after"]["policies"].items()}
            check.update(observed_before=observed_before, observed_after=observed_after,
                         passed=observed_before == check["expected_before"] and observed_after == check["expected_after"])
            before_case = add_case(spec["name"] + "-before", files, expected_vector(spec["before"]))
            after_case = add_case(spec["name"] + "-after", altered, expected_vector(spec["after"]))
        documentary_checks.append(check)
        native_invariance = (spec["operator"] in ("T01", "T08")
                             or context["comparison_convention"] in report.get("asserted_invariance_conventions", []))
        transforms.append({"name": spec["name"], "operator": spec["operator"], "report_path": report_path,
                           "before_case_id": before_case["case_id"] if altered is not None else None,
                           "after_case_id": after_case["case_id"] if altered is not None else None,
                           "native_full_vector_invariance_asserted": native_invariance,
                           "interpretation": report["relation_type"]})

    # Deliberately invalid inputs are controls, never successful metamorphic runs.
    base = fresh_seed(repository, "W1", run_id + "-CONTROL-INVALID", profile)
    stale = dict(base)
    stale["records/R02_aux.txt"] += b"\nFresh F3 stale-inventory control.\n"
    _, precondition = transform(stale, run_id + "-STALE", "T01", {"order_independent": True}, profile=profile)
    write_new_json(out / "controls/T01_stale_inventory.json", precondition)
    add_case("CONTROL-stale-inventory", stale, expected_vector(O02="V"))
    duplicate = dict(base)
    raw_claims = parse(base[RECORDS["claims"]])["claims"]
    raw = canonical(raw_claims)
    duplicate[RECORDS["claims"]] = b'{"claims":' + raw + b',"claims":' + raw + b'}\n'
    duplicate["inventory.json"] = encoded({"members": [{"path": p, "bytes": len(b), "sha256": sha256(b)}
                                                       for p, b in sorted(duplicate.items()) if p != "inventory.json"]})
    write_new_json(out / "controls/duplicate_reference.json", evaluate_files(duplicate, run_id + "-DUPLICATE"))
    add_case("CONTROL-duplicate-claims", duplicate, expected_vector("U", O01="V"))
    add_case("CONTROL-invalid-arm", base, None, expected_exit=2, arm_override="F3_INVALID_ARM")

    plan = {"schema": "nsc-r5-f3-o15-native-plan/1", "run_id": run_id, "locked_utc": utc(),
            "scope": "New synthetic " + generation + " fixture qualification; documentary five-convention evaluation remains separate.",
            "generation": generation, "native_profile_id": profile["profile_id"],
            "native_comparison_convention": context["comparison_convention"],
            "native_comparison_scope": context["comparison_scope"],
            "profile_sha256": sha256(profile_path.read_bytes()), "component_source_binding": code_binding,
            "expected_transformations": planned_specs(generation), "cases": cases, "transforms": transforms,
            "documentary_known_answer_checks": documentary_checks,
            "precondition_control_expected": "T01 stale inventory returns PRECONDITION_FAILED",
            "historical_results_mutated": False, "statistical_or_causal_claim": False}
    write_new_json(out / "PLAN.json", plan)
    plan_sha = sha256((out / "PLAN.json").read_bytes())
    write_new_json(out / "ENVIRONMENT.json", {"python": sys.version, "executable": sys.executable,
                                              "platform": platform.platform(), "plan_sha256": plan_sha,
                                              "generation": generation, "profile_sha256": context["profile_sha256"],
                                              "checker_hashes": context["checker_hashes"]})
    runs = []
    for case in cases:
        for arm in ARMS:
            runs.append(invoke(repository, out, context, case, arm, len(runs) + 1, timeout=timeout))
    run_map = {(r["case_id"], r["arm"]): r for r in runs}
    pair_results = []
    for item in transforms:
        for arm in ARMS:
            before_run = run_map.get((item["before_case_id"], arm))
            after_run = run_map.get((item["after_case_id"], arm))
            bv = before_run["observed_vector"] if before_run else None
            av = after_run["observed_vector"] if after_run else None
            changed = [o for o in ALL_S if bv[o] != av[o]] if bv is not None and av is not None else None
            required = item["native_full_vector_invariance_asserted"]
            pair_results.append({"name": item["name"], "operator": item["operator"], "generation": generation,
                                 "arm": arm, "before_vector": bv, "after_vector": av,
                                 "before_aggregate": before_run["aggregate"] if before_run else None,
                                 "after_aggregate": after_run["aggregate"] if after_run else None,
                                 "changed_obligations": changed,
                                 "nonfocal_changed_obligations": [o for o in changed if o != "O15"] if changed is not None else None,
                                 "full_vector_invariance_asserted": required,
                                 "relation_status": ("EXECUTION_INCOMPLETE" if changed is None else
                                                     ("HOLDS" if not changed else "VIOLATED") if required else
                                                     "OBSERVED_CONTRAST_OR_UNASSERTED_RELATION"),
                                 "interpretation": item["interpretation"]})
    write_new_json(out / "NATIVE_RELATIONS.json", {"schema": "nsc-r5-f3-native-relations/1", "generation": generation,
                                                 "scope": "Complete O01–O16 vectors, with every nonfocal change retained.",
                                                 "pairs": pair_results})
    shared = []
    for case in cases:
        arm_runs = {a: run_map[(case["case_id"], a)] for a in ARMS}
        if not all(r["execution_status"] == "COMPLETED" for r in arm_runs.values()):
            continue
        # Input/admission negative controls do not enter this semantic comparison.
        if "/CONTROL-" in case["input_path"]:
            continue
        ref = evaluate_files(read_tree(out / case["input_path"]), case["case_id"])
        if ref["status"] != "COMPLETED":
            continue
        labels = {a: arm_runs[a]["O15"] for a in ARMS}
        agree = labels["T_FULL"] == labels["B_ASSERT"]
        shared.append({"case_id": case["case_id"], "native_O15": labels, "native_agreement": agree,
                       "documentary_reference": {p: r["verdict"] for p, r in ref["policies"].items()},
                       "shared_disagreement_by_convention": {
                           p: agree and labels["T_FULL"] != r["verdict"] for p, r in ref["policies"].items()}})
    write_new_json(out / "SHARED_REFERENCE_DISAGREEMENTS.json", {
        "schema": "nsc-r5-f3-conditional-reference-comparison/1", "generation": generation,
        "interpretation": "A mismatch is conditional on the named reference convention. No convention is made ground truth by agreement or by this corpus.",
        "scope": "Synthetic fixture instances with both native reports; invalid-input controls excluded. Not a sample-based rate or a new prospective estimate.",
        "cases": shared})
    passed = (all(r["expectation_met"] for r in runs) and all(c["passed"] for c in documentary_checks)
              and precondition["status"] == "PRECONDITION_FAILED"
              and all(p["relation_status"] not in ("EXECUTION_INCOMPLETE", "VIOLATED") for p in pair_results))
    result = {"schema": "nsc-r5-f3-o15-native-results/1", "status": "PASS" if passed else "FAIL",
              "run_id": run_id, "plan_sha256": plan_sha, "completed_utc": utc(),
              "generation": generation, "profile_id": profile["profile_id"], "candidate_invocations": len(runs),
              "semantic_reports": sum(r["execution_status"] == "COMPLETED" for r in runs),
              "controlled_execution_errors": sum(r["execution_status"] == "EXECUTION_ERROR" and r["expectation_met"] for r in runs),
              "expectations_met": sum(r["expectation_met"] for r in runs),
              "documentary_checks_passed": sum(c["passed"] for c in documentary_checks),
              "documentary_checks_total": len(documentary_checks), "transformations": transforms,
              "native_full_vector_relation_checks": sum(p["full_vector_invariance_asserted"] for p in pair_results),
              "nonfocal_changes": [p for p in pair_results if p["nonfocal_changed_obligations"]],
              "native_relations_path": "NATIVE_RELATIONS.json", "runs": runs,
              "conditional_reference_comparisons_path": "SHARED_REFERENCE_DISAGREEMENTS.json",
              "limits": ["Native results concern unchanged " + generation + " on fresh F3 dossiers, not a replay of historical case IDs.",
                         context["comparison_scope"],
                         "All fixtures are synthetic; no field evaluation or causal inference is claimed.",
                         "T03/T04/T06/T07 are contrasts or convention-conditioned changes; T05 is repair, not single-hop invariance.",
                         "T08 concerns only the implemented row-local membership model and order-independent result targets.",
                         "No historical oracle, checker report or FAIL_CLOSED custody outcome is replaced."]}
    write_new_json(out / "SUMMARY.json", result)
    return result
