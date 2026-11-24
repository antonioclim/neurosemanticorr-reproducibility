from copy import deepcopy
from fractions import Fraction
from itertools import product

from ..build_examples import simple_case, toy_request
from ..canonical import digest


def reseal(request):
    request["matrix"]["sha256"] = digest(request["matrix"]["payload"])
    return request


def resign(report):
    report["report_sha256"] = digest({key: value for key, value in report.items() if key != "report_sha256"})
    return report


def tiny(budget=0, eligible=True):
    return toy_request([simple_case("a", allowed=("S", "V"), eligible=eligible),
                        simple_case("b", allowed=("S", "V"), eligible=eligible)],
                       {"all-S": {"a": "S", "b": "S"}}, budget=budget, threshold="0")


def brute_force(request):
    """Separate direct enumeration: no model, engine, gain or DP helper calls."""
    payload = request["matrix"]["payload"]
    cases = payload["cases"]
    observed = {item["case_id"]: item["label"] for item in request["observations"]}
    choices = [tuple(y for y in case["allowed_labels"] if case["case_id"] not in observed or y == observed[case["case_id"]]) for case in cases]
    policies = {p["convention_id"]: p["predictions"] for p in payload["conventions"]}
    records = []
    for centre in payload["centres"]:
        predicted = [policies[centre["convention_by_case"][c["case_id"]]][c["case_id"]] for c in cases]
        for labels in product(*choices):
            if any(not c["exception_eligible"] and y != g for c, y, g in zip(cases, labels, predicted)):
                continue
            distance = sum(y != g for c, y, g in zip(cases, labels, predicted) if c["exception_eligible"])
            score = sum((Fraction(c["weight"]) for c, y in zip(cases, labels)
                         if c["role"] == "frame" and c["checker_labels"]["t"] == c["checker_labels"]["b"] and y != c["checker_labels"]["t"]), Fraction(0))
            records.append((distance, score))
    threshold = Fraction(request["threshold"])
    values = [score for distance, score in records if distance <= request["budget"]]
    limits = (min(values), max(values)) if values else None
    status = "OUT_OF_MODEL" if limits is None else "AT_OR_BELOW" if limits[1] <= threshold else "ABOVE" if limits[0] > threshold else "UNDETERMINED"
    low = [cost for cost, score in records if score <= threshold]
    high = [cost for cost, score in records if score > threshold]
    return {"interval": {"lower": str(limits[0]), "upper": str(limits[1])} if limits else None,
            "status": status, "fit": min(cost for cost, _ in records) if records else None,
            "low_radius": min(low) if low else None, "high_radius": min(high) if high else None}
