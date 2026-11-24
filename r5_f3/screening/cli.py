"""Run one explicitly declared screening audit request."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

if __package__:
    from .screening import InputError, make_plan, score_plan
else:
    from screening import InputError, make_plan, score_plan


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def invalid_constant(value):
    raise InputError(f"non-finite JSON number: {value}")


def run_bytes(raw, expected_sha256=None):
    actual = sha256(raw).hexdigest()
    if expected_sha256 is not None and actual != expected_sha256:
        raise InputError("request SHA-256 does not match --expect-sha256")
    try:
        request = json.loads(raw.decode("utf-8", errors="strict"),
                             object_pairs_hook=unique_object, parse_constant=invalid_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise InputError(f"invalid UTF-8 JSON: {exc}") from exc
    required = {"schema", "plan_input", "checker_outputs", "observations", "alpha", "sampling_basis"}
    if type(request) is not dict or set(request) != required or request["schema"] != "nsc-screening-request/1":
        raise InputError("unknown request schema or fields")
    expected_plan = {"case_ids", "flagged_ids", "budget", "permutation", "design_id"}
    if type(request["plan_input"]) is not dict or set(request["plan_input"]) != expected_plan:
        raise InputError("unknown or missing plan_input fields")
    plan = make_plan(**request["plan_input"])
    result = score_plan(plan, request["checker_outputs"], request["observations"],
                        alpha=request["alpha"], sampling_basis=request["sampling_basis"])
    return {"schema": "nsc-screening-cli-report/1", "request_sha256": actual,
            "source_sha256": {p.name: sha256(p.read_bytes()).hexdigest()
                              for p in (Path(__file__), Path(__file__).with_name("screening.py"))},
            "plan": plan, "result": result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("--expect-sha256")
    parser.add_argument("--out", type=Path, help="new output file; existing files are not overwritten")
    args = parser.parse_args()
    try:
        result = run_bytes(args.request.read_bytes(), args.expect_sha256)
        text = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
        if args.out:
            with args.out.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
        else:
            sys.stdout.write(text)
        return 0 if result["result"]["status"] == "SCORED_CONDITIONALLY" else 2
    except (InputError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "INPUT_ERROR", "message": str(exc)}), file=sys.stderr)
        return 2
    except OSError as exc:
        print(json.dumps({"status": "EXECUTION_ERROR", "message": str(exc)}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
