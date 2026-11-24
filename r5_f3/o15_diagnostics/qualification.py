"""Read-only documentary regression against the retained phase2 evaluator."""
from __future__ import annotations

from pathlib import Path
import runpy
import sys
import types

from .evidence import InputError, binding, parse, sha256
from .reference import POLICIES, RECORDS, evaluate_files


def canonical_evaluator(repository):
    source = Path(repository) / "phase2/02_source"
    old = sys.modules.get("o15_reference")
    prior = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    module = types.ModuleType("o15_reference")
    module.__dict__.update(runpy.run_path(str(source / "o15_reference.py")))
    sys.modules["o15_reference"] = module
    try:
        evaluate = runpy.run_path(str(source / "decision_audit.py"))["evaluate"]
    finally:
        sys.dont_write_bytecode = prior
        if old is None:
            del sys.modules["o15_reference"]
        else:
            sys.modules["o15_reference"] = old
    return evaluate


def regression(repository, archive=None):
    repository = Path(repository)
    evaluator = canonical_evaluator(repository)
    fixtures = repository / "phase2/01_fixtures"
    expected = parse((fixtures / "EXPECTED.json").read_bytes())
    sources = [(name, fixtures / "dockets" / name, data["expected"], "phase2_locked_probe")
               for name, data in sorted(expected["cases"].items())]
    if archive is not None:
        archive = Path(archive)
        paths = sorted({p.parent.parent for p in archive.rglob("R15_claims.json")
                        if p.parent.name == "records"})
        if len(paths) != 192:
            raise InputError("archive regression requires exactly the retained 192 dossier paths; found " + str(len(paths)))
        sources.extend((p.name, p, None, "retained_prospective_dossier") for p in paths)
    checks = []
    for case_id, path, locked, origin in sources:
        files = {relative: (path / relative).read_bytes() for relative in RECORDS.values() if (path / relative).is_file()}
        observed = evaluate_files(files, case_id)
        reference = {p: r["expected"] for p, r in evaluator(path).items()}
        labels = {p: r["verdict"] for p, r in observed.get("policies", {}).items()}
        checks.append({"case_id": case_id, "origin": origin, "input_binding": binding(files),
                       "canonical": reference, "new_reference": labels, "locked_expected": locked,
                       "passed": labels == reference and (locked is None or labels == locked)})
    return {"schema": "nsc-r5-f3-o15-regression/1", "status": "PASS" if all(c["passed"] for c in checks) else "FAIL",
            "case_count": len(checks), "convention_comparisons": len(checks) * len(POLICIES),
            "canonical_source_hashes": {n: sha256((repository / "phase2/02_source" / n).read_bytes())
                                        for n in ("o15_reference.py", "decision_audit.py")},
            "checks": checks, "original_checker_invocations": 0,
            "limits": ["Documentary reference regression only; not a native checker execution.",
                       "Strict JSON parsing failures in the new API are INPUT_ERROR without a semantic label.",
                       "The retained valid/missing-evidence cases do not test every malformed input."]}
