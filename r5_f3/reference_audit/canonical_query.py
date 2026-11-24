"""Closed-form query certificates only for the verified canonical frame."""

import csv
from itertools import combinations

from .canonical import digest, file_digest
from .model import rational_text, validate_request
from .provenance import HERE, code_identity

FRAME_ID = "NSC_PROS_v1.O15.192"
CONVENTION_VERSION = "R4-phase2-3b242e611f9f"
POLICIES = ("literal_only", "suffix_only", "either_unique", "prefer_literal", "prefer_suffix")
MATRIX_SHA256 = "88b288110ef278626498d34e1163b0423ec6983f427a1af5d0220134d0aacc27"


def canonical_rows():
    path = HERE / "inputs/o15_archived_reference_matrix_192.csv"
    if file_digest(path) != MATRIX_SHA256:
        raise RuntimeError("Installed canonical CSV fails its recorded SHA-256 binding")
    with path.open(encoding="utf-8", newline="") as stream:
        return sorted(csv.DictReader(stream), key=lambda row: row["case_id"])


def _scope_reasons(model, rows):
    reasons = []
    by_id = {row["case_id"]: row for row in rows}
    if model.frame_id != FRAME_ID:
        reasons.append("UNVERIFIED_FRAME_ID")
    if model.model_scope != "global":
        reasons.append("GLOBAL_SCOPE_REQUIRED")
    if model.threshold != 24:
        reasons.append("THRESHOLD_MUST_EQUAL_24")
    if not 0 <= model.budget <= 8:
        reasons.append("ONLY_BUDGETS_0_TO_8_VERIFIED")
    if model.observations:
        reasons.append("FIXED_QUERY_MINIMUM_STARTS_WITH_NO_OBSERVATIONS")
    if len(model.cases) != 192 or {c.case_id for c in model.cases} != set(by_id):
        reasons.append("CASE_IDENTITIES_DIFFER_FROM_CANONICAL_192")
    else:
        for case in model.cases:
            row = by_id[case.case_id]
            if case.role != "frame" or case.weight != 1 or not case.exception_eligible:
                reasons.append("UNIT_WEIGHT_ELIGIBLE_FRAME_COORDINATES_REQUIRED")
            if case.context_id != row["context"] or case.t != row["archived_paired_o15_agreement"] or case.b != case.t:
                reasons.append("CASE_METADATA_OR_CHECKER_LABELS_DIFFER")
        restricted = all(set(c.allowed) == {by_id[c.case_id][p] for p in POLICIES} for c in model.cases)
        broad = all(set(c.allowed) == {"S", "V", "U"} for c in model.cases)
        if not (restricted or broad):
            reasons.append("ADMISSIBILITY_IS_NOT_ONE_OF_THE_TWO_VERIFIED_CHOICES")
    conventions = {item["convention_id"]: item for item in model.conventions}
    if set(conventions) != set(POLICIES):
        reasons.append("FIVE_CANONICAL_CONVENTIONS_REQUIRED")
    elif {c.case_id for c in model.cases} == set(by_id):
        for name, convention in conventions.items():
            if convention["version"] != CONVENTION_VERSION or any(convention["predictions"][cid] != row[name] for cid, row in by_id.items()):
                reasons.append("CONVENTION_VERSION_OR_PREDICTIONS_DIFFER")
    if len(model.centres) != 5 or {c.centre_id for c in model.centres} != set(POLICIES):
        reasons.append("FIVE_CANONICAL_GLOBAL_CENTRES_REQUIRED")
    else:
        for centre in model.centres:
            if set(centre.assignment) != {centre.centre_id}:
                reasons.append("CENTRE_ASSIGNMENT_DIFFERS_FROM_CANONICAL_GLOBAL_MODEL")
    return sorted(set(reasons))


