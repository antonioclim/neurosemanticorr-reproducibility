"""Build local examples from retained data, without running archived checkers."""

from copy import deepcopy
import json

from .canonical import CANONICALISATION, digest, display_json, file_digest, load_file
from .canonical_query import CONVENTION_VERSION, FRAME_ID, POLICIES, canonical_rows
from .model import SCHEMA, validate_request
from .provenance import HERE

RETAINED_RESULT_SHA256 = "259e8bd285373048e53fc5fedcfae0a221ffa310eb9e5b159843e7693363dbbb"


def observation(case_id, label, evidence_id, basis):
    payload = {"case_id": case_id, "label": label, "basis": basis}
    return {"case_id": case_id, "label": label,
            "evidence": {"evidence_id": evidence_id, "canonicalisation": CANONICALISATION,
                         "sha256": digest(payload), "payload": payload}}


def seal(payload, *, frame_id, observations=(), budget=0, threshold="24", scope="global"):
    request = {"schema": SCHEMA, "frame_id": frame_id,
               "matrix": {"canonicalisation": CANONICALISATION, "sha256": digest(payload), "payload": deepcopy(payload)},
               "model_scope": {"kind": scope, "enumeration": "explicit", "budget_scope": "shared_total"},
               "observations": deepcopy(list(observations)), "budget": budget, "threshold": threshold}
    validate_request(request)
    return request


def canonical_request(budget=0, broad=False, observations=(), include_probes=False, protect_probes=False):
    rows = canonical_rows()
    cases = [{"case_id": row["case_id"], "context_id": row["context"], "role": "frame",
              "checker_labels": {"t": row["archived_paired_o15_agreement"], "b": row["archived_paired_o15_agreement"]},
              "allowed_labels": ["S", "V", "U"] if broad else sorted({row[p] for p in POLICIES}),
              "weight": "1", "exception_eligible": True} for row in rows]
    predictions = {p: {row["case_id"]: row[p] for row in rows} for p in POLICIES}
    if include_probes:
        path = HERE / "inputs/PHASE2_RESULT.json"
        if file_digest(path) != RETAINED_RESULT_SHA256:
            raise RuntimeError("Retained probe-result identity differs")
        retained = load_file(path)
        for case_id, labels in sorted(retained["new_probes"]["labels"].items()):
            cases.append({"case_id": case_id, "context_id": "external-probes", "role": "external_query",
                          "checker_labels": {"t": None, "b": None}, "allowed_labels": ["S", "V", "U"],
                          "weight": "0", "exception_eligible": not protect_probes})
            for p in POLICIES:
                predictions[p][case_id] = labels[p]
    conventions = [{"convention_id": p, "version": CONVENTION_VERSION, "predictions": predictions[p]} for p in POLICIES]
    centres = [{"centre_id": p, "convention_by_case": {case["case_id"]: p for case in cases}} for p in POLICIES]
    return seal({"cases": cases, "conventions": conventions, "centres": centres},
                frame_id=FRAME_ID, observations=observations, budget=budget)


def toy_request(cases, predictions, *, observations=(), budget=0, threshold="0", scope="global", assignments=None):
    conventions = [{"convention_id": name, "version": "example-v1", "predictions": labels} for name, labels in predictions.items()]
    if assignments is None:
        assignments = {name: {case["case_id"]: name for case in cases} for name in predictions}
    centres = [{"centre_id": name, "convention_by_case": values} for name, values in assignments.items()]
    return seal({"cases": cases, "conventions": conventions, "centres": centres}, frame_id="constructed-example-v1",
                observations=observations, budget=budget, threshold=threshold, scope=scope)


def simple_case(case_id, *, allowed=("S", "V", "U"), t="S", b="S", weight="1", eligible=True, context="context-1", role="frame"):
    return {"case_id": case_id, "context_id": context, "role": role,
            "checker_labels": {"t": t, "b": b}, "allowed_labels": list(allowed),
            "weight": weight, "exception_eligible": eligible}


