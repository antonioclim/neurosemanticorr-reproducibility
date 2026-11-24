"""Independent exact-cost DP and direct witness checks.

This module does not call the endpoint optimiser or its profile/gain helpers.
It validates sharp bounds and first-region budgets by a separate recurrence.
"""

from fractions import Fraction

from .canonical import InputError, VerificationError, canonical_bytes, digest, loads
from .model import LABELS, rational, rational_text, validate_request
from .provenance import code_identity


def require(condition, message):
    if not condition:
        raise VerificationError(message)


def same(actual, expected, message):
    require(canonical_bytes(actual) == canonical_bytes(expected), message)


def _score(case, value):
    return case.weight if case.role == "frame" and case.t == case.b and value != case.t else Fraction(0)


def _exact_cost_states(model, centre):
    states = {0: (Fraction(0), Fraction(0))}
    for case, allowed, prediction in zip(model.cases, model.admissible, centre.labels):
        next_states = {}
        for cost, (low, high) in states.items():
            for value in allowed:
                if not case.exception_eligible and value != prediction:
                    continue
                new_cost = cost + int(case.exception_eligible and value != prediction)
                new_low, new_high = low + _score(case, value), high + _score(case, value)
                if new_cost in next_states:
                    old_low, old_high = next_states[new_cost]
                    new_low, new_high = min(old_low, new_low), max(old_high, new_high)
                next_states[new_cost] = (new_low, new_high)
        states = next_states
        if not states:
            break
    return states


def _direct_certificate(model, certificate, budget=None, score=None, purpose=None):
    expected_fields = {"purpose", "request_sha256", "matrix_sha256", "centre_id", "budget", "distance", "score", "labels", "changed_case_ids"}
    require(type(certificate) is dict and set(certificate) == expected_fields, "Certificate fields do not match the contract")
    require(certificate["request_sha256"] == model.request_sha256 and certificate["matrix_sha256"] == model.matrix_sha256,
            "Certificate is bound to a different request or matrix")
    if purpose is not None:
        require(certificate["purpose"] == purpose, "Certificate purpose differs")
    else:
        require(certificate["purpose"] in ("lower_endpoint", "upper_endpoint", "first_at_or_below", "first_above"), "Unknown certificate purpose")
    require(type(certificate["budget"]) is int and certificate["budget"] >= 0, "Certificate budget is not a nonnegative integer")
    if budget is not None:
        require(certificate["budget"] == budget, "Certificate budget differs")
    require(type(certificate["distance"]) is int and certificate["distance"] >= 0, "Certificate distance is not a nonnegative integer")
    centres = {centre.centre_id: centre for centre in model.centres}
    require(type(certificate["centre_id"]) is str and certificate["centre_id"] in centres, "Unknown witness centre")
    centre = centres[certificate["centre_id"]]
    labels = certificate["labels"]
    require(type(labels) is dict and set(labels) == {case.case_id for case in model.cases}, "Witness case IDs differ from the model")
    actual_score, changed = Fraction(0), []
    for case, allowed, prediction in zip(model.cases, model.admissible, centre.labels):
        value = labels[case.case_id]
        require(type(value) is str and value in LABELS, "Invalid witness label")
        require(value in allowed, "Witness violates local admissibility or an adjudicated label")
        if value != prediction:
            require(case.exception_eligible, "Witness changes a protected coordinate")
            changed.append(case.case_id)
        actual_score += _score(case, value)
    require(len(changed) <= certificate["budget"], "Witness exceeds its exception budget")
    same(certificate["changed_case_ids"], sorted(changed), "Changed-case identifiers are incorrect")
    require(certificate["distance"] == len(changed), "Witness distance is incorrect")
    try:
        supplied_score = rational(certificate["score"], "$.certificate.score")
    except InputError as error:
        raise VerificationError(str(error)) from error
    require(supplied_score == actual_score, "Witness score is incorrect")
    require(certificate["score"] == rational_text(actual_score), "Witness score is not in reduced output form")
    if score is not None:
        require(actual_score == score, "Witness does not attain the exact expected endpoint")
    return {"score": rational_text(actual_score), "distance": len(changed), "budget": certificate["budget"],
            "centre_id": centre.centre_id, "admissibility": True, "observations": True, "protections": True}


