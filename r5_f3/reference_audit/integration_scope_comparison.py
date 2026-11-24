"""E05: global/contextwise engine results and a separate casewise-product comparator.

The casewise comparator is not an engine execution on 5**192 joint assignments.
It calculates k=0 extrema of the complete local prediction product directly.
"""

from copy import deepcopy
from itertools import product

from .build_examples import canonical_request, observation
from .canonical import digest
from .canonical_query import POLICIES, canonical_rows
from .engine import audit
from .provenance import code_identity


def run():
    rows = canonical_rows()
    contexts = sorted({row["context"] for row in rows})
    if len(contexts) != 4:
        raise AssertionError("The verified context domain differs")
    conflict = next(row["case_id"] for row in rows if row["probe"] == "dual_alias_conflict")
    results = {}
    for label in ("S", "V"):
        observed = [observation(conflict, label, "scope-comparison-" + label,
                                "Explicit stipulated canonical conflict-query branch for scope comparison")]
        global_request = canonical_request(0, False, observed)
        global_report = audit(global_request)
        context_request = deepcopy(global_request)
        context_request["model_scope"]["kind"] = "contextwise"
        centres, direct_scores = [], []
        for chosen in product(POLICIES, repeat=len(contexts)):
            mapping = dict(zip(contexts, chosen))
            assignment = {row["case_id"]: mapping[row["context"]] for row in rows}
            centre_id = "ctx-" + "-".join(str(POLICIES.index(name)) for name in chosen)
            centres.append({"centre_id": centre_id, "convention_by_case": assignment})
            # Separate raw-row enumeration: no optimiser or model helper calls.
            vector = {row["case_id"]: row[mapping[row["context"]]] for row in rows}
            if vector[conflict] == label:
                direct_scores.append(sum(vector[row["case_id"]] != row["archived_paired_o15_agreement"] for row in rows))
        context_request["matrix"]["payload"]["centres"] = centres
        context_request["matrix"]["sha256"] = digest(context_request["matrix"]["payload"])
        context_report = audit(context_request)
        enumerated = {"lower": str(min(direct_scores)), "upper": str(max(direct_scores))}
        if context_report["interval"] != enumerated or len(centres) != 625:
            raise AssertionError("Explicit complete context model does not match raw enumeration")
        local_sets = {row["case_id"]: {row[p] for p in POLICIES} for row in rows}
        local_sets[conflict] &= {label}
        if any(not values for values in local_sets.values()):
            raise AssertionError("Unexpected empty local product")
        casewise = {
            "lower": str(sum(min(value != row["archived_paired_o15_agreement"] for value in local_sets[row["case_id"]]) for row in rows)),
            "upper": str(sum(max(value != row["archived_paired_o15_agreement"] for value in local_sets[row["case_id"]]) for row in rows))
        }
        expected = {"S": ((0, 16), (0, 40), (0, 47)), "V": ((32, 48), (8, 48), (1, 48))}[label]
        actual = (global_report["interval"], context_report["interval"], casewise)
        if tuple(tuple(int(value[key]) for key in ("lower", "upper")) for value in actual) != expected:
            raise AssertionError("E05 comparison differs from the retained F2 values")
        results[label] = {
            "global_engine": {"interval": actual[0], "joint_centres": 5, "request_sha256": digest(global_request), "report_sha256": global_report["report_sha256"]},
            "contextwise_engine": {"interval": actual[1], "joint_centres": 625, "enumeration_complete_by_construction": True,
                                    "matches_independent_raw_enumeration": True, "request_sha256": digest(context_request), "report_sha256": context_report["report_sha256"]},
            "casewise_product_comparator": {"interval": actual[2], "engine_invoked_on_full_product": False,
                                            "method": "Separate k=0 sum of coordinate extrema on the full local prediction product"}}
    result = {"status": "PASS", "integration_case": "E05", "budget": 0, "conflict_query_case_id": conflict,
              "contexts": contexts, "branches": results, "producer": code_identity(),
              "scope": "Declared prediction union; global and complete contextwise models use the engine; the complete casewise model uses a separate analytical product comparator",
              "original_checker_invocations": 0}
    result["result_sha256"] = digest(result)
    return result
