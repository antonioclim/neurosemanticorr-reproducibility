"""Strict request validation; no optimisation and no external file resolution."""

from dataclasses import dataclass
from fractions import Fraction
import re

from .canonical import CANONICALISATION, InputError, canonical_bytes, digest, loads

SCHEMA = "nsc.reference-audit.request/1"
LABELS = ("S", "V", "U")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,255}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
RATIONAL = re.compile(r"(0|[1-9][0-9]*)(/[1-9][0-9]*)?\Z")


def fail(code, message, path):
    raise InputError(code, message, path)


def fields(value, expected, path):
    if type(value) is not dict:
        fail("OBJECT_REQUIRED", "Expected an object", path)
    missing, extra = set(expected) - set(value), set(value) - set(expected)
    if missing or extra:
        fail("OBJECT_FIELDS", f"Missing fields: {sorted(missing)}; unknown fields: {sorted(extra)}", path)


def identifier(value, path):
    if type(value) is not str or IDENTIFIER.fullmatch(value) is None:
        fail("INVALID_IDENTIFIER", "Expected a nonempty identifier using the documented ASCII characters", path)
    return value


def hash_value(value, path):
    if type(value) is not str or HASH.fullmatch(value) is None:
        fail("INVALID_SHA256", "Expected 64 lowercase hexadecimal characters", path)
    return value


def rational(value, path):
    if type(value) is not str or RATIONAL.fullmatch(value) is None:
        fail("INVALID_RATIONAL", "Expected a nonnegative integer or rational string such as '2' or '1/2'", path)
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as error:
        fail("INVALID_RATIONAL", str(error), path)


def rational_text(value):
    value = Fraction(value)
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def label(value, path, nullable=False):
    if nullable and value is None:
        return None
    if type(value) is not str or value not in LABELS:
        fail("INVALID_LABEL", "Expected an observed S, V or U label", path)
    return value


def sequence(value, path, nonempty=False):
    if type(value) is not list or (nonempty and not value):
        fail("ARRAY_REQUIRED", "Expected an array" + (" with at least one item" if nonempty else ""), path)


@dataclass(frozen=True)
class Case:
    case_id: str
    context_id: str
    role: str
    t: str | None
    b: str | None
    allowed: tuple[str, ...]
    weight: Fraction
    exception_eligible: bool

    def contribution(self, value):
        if self.role == "frame" and self.t == self.b and value != self.t:
            return self.weight
        return Fraction(0)


@dataclass(frozen=True)
class Centre:
    centre_id: str
    assignment: tuple[str, ...]
    labels: tuple[str, ...]


@dataclass(frozen=True)
class Model:
    raw: dict
    frame_id: str
    cases: tuple[Case, ...]
    centres: tuple[Centre, ...]
    conventions: tuple[dict, ...]
    admissible: tuple[tuple[str, ...], ...]
    observations: tuple[dict, ...]
    budget: int
    threshold: Fraction
    model_scope: str
    request_sha256: str
    matrix_sha256: str