def verify_witness(request, certificate):
    """Verify an endpoint at the request budget or a minimal region-radius witness."""
    model = validate_request(request)
    try:
        certificate = loads(canonical_bytes(certificate))
    except InputError as error:
        raise VerificationError(str(error)) from error
    receipt = _direct_certificate(model, certificate)
    states = [_exact_cost_states(model, centre) for centre in model.centres]
    purpose = certificate["purpose"]
    value = Fraction(receipt["score"])
    if purpose in ("lower_endpoint", "upper_endpoint"):
        require(certificate["budget"] == model.budget, "Endpoint certificate must use the request budget")
        values = [bounds for items in states for cost, bounds in items.items() if cost <= model.budget]
        require(bool(values), "No endpoint exists at the request budget")
        expected = min(x[0] for x in values) if purpose == "lower_endpoint" else max(x[1] for x in values)
        require(value == expected, "Certificate does not attain the exact endpoint at the request budget")
        domain = "requested_budget_endpoint"
    else:
        lower_region = purpose == "first_at_or_below"
        costs = [cost for items in states for cost, bounds in items.items()
                 if (bounds[0] <= model.threshold if lower_region else bounds[1] > model.threshold)]
        require(bool(costs), "The claimed decision region is unattainable")
        require(certificate["budget"] == min(costs), "Region certificate does not use the first feasible budget")
        require(value <= model.threshold if lower_region else value > model.threshold, "Certificate lies in the wrong decision region")
        domain = "first_region_budget"
    return {"status": "VALID_WITNESS", "request_sha256": model.request_sha256, **receipt,
            "certificate_domain": domain, "sharpness_or_minimal_radius_verified": True,
            "scope": "Independent exact-cost DP plus direct admissibility, budget and score checks"}


