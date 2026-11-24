"""Recompute the retained screening comparison with the F3 implementation.

This is a retrospective software replay of frozen selections and adjudications.
It executes no checker and draws no new random sample.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

if __package__:
    from .cli import run_bytes, unique_object, invalid_constant
    from .screening import InputError, make_plan
else:
    from cli import run_bytes, unique_object, invalid_constant
    from screening import InputError, make_plan

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "BLIND_SELECTION.json": "e900b01104a5f5731ebbf6a69d92e4791342cdfb8680bd6eb5f35fd4ea32d625",
    "PROSPECTIVE_RESULTS.json": "dcfaaf9b0bc690fecb19db40db1f75c81461d152a7f7000ca70d4e6c6bba8e0f",
    "PERMUTATIONS.json": "2449f546e053a9446b6fd65cf0e81fc6cfc87114a800d0aead9a1d25f9f9da86",
    "O15_REFERENCE.json": "28f568cb904c2348bbaad4074b8bee01475d138054e494d1c8c9b34bfca2d96e",
    "ANALYSIS_PLAN.md": "8f30bc5cdc2fec5dc3f04dae55ca1b090d935750548daa8381211e6e3fc85830",
    "SELECTION_COMMITMENT.json": "1ae99cfff82d6920aca8f3197c0e6da1cafdd40ab19e9adab2d6d11cd6324e0a",
}


def require(condition, message):
    if not condition:
        raise InputError(message)


def dump(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def replay(out):
    data = {}
    for name, expected in EXPECTED.items():
        raw = (ROOT / "inputs" / name).read_bytes()
        require(sha256(raw).hexdigest() == expected, f"historical source identity mismatch: {name}")
        if name.endswith(".json"):
            data[name] = json.loads(raw, object_pairs_hook=unique_object, parse_constant=invalid_constant)
    selected = data["BLIND_SELECTION.json"]
    original = data["PROSPECTIVE_RESULTS.json"]
    reference_rows = data["O15_REFERENCE.json"]["cases"]
    reference = {r["case_id"]: r["expected"] for r in reference_rows}
    require(len(reference) == len(reference_rows) == 192, "reference identities differ")
    require(set(reference) == set(selected["case_outputs"]), "reference and checker frame differ")
    require(original["blind_selection_sha256"] == EXPECTED["BLIND_SELECTION.json"], "selection binding differs")
    require(original["reference_sha256"] == EXPECTED["O15_REFERENCE.json"], "reference binding differs")
    orders = data["PERMUTATIONS.json"]["context_orders"]
    require(set(orders) == set(original["contexts"]), "context identities differ")
    out.mkdir(parents=True, exist_ok=False)
    reports = {}; comparisons = []
    for context in sorted(orders):
        frame = {case: row for case, row in selected["case_outputs"].items() if row["context"] == context}
        require(len(frame) == 48, f"context {context} does not have 48 cases")
        require(all(row["comparable"] for row in frame.values()), "incomparable output pair")
        for policy in ("screen_and_uniform", "uniform_completion"):
            flags = sorted(case for case, row in frame.items()
                           if policy == "screen_and_uniform" and row["screen"]["status"] == "flagged")
            plan_input = {"case_ids": sorted(frame), "flagged_ids": flags,
                          "budget": original["per_context_budget"], "permutation": orders[context],
                          "design_id": f"R1PROS-frozen/{context}/{policy}"}
            plan = make_plan(**plan_input)
            historical_selection = selected["context_selections"][context][policy]
            require(plan["selection"]["certainty"] == historical_selection["certainty_selected"],
                    f"certainty selection differs for {context}/{policy}")
            require(plan["selection"]["residual_draw"] == historical_selection["residual_draw"],
                    f"residual selection differs for {context}/{policy}")
            request = {"schema": "nsc-screening-request/1", "plan_input": plan_input,
                       "checker_outputs": {case: row["O15"] for case, row in frame.items()},
                       "observations": {case: reference[case] for case in plan["selection"]["reviewed"]},
                       "alpha": original["per_context_alpha"],
                       "sampling_basis": "Replayed frozen SRS permutation and selected IDs from the retained R1PROS analysis plan; retrospective calculation"}
            raw = dump(request); report = run_bytes(raw)
            name = f"{context}__{policy}"
            (out / f"{name}.request.json").write_bytes(raw)
            (out / f"{name}.report.json").write_bytes(dump(report))
            observed = report["result"]
            historical = original["contexts"][context]["policy_results"][policy]
            pairs = {"found_errors": "agreement_errors_found", "reviewed": "agreement_reviews",
                     "certainty_errors": "certainty_agreement_errors",
                     "residual_population": "residual_population", "residual_sample": "residual_sample",
                     "residual_errors_observed": "residual_errors_sampled",
                     "conditional_upper": "one_look_upper", "interval": "deterministic_interval",
                     "found_case_ids": "found_case_ids"}
            for now, before in pairs.items():
                a, b = observed[now], historical[before]
                if now == "found_case_ids":
                    a, b = sorted(a), sorted(b)
                require(a == b, f"replay mismatch: {name}/{now}: {a!r} != {b!r}")
                comparisons.append({"context": context, "policy": policy, "field": now, "matches": True})
            reports[name] = observed
    primary = [r for name, r in reports.items() if name.endswith("__screen_and_uniform")]
    uniform = [r for name, r in reports.items() if name.endswith("__uniform_completion")]
    pooled = {"screen_reviewed": sum(r["reviewed"] for r in primary),
              "screen_flags": sum(r["flag_count"] for r in primary),
              "screen_found": sum(r["found_errors"] for r in primary),
              "screen_residual_draw": sum(r["residual_sample"] for r in primary),
              "screen_residual_hits": sum(r["residual_errors_observed"] for r in primary),
              "screen_bonferroni_upper": sum(r["conditional_upper"] for r in primary),
              "uniform_reviewed": sum(r["reviewed"] for r in uniform),
              "uniform_found": sum(r["found_errors"] for r in uniform)}
    require(pooled["screen_bonferroni_upper"] == original["primary_familywise_upper_sum"], "pooled historical bound differs")
    result = {"schema": "nsc-f3-screening-replay/1", "status": "PASS_ARCHIVED_DESIGN_REPLAY",
              "input_sha256": EXPECTED,
              "source_sha256": {p.name: sha256(p.read_bytes()).hexdigest() for p in
                                (Path(__file__), ROOT/"screening.py", ROOT/"cli.py")},
              "context_policy_reports": len(reports), "field_comparisons": len(comparisons),
              "comparisons": comparisons, "pooled": pooled,
              "scope": "Retrospective software replay; original prospective result of 60 is preserved",
              "checker_invocations": 0, "new_draws": 0, "new_human_adjudications": 0}
    (out / "REPLAY_RESULTS.json").write_bytes(dump(result))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new output directory")
    args = parser.parse_args()
    try:
        result = replay(args.out)
        print(json.dumps({key: result[key] for key in ("status", "context_policy_reports", "field_comparisons", "pooled")}, indent=2))
    except (InputError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "INPUT_OR_REPLAY_ERROR", "message": str(exc)}), file=sys.stderr)
        raise SystemExit(2) from exc
    except OSError as exc:
        print(json.dumps({"status": "EXECUTION_ERROR", "message": str(exc)}), file=sys.stderr)
        raise SystemExit(3) from exc
