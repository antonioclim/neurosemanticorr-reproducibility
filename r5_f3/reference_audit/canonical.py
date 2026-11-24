"""Strict JSON loading and the documented payload commitment."""

from hashlib import sha256
import json
from pathlib import Path

CANONICALISATION = "nsc-json-utf8-sort-keys-v1"


class InputError(ValueError):
    def __init__(self, code, message, path="$"):
        self.code, self.path = code, path
        super().__init__(message)


class VerificationError(ValueError):
    pass


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError("DUPLICATE_JSON_KEY", f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _floating(value):
    raise InputError("NONINTEGER_JSON_NUMBER", "JSON floating-point and non-finite numbers are not admitted; use rational strings")


def loads(text):
    try:
        return json.loads(text, object_pairs_hook=_pairs, parse_float=_floating, parse_constant=_floating)
    except InputError:
        raise
    except (ValueError, TypeError, UnicodeError) as error:
        raise InputError("INVALID_JSON", str(error)) from error


def load_file(path):
    try:
        return loads(Path(path).read_text(encoding="utf-8"))
    except InputError:
        raise
    except (OSError, UnicodeError) as error:
        raise InputError("UNREADABLE_INPUT", str(error)) from error


def _json_tree(value, path="$"):
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is list:
        for i, child in enumerate(value):
            _json_tree(child, f"{path}[{i}]")
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for key, child in value.items():
            _json_tree(child, f"{path}.{key}")
        return
    raise InputError("INVALID_JSON_TYPE", "Only objects, arrays, strings, integers, booleans and null are admitted", path)


def canonical_bytes(value):
    """No Unicode normalisation; array order retained; no trailing newline."""
    _json_tree(value)
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, UnicodeError, TypeError) as error:
        raise InputError("CANONICALISATION_FAILED", str(error)) from error


def digest(value):
    return sha256(canonical_bytes(value)).hexdigest()


def display_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def file_digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()