def verify_report(request, report):
    model = validate_request(request)
    try:
        report = loads(canonical_bytes(report))
    except InputError as error:
        raise VerificationError(str(error)) from error
    expected_fields = {"schema", "status", "frame_id", "request_sha256", "matrix_sha256", "producer", "model_scope",
                       "score", "budget", "threshold", "interval", "interval_is_envelope", "feasible_centres", "centres",
                       "endpoint_certificates", "radii", "region_certificates", "nesting", "observation_evidence",
                       "evidence_scope", "execution_scope", "report_sha256"}
    require(type(report) is dict and set(report) == expected_fields, "Report fields do not match the contract")
    require(report["schema"] == "nsc.reference-audit.report/1", "Unsupported report schema")
    body = {key: value for key, value in report.items() if key != "report_sha256"}
    require(report["report_sha256"] == digest(body), "Report digest mismatch")
    require(report["request_sha256"] == model.request_sha256 and report["matrix_sha256"] == model.matrix_sha256,
            "Report input binding mismatch")
    require(report["frame_id"] == model.frame_id, "Report frame ID differs")
    same(report["producer"], code_identity(), "Producer code identity differs from this installed component")
    same(report["model_scope"], {**model.raw["model_scope"], "joint_centres_supplied": len(model.centres),
                                "complete_cartesian_product_certified": False}, "Report scope differs")
    same(report["budget"], model.budget, "Report budget differs")
    require(report["threshold"] == rational_text(model.threshold), "Report threshold differs")
    require(report["score"] == "weighted_identical_output_shared_error_on_frame_only", "Unknown score")
    require(report["interval_is_envelope"] is True, "Interval envelope qualification is absent")
    centre_records, at_budget = [], []
    all_fit, first_low, first_high = [], [], []
    total_dp_states = 0
    for centre in model.centres:
        states = _exact_cost_states(model, centre)
        total_dp_states += len(states)
        blocked, mandatory = [], []
        for case, allowed, prediction in zip(model.cases, model.admissible, centre.labels):
            if not allowed:
                blocked.append({"case_id": case.case_id, "reason": "OBSERVATION_EXCLUDES_ALL_ADMISSIBLE_LABELS"})
            elif not case.exception_eligible and prediction not in allowed:
                blocked.append({"case_id": case.case_id, "reason": "PROTECTED_COORDINATE_CONFLICT"})
            elif case.exception_eligible and prediction not in allowed:
                mandatory.append(case.case_id)
        minimum = min(states) if states else None
        if states:
            all_fit.append(minimum)
            first_low.extend(cost for cost, (low, _) in states.items() if low <= model.threshold)
            first_high.extend(cost for cost, (_, high) in states.items() if high > model.threshold)
        values = [bounds for cost, bounds in states.items() if cost <= model.budget]
        bounds = (min(x[0] for x in values), max(x[1] for x in values)) if values else None
        if bounds is not None:
            at_budget.append((centre.centre_id, bounds))
        reasons = list(blocked)
        if minimum is not None and minimum > model.budget:
            reasons.append({"reason": "MANDATORY_DEPARTURES_EXCEED_BUDGET"})
        centre_records.append({"centre_id": centre.centre_id, "minimum_required_departures": minimum,
                               "mandatory_case_ids": sorted(mandatory), "feasible_at_budget": bounds is not None,
                               "interval": {"lower": rational_text(bounds[0]), "upper": rational_text(bounds[1])} if bounds else None,
                               "incompatibilities": reasons})
    same(report["centres"], centre_records, "Per-centre results disagree with exact-cost DP")
    same(report["feasible_centres"], [item[0] for item in at_budget], "Feasible centre IDs disagree")
    if at_budget:
        lower = min(item[1][0] for item in at_budget)
        upper = max(item[1][1] for item in at_budget)
        status = "AT_OR_BELOW" if upper <= model.threshold else "ABOVE" if lower > model.threshold else "UNDETERMINED"
        interval = {"lower": rational_text(lower), "upper": rational_text(upper)}
    else:
        status, interval = "OUT_OF_MODEL", None
    require(report["status"] == status, "Decision disagrees with exact-cost DP")
    same(report["interval"], interval, "Global interval disagrees with exact-cost DP")
    require(type(report["endpoint_certificates"]) is dict and set(report["endpoint_certificates"]) == {"lower", "upper"}, "Endpoint certificate fields differ")
    witness_receipts = []
    for endpoint in ("lower", "upper"):
        certificate = report["endpoint_certificates"][endpoint]
        if interval is None:
            require(certificate is None, "Empty family must not have endpoint witnesses")
        else:
            witness_receipts.append(_direct_certificate(model, certificate, model.budget,
                                                        lower if endpoint == "lower" else upper, endpoint + "_endpoint"))
    region = {"at_or_below": min(first_low) if first_low else None, "above": min(first_high) if first_high else None}
    opposite_key = "above" if status == "AT_OR_BELOW" else "at_or_below" if status == "ABOVE" else None
    opposite = {"reference_budget": model.budget, "reference_decision": status, "region": opposite_key,
                "first_budget": region[opposite_key] if opposite_key else None,
                "reason": "FIRST_OPPOSITE_COMPLETION" if opposite_key and region[opposite_key] is not None
                          else "OPPOSITE_REGION_UNATTAINABLE" if opposite_key else "NO_UNANIMOUS_INITIAL_DECISION"}
    same(report["radii"], {"minimum_feasible_budget": min(all_fit) if all_fit else None,
                           "first_at_or_below": region["at_or_below"], "first_above": region["above"],
                           "infinity_encoding": "null", "first_opposite_completion": opposite}, "Radii disagree with exact-cost DP")
    require(type(report["region_certificates"]) is dict and set(report["region_certificates"]) == set(region), "Region certificate fields differ")
    for name, radius in region.items():
        certificate = report["region_certificates"][name]
        if radius is None:
            require(certificate is None, "Unattainable region must not have a witness")
        else:
            receipt = _direct_certificate(model, certificate, radius, purpose="first_" + name)
            value = Fraction(receipt["score"])
            require((value <= model.threshold) if name == "at_or_below" else (value > model.threshold), "Region witness is on the wrong side")
            witness_receipts.append(receipt)
    same(report["nesting"], {"same_observations_and_model": True, "enlarging_budget_preserves_prior_assignments": True,
                             "opposite_unanimous_reversal_possible": False}, "Nesting statement differs")
    same(report["observation_evidence"], [{"case_id": o["case_id"], "label": o["label"],
                                          "evidence_id": o["evidence"]["evidence_id"], "payload_sha256": o["evidence"]["sha256"]}
                                         for o in model.observations], "Observation evidence identities differ")
    require(report["evidence_scope"] == "Payload identities and hashes are checked; external authority and truth of adjudications are assumptions.", "Evidence scope differs")
    same(report["execution_scope"], {"original_checker_invocations": 0, "prospective_experiments": 0,
                                    "calculation": "finite_reference_model_sensitivity"}, "Execution scope differs")
    receipt = {"schema": "nsc.reference-audit.verification/1", "status": "VERIFIED",
               "request_sha256": model.request_sha256, "matrix_sha256": model.matrix_sha256,
               "report_sha256": report["report_sha256"], "verifier": code_identity(),
               "method": "independent_exact_cost_dynamic_programming_and_direct_witness_validation",
               "decision": status, "interval": interval, "centre_count": len(model.centres),
               "terminal_exact_cost_states": total_dp_states, "witnesses": witness_receipts,
               "original_checker_invocations": 0}
    receipt["verification_sha256"] = digest(receipt)
    return receipt
