"""Strict evidence input and byte bindings; standard library only."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

MAX_BYTES = 1048576
FIXED_PROFILE_CANONICAL_HASHES = {
    "P4": "c3d6520613a33d1e06eae811bcd1e61559d4246a20a5739bcb3f325c6f05e920",
    "P5": "1fde671247bc7019383d9482349ea06ea4abd97cc2bac401dd63ad241fdd8652",
}


class InputError(ValueError):
    """Invalid input/admission, never an O15 verdict."""


class PreconditionError(ValueError):
    """An operator's declared domain does not contain this input."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError("DUPLICATE_JSON_KEY:" + repr(key))
        result[key] = value
    return result


def forbidden_number(token):
    raise InputError("INEXACT_OR_NONFINITE_JSON_NUMBER:" + token)


def parse(raw, name="document"):
    if len(raw) > MAX_BYTES:
        raise InputError("RECORD_BYTE_BOUND:" + name)
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"),
                           object_pairs_hook=unique_object,
                           parse_float=forbidden_number,
                           parse_constant=forbidden_number)
        # Reject escaped surrogate code points as well as invalid UTF-8 bytes.
        canonical(value)
        return value
    except InputError:
        raise
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise InputError("INVALID_JSON:" + name + ":" + type(exc).__name__) from exc


def read_tree(path):
    root = Path(path)
    if root.is_symlink() or not root.is_dir():
        raise InputError("DOSSIER_ROOT_MUST_BE_A_REAL_DIRECTORY")
    files = {}
    for parent, dirs, names in os.walk(root, followlinks=False):
        for name in dirs + names:
            member = Path(parent) / name
            mode = member.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise InputError("UNSAFE_MEMBER:" + str(member.relative_to(root)))
        for name in names:
            member = Path(parent) / name
            relative = member.relative_to(root).as_posix()
            files[relative] = member.read_bytes()
            if sum(map(len, files.values())) > MAX_BYTES or len(files) > 128:
                raise InputError("DOSSIER_BOUND")
    return files


def binding(files):
    rows = [{"path": p, "bytes": len(b), "sha256": sha256(b)}
            for p, b in sorted(files.items())]
    return {"domain": "sorted-relative-path-byte-manifest-v1",
            "sha256": sha256(canonical(rows)), "bytes": sum(r["bytes"] for r in rows),
            "files": rows}


def json_documents(files):
    return {p: parse(b, p) for p, b in files.items() if p.endswith(".json")}


def encoded(value, *, pretty=False):
    return (json.dumps(value, ensure_ascii=False, sort_keys=not pretty,
                       indent=2 if pretty else None,
                       separators=None if pretty else (",", ":"), allow_nan=False)
            + "\n").encode("utf-8")


def write_new_json(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(encoded(value, pretty=True))


def write_new_tree(path, files):
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise InputError("OUTPUT_ALREADY_EXISTS:" + str(target))
    # All member names originate from read_tree or explicit fixed paths.
    for name in files:
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise InputError("UNSAFE_OUTPUT_MEMBER")
    target.mkdir(parents=True, exist_ok=False)
    for name, raw in sorted(files.items()):
        member = target / name
        member.parent.mkdir(parents=True, exist_ok=True)
        with member.open("xb") as stream:
            stream.write(raw)


def validate_case_id(case_id):
    if type(case_id) is not str or not case_id.strip() or len(case_id) > 180:
        raise InputError("case_id must be a nonempty string of at most 180 characters")
    if any(ord(c) < 32 for c in case_id):
        raise InputError("case_id contains a control character")


def validate_p5_profile(profile):
    if (type(profile) is not dict or profile.get("schema") != "nsc-p5-fixed-profile/1"
            or profile.get("profile_id") != "NSC-P5-CORE-1"
            or type(profile.get("alias_grammar")) is not dict
            or profile.get("alias_grammar", {}).get("lookup_key") != "exact_nonempty_suffix"
            or profile.get("alias_grammar", {}).get("max_hops") != 1):
        raise InputError("UNSUPPORTED_NATIVE_PROFILE")


def validate_fixed_profile(profile):
    if type(profile) is not dict:
        raise InputError("PROFILE_MUST_BE_OBJECT")
    if profile.get("schema") == "nsc-p4-fixed-profile/2" and profile.get("profile_id") == "NSC-P3-CORE-RECOVERY-2":
        generation = "P4"
    else:
        validate_p5_profile(profile)
        generation = "P5"
    for key in ("required_paths", "optional_paths", "category_order", "response_states", "input_states"):
        value = profile.get(key)
        if type(value) is not list or any(type(x) is not str for x in value):
            raise InputError("INVALID_PROFILE_FIELD:" + key)
    if profile.get("active_obligations") != [f"O{i:02d}" for i in range(1, 17)]:
        raise InputError("INVALID_PROFILE_OBLIGATIONS")
    if sha256(canonical(profile)) != FIXED_PROFILE_CANONICAL_HASHES[generation]:
        raise InputError("FROZEN_PROFILE_CONTENT_MISMATCH:" + generation)
    return generation


def profile_custody(files, profile):
    validate_fixed_profile(profile)
    docs = json_documents(files)
    required = set(profile["required_paths"])
    allowed = required | set(profile["optional_paths"])
    issues = []
    if not required <= set(files) <= allowed:
        issues.append("PROFILE_MEMBERSHIP")
    header = docs.get("bundle.json", {})
    if type(header) is not dict or header.get("profile_id") != profile["profile_id"]:
        issues.append("PROFILE_ID")
    expected = [{"path": p, "bytes": len(b), "sha256": sha256(b)}
                for p, b in sorted(files.items()) if p != "inventory.json"]
    inventory = docs.get("inventory.json")
    # Python's ordinary container equality conflates True with 1. Custody is
    # a typed JSON relation: an inventory byte count must match as an integer.
    if type(inventory) is not dict or canonical(inventory.get("members")) != canonical(expected):
        issues.append("RAW_INVENTORY")
    payload = docs.get("semantic_payload.json")
    descriptor = {"domain": "canonical-json-v1", "algorithm": "sha256",
                  "value": sha256(canonical(payload))}
    r01 = docs.get("records/R01.json")
    if type(r01) is not dict or r01.get("semantic_digest") != descriptor:
        issues.append("SEMANTIC_COMMITMENT")
    return {"status": "PASS" if not issues else "FAIL", "issues": issues}


def seal_profile(files, profile):
    """Recommit a new complete P4/P5 package without changing source anchors."""
    validate_fixed_profile(profile)
    files = dict(files)
    payload = parse(files["semantic_payload.json"], "semantic_payload.json")
    files["records/R01.json"] = encoded({"semantic_digest": {
        "domain": "canonical-json-v1", "algorithm": "sha256",
        "value": sha256(canonical(payload))}})
    files["inventory.json"] = encoded({"members": [
        {"path": p, "bytes": len(b), "sha256": sha256(b)}
        for p, b in sorted(files.items()) if p != "inventory.json"]})
    result = profile_custody(files, profile)
    if result["status"] != "PASS":
        raise InputError("RECOMMIT_FAILED:" + ",".join(result["issues"]))
    return files


def p5_custody(files, profile):
    validate_p5_profile(profile)
    return profile_custody(files, profile)


def seal_p5(files, profile):
    validate_p5_profile(profile)
    return seal_profile(files, profile)
