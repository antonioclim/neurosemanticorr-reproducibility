"""Audit exact decisions over a finite set of whole-frame O15 conventions."""

from functools import partial
from itertools import combinations

import o15_reference as ref

POLICIES = ("literal_only", "suffix_only", "either_unique", "prefer_literal", "prefer_suffix")
VERDICTS = frozenset("SVU")


def resolve(policy, source, aliases):
    if policy == "either_unique":
        return ref.resolve_source(source, aliases)
    if source.startswith(ref.ALIAS_PREFIX):
        suffix = source[len(ref.ALIAS_PREFIX):]
        if not suffix:
            raise ValueError("empty alias key")
        keys = {
            "literal_only": (source,), "suffix_only": (suffix,),
            "prefer_literal": (source, suffix), "prefer_suffix": (suffix, source),
        }[policy]
        for key in keys:
            if key in aliases:
                source = aliases[key]
                break
        else:
            raise ValueError("no mapping for alias")
    ref.pointer_tokens(source)
    return source


def evaluate(path):
    """Keep policy traces separately. An execution exception is never an O15 label."""
    return {policy: ref.adjudicate(path, partial(resolve, policy)) for policy in POLICIES}


def compatible(labels, observations):
    """Filter by explicit labels, including U only when U was adjudicated."""
    if not labels:
        raise ValueError("the declared model needs at least one policy")
    cases = set(next(iter(labels.values())))
    if any(set(vector) != cases for vector in labels.values()):
        raise ValueError("policy vectors must span the same cases")
    if not set(observations) <= cases:
        raise ValueError("observation is outside the declared frame")
    if any(type(label) is not str or label not in VERDICTS for label in observations.values()):
        raise ValueError("observations must contain adjudicated S, V or U labels")
    return tuple(policy for policy, vector in labels.items()
                 if all(vector[case] == label for case, label in observations.items()))


def decision(labels, counts, observations, ceiling):
    if type(ceiling) is not int or ceiling < 0 or set(labels) != set(counts):
        raise ValueError("invalid threshold or policy counts")
    if any(type(value) is not int or value < 0 for value in counts.values()):
        raise ValueError("counts must be nonnegative integers")
    retained = compatible(labels, observations)
    if not retained:
        return {"status": "OUT_OF_MODEL", "retained_policies": [],
                "attainable_counts": [], "interval": None}
    values = sorted({counts[policy] for policy in retained})
    status = "AT_OR_BELOW" if values[-1] <= ceiling else (
        "ABOVE" if values[0] > ceiling else "UNDETERMINED")
    return {"status": status, "retained_policies": list(retained),
            "attainable_counts": values, "interval": [values[0], values[-1]]}


def minimum_witness(labels, counts, ceiling):
    """Exact minimum-cardinality nonadaptive cover of cross-threshold policy pairs."""
    compatible(labels, {})  # validate the common domain
    pairs = [(a, b) for a, b in combinations(labels, 2)
             if (counts[a] <= ceiling) != (counts[b] <= ceiling)]
    target = (1 << len(pairs)) - 1
    by_mask = {}
    for case in sorted(next(iter(labels.values()))):
        mask = sum(1 << k for k, (a, b) in enumerate(pairs) if labels[a][case] != labels[b][case])
        if mask and mask not in by_mask:
            by_mask[mask] = case
    best = {0: ()}
    for mask, case in sorted(by_mask.items(), key=lambda item: item[1]):
        for covered, previous in tuple(best.items()):
            union = covered | mask
            proposal = (*previous, case)
            if union not in best or (len(proposal), proposal) < (len(best[union]), best[union]):
                best[union] = proposal
    if target not in best:
        return {"status": "INSUFFICIENT_DISTINGUISHING_CASES", "case_ids": None,
                "opposite_pairs": [list(pair) for pair in pairs]}
    cases = best[target]
    return {"status": "SEPARATING_SET", "case_ids": list(cases),
            "opposite_pairs": [list(pair) for pair in pairs],
            "case_labels": {case: {p: labels[p][case] for p in labels} for case in cases}}
