"""Finite-frame screening plans and exact conditional sampling bounds.

Selection never reads adjudicated labels. The statistical bound is conditional
on a declared simple-random-sampling design, not established by a hash or seed.
"""

from fractions import Fraction
from hashlib import sha256
import json
from math import comb

VERSION = "nsc-screening/1"
LABELS = frozenset(("S", "V", "U"))


class InputError(ValueError):
    """A malformed input, distinct from an oversubscribed review design."""


def canonical_digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _integer(value, name):
    if type(value) is not int or value < 0:
        raise InputError(f"{name} must be a nonnegative integer, excluding bool")
    return value


def _ids(values, name):
    if type(values) is not list or any(type(v) is not str or not v.strip() for v in values):
        raise InputError(f"{name} must be a list of nonempty string identifiers")
    if len(set(values)) != len(values):
        raise InputError(f"{name} contains duplicate identifiers")
    return values


def _alpha(value):
    if type(value) is not str:
        raise InputError("alpha must be an exact rational string")
    try:
        result = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise InputError("alpha is not an exact rational") from exc
    if not 0 < result < 1:
        raise InputError("alpha must lie strictly between zero and one")
    return result


def make_plan(case_ids, flagged_ids, budget, permutation, design_id):
    """Review all flags, then fill from the supplied whole-frame permutation.

The permutation is an input to a frozen design, never a new post hoc draw.
When F > B this implementation rejects the design; it does not truncate flags.
"""
    _ids(case_ids, "case_ids")
    _ids(flagged_ids, "flagged_ids")
    _ids(permutation, "permutation")
    _integer(budget, "budget")
    if type(design_id) is not str or not design_id.strip():
        raise InputError("design_id must be a nonempty string")
    if not set(flagged_ids) <= set(case_ids):
        raise InputError("a flag lies outside the frame")
    if set(permutation) != set(case_ids):
        raise InputError("permutation must contain each frame identifier exactly once")
    if budget > len(case_ids):
        raise InputError("budget exceeds the frame size")
    inputs = {"case_ids": sorted(case_ids), "flagged_ids": sorted(flagged_ids),
              "budget": budget, "permutation": permutation, "design_id": design_id}
    common = {"schema": VERSION, "design_id": design_id,
              "input": inputs, "input_sha256": canonical_digest(inputs),
              "frame_size": len(case_ids), "flag_count": len(flagged_ids),
              "budget": budget, "overflow_rule": "REJECT_DESIGN"}
    if len(flagged_ids) > budget:
        return {**common, "status": "INVALID_DESIGN", "selection": None,
                "reason": "FLAG_PANEL_EXCEEDS_BUDGET",
                "shortfall": len(flagged_ids) - budget}
    flags = set(flagged_ids)
    certainty = [case for case in permutation if case in flags]
    residual_frame = [case for case in permutation if case not in flags]
    draw = residual_frame[:budget - len(certainty)]
    return {**common, "status": "PLAN_DEFINED", "shortfall": 0,
            "selection": {"certainty": certainty, "residual_frame": residual_frame,
                          "residual_draw": draw, "reviewed": certainty + draw},
            "reason": None}


def check_plan(plan):
    if type(plan) is not dict or type(plan.get("input")) is not dict:
        raise InputError("missing plan input")
    source = plan["input"]
    if set(source) != {"case_ids", "flagged_ids", "budget", "permutation", "design_id"}:
        raise InputError("unknown or missing plan input field")
    expected = make_plan(**source)
    try:
        same_typed_json = canonical_digest(plan) == canonical_digest(expected)
    except (TypeError, ValueError) as exc:
        raise InputError("plan is not valid finite JSON") from exc
    if not same_typed_json:
        raise InputError("plan differs from its inputs or digest")
    return expected


def upper_count(population, sample, adverse, alpha):
    """Invert the exact hypergeometric lower tail, with strict P(X<=x)>alpha.

The count includes observed residual errors. The result covers the finite
residual frame under SRS without replacement and fixed, accurate labels.
"""
    for value, name in ((population, "population"), (sample, "sample"), (adverse, "adverse")):
        _integer(value, name)
    level = _alpha(alpha)
    if not adverse <= sample <= population:
        raise InputError("require 0 <= adverse <= sample <= population")
    denominator = comb(population, sample)

    def retained(total):
        low = max(0, sample - (population - total))
        high = min(adverse, sample, total)
        numerator = sum(comb(total, x) * comb(population - total, sample - x)
                        for x in range(low, high + 1))
        return numerator * level.denominator > denominator * level.numerator

    # The lower tail decreases in the unknown population error count.
    lo, hi = adverse, population - sample + adverse
    while lo < hi:
        middle = (lo + hi + 1) // 2
        if retained(middle):
            lo = middle
        else:
            hi = middle - 1
    return lo


