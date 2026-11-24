"""Command-line interface; valid OUT_OF_MODEL results have exit code zero."""

import argparse
import sys

from .canonical import CANONICALISATION, InputError, VerificationError, digest, display_json, load_file, loads
from .canonical_query import canonical_query_minimum
from .engine import audit
from .verification import verify_report


def _input(path):
    return loads(sys.stdin.read()) if path == "-" else load_file(path)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m r5_f3.reference_audit")
    sub = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (("audit", "Compute exact bounds, decisions and witnesses"),
                               ("q-min", "Return only the verified canonical query minimum"),
                               ("digest", "Hash one JSON value in the documented canonical domain")):
        item = sub.add_parser(command, help=help_text)
        item.add_argument("input", help="UTF-8 JSON path, or - for standard input")
    verify = sub.add_parser("verify", help="Verify a report using independent exact-cost DP")
    verify.add_argument("input", help="Original request JSON path")
    verify.add_argument("report", help="Report JSON path")
    args = parser.parse_args(argv)
    try:
        value = _input(args.input)
        if args.command == "audit":
            result = audit(value)
        elif args.command == "q-min":
            result = canonical_query_minimum(value)
        elif args.command == "digest":
            result = {"canonicalisation": CANONICALISATION, "sha256": digest(value)}
        else:
            try:
                report = load_file(args.report)
            except InputError as error:
                raise VerificationError("Invalid report JSON: " + str(error)) from error
            result = verify_report(value, report)
        sys.stdout.write(display_json(result))
        return 0
    except InputError as error:
        sys.stdout.write(display_json({"status": "INPUT_ERROR", "code": error.code,
                                      "path": error.path, "message": str(error)}))
        return 2
    except VerificationError as error:
        sys.stdout.write(display_json({"status": "VERIFICATION_FAILED", "message": str(error)}))
        return 3
    except Exception as error:
        # An execution failure never becomes a reference verdict or OUT_OF_MODEL.
        sys.stdout.write(display_json({"status": "EXECUTION_ERROR", "error_type": type(error).__name__, "message": str(error)}))
        return 4
