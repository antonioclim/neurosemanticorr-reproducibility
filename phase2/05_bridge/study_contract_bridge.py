"""Reconstruct one retained Study Contract population using the standard library."""

import argparse
import copy
import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from zipfile import ZipFile

ARCHIVE_SHA256 = "6f758773b489cea9bc17fc36cd30013e24543256631eb2cb9ea53aaf64cd24c5"
ARCHIVE_BYTES = 53_468_001
PREFIX = (
    "neuroSEMANTICorr v12/01_CURRENT_M06DR/04_CURRENT_EVIDENCE/SUCCESSOR_CHAIN/"
    "M05E_Q0941_RAW/PAIRS/001_C24_Q0941/CANDIDATE/"
)
FILES = {
    "data": "data.json",
    "contract": "pair_admission/contract.json",
    "state": "pair_admission/states.csv",
    "alignment": "pair_admission/alignment.json",
    "runtime": "pair_admission/admission/study_contract_validation.json",
    "binding": "pair_binding.json",
    "result": "RESULT.json",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def canonical_digest(value):
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return digest(payload.encode("utf-8"))


def unique_pairs(entries):
    result = dict(entries)
    if len(result) != len(entries):
        raise ValueError("Repeated JSON key")
    return result


def as_json(data):
    return json.loads(data, object_pairs_hook=unique_pairs)


def read_state_rows(payload):
    rows = list(csv.reader(io.StringIO(payload.decode("utf-8-sig"), newline=""), strict=True))
    if not rows or not rows[0] or not all(rows[0]) or len(set(rows[0])) != len(rows[0]):
        raise ValueError("Missing or nonunique CSV columns")
    columns, *values = rows
    if any(len(row) != len(columns) for row in values):
        raise ValueError("CSV record length differs from its header")
    return columns, [dict(zip(columns, row)) for row in values]


def read_archive(archive_path):
    if archive_path.stat().st_size != ARCHIVE_BYTES or file_digest(archive_path) != ARCHIVE_SHA256:
        raise ValueError("Archive identity mismatch")
    with ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(set(names)) != len(names):
            raise ValueError("Archive contains duplicate member names")
        manifest_name = PREFIX + "DATA_MANIFEST.json"
        manifest_raw = archive.read(manifest_name)
        manifest_rows = [row for row in as_json(manifest_raw) if row["type"] == "file"]
        manifest = {row["path"]: row for row in manifest_rows}
        if len(manifest) != len(manifest_rows):
            raise ValueError("Duplicate data manifest path")
        inputs = {}
        identity = {"data_manifest": {"member": manifest_name, "sha256": digest(manifest_raw)}}
        for name, rel in FILES.items():
            member_name = f"{PREFIX}DATA/{rel}"
            member = archive.read(member_name)
            if (len(member), digest(member)) != (manifest[rel]["bytes"], manifest[rel]["sha256"]):
                raise ValueError(f"Data manifest does not bind {rel}")
            inputs[name] = member if name == "state" else as_json(member)
            identity[name] = {"member": member_name, "sha256": digest(member), "bytes": len(member)}
    return inputs, identity


def evaluate(records):
    data = records["data"]
    contract = records["contract"]
    alignment = records["alignment"]
    runtime = records["runtime"]
    binding = records["binding"]
    result = records["result"]
    columns, states = read_state_rows(records["state"])
    if not data or any(list(row) != columns for row in data):
        raise ValueError("Archived v12 input has unexpected data columns")
    identifiers = [entry["id"] for entry in contract["variables"] if entry["role"] == "identifier"]
    if identifiers != ["id"] or any(type(row["id"]) is not int for row in data):
        raise ValueError("Archived v12 input requires its declared integer row id")
    [population] = contract["analytic_populations"]
    population_name = population["id"]
    required = population["required_variables"]
    allowed_states = population["allowed_states"]
    if (population_name != "P" or required != [f"V{i:02d}" for i in range(10)]
            or allowed_states != {name: ["observed"] for name in required}):
        raise ValueError("Archive contains a different eligibility rule")
    errors = []

    def check(condition, code):
        if not condition:
            errors.append(code)

    checks = (
        (runtime["schema"], "semcorr-study-runtime-1"),
        (runtime["status"], "PASS"),
        (alignment["schema"], "semcorr-response-alignment-1"),
        (binding["schema"], "semcorr-network-study-binding-1"),
        (result["schema"], "semcorr-s5c-timing-replicate/1"),
    )
    check(all(a == b for a, b in checks), "legacy_document_kind")
    check(len(states) == len(data) == runtime["n_rows"], "input_row_count")
    check(runtime["purpose"] == "synthetic_execution_only" and runtime["scientific_validation"] is False,
          "runtime_scope")
    check(result["cell_id"] == "C24" and result["replicate"] == 941 and result["primary"] is False,
          "result_scope")
    check(runtime["stage_populations"] == {"network": population_name}, "stage_population")
    check(binding["population_id"] == population_name, "binding_population")
    check(binding["population_sha256"] == canonical_digest(population), "binding_population_digest")

    seal = {
        "schema": "semcorr-admitted-frames-1",
        "contract_sha256": canonical_digest(contract),
        "data_frame_sha256": canonical_digest(data),
        "state_frame_sha256": canonical_digest(states),
        "data_columns": columns,
        "state_columns": columns,
        "n_rows": len(data),
    }
    for key in ("contract_sha256", "data_frame_sha256", "state_frame_sha256"):
        check(runtime[key] == seal[key], key)
    check(runtime["frame_seal"] == seal, "runtime_frame_seal")
    check(alignment["frame_seal"] == seal, "alignment_frame_seal")
    check(binding["frame_seal"] == seal, "binding_frame_seal")
    check(binding["contract_sha256"] == seal["contract_sha256"], "binding_contract_digest")
    states_sha256 = digest(records["state"])
    check(runtime["state_source"] == {"kind": "explicit_positional_sidecar", "sha256": states_sha256}
          and alignment["states_payload_sha256"] == states_sha256, "state_payload_digest")
    check(runtime["alignment"]["receipt_sha256"] == canonical_digest(alignment), "alignment_receipt_digest")
    check(alignment["identifier_variables"] == identifiers, "alignment_identifiers")
    tokens = [canonical_digest([row["id"]]) for row in data]
    check(len(set(tokens)) == len(tokens), "row_identifier_uniqueness")
    check(alignment["ordered_row_tokens"] == tokens, "ordered_identity_tokens")
    check(binding["alignment"] == runtime["alignment"], "binding_alignment")
    limits = ("producer_authenticated", "initial_pairing_verified")
    check(all(container[name] is False for container in (runtime["alignment"], alignment) for name in limits),
          "alignment_assurance_scope")

    positions = [i for i, row in enumerate(states)
                 if all(row[column] in allowed_states[column] for column in required)]
    position_set = set(positions)
    excluded = [i for i in range(len(data)) if i not in position_set]
    observed = runtime["analytic_populations"][population_name]
    reported = observed["row_positions"]
    check(all(type(i) is int and 0 <= i < len(data) for i in reported), "reported_position_bounds")
    check(reported == sorted(set(reported)), "reported_position_order_and_uniqueness")
    check(observed["row_count"] == len(reported) == len(positions), "population_count")
    check(reported == positions, "population_membership")
    check(observed["positions_sha256"] == canonical_digest(reported), "runtime_positions_self_digest")
    check(binding["population_row_positions"] == positions, "binding_population_positions")
    check(binding["retained_source_positions"] == result["retained"] == positions, "downstream_retained_positions")
    check(binding["excluded_by_population"] == excluded, "binding_excluded_positions")
    check(binding["row_positions_sha256"] == canonical_digest(positions), "binding_positions_digest")
    return {
        "input_rows": len(data),
        "reconstructed_population_rows": len(positions),
        "reported_population_rows": observed["row_count"],
        "reconstructed_positions_sha256": canonical_digest(positions),
        "reconstructed_ordered_identity_vector_sha256": canonical_digest(tokens),
        "diagnostics": errors,
    }


def run_trials(records):
    original = evaluate(records)
    population = records["runtime"]["analytic_populations"]["P"]
    positions = population["row_positions"]
    smallest_excluded = min(set(range(len(records["data"]))) - set(positions))

    substitution = copy.deepcopy(records)
    report = substitution["runtime"]["analytic_populations"]["P"]
    report["row_positions"] = sorted([smallest_excluded, *positions[1:]])
    report["positions_sha256"] = canonical_digest(report["row_positions"])
    substituted = evaluate(substitution)

    false_identity = copy.deepcopy(records)
    false_identity["data"][0]["id"] = max(row["id"] for row in records["data"]) + 1
    identity_changed = evaluate(false_identity)

    false_length = copy.deepcopy(records)
    false_length["runtime"]["analytic_populations"]["P"]["row_count"] += 1
    length_changed = evaluate(false_length)

    tests = {
        "original": original,
        "position_substitution_with_updated_self_digest": substituted,
        "row_identifier_replacement": identity_changed,
        "reported_length_increase": length_changed,
    }
    expected_diagnostics = {
        "original": set(),
        "position_substitution_with_updated_self_digest": {"population_membership"},
        "row_identifier_replacement": {"data_frame_sha256", "runtime_frame_seal", "alignment_frame_seal",
                                      "binding_frame_seal", "ordered_identity_tokens"},
        "reported_length_increase": {"population_count"},
    }
    passed = (
        original["input_rows"] == 200
        and original["reconstructed_population_rows"] == 156
        and all(set(value["diagnostics"]) == expected_diagnostics[name] for name, value in tests.items())
    )
    return passed, tests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    records, identity = read_archive(args.archive)
    passed, trials = run_trials(records)
    receipt = {
        "schema": "nsc-r4-f2-retained-study-contract-bridge/1",
        "status": "PASS_PROTOCOL_TRIALS" if passed else "FAIL_PROTOCOL_TRIALS",
        "archive_sha256": ARCHIVE_SHA256,
        "protocol_sha256": file_digest(Path(__file__).with_name("BRIDGE_PROTOCOL.md")),
        "script_sha256": file_digest(Path(__file__)),
        "source_pair": "M05E-EQUIV:C24:Q0941:CANDIDATE",
        "source_documents": identity,
        "field_mapping": {
            "input_length": "/n_rows",
            "retained_positions": "/analytic_populations/P/row_positions",
            "selected_length": "/analytic_populations/P/row_count",
            "selected_positions_digest": "/analytic_populations/P/positions_sha256",
            "identity_assurance": "/alignment",
        },
        "producer_authenticated": False,
        "initial_pairing_verified": False,
        "executed_archived_producer_or_checkers": 0,
        "trials": trials,
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