def zero_hit_upper(population, sample, adverse, alpha):
    """Explicitly reject a positive hit before using a zero-hit calculation."""
    _integer(adverse, "adverse")
    if adverse != 0:
        raise InputError("ZERO_HIT_PRECONDITION_FAILED")
    return upper_count(population, sample, adverse, alpha)


def score_plan(plan, checker_outputs, observations, *, alpha, sampling_basis):
    """Score selected accurate adjudications only, under an explicit design.

checker_outputs maps every frame ID to [T_FULL, B_ASSERT]. observations maps
exactly the reviewed IDs to S/V/U. Full-frame truth is neither required nor read.
sampling_basis is a documentary description, not authenticated by this module.
"""
    plan = check_plan(plan)
    _alpha(alpha)
    if type(sampling_basis) is not str or not sampling_basis.strip():
        raise InputError("an explicit sampling basis is required")
    if plan["status"] != "PLAN_DEFINED":
        return {"schema": VERSION, "status": "INVALID_DESIGN",
                "reason": plan["reason"], "plan_input_sha256": plan["input_sha256"],
                "interval": None, "conditional_upper": None}
    cases = set(plan["input"]["case_ids"])
    if type(checker_outputs) is not dict or set(checker_outputs) != cases:
        raise InputError("checker outputs must cover exactly the declared frame")
    for case, pair in checker_outputs.items():
        if (type(pair) is not list or len(pair) != 2 or
                any(type(x) is not str or x not in LABELS for x in pair) or pair[0] != pair[1]):
            raise InputError(f"{case}: this scope requires two comparable agreeing S/V/U outputs")
    selected = plan["selection"]
    reviewed = set(selected["reviewed"])
    if type(observations) is not dict or set(observations) != reviewed:
        raise InputError("observations must cover exactly the reviewed IDs")
    if any(type(v) is not str or v not in LABELS for v in observations.values()):
        raise InputError("adjudicated labels must be S, V or U")
    errors = {case for case, value in observations.items() if checker_outputs[case][0] != value}
    certainty_errors = errors.intersection(selected["certainty"])
    residual_errors = errors.intersection(selected["residual_draw"])
    population, sample = len(selected["residual_frame"]), len(selected["residual_draw"])
    observed = len(residual_errors)
    bound = (zero_hit_upper if observed == 0 else upper_count)(population, sample, observed, alpha)
    flags = plan["flag_count"]
    inputs = {"plan": plan, "checker_outputs": checker_outputs, "observations": observations,
              "alpha": alpha, "sampling_basis": sampling_basis}
    return {
        "schema": VERSION, "status": "SCORED_CONDITIONALLY",
        "plan_input_sha256": plan["input_sha256"], "scoring_input_sha256": canonical_digest(inputs),
        "frame_size": len(cases), "reviewed": len(reviewed), "flag_count": flags,
        "certainty_errors": len(certainty_errors), "residual_population": population,
        "residual_sample": sample, "residual_errors_observed": observed,
        "found_errors": len(errors), "found_case_ids": sorted(errors),
        "interval": [len(errors), len(errors) + len(cases) - len(reviewed)],
        "flag_precision": str(Fraction(len(certainty_errors), flags)) if flags else None,
        "flag_precision_reason": None if flags else "UNDEFINED_EMPTY_FLAG_PANEL",
        "zero_hit_precondition": observed == 0,
        "bound_method": "ZERO_HIT_EXACT" if observed == 0 else "GENERAL_HYPERGEOMETRIC_EXACT",
        "residual_upper": bound, "conditional_upper": len(certainty_errors) + bound,
        "alpha": str(_alpha(alpha)), "sampling_basis": sampling_basis,
        "assumptions": ["SRS without replacement within the fixed residual frame",
                        "selection fixed independently of the residual adjudicated labels",
                        "accurate adjudications", "one prespecified look"],
        "scope": "Finite-frame conditional sampling bound; no new prospective experiment",
    }