def build():
    examples = {}
    examples["canonical_restricted_k0"] = canonical_request()
    examples["canonical_broad_k7"] = canonical_request(7, True)
    examples["canonical_broad_k8"] = canonical_request(8, True)
    conflict = next(row["case_id"] for row in canonical_rows() if row["probe"] == "dual_alias_conflict")
    for label in ("S", "V"):
        obs = [observation(conflict, label, "stipulated-conflict-" + label, "Explicit stipulated branch of the canonical archived query; not a new human adjudication")]
        examples[f"single_conflict_{label}_broad_k1"] = canonical_request(1, True, obs)
        examples[f"single_conflict_{label}_broad_k0"] = canonical_request(0, True, obs)
        if label == "V":
            examples["single_conflict_V_restricted_k1"] = canonical_request(1, False, obs)
    obs = [observation("F2-MIRROR-SUFFIX", "S", "retained-mirror-S", "inputs/PHASE2_RESULT.json#transcripts/mirror_suffix_identifies_set; retained stipulated transcript")]
    examples["mirror_S_external_eligible_k1"] = canonical_request(1, False, obs, True, False)
    examples["mirror_S_external_protected_k1"] = canonical_request(1, False, obs, True, True)
    retained = load_file(HERE / "inputs/PHASE2_RESULT.json")
    for name, transcript in retained["transcripts"].items():
        obs = [observation(case_id, value, f"retained-{name}-{case_id}", f"inputs/PHASE2_RESULT.json#transcripts/{name}; retained stipulated transcript")
               for case_id, value in transcript["observations"].items()]
        examples["original_" + name] = canonical_request(0, False, obs, True)
    cases = [simple_case("weighted-mandatory", allowed=("V", "U"), weight="1/2"),
             simple_case("protected-disagreement", t="S", b="V", weight="2", eligible=False),
             simple_case("external-U", t=None, b=None, weight="0", role="external_query")]
    examples["weighted_protected_third_outcome"] = toy_request(cases,
        {"centre": {"weighted-mandatory": "S", "protected-disagreement": "V", "external-U": "S"}},
        budget=2, threshold="1/4", observations=[observation("external-U", "U", "external-U-evidence", "Constructed exact U observation for zero-weight budget accounting")])
    examples["valid_out_of_model"] = toy_request([simple_case("restricted", allowed=("V",))], {"centre": {"restricted": "S"}},
        budget=1, observations=[observation("restricted", "S", "outside-admissibility", "Constructed valid transcript incompatible with the declared local admissibility set")])
    cases = [simple_case(name, allowed=("S", "V"), context=context) for name, context in
             (("A1", "A"), ("A2", "A"), ("B1", "B"), ("B2", "B"))]
    predictions = {name: {case["case_id"]: label for case in cases} for name, label in (("all-S", "S"), ("all-V", "V"))}
    context_assignments = {"both-S": {case["case_id"]: "all-S" for case in cases},
                           "A-S-B-V": {case["case_id"]: "all-S" if case["context_id"] == "A" else "all-V" for case in cases}}
    examples["contextwise_explicit_subset"] = toy_request(cases, predictions, threshold="1", scope="contextwise", assignments=context_assignments)
    case_assignments = {"alternating-1": {case["case_id"]: "all-S" if i % 2 == 0 else "all-V" for i, case in enumerate(cases)},
                        "alternating-2": {case["case_id"]: "all-V" if i % 2 == 0 else "all-S" for i, case in enumerate(cases)}}
    examples["casewise_explicit_subset"] = toy_request(cases, predictions, threshold="1", scope="casewise", assignments=case_assignments)
    target = HERE / "examples"
    target.mkdir(exist_ok=True)
    identities = {}
    for name, request in examples.items():
        validate_request(request)
        path = target / (name + ".json")
        path.write_text(display_json(request), encoding="utf-8")
        identities[name] = {"request_sha256": digest(request), "file_sha256": file_digest(path)}
    expected = {
        "canonical_restricted_k0": {"status": "UNDETERMINED", "interval": {"lower": "0", "upper": "48"}},
        "single_conflict_S_broad_k1": {"status": "UNDETERMINED", "interval": {"lower": "0", "upper": "47"}},
        "single_conflict_V_broad_k1": {"status": "UNDETERMINED", "interval": {"lower": "1", "upper": "49"}},
        "single_conflict_V_restricted_k1": {"status": "UNDETERMINED", "interval": {"lower": "1", "upper": "48"}},
        "mirror_S_external_eligible_k1": {"status": "UNDETERMINED", "interval": {"lower": "0", "upper": "48"}, "first_at_or_below": 1},
        "mirror_S_external_protected_k1": {"status": "ABOVE", "interval": {"lower": "31", "upper": "48"}, "first_at_or_below": 8},
        "weighted_protected_third_outcome": {"status": "ABOVE", "interval": {"lower": "1/2", "upper": "1/2"}},
        "valid_out_of_model": {"status": "OUT_OF_MODEL", "interval": None},
        "canonical_query_minima": {"7": 15, "8": 33},
    }
    (target / "EXPECTED.json").write_text(display_json({"scope": "Independent retained F2 values and explicitly derived small examples; no original checker run", "expected": expected}), encoding="utf-8")
    (target / "EXAMPLE_IDENTITIES.json").write_text(display_json(identities), encoding="utf-8")
    return identities


if __name__ == "__main__":
    print(json.dumps({"examples_written": len(build())}, indent=2))
