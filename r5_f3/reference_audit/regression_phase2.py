"""Execute the retained documentary evaluator, not either native checker."""

import importlib.util
import sys

from .build_examples import canonical_request, observation
from .canonical import digest, file_digest, load_file
from .canonical_query import POLICIES, canonical_rows
from .engine import audit
from .provenance import HERE, code_identity
from .verification import verify_report

REFERENCE_SHA = "f17a9411ca5398e4834fb5212b948aecc793414f2929a273f521900c3995a9d6"
DECISION_SHA = "3b242e611f9fa1d0fb12e8872675d1962a8aea1cac97b5d5b1843de5d334ae4e"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run():
    fixture = HERE / "fixtures/phase2_reference"
    reference_path, decision_path = fixture / "o15_reference.py", fixture / "decision_audit.py"
    if file_digest(reference_path) != REFERENCE_SHA or file_digest(decision_path) != DECISION_SHA:
        raise AssertionError("The retained documentary evaluator identity differs")
    reference = _load("nsc_retained_o15_reference", reference_path)
    previous = sys.modules.get("o15_reference")
    sys.modules["o15_reference"] = reference
    try:
        phase2 = _load("nsc_retained_phase2_decision", decision_path)
    finally:
        if previous is None:
            del sys.modules["o15_reference"]
        else:
            sys.modules["o15_reference"] = previous
    retained = load_file(HERE / "inputs/PHASE2_RESULT.json")
    probe_results = {}
    docket_files = {}
    for path in sorted((fixture / "dockets").iterdir()):
        trace = phase2.evaluate(path)
        actual = {p: trace[p]["expected"] for p in POLICIES}
        if actual != retained["new_probes"]["labels"][path.name]:
            raise AssertionError("Documentary probe-label regression: " + path.name)
        probe_results[path.name] = actual
        for source in sorted(path.rglob("*.json")):
            docket_files[str(source.relative_to(HERE))] = file_digest(source)
    if set(probe_results) != set(retained["new_probes"]["labels"]):
        raise AssertionError("The original probe domain is not covered exactly")
    rows = canonical_rows()
    labels = {p: {row["case_id"]: row[p] for row in rows} for p in POLICIES}
    counts = {p: sum(row[p] != row["archived_paired_o15_agreement"] for row in rows) for p in POLICIES}
    for case_id, values in probe_results.items():
        for p in POLICIES:
            labels[p][case_id] = values[p]
    transcripts = {name: value["observations"] for name, value in retained["transcripts"].items()}
    transcripts["empty_transcript"] = {}
    conflict = next(row["case_id"] for row in rows if row["probe"] == "dual_alias_conflict")
    transcripts["single_conflict_S"] = {conflict: "S"}
    transcripts["single_conflict_V"] = {conflict: "V"}
    comparisons = {}
    for name, observed in transcripts.items():
        expected = phase2.decision(labels, counts, observed, 24)
        observations = [observation(cid, value, "regression-" + name + "-" + cid,
                                    "Retained or explicitly stipulated k=0 regression transcript") for cid, value in observed.items()]
        request = canonical_request(0, False, observations, include_probes=True)
        report = audit(request)
        actual = {"status": report["status"], "retained_policies": report["feasible_centres"],
                  "attainable_counts": sorted({counts[p] for p in report["feasible_centres"]}),
                  "interval": [int(report["interval"][x]) for x in ("lower", "upper")] if report["interval"] else None}
        if actual != expected:
            raise AssertionError("Phase2 k=0 decision regression: " + name)
        if name in retained["transcripts"] and expected != retained["transcripts"][name]["global"]:
            raise AssertionError("Retained original transcript changed: " + name)
        receipt = verify_report(request, report)
        comparisons[name] = {"phase2": expected, "reference_audit": actual,
                             "request_sha256": digest(request), "report_sha256": report["report_sha256"],
                             "verification_sha256": receipt["verification_sha256"], "match": True}
    result = {"status": "PASS", "scope": "Actual retained phase2 documentary evaluator and k=0 regression; no original checker execution",
              "documentary_evaluator_sha256": {"o15_reference.py": REFERENCE_SHA, "decision_audit.py": DECISION_SHA},
              "fixture_file_sha256": docket_files, "producer": code_identity(),
              "probe_labels": probe_results, "transcripts": comparisons,
              "original_checker_invocations": 0, "prospective_experiments": 0}
    result["result_sha256"] = digest(result)
    return result