def canonical_query_minimum(request):
    model = validate_request(request)
    rows = canonical_rows()
    reasons = _scope_reasons(model, rows)
    binding = {"schema": "nsc.reference-audit.query-certificate/1", "request_sha256": model.request_sha256,
               "matrix_sha256": model.matrix_sha256, "canonical_csv_sha256": MATRIX_SHA256,
               "frame_id": model.frame_id, "producer": code_identity(), "budget": model.budget,
               "threshold": rational_text(model.threshold), "original_checker_invocations": 0}
    if reasons:
        report = {**binding, "status": "NOT_APPLICABLE", "reasons": reasons,
                  "minimum_query_count": None, "case_ids": None,
                  "scope": "No general query optimiser or extrapolation is supplied."}
        report["certificate_sha256"] = digest(report)
        return report
    groups = {name: [row for row in rows if row["probe"] == name]
              for name in ("suffix_alias_clean", "dual_alias_conflict", "exact_alias_clean")}
    A, B, C = (groups[name] for name in ("suffix_alias_clean", "dual_alias_conflict", "exact_alias_clean"))
    counts = {p: sum(row[p] != row["archived_paired_o15_agreement"] for row in rows) for p in POLICIES}
    opposing = [(g, h) for g, h in combinations(POLICIES, 2) if (counts[g] <= 24) != (counts[h] <= 24)]
    if list(map(len, (A, B, C))) != [16, 16, 16] or len(opposing) != 6:
        raise RuntimeError("Canonical structural certificate prerequisites failed")
    discrepancy_ids = [row["case_id"] for row in rows if row["either_unique"] != row["prefer_literal"]]
    if discrepancy_ids != [row["case_id"] for row in B]:
        raise RuntimeError("Canonical closest-pair structure differs")
    k = model.budget
    if k <= 7:
        selected = B[:2 * k + 1]
        distances = [{"centres": [g, h], "selected_distance": sum(row[g] != row[h] for row in selected)} for g, h in opposing]
        if any(item["selected_distance"] != 2 * k + 1 for item in distances):
            raise RuntimeError("Selected query set fails its distance certificate")
        proof = {"type": "STABLE_REGIONS_AND_CROSS_REGION_DISTANCE",
                 "centre_counts": counts, "opposing_pairs": distances,
                 "closest_pair": ["prefer_literal", "either_unique"],
                 "closest_pair_difference_ids": discrepancy_ids,
                 "lower_bound": "Any set of at most 2k coordinates permits a transcript within k of both members of the closest opposing pair.",
                 "region_stability": "Every reference within k <= 7 of a centre with count 0 or 16 stays at or below 24; every such reference around count 32 or 48 stays above 24.",
                 "necessary_conflict_queries": 2 * k + 1}
    else:
        E = sorted(A + B, key=lambda row: row["case_id"])
        selected = E + [C[0]]
        necessity = []
        for row in E:
            seven = [other["case_id"] for other in E if other["case_id"] != row["case_id"]][:7]
            necessity.append({"indispensable_case_id": row["case_id"], "centre_id": "either_unique",
                              "common_repairs": seven, "additional_repair": row["case_id"],
                              "counts": ["25", "24"], "distances": [7, 8]})
        proof = {"type": "THRESHOLD_BOUNDARY_32_PLUS_1", "centre_counts": counts,
                 "necessary_case_ids": [row["case_id"] for row in E], "necessity_witnesses": necessity,
                 "additional_case_id": C[0]["case_id"], "additional_stratum": "exact_alias_clean",
                 "obstruction_with_32_queries": {"centres": ["either_unique", "suffix_only"],
                     "common_repairs": [row["case_id"] for row in A[:8]], "counts": ["24", "40"], "distances": [8, 8]},
                 "sufficiency_rule": {"compatibility_check_required_first": True,
                     "errors_on_necessary_set_at_most23": "AT_OR_BELOW", "errors_on_necessary_set_at_least25": "ABOVE",
                     "errors_on_necessary_set_equal24": {"extra_label_matches_checker": "AT_OR_BELOW",
                         "extra_label_matches_suffix_only": "ABOVE", "extra_label_U": "OUT_OF_MODEL"}}}
    report = {**binding, "status": "VERIFIED_CANONICAL_MINIMUM", "minimum_query_count": len(selected),
              "case_ids": [row["case_id"] for row in selected], "proof": proof,
              "admissibility": "broad_S_V_U" if all(set(c.allowed) == {"S", "V", "U"} for c in model.cases) else "restricted_local_prediction_union",
              "scope": "Exact fixed-query minimum for every compatible transcript on this verified frame and budget. Not adaptive cost, human effort or a result for other frames."}
    report["certificate_sha256"] = digest(report)
    return report
