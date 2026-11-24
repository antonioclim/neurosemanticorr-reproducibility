"""Sharp endpoints from mandatory departures and sorted optional improvements."""

from dataclasses import dataclass
from fractions import Fraction

from .canonical import digest
from .model import rational_text, validate_request
from .provenance import code_identity


@dataclass
class Profile:
    centre: object
    mandatory_ids: list
    blocked: list
    lower_labels: list
    upper_labels: list
    lower_base: Fraction
    upper_base: Fraction
    decreases: list
    increases: list

    @property
    def minimum_distance(self):
        return None if self.blocked else len(self.mandatory_ids)

    def interval(self, budget):
        if self.minimum_distance is None or self.minimum_distance > budget:
            return None
        extra = budget - self.minimum_distance
        return (self.lower_base - sum((x[0] for x in self.decreases[:extra]), Fraction(0)),
                self.upper_base + sum((x[0] for x in self.increases[:extra]), Fraction(0)))


def _profile(model, centre):
    blocked = []
    mandatory = []
    for case, allowed, prediction in zip(model.cases, model.admissible, centre.labels):
        if not allowed:
            blocked.append({"case_id": case.case_id, "reason": "OBSERVATION_EXCLUDES_ALL_ADMISSIBLE_LABELS"})
        elif not case.exception_eligible and prediction not in allowed:
            blocked.append({"case_id": case.case_id, "reason": "PROTECTED_COORDINATE_CONFLICT"})
        elif case.exception_eligible and prediction not in allowed:
            mandatory.append(case.case_id)
    result = Profile(centre, sorted(mandatory), blocked, [], [], Fraction(0), Fraction(0), [], [])
    if blocked:
        return result
    for i, (case, allowed, prediction) in enumerate(zip(model.cases, model.admissible, centre.labels)):
        smallest = min(allowed, key=lambda y: (case.contribution(y), y))
        largest = min(allowed, key=lambda y: (-case.contribution(y), y))
        if prediction not in allowed:  # A mandatory eligible departure.
            lower, upper = smallest, largest
        else:
            lower = upper = prediction
            if case.exception_eligible:
                down = case.contribution(prediction) - case.contribution(smallest)
                up = case.contribution(largest) - case.contribution(prediction)
                if down > 0:
                    result.decreases.append((down, i, smallest))
                if up > 0:
                    result.increases.append((up, i, largest))
        result.lower_labels.append(lower)
        result.upper_labels.append(upper)
        result.lower_base += case.contribution(lower)
        result.upper_base += case.contribution(upper)
    result.decreases.sort(key=lambda x: (-x[0], model.cases[x[1]].case_id))
    result.increases.sort(key=lambda x: (-x[0], model.cases[x[1]].case_id))
    return result


def _certificate(model, profile, budget, upper, purpose):
    limits = profile.interval(budget)
    if limits is None:
        return None
    labels = list(profile.upper_labels if upper else profile.lower_labels)
    improvements = profile.increases if upper else profile.decreases
    for _, i, y in improvements[:budget - profile.minimum_distance]:
        labels[i] = y
    changed = sorted(case.case_id for case, y, g in zip(model.cases, labels, profile.centre.labels) if y != g)
    return {"purpose": purpose, "request_sha256": model.request_sha256,
            "matrix_sha256": model.matrix_sha256, "centre_id": profile.centre.centre_id,
            "budget": budget, "distance": len(changed), "score": rational_text(limits[int(upper)]),
            "labels": {case.case_id: y for case, y in zip(model.cases, labels)},
            "changed_case_ids": changed}


def _region_radius(profile, threshold, upper):
    if profile.minimum_distance is None:
        return None
    value = profile.upper_base if upper else profile.lower_base
    improvements = profile.increases if upper else profile.decreases
    for count in range(len(improvements) + 1):
        reaches_region = value > threshold if upper else value <= threshold
        if reaches_region:
            return profile.minimum_distance + count
        if count < len(improvements):
            value += improvements[count][0] if upper else -improvements[count][0]
    return None


def _min_available(values):
    candidates = [x for x in values if x is not None]
    return min(candidates) if candidates else None


