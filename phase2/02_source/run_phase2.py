"""Run the locked local O15 reference and decision-audit evaluation."""

import argparse
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path

from decision_audit import POLICIES, compatible, decision, evaluate, minimum_witness
from o15_reference import RECORDS

ROOT = Path(__file__).resolve().parents[1]
ARCHIVED = {
    "reference/oracle.py": "3456bb19588780c09241da73ce124153571d5206d1871b2f66d3e7aaf22f96a0",
    "00_plan/O15_REFERENCE.json": "28f568cb904c2348bbaad4074b8bee01475d138054e494d1c8c9b34bfca2d96e",
    "evaluation/BLIND_SELECTION.json": "e900b01104a5f5731ebbf6a69d92e4791342cdfb8680bd6eb5f35fd4ea32d625",
    "frame_design/FRAME.json": "be763881b1a0d53f64f2b86c34d76ca3f98afcc5a90a562a0d7cc4205b600a75",
}
F1_COUNTS = dict(zip(POLICIES, (0, 48, 32, 16, 32)))
FIXTURE_LOCK_SHA256 = "e7cfb330ce396723ce5655b5d528b51fbac27aa2c8223f59eb262336c23ac5d9"
CEILING = 24


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def current_protocol_files():
    files = [ROOT / "00_protocol/PROTOCOL_EN_GB.md"]
    for subtree in ("01_fixtures", "02_source"):
        files.extend(path for path in (ROOT / subtree).rglob("*")
                     if path.is_file() and "__pycache__" not in path.parts)
    return {path.relative_to(ROOT).as_posix(): digest(path) for path in sorted(files)}


def verify_fixture_lock():
    fixtures = ROOT / "01_fixtures"
    path = fixtures / "FIXTURE_LOCK.json"
    if digest(path) != FIXTURE_LOCK_SHA256:
        raise ValueError("The independent fixture lock differs")
    stored = read(path)
    files = {item.relative_to(fixtures).as_posix(): item for item in fixtures.rglob("*")
             if item.is_file() and item != path and "__pycache__" not in item.parts}
    if set(files) != set(stored["files"]):
        raise ValueError("Fixture inventory differs")
    for name, record in stored["files"].items():
        if files[name].stat().st_size != record["nbytes"] or digest(files[name]) != record["sha256"]:
            raise ValueError(f"Independently frozen fixture differs: {name}")


def seal(path):
    fixture = ROOT / "01_fixtures/EXPECTED.json"
    if not fixture.is_file() or path.exists():
        raise ValueError("Sealing requires independent fixture predictions and a new output path")
    verify_fixture_lock()
    locked = {"schema": "neurosemanticorr-phase2-local-lock/1", "threshold_on_archived_frame": CEILING,
              "policy_order": list(POLICIES), "archived_file_sha256": ARCHIVED,
              "input_sha256": current_protocol_files()}
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(locked, indent=2, sort_keys=True) + "\n")


def verify_local_lock(path):
    lock = read(path)
    if (lock["archived_file_sha256"] != ARCHIVED or lock["policy_order"] != list(POLICIES)
            or lock["threshold_on_archived_frame"] != CEILING
            or lock["input_sha256"] != current_protocol_files()):
        raise ValueError("Phase 2 inputs differ from the pre-execution lock")


