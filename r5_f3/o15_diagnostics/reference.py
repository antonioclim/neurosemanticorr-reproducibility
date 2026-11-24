"""Documentary O15 evaluator, not T_FULL or B_ASSERT.

The five resolver conventions and admitted-document checks follow the retained
phase2 reference. Strict parsing failures have a separate INPUT_ERROR status;
missing records remain U and explicit semantic violations remain V.
"""
from __future__ import annotations

from fractions import Fraction
import re

from .evidence import InputError, binding, parse, validate_case_id

VERSION = "R5-F3-O15-REFERENCE-1"
POLICIES = ("literal_only", "suffix_only", "either_unique", "prefer_literal", "prefer_suffix")
RECORDS = {"claims": "records/R15_claims.json", "edges": "records/R15_edges.json",
           "result": "records/R11_result.json"}


class Violation(ValueError):
    """A specific invalid documentary relation, not an execution failure."""


def text(record, key):
    if type(record) is not dict or type(record.get(key)) is not str or not record[key]:
        raise Violation(key + " must be a nonempty string")
    return record[key]


def metadata(record):
    if type(record) is not dict:
        raise Violation("metadata must be an object")
    count = record.get("denominator")
    if type(count) is not int or count < 0:
        raise Violation("denominator must be a nonnegative integer")
    return text(record, "unit"), count, text(record, "scope")


def exact_value(value):
    if type(value) is int:
        return "number", Fraction(value)
    if type(value) is dict and set(value) == {"numerator", "denominator"}:
        n, d = value["numerator"], value["denominator"]
        if type(n) is int and type(d) is int and d > 0:
            return "number", Fraction(n, d)
    if type(value) in (str, bool, type(None)):
        return type(value).__name__, value
    raise Violation("value must be an exact scalar or a rational with positive denominator")


def pointer_tokens(pointer):
    # The O15 profile deliberately requires a nonempty pointer. RFC6901's empty
    # document pointer is not admitted as a scalar claim source in this profile.
    if type(pointer) is not str or not pointer.startswith("/"):
        raise Violation("a source pointer must start with /")
    tokens = pointer[1:].split("/")
    if any(re.search(r"~(?![01])", token) for token in tokens):
        raise Violation("source pointer contains an invalid tilde escape")
    return [t.replace("~1", "/").replace("~0", "~") for t in tokens]


def pointer_value(document, pointer):
    node = document
    for token in pointer_tokens(pointer):
        if type(node) is dict and token in node:
            node = node[token]
        elif (type(node) is list and re.fullmatch(r"0|[1-9][0-9]*", token)
              and len(token) <= len(str(len(node))) and int(token) < len(node)):
            node = node[int(token)]
        else:
            raise Violation("pointer " + repr(pointer) + " does not resolve")
    return node


def resolve(policy, source, aliases):
    if policy not in POLICIES:
        raise InputError("UNKNOWN_CONVENTION:" + str(policy))
    if type(source) is not str:
        raise Violation("source pointer must be a string")
    if source.startswith("alias:"):
        suffix = source[6:]
        if not suffix:
            raise Violation("empty alias key")
        if type(aliases) is not dict:
            raise Violation("alias map is unavailable")
        if policy == "either_unique":
            targets = {aliases[k] for k in (suffix, source) if k in aliases}
            if not targets:
                raise Violation("no mapping for alias")
            if len(targets) != 1:
                raise Violation("alias spellings map to different pointers")
            source = targets.pop()
        else:
            keys = {"literal_only": (source,), "suffix_only": (suffix,),
                    "prefer_literal": (source, suffix), "prefer_suffix": (suffix, source)}[policy]
            for key in keys:
                if key in aliases:
                    source = aliases[key]
                    break
            else:
                raise Violation("no mapping for alias")
    pointer_tokens(source)
    return source


def adjudicate(documents, missing, policy):
    violations, resolved = [], []
    ids = {}
    for kind in ("edges", "result"):
        if kind in documents:
            try:
                ids[kind] = text(documents[kind], "result_id")
            except Violation as exc:
                violations.append({"record": RECORDS[kind], "problem": str(exc)})
    if len(set(ids.values())) > 1:
        violations.append({"record": RECORDS["edges"], "problem": "result_id does not match R11"})
    claims = []
    if "claims" in documents:
        try:
            candidates = documents["claims"].get("claims")
            if type(candidates) is not list or not candidates or any(type(c) is not dict for c in candidates):
                raise Violation("claims must be a nonempty array of objects")
            claim_ids = [text(c, "claim_id") for c in candidates]
            if len(set(claim_ids)) != len(claim_ids):
                raise Violation("claim identifiers must be unique")
            claims = list(zip(claim_ids, candidates))
        except Violation as exc:
            violations.append({"record": RECORDS["claims"], "problem": str(exc)})
    aliases = fields = None
    if "edges" in documents:
        try:
            edges = documents["edges"]
            if (type(edges.get("aliases")) is not dict
                    or any(type(v) is not str for v in edges["aliases"].values())):
                raise Violation("aliases must be a map to strings")
            if type(edges.get("field_metadata")) is not dict:
                raise Violation("field_metadata must be an object")
            aliases, fields = edges["aliases"], edges["field_metadata"]
        except Violation as exc:
            violations.append({"record": RECORDS["edges"], "problem": str(exc)})
    for claim_id, claim in claims:
        try:
            source = text(claim, "source_pointer")
            claim_meta = metadata(claim)
            if "value" not in claim:
                raise Violation("missing claimed value")
            claim_value = exact_value(claim["value"])
            if source.startswith("alias:") and aliases is None:
                if source == "alias:":
                    raise Violation("empty alias key")
                continue
            pointer = resolve(policy, source, aliases)
            if fields is not None:
                if pointer not in fields:
                    raise Violation("no field metadata for " + repr(pointer))
                if claim_meta != metadata(fields[pointer]):
                    raise Violation("unit, denominator or scope does not match field metadata")
            if "result" in documents and claim_value != exact_value(pointer_value(documents["result"], pointer)):
                raise Violation("claimed value does not match the resolved result")
            resolved.append({"claim_id": claim_id, "source_pointer": source, "pointer": pointer,
                             "result_id": ids.get("result"), "metadata": {
                                 "unit": claim_meta[0], "denominator": claim_meta[1], "scope": claim_meta[2]}})
        except Violation as exc:
            violations.append({"claim_id": claim_id, "problem": str(exc)})
    return {"execution_status": "COMPLETED", "verdict": "V" if violations else "U" if missing else "S",
            "rationale": {"violations": violations, "missing": list(missing), "resolved": resolved}}


def evaluate_files(files, case_id):
    validate_case_id(case_id)
    report = {"schema": "nsc-r5-f3-o15-reference/1", "evaluator": VERSION,
              "case_id": case_id, "input_binding": binding(files),
              "scope": "Documentary three-record O15 reference; not a checker execution.",
              "convention_order": list(POLICIES)}
    documents, missing = {}, []
    try:
        for kind, path in RECORDS.items():
            if path not in files:
                missing.append(path)
                continue
            value = parse(files[path], path)
            if type(value) is not dict:
                raise InputError("RECORD_MUST_BE_OBJECT:" + path)
            documents[kind] = value
    except InputError as exc:
        return {**report, "status": "INPUT_ERROR", "policies": {},
                "error": {"type": type(exc).__name__, "message": str(exc)},
                "semantic_verdict_assigned": False}
    report["policies"] = {p: adjudicate(documents, missing, p) for p in POLICIES}
    report["status"] = "COMPLETED"
    return report
