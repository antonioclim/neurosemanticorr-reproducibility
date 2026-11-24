"""Run the frozen O15 reference on the synthetic build-report example."""

import argparse
from hashlib import sha256
import importlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_bindings(paths, root):
    for path, expected in paths.items():
        if digest(root / path) != expected:
            raise ValueError(f"Unexpected bytes: {root / path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path,
                        help="Directory holding the unmodified Phase 2 reference modules")
    args = parser.parse_args()
    source_dir = args.source_dir.resolve()
    lock = read_json(ROOT / "EXAMPLE_LOCK.json")
    check_bindings(lock["inputs"], ROOT)
    check_bindings(lock["phase2_modules"], source_dir)
    spec = read_json(ROOT / "EXPECTED.json")

    sys.path.insert(0, str(source_dir))
    evaluator = importlib.import_module("decision_audit")
    if tuple(spec["policy_order"]) != evaluator.POLICIES:
        raise ValueError("Policy order differs from expectations")

    trace = {}
    for name, expected in spec["dossiers"].items():
        actual = evaluator.evaluate(ROOT / "dossiers" / name)
        trace[name] = actual
        for policy, label in zip(evaluator.POLICIES, expected["labels"], strict=True):
            report = actual[policy]
            rationale = report["rationale"]
            witness = ({"claim_id": "smoke-pass-fraction", "pointer": expected["satisfied_pointer"]}
                       if label == "S" else None)
            expected_resolved = [witness] if witness else []
            if (report["expected"] != label or rationale["missing"]
                    or rationale["resolved"] != expected_resolved
                    or bool(rationale["violations"]) != (label == "V")):
                raise ValueError(f"{name}, {policy}: unexpected audit trace {report}")
            if label == "V":
                problem = ("alias spellings map to different pointers"
                           if policy == "either_unique" and name.startswith(("D3", "D4"))
                           else "unit, denominator or scope does not match field metadata")
                if rationale["violations"] != [{"claim_id": "smoke-pass-fraction", "problem": problem}]:
                    raise ValueError(f"{name}, {policy}: unexpected violation rationale")

    print(json.dumps({
        "schema": "nsc-r4-o15-build-report-receipt/1",
        "status": "PASS_SYNTHETIC_INTERFACE_EXAMPLE",
        "scope": "Synthetic software build-report example, outside Phase 2 and archived frames",
        "example_lock_sha256": digest(ROOT / "EXAMPLE_LOCK.json"),
        "phase2_module_sha256": lock["phase2_modules"],
        "comparisons": len(trace) * len(evaluator.POLICIES),
        "judgements": trace,
    }, indent=2))


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    main()