def validate_request(request):
    # Validate JSON types and detach the immutable mathematical representation
    # from any mutable dictionary retained by an API caller.
    request = loads(canonical_bytes(request))
    fields(request, ("schema", "frame_id", "matrix", "model_scope", "observations", "budget", "threshold"), "$")
    if request["schema"] != SCHEMA:
        fail("UNSUPPORTED_SCHEMA", "Unsupported request schema", "$.schema")
    frame_id = identifier(request["frame_id"], "$.frame_id")
    budget = request["budget"]
    if type(budget) is not int or budget < 0:
        fail("INVALID_BUDGET", "budget must be a nonnegative integer, not a boolean", "$.budget")
    threshold = rational(request["threshold"], "$.threshold")
    scope = request["model_scope"]
    fields(scope, ("kind", "enumeration", "budget_scope"), "$.model_scope")
    if scope["kind"] not in ("global", "contextwise", "casewise") or type(scope["kind"]) is not str:
        fail("INVALID_SCOPE", "Unknown model scope", "$.model_scope.kind")
    if scope["enumeration"] != "explicit" or scope["budget_scope"] != "shared_total":
        fail("UNSUPPORTED_SCOPE", "Only explicit joint centres with a shared total budget are supported", "$.model_scope")
    matrix = request["matrix"]
    fields(matrix, ("canonicalisation", "sha256", "payload"), "$.matrix")
    if matrix["canonicalisation"] != CANONICALISATION:
        fail("UNSUPPORTED_CANONICALISATION", "Unknown matrix digest domain", "$.matrix.canonicalisation")
    hash_value(matrix["sha256"], "$.matrix.sha256")
    if digest(matrix["payload"]) != matrix["sha256"]:
        fail("MATRIX_HASH_MISMATCH", "Matrix digest does not match the supplied payload", "$.matrix.sha256")
    payload = matrix["payload"]
    fields(payload, ("cases", "conventions", "centres"), "$.matrix.payload")
    sequence(payload["cases"], "$.matrix.payload.cases", True)
    cases, seen = [], set()
    for i, item in enumerate(payload["cases"]):
        path = f"$.matrix.payload.cases[{i}]"
        fields(item, ("case_id", "context_id", "role", "checker_labels", "allowed_labels", "weight", "exception_eligible"), path)
        case_id = identifier(item["case_id"], path + ".case_id")
        if case_id in seen:
            fail("DUPLICATE_CASE_ID", "Each case_id must occur exactly once", path)
        seen.add(case_id)
        context_id = identifier(item["context_id"], path + ".context_id")
        if item["role"] not in ("frame", "external_query") or type(item["role"]) is not str:
            fail("INVALID_ROLE", "role must be frame or external_query", path + ".role")
        if type(item["exception_eligible"]) is not bool:
            fail("EXPLICIT_ELIGIBILITY_REQUIRED", "exception_eligible must be an explicit boolean", path)
        fields(item["checker_labels"], ("t", "b"), path + ".checker_labels")
        nullable = item["role"] == "external_query"
        t = label(item["checker_labels"]["t"], path + ".checker_labels.t", nullable)
        b = label(item["checker_labels"]["b"], path + ".checker_labels.b", nullable)
        if (t is None) != (b is None):
            fail("INCOMPLETE_CHECKER_PAIR", "External checker labels must be both null or both observed", path)
        weight = rational(item["weight"], path + ".weight")
        if nullable and weight != 0:
            fail("EXTERNAL_QUERY_WEIGHT", "An external query must explicitly have weight zero", path + ".weight")
        sequence(item["allowed_labels"], path + ".allowed_labels", True)
        for y in item["allowed_labels"]:
            label(y, path + ".allowed_labels")
        if len(set(item["allowed_labels"])) != len(item["allowed_labels"]):
            fail("DUPLICATE_ALLOWED_LABEL", "Local admissibility labels must be unique", path)
        cases.append(Case(case_id, context_id, item["role"], t, b,
                          tuple(y for y in LABELS if y in item["allowed_labels"]), weight, item["exception_eligible"]))
    if not any(case.role == "frame" for case in cases):
        fail("EMPTY_SCORED_FRAME", "At least one frame case is required", "$.matrix.payload.cases")
    case_ids = {case.case_id for case in cases}
    sequence(payload["conventions"], "$.matrix.payload.conventions", True)
    conventions, by_convention = [], {}
    for i, item in enumerate(payload["conventions"]):
        path = f"$.matrix.payload.conventions[{i}]"
        fields(item, ("convention_id", "version", "predictions"), path)
        convention_id = identifier(item["convention_id"], path + ".convention_id")
        identifier(item["version"], path + ".version")
        if convention_id in by_convention:
            fail("DUPLICATE_CONVENTION_ID", "Convention IDs must be unique", path)
        if type(item["predictions"]) is not dict or set(item["predictions"]) != case_ids:
            fail("CONVENTION_COVERAGE", "Every convention must predict every declared case exactly once", path)
        for y in item["predictions"].values():
            label(y, path + ".predictions")
        conventions.append(item)
        by_convention[convention_id] = item
    sequence(payload["centres"], "$.matrix.payload.centres", True)
    centres, centre_ids, joint_assignments = [], set(), set()
    for i, item in enumerate(payload["centres"]):
        path = f"$.matrix.payload.centres[{i}]"
        fields(item, ("centre_id", "convention_by_case"), path)
        centre_id = identifier(item["centre_id"], path + ".centre_id")
        if centre_id in centre_ids:
            fail("DUPLICATE_CENTRE_ID", "Centre IDs must be unique", path)
        centre_ids.add(centre_id)
        assignment = item["convention_by_case"]
        if type(assignment) is not dict or set(assignment) != case_ids:
            fail("CENTRE_COVERAGE", "A centre must assign a convention to every case exactly once", path)
        for value in assignment.values():
            if type(value) is not str or value not in by_convention:
                fail("UNKNOWN_CONVENTION", "Centre refers to an undeclared convention", path)
        values = tuple(assignment[c.case_id] for c in cases)
        if values in joint_assignments:
            fail("DUPLICATE_JOINT_CENTRE", "Duplicate joint assignments are not admitted", path)
        joint_assignments.add(values)
        if scope["kind"] == "global" and len(set(values)) != 1:
            fail("GLOBAL_SCOPE_VIOLATION", "A global centre must use one convention throughout the domain", path)
        if scope["kind"] == "contextwise":
            context_values = {}
            for case, value in zip(cases, values):
                if case.context_id in context_values and context_values[case.context_id] != value:
                    fail("CONTEXT_SCOPE_VIOLATION", "A contextwise centre must be constant within each context", path)
                context_values[case.context_id] = value
        predictions = tuple(by_convention[name]["predictions"][case.case_id] for case, name in zip(cases, values))
        centres.append(Centre(centre_id, values, predictions))
    sequence(request["observations"], "$.observations")
    observed, evidence_ids = {}, set()
    for i, observation in enumerate(request["observations"]):
        path = f"$.observations[{i}]"
        fields(observation, ("case_id", "label", "evidence"), path)
        case_id = identifier(observation["case_id"], path + ".case_id")
        if case_id not in case_ids:
            fail("UNKNOWN_OBSERVATION_CASE", "Observation is outside the declared domain", path)
        if case_id in observed:
            fail("DUPLICATE_OBSERVATION", "A case may have only one observation record, even when duplicate labels agree", path)
        observed[case_id] = label(observation["label"], path + ".label")
        evidence = observation["evidence"]
        fields(evidence, ("evidence_id", "canonicalisation", "sha256", "payload"), path + ".evidence")
        evidence_id = identifier(evidence["evidence_id"], path + ".evidence.evidence_id")
        if evidence_id in evidence_ids:
            fail("DUPLICATE_EVIDENCE_ID", "Evidence IDs must uniquely identify their observation records", path)
        evidence_ids.add(evidence_id)
        if evidence["canonicalisation"] != CANONICALISATION:
            fail("UNSUPPORTED_CANONICALISATION", "Unknown evidence digest domain", path + ".evidence")
        hash_value(evidence["sha256"], path + ".evidence.sha256")
        evidence_payload = evidence["payload"]
        fields(evidence_payload, ("case_id", "label", "basis"), path + ".evidence.payload")
        if evidence_payload["case_id"] != case_id or evidence_payload["label"] != observed[case_id]:
            fail("OBSERVATION_EVIDENCE_MISMATCH", "Evidence must bind this exact case_id and label", path)
        if type(evidence_payload["basis"]) is not str or not evidence_payload["basis"].strip():
            fail("MISSING_EVIDENCE_BASIS", "Evidence basis must be a nonempty description or source locator", path)
        if digest(evidence_payload) != evidence["sha256"]:
            fail("EVIDENCE_HASH_MISMATCH", "Evidence digest does not match its supplied payload", path)
    admissible = tuple(tuple(y for y in case.allowed if case.case_id not in observed or y == observed[case.case_id]) for case in cases)
    return Model(request, frame_id, tuple(cases), tuple(centres), tuple(conventions), admissible,
                 tuple(request["observations"]), budget, threshold, scope["kind"], digest(request), matrix["sha256"])