def audit(request):
    """Return a deterministic report. A valid empty family is not an input error."""
    model = validate_request(request)
    profiles = [_profile(model, centre) for centre in model.centres]
    feasible = [p for p in profiles if p.interval(model.budget) is not None]
    if feasible:
        lower_profile = min(feasible, key=lambda p: (p.interval(model.budget)[0], p.centre.centre_id))
        upper_profile = min(feasible, key=lambda p: (-p.interval(model.budget)[1], p.centre.centre_id))
        lower, upper = lower_profile.interval(model.budget)[0], upper_profile.interval(model.budget)[1]
        status = "AT_OR_BELOW" if upper <= model.threshold else "ABOVE" if lower > model.threshold else "UNDETERMINED"
        interval = {"lower": rational_text(lower), "upper": rational_text(upper)}
        witnesses = {"lower": _certificate(model, lower_profile, model.budget, False, "lower_endpoint"),
                     "upper": _certificate(model, upper_profile, model.budget, True, "upper_endpoint")}
    else:
        status, interval = "OUT_OF_MODEL", None
        witnesses = {"lower": None, "upper": None}
    region_radii, region_certificates = {}, {}
    for region, upper in (("at_or_below", False), ("above", True)):
        candidates = [(radius, p.centre.centre_id, p) for p in profiles
                      if (radius := _region_radius(p, model.threshold, upper)) is not None]
        if candidates:
            radius, _, profile = min(candidates, key=lambda x: (x[0], x[1]))
            region_radii[region] = radius
            region_certificates[region] = _certificate(model, profile, radius, upper, "first_" + region)
        else:
            region_radii[region] = None
            region_certificates[region] = None
    opposite_region = "above" if status == "AT_OR_BELOW" else "at_or_below" if status == "ABOVE" else None
    opposite = {"reference_budget": model.budget, "reference_decision": status,
                "region": opposite_region,
                "first_budget": region_radii[opposite_region] if opposite_region else None,
                "reason": "FIRST_OPPOSITE_COMPLETION" if opposite_region and region_radii[opposite_region] is not None
                          else "OPPOSITE_REGION_UNATTAINABLE" if opposite_region else "NO_UNANIMOUS_INITIAL_DECISION"}
    centre_reports = []
    for p in profiles:
        limits = p.interval(model.budget)
        reasons = list(p.blocked)
        if not reasons and p.minimum_distance > model.budget:
            reasons.append({"reason": "MANDATORY_DEPARTURES_EXCEED_BUDGET"})
        centre_reports.append({"centre_id": p.centre.centre_id,
                               "minimum_required_departures": p.minimum_distance,
                               "mandatory_case_ids": p.mandatory_ids,
                               "feasible_at_budget": limits is not None,
                               "interval": {"lower": rational_text(limits[0]), "upper": rational_text(limits[1])} if limits else None,
                               "incompatibilities": reasons})
    report = {"schema": "nsc.reference-audit.report/1", "status": status,
              "frame_id": model.frame_id, "request_sha256": model.request_sha256,
              "matrix_sha256": model.matrix_sha256, "producer": code_identity(),
              "model_scope": {**model.raw["model_scope"], "joint_centres_supplied": len(model.centres),
                              "complete_cartesian_product_certified": False},
              "score": "weighted_identical_output_shared_error_on_frame_only",
              "budget": model.budget, "threshold": rational_text(model.threshold),
              "interval": interval, "interval_is_envelope": True,
              "feasible_centres": [p.centre.centre_id for p in profiles if p.interval(model.budget) is not None],
              "centres": centre_reports, "endpoint_certificates": witnesses,
              "radii": {"minimum_feasible_budget": _min_available(p.minimum_distance for p in profiles),
                        "first_at_or_below": region_radii["at_or_below"], "first_above": region_radii["above"],
                        "infinity_encoding": "null", "first_opposite_completion": opposite},
              "region_certificates": region_certificates,
              "nesting": {"same_observations_and_model": True, "enlarging_budget_preserves_prior_assignments": True,
                          "opposite_unanimous_reversal_possible": False},
              "observation_evidence": [{"case_id": o["case_id"], "label": o["label"],
                                        "evidence_id": o["evidence"]["evidence_id"],
                                        "payload_sha256": o["evidence"]["sha256"]} for o in model.observations],
              "evidence_scope": "Payload identities and hashes are checked; external authority and truth of adjudications are assumptions.",
              "execution_scope": {"original_checker_invocations": 0, "prospective_experiments": 0,
                                  "calculation": "finite_reference_model_sensitivity"}}
    report["report_sha256"] = digest(report)
    return report
