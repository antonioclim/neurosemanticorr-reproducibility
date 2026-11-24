"""Portable CLI for documentary O15 diagnostics and fresh native P4/P5 checks."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .evidence import InputError, parse, read_tree, write_new_json, write_new_tree
from .native import native_suite
from .operators import SPECS, transform
from .qualification import regression
from .reference import evaluate_files


def error_report_is_safe(args, report_path):
    if not report_path or Path(report_path).exists():
        return False
    path = Path(report_path).resolve()
    return all(not path.is_relative_to(Path(getattr(args, name)).resolve())
               for name in ("input", "output_dir") if getattr(args, name, None))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    ref = sub.add_parser("reference", help="Evaluate five documentary conventions; no checker is invoked")
    ref.add_argument("--input", required=True)
    ref.add_argument("--case-id", required=True)
    ref.add_argument("--output", required=True)
    op = sub.add_parser("transform", help="Apply a scoped operator; preserve precondition failures distinctly")
    op.add_argument("--input", required=True)
    op.add_argument("--case-id", required=True)
    op.add_argument("--operator", choices=tuple(SPECS), required=True)
    op.add_argument("--parameters", required=True, help="Strict JSON parameter file")
    op.add_argument("--profile", help="Required for a complete P4/P5 evidence bundle")
    op.add_argument("--output-dir", required=True)
    op.add_argument("--output", required=True, help="Report path, outside input and output evidence")
    native = sub.add_parser("native-suite", help="Qualify fresh T01–T08 native fixtures, with a plan locked before invocations")
    native.add_argument("--repository", default=str(Path(__file__).resolve().parents[2]))
    native.add_argument("--generation", choices=("P4", "P5"), default="P5")
    native.add_argument("--out", required=True)
    native.add_argument("--timeout", type=float, default=5.0)
    reg = sub.add_parser("regression", help="Compare with retained documentary reference and locked fixtures")
    reg.add_argument("--repository", default=str(Path(__file__).resolve().parents[2]))
    reg.add_argument("--archive", help="Optional extracted NSC_PROS_v1 containing exactly 192 dockets")
    reg.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    report_path = getattr(args, "output", None)
    try:
        if args.command in ("reference", "transform"):
            source = Path(args.input).resolve()
            if Path(report_path).resolve().is_relative_to(source):
                raise InputError("REPORT_MUST_BE_OUTSIDE_INPUT")
            files = read_tree(source)
        if args.command == "reference":
            result = evaluate_files(files, args.case_id)
        elif args.command == "transform":
            target = Path(args.output_dir).resolve()
            if target.is_relative_to(source) or source.is_relative_to(target):
                raise InputError("OUTPUT_AND_INPUT_TREES_MUST_BE_DISJOINT")
            if Path(report_path).resolve().is_relative_to(target):
                raise InputError("REPORT_MUST_BE_OUTSIDE_TRANSFORMED_EVIDENCE")
            parameters = parse(Path(args.parameters).read_bytes(), "operator parameters")
            profile = parse(Path(args.profile).read_bytes(), "profile") if args.profile else None
            output, result = transform(files, args.case_id, args.operator, parameters, profile=profile)
            if output is not None:
                write_new_tree(target, output)
        elif args.command == "native-suite":
            result = native_suite(args.repository, args.out, generation=args.generation, timeout=args.timeout)
            print(result["status"], result["expectations_met"], "/", result["candidate_invocations"], "native expectations")
            return 0 if result["status"] == "PASS" else 1
        else:
            result = regression(args.repository, args.archive)
        result["cli_command"] = [sys.executable, "-m", "r5_f3.o15_diagnostics", *(argv if argv is not None else sys.argv[1:])]
        write_new_json(report_path, result)
        print(result["status"])
        return 0 if result["status"] in ("COMPLETED", "TRANSFORMED", "PASS") else 2 if result["status"] == "INPUT_ERROR" else 1
    except (InputError, OSError) as exc:
        result = {"schema": "nsc-r5-f3-o15-error/1", "status": "INPUT_ERROR" if isinstance(exc, InputError) else "EXECUTION_ERROR",
                  "error_type": type(exc).__name__, "error": str(exc), "semantic_verdict_assigned": False}
        # Never put an error report into either evidence tree, even on failure.
        if error_report_is_safe(args, report_path):
            write_new_json(report_path, result)
        print(result["status"] + ": " + str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        # Unexpected execution faults are explicitly not converted to V or U.
        result = {"schema": "nsc-r5-f3-o15-error/1", "status": "EXECUTION_ERROR",
                  "error_type": type(exc).__name__, "error": str(exc), "semantic_verdict_assigned": False}
        if error_report_is_safe(args, report_path):
            write_new_json(report_path, result)
        print("EXECUTION_ERROR: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