def reconstruct_frame(archive):
    for relative, expected in ARCHIVED.items():
        if digest(archive / relative) != expected:
            raise ValueError(f"Archived identity mismatch: {relative}")
    frame = {row["case_id"]: row for row in read(archive / "frame_design/FRAME.json")["cases"]}
    refs = {row["case_id"]: row for row in read(archive / "00_plan/O15_REFERENCE.json")["cases"]}
    outputs = read(archive / "evaluation/BLIND_SELECTION.json")["case_outputs"]
    if len(frame) != 192 or set(frame) != set(refs) or set(frame) != set(outputs):
        raise ValueError("Archived comparison frame differs")
    observed = {}
    labels = {policy: {} for policy in POLICIES}
    for case in sorted(frame):
        path = archive / "dockets" / case
        pair = outputs[case]["O15"]
        if not outputs[case]["comparable"] or len(pair) != 2 or pair[0] != pair[1]:
            raise ValueError(f"Case {case} was not a comparable agreement")
        if any(refs[case]["reference_evidence"][rel]["sha256"] != digest(path / rel)
               for rel in RECORDS.values()):
            raise ValueError(f"Archived documentary bytes differ for {case}")
        observed[case] = pair[0]
        values = evaluate(path)
        for policy in POLICIES:
            labels[policy][case] = values[policy]["expected"]
        if labels["either_unique"][case] != refs[case]["expected"]:
            raise ValueError(f"Archived reference label did not reproduce: {case}")
    counts = {p: sum(vector[c] != result for c, result in observed.items()) for p, vector in labels.items()}
    if counts != F1_COUNTS:
        raise ValueError(f"Five-policy replay does not reproduce Phase 1: {counts!r}")
    witness = minimum_witness(labels, counts, CEILING)
    possible = [c for c in sorted(frame) if {labels[p][c] for p in POLICIES if counts[p] <= CEILING}.isdisjoint(
                                           {labels[p][c] for p in POLICIES if counts[p] > CEILING})]
    if not possible or witness["case_ids"] != possible[:1]:
        raise ValueError("Exact witness minimisation did not match independent singleton enumeration")
    case = witness["case_ids"][0]
    branches = {label: decision(labels, counts, {case: label}, CEILING)
                for label in sorted(set(witness["case_labels"][case].values()))}
    equivalent = [list(pair) for pair in combinations(POLICIES, 2) if labels[pair[0]] == labels[pair[1]]]
    return labels, counts, {"archive_sha256": ARCHIVED, "frame_size": len(frame),
                            "label_replay": "192 sealed either_unique labels reproduced",
                            "document_hashes_verified": len(RECORDS) * len(frame),
                            "mismatch_counts": counts, "ceiling": CEILING,
                            "initial_decision": decision(labels, counts, {}, CEILING),
                            "minimum_witness": {**witness, "chosen_probe_family": frame[case]["probe"],
                                                "singletons_sufficient": len(possible)},
                            "possible_decisions_after_witness": branches,
                            "equivalent_policy_label_pairs_on_frame": equivalent}


def run(path, archive):
    verify_local_lock(path)
    verify_fixture_lock()
    spec = read(ROOT / "01_fixtures/EXPECTED.json")
    if spec["policy_order"] != list(POLICIES):
        raise ValueError("Fixture policy order differs")
    reports = {case: evaluate(ROOT / "01_fixtures/dockets" / case) for case in spec["cases"]}
    case_rows = {case: {policy: report["expected"] for policy, report in values.items()}
                 for case, values in reports.items()}
    failures = [{"case_id": case, "expected": row["expected"], "observed": case_rows[case]}
                for case, row in spec["cases"].items() if row["expected"] != case_rows[case]]
    archived_labels, counts, frame_report = reconstruct_frame(archive)
    observations_allowed = {policy: {**archived_labels[policy], **{case: row[policy]
                                                                  for case, row in case_rows.items()}}
                            for policy in POLICIES}
    if set(case_rows) & set(next(iter(archived_labels.values()))):
        raise ValueError("New fixtures must have identities separate from archived cases")
    transcript_reports = {}
    for transcript_id, expected in spec["transcripts"].items():
        evidence = expected["labels"]
        summary = decision(observations_allowed, counts, evidence, CEILING)
        separately = {case: list(compatible(observations_allowed, {case: label}))
                      for case, label in evidence.items()}
        local = expected.get("synthetic_local_policies", {})
        local_checks = {case: policy in separately[case] for case, policy in local.items()}
        classification = "out_of_model" if summary["status"] == "OUT_OF_MODEL" else "compatible"
        passed = (summary["retained_policies"] == expected["remaining_policies"]
                  and classification == expected["classification"]
                  and all(separately.values()) and all(local_checks.values()))
        if not passed:
            failures.append({"transcript_id": transcript_id, "expected": expected,
                             "observed": summary, "classification": classification})
        transcript_reports[transcript_id] = {"observations": evidence, "separately_compatible": separately,
                                              "synthetic_local_policy_checks": local_checks,
                                              "global": summary, "matches_frozen_expectation": passed,
                                              "count_scope": "archived 192 only, conditional on same global model"}
    verify_local_lock(path)
    result = {"status": "PASS_LOCAL_SCOPED_EVALUATION" if not failures else "FAIL_LOCAL_SCOPED_EVALUATION",
              "lock_sha256": digest(path), "archived_frame": frame_report,
              "new_probes": {"total_dossiers": len(reports), "policy_checks": len(POLICIES) * len(reports),
                             "labels": case_rows, "traces": reports},
              "transcripts": transcript_reports, "failures": failures,
              "archived_checkers_reexecuted": 0, "submission_status": "DO_NOT_SUBMIT"}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=ROOT / "00_protocol/PREEXECUTION_LOCK.json")
    parser.add_argument("--frozen-root", type=Path)
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    if args.seal:
        if args.frozen_root is not None:
            parser.error("sealing does not evaluate the frozen frame")
        seal(args.lock)
    else:
        if args.frozen_root is None:
            parser.error("evaluation requires --frozen-root")
        result = run(args.lock, args.frozen_root)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        raise SystemExit(0 if not result["failures"] else 1)
