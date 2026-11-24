"""Exercise the published documentary CLI and its output-boundary failures."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

from .evidence import binding, parse, write_new_json


def qualify(output):
    root = Path(__file__).resolve().parent
    repository = root.parents[1]
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    base = [sys.executable, "-B", "-m", "r5_f3.o15_diagnostics"]
    checks = []

    def run(name, args, expected, criterion):
        start = datetime.now(timezone.utc).isoformat()
        clock = time.monotonic()
        process = subprocess.run(base + args, cwd=repository, capture_output=True, check=False, timeout=30)
        duration = time.monotonic() - clock
        attempt = out / name
        attempt.mkdir()
        (attempt / "stdout.bin").write_bytes(process.stdout)
        (attempt / "stderr.bin").write_bytes(process.stderr)
        report = Path(args[args.index("--output") + 1])
        # Reports include measured floating-point durations. The strict evidence
        # parser applies to dossiers/configuration, not to a report's timing data.
        value = json.loads(report.read_bytes()) if report.exists() else None
        passed = process.returncode == expected and criterion(value)
        row = {"name": name, "command": base + args, "cwd": str(repository), "started_utc": start,
               "duration_seconds": duration, "exit_code": process.returncode, "expected_exit_code": expected,
               "stdout": process.stdout.decode(), "stderr": process.stderr.decode(), "report_path": str(report),
               "report_status": value.get("status") if value else None, "passed": passed}
        write_new_json(attempt / "RECEIPT.json", row)
        checks.append(row)

    for case in parse((root / "examples/EXPECTED.json").read_bytes())["cases"]:
        run("reference-" + case["case_id"], ["reference", "--input", str(root / "examples" / case["path"]),
            "--case-id", case["case_id"], "--output", str(out / (case["case_id"] + ".json"))], 0,
            lambda d, expected=case["expected_documentary_verdicts"]:
            {p: x["verdict"] for p, x in d["policies"].items()} == expected)
    for name, source, operator, params, expected in [
        ("contrast", "conflicting_alias", "T03", "T03_min", 0),
        ("repair", "chain", "T05", "T05_repair", 0),
        ("bad_nested", "chain", "T02", "T02_bad_nested", 1),
    ]:
        run(name, ["transform", "--input", str(root / "examples/dockets" / source),
            "--case-id", "F3-CLI-" + name, "--operator", operator,
            "--parameters", str(root / "examples/parameters" / (params + ".json")),
            "--output-dir", str(out / (name + "-dossier")), "--output", str(out / (name + ".json"))], expected,
            lambda d, code=expected: d["status"] == ("TRANSFORMED" if code == 0 else "PRECONDITION_FAILED"))
    for kind in ("input", "output"):
        source = root / "examples/dockets/direct"
        target = out / ("must-not-create-" + kind)
        forbidden = (source if kind == "input" else target) / "FORBIDDEN_REPORT.json"
        run("report-inside-" + kind, ["transform", "--input", str(source), "--case-id", "F3-CLI-PATH",
            "--operator", "T01", "--parameters", str(root / "examples/parameters/T01.json"),
            "--output-dir", str(target), "--output", str(forbidden)], 2,
            lambda d, path=forbidden: d is None and not path.exists())
    result = {"schema": "nsc-r5-f3-cli-qualification/1", "status": "PASS" if all(c["passed"] for c in checks) else "FAIL",
              "checks": checks, "component_source_binding": binding({p.name: p.read_bytes() for p in root.glob("*.py")}),
              "limits": "Documentary CLI qualification only; no native checker invocation in these eight checks."}
    write_new_json(out / "SUMMARY.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="Fresh report directory")
    result = qualify(parser.parse_args().out)
    print(result["status"], sum(c["passed"] for c in result["checks"]), "/", len(result["checks"]))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
