"""Assertion implementation of the bounded P5 profile with explicit O15 aliases.

Only evidence and the neutral fixed profile are inputs. No producer, oracle,
mutation constructor or other candidate implementation is imported.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys

BOUND = 10**9
MAX_BYTES = 1048576
OBLIGATIONS = tuple(f'O{i:02d}' for i in range(1, 17))
ALIAS_GRAMMAR = {
    'version': 'NSC-O15-ALIAS-1', 'prefix': 'alias:',
    'lookup_key': 'exact_nonempty_suffix', 'max_hops': 1,
    'pointer_escapes': ['~0', '~1'],
    'array_index': 'canonical_nonnegative_decimal',
    'clause_id': 'O15.claim_source',
}


class AdmissionError(ValueError):
    def __init__(self, reason, pointer='', observed=None):
        super().__init__(reason)
        self.reason, self.pointer, self.observed = reason, pointer, observed


class MissingEvidence(ValueError):
    def __init__(self, path, pointer='', reason='MISSING_LOCAL_EVIDENCE'):
        super().__init__(reason)
        self.path, self.pointer, self.reason = path, pointer, reason


class Contradiction(ValueError):
    def __init__(self, reason, observed, expected, *, path=None, pointer=None):
        super().__init__(reason)
        self.reason, self.observed, self.expected = reason, observed, expected
        self.path, self.pointer = path, pointer


class AdmissionDecisionAlreadyRecorded(Exception):
    pass


class Pairs(list):
    pass


class NumericToken:
    def __init__(self, token, reason):
        self.token = token if len(token) <= 128 else {'token_prefix': token[:128], 'token_length': len(token)}
        self.reason = reason


def bounded_integer_token(token):
    # Avoid interpreter-specific decimal conversion limits before the pointer is known.
    if len(token.lstrip('-')) > 10:
        return NumericToken(token, 'INTEGER_BOUND')
    return int(token)


def pointer_part(value):
    return str(value).replace('~', '~0').replace('/', '~1')


def strict_json(data):
    """Bounded JSON admission with diagnostic paths, including rejected tokens."""
    if len(data) > MAX_BYTES:
        raise AdmissionError('JSON_BYTE_LIMIT', observed=len(data))
    try:
        source = data.decode('utf-8', errors='strict')
        parsed = json.loads(source, object_pairs_hook=Pairs,
                            parse_int=bounded_integer_token,
                            parse_float=lambda t: NumericToken(t, 'FLOAT_NOT_SUPPORTED'),
                            parse_constant=lambda t: NumericToken(t, 'NONFINITE_LITERAL'))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise AdmissionError('MALFORMED_JSON', observed=type(exc).__name__) from exc
    nodes = 0
    def visit(value, path, depth):
        nonlocal nodes
        nodes += 1
        if nodes > 20000 or depth > 32:
            raise AdmissionError('JSON_TREE_LIMIT', path)
        if isinstance(value, NumericToken):
            raise AdmissionError(value.reason, path, value.token)
        if isinstance(value, Pairs):
            out = {}
            for key, child in value:
                if key in out:
                    raise AdmissionError('DUPLICATE_JSON_KEY', path + '/' + pointer_part(key), key)
                valid_string(key, path)
                out[key] = visit(child, path + '/' + pointer_part(key), depth + 1)
            return out
        if type(value) is list:
            return [visit(x, path + '/' + str(i), depth + 1) for i, x in enumerate(value)]
        if type(value) is str:
            valid_string(value, path)
        elif type(value) is int:
            if abs(value) > BOUND:
                raise AdmissionError('INTEGER_BOUND', path, value)
        elif value is not None and type(value) is not bool:
            raise AdmissionError('UNSUPPORTED_JSON_TYPE', path, type(value).__name__)
        return value
    return visit(parsed, '', 0)


def valid_string(value, pointer=''):
    if len(value) > 10000 or any(0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise AdmissionError('INVALID_STRING', pointer)
    return value


def exact_int(value, pointer='', minimum=None):
    if type(value) is not int or abs(value) > BOUND or (minimum is not None and value < minimum):
        raise AdmissionError('EXPECTED_BOUNDED_INTEGER', pointer, value)
    return value


def rational(value, pointer='', *, internal=False):
    if type(value) is not dict or set(value) != {'numerator', 'denominator'}:
        raise AdmissionError('EXPECTED_RATIONAL_OBJECT', pointer, value)
    n, d = value['numerator'], value['denominator']
    if type(n) is not int or type(d) is not int or d <= 0:
        raise AdmissionError('EXPECTED_RATIONAL_COMPONENTS', pointer, value)
    if not internal and (abs(n) > BOUND or d > BOUND):
        raise AdmissionError('RATIONAL_BOUND', pointer, value)
    return Fraction(n, d)


def fraction_value(n, d=1):
    f = Fraction(n, d)
    return {'numerator': f.numerator, 'denominator': f.denominator}


def six_places(value):
    f = rational(value, internal=True)
    q, rem = divmod(abs(f.numerator) * 1000000, f.denominator)
    if 2 * rem > f.denominator or (2 * rem == f.denominator and q % 2):
        q += 1
    sign = '-' if f.numerator < 0 and q else ''
    return f'{sign}{q // 1000000}.{q % 1000000:06d}'


def equal(left, right):
    """Typed structural equality, with exact equality for rational leaves.

    Right-side references can be unbounded exact internally derived fractions.
    Retained left-side rational components must remain admitted.
    """
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        if 'numerator' in left or 'numerator' in right:
            try:
                return rational(left) == rational(right, internal=True)
            except AdmissionError:
                return False
        return set(left) == set(right) and all(equal(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(equal(a, b) for a, b in zip(left, right))
    return left == right


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_relative(value):
    if type(value) is not str or not value or '\\' in value:
        return False
    p = PurePosixPath(value)
    return not p.is_absolute() and all(x not in ('', '.', '..') for x in value.split('/'))


def object_fields(value, required, optional=(), pointer=''):
    if type(value) is not dict:
        raise AdmissionError('EXPECTED_OBJECT', pointer, value)
    missing = set(required) - set(value)
    if missing:
        key = sorted(missing)[0]
        raise AdmissionError('REQUIRED_FIELD_ABSENT', pointer + '/' + pointer_part(key), None)
    extra = set(value) - set(required) - set(optional)
    if extra:
        key = sorted(extra)[0]
        raise AdmissionError('UNSUPPORTED_FIELD', pointer + '/' + pointer_part(key), value[key])
    return value


def expected_type(value, kind, pointer=''):
    if type(value) is not kind:
        raise AdmissionError('EXPECTED_' + kind.__name__.upper(), pointer, value)
    if kind is str:
        valid_string(value, pointer)
    if kind is int:
        exact_int(value, pointer)
    return value


def strings(value, pointer=''):
    expected_type(value, list, pointer)
    for i, item in enumerate(value):
        expected_type(item, str, pointer + '/' + str(i))
    return value


def require(condition, reason, observed, expected, *, path=None, pointer=None):
    if not condition:
        raise Contradiction(reason, observed, expected, path=path, pointer=pointer)


def independently(*assertions):
    """An unavailable premise cannot suppress a separate readable contradiction."""
    missing = []
    for assertion in assertions:
        try:
            assertion()
        except MissingEvidence as exc:
            missing.append(exc)
    if missing:
        raise missing[0]


def keyed(rows, path, pointer='/rows', key='id'):
    """An ambiguous correspondence is unavailable to downstream predicates."""
    ids = [row[key] for row in rows]
    if len(set(ids)) != len(ids):
        raise MissingEvidence(path, pointer, 'AMBIGUOUS_STABLE_IDENTITIES')
    return dict(zip(ids, rows))


def admit_schema(value, schema, workflow, pointer=''):
    """Independent interpreter of the frozen declarative type grammar."""
    if type(schema) is str:
        if schema == 'null':
            if value is not None:
                raise AdmissionError('EXPECTED_NULL', pointer, value)
        elif schema in ('int', 'posint'):
            exact_int(value, pointer, 1 if schema == 'posint' else None)
        elif schema == 'str':
            expected_type(value, str, pointer)
            if not value:
                raise AdmissionError('EXPECTED_NONEMPTY_STRING', pointer, value)
        elif schema == 'bool':
            expected_type(value, bool, pointer)
        else:
            raise ValueError('unsupported fixed schema token')
        return
    if 'workflow_variant' in schema:
        if workflow not in schema['workflow_variant']:
            raise AdmissionError('UNSUPPORTED_WORKFLOW', '/workflow', workflow)
        return admit_schema(value, schema['workflow_variant'][workflow], workflow, pointer)
    if 'one_of' in schema:
        failures = []
        for possibility in schema['one_of']:
            try:
                admit_schema(value, possibility, workflow, pointer)
                return
            except AdmissionError as exc:
                failures.append(exc)
        # Keep the most specific known field location rather than a parent-only pointer.
        raise max(failures, key=lambda x: x.pointer.count('/'))
    if 'list' in schema:
        expected_type(value, list, pointer)
        for index, child in enumerate(value):
            admit_schema(child, schema['list'], workflow, pointer + '/' + str(index))
        return
    if 'map' in schema:
        expected_type(value, dict, pointer)
        for key, child in value.items():
            if not key:
                raise AdmissionError('EXPECTED_NONEMPTY_MAP_KEY', pointer, key)
            admit_schema(child, schema['map'], workflow, pointer + '/' + pointer_part(key))
        return
    if 'fields' in schema:
        required, optional = schema['fields'], schema.get('optional', {})
        object_fields(value, required, optional, pointer)
        for key, child in value.items():
            admit_schema(child, required.get(key, optional.get(key)), workflow, pointer + '/' + pointer_part(key))
        return
    raise ValueError('unsupported fixed schema descriptor')


def schema_uses_workflow(schema):
    if type(schema) is dict:
        return 'workflow_variant' in schema or any(schema_uses_workflow(x) for x in schema.values())
    if type(schema) is list:
        return any(schema_uses_workflow(x) for x in schema)
    return False


def resolve_pointer(value, pointer):
    if pointer == '':
        return value
    if type(pointer) is not str or not pointer.startswith('/'):
        raise ValueError('not an absolute JSON pointer')
    for encoded in pointer[1:].split('/'):
        key = encoded.replace('~1', '/').replace('~0', '~')
        if type(value) is list:
            if not key.isdigit() or (len(key) > 1 and key.startswith('0')):
                raise ValueError('invalid array pointer')
            value = value[int(key)]
        elif type(value) is dict:
            value = value[key]
        else:
            raise ValueError('pointer enters a scalar')
    return value


def resolve_claim_reference(value, aliases, reference):
    """Resolve exactly one explicit alias, then a strict retained-field pointer.

    This is specific to the new O15 grammar; other obligations retain their
    existing pointer semantics. Unicode alias names are exact opaque suffixes.
    """
    if reference.startswith('/'):
        pointer = reference
    elif reference.startswith('alias:') and reference[6:]:
        pointer = aliases.get(reference[6:])
    else:
        raise ValueError('unsupported claim reference')
    if type(pointer) is not str or not pointer.startswith('/'):
        raise ValueError('alias must resolve once to a nonempty direct pointer')
    for token in pointer[1:].split('/'):
        index = 0
        while index < len(token):
            if token[index] == '~':
                if index + 1 == len(token) or token[index + 1] not in '01':
                    raise ValueError('invalid claim pointer escape')
                index += 2
            else:
                index += 1
        key = token.replace('~1', '/').replace('~0', '~')
        if type(value) is dict:
            value = value[key]
        elif type(value) is list:
            if not key or any(c not in '0123456789' for c in key) or (len(key) > 1 and key[0] == '0'):
                raise ValueError('noncanonical claim array index')
            value = value[int(key)]
        else:
            raise ValueError('claim pointer enters a scalar')
    return pointer, value


def undefined(reason):
    return {'status': 'UNDEFINED', 'reason': reason}


def mean_available(values):
    present = [x for x in values if x is not None]
    return Fraction(sum(present), len(present)) if present else None


def retained_fraction(value):
    return fraction_value(value.numerator, value.denominator)


def ratio_value(numerator, denominator, missing_reason='MISSING_INPUT'):
    if numerator is None or denominator is None:
        return undefined(missing_reason)
    if denominator == 0:
        return undefined('ZERO_DENOMINATOR')
    return retained_fraction(Fraction(numerator) / Fraction(denominator))


class Bundle:
    def __init__(self, directory):
        self.directory = Path(directory)
        if self.directory.is_symlink() or not self.directory.is_dir():
            raise ValueError('case bundle must be a real directory')
        self.raw, self.values, self.errors, self.unsafe = {}, {}, {}, []
        total = 0
        for base, directories, files in os.walk(self.directory, followlinks=False):
            for name in list(directories):
                path = Path(base) / name
                if path.is_symlink():
                    self.unsafe.append(path.relative_to(self.directory).as_posix())
                    directories.remove(name)
            for name in sorted(files):
                path = Path(base) / name
                rel = path.relative_to(self.directory).as_posix()
                if not stat.S_ISREG(path.lstat().st_mode) or path.is_symlink():
                    self.unsafe.append(rel)
                    continue
                size = path.stat().st_size
                if size > MAX_BYTES or total + size > MAX_BYTES:
                    raise ValueError('case bundle exceeds byte limit')
                data = path.read_bytes()
                total += len(data)
                if total > MAX_BYTES:
                    raise ValueError('case bundle changed beyond byte limit')
                self.raw[rel] = data
                if rel.endswith('.json'):
                    try:
                        self.values[rel] = strict_json(data)
                    except AdmissionError as exc:
                        self.errors[rel] = exc

    def need(self, path, pointer=''):
        if path not in self.raw:
            raise MissingEvidence(path, pointer)
        if path in self.errors:
            raise MissingEvidence(path, pointer, 'INADMISSIBLE_LOCAL_EVIDENCE')
        if path not in self.values:
            raise MissingEvidence(path, pointer, 'NON_JSON_LOCAL_EVIDENCE')
        return self.values[path]


def create_report(path, value, bundle):
    path = Path(path)
    if path.resolve().is_relative_to(Path(bundle).resolve()):
        raise ValueError('report output must be outside the case bundle')
    data = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8') + b'\n'
    if len(data) > MAX_BYTES:
        raise ValueError('report exceeds byte limit')
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())


# Normative identifier/locator data, copied from the neutral interface, not candidate code.
LOCATORS = {'O01': {'node_id': 'R01',
         'edge_id': None,
         'path': 'records/R01.json',
         'json_pointer': '/semantic_digest/value',
         'obligation_id': 'O01',
         'predicate_instance_id': 'P3BENCH-PRED-O01-SEMANTIC_COMMITMENT_R01'},
 'O02': {'node_id': 'INVENTORY',
         'edge_id': None,
         'path': 'inventory.json',
         'json_pointer': '/members',
         'obligation_id': 'O02',
         'predicate_instance_id': 'P3BENCH-PRED-O02-RAW_INVENTORY_MEMBERSHIP'},
 'O03': {'node_id': 'R03',
         'edge_id': 'CONFIG_RESOLUTION',
         'path': 'records/R03.json',
         'json_pointer': '/executed',
         'obligation_id': 'O03',
         'predicate_instance_id': 'P3BENCH-PRED-O03-CONFIG_RESOLUTION_TRIPLE'},
 'O04': {'node_id': 'R04',
         'edge_id': 'SOURCE_ANCHOR',
         'path': 'records/R04.json',
         'json_pointer': '/executed_source_sha256',
         'obligation_id': 'O04',
         'predicate_instance_id': 'P3BENCH-PRED-O04-APPROVED_SOURCE_RUNTIME_ANCHOR'},
 'O05': {'node_id': 'R05',
         'edge_id': 'DATA_STATE_ALIGNMENT',
         'path': 'records/R05_alignment_receipt.json',
         'json_pointer': '',
         'obligation_id': 'O05',
         'predicate_instance_id': 'P3BENCH-PRED-O05-KEYED_FACTS_POSITIONAL_RECEIPT'},
 'O06': {'node_id': 'R06',
         'edge_id': 'POPULATION_SOURCE_MAP',
         'path': 'records/R06_materialisation.json',
         'json_pointer': '/populations',
         'obligation_id': 'O06',
         'predicate_instance_id': 'P3BENCH-PRED-O06-DECLARED_POPULATION_MEMBERSHIP'},
 'O07': {'node_id': 'STATES',
         'edge_id': 'DATA_STATE_COHERENCE',
         'path': 'data/states_or_change_facts.json',
         'json_pointer': '/rows',
         'obligation_id': 'O07',
         'predicate_instance_id': 'P3BENCH-PRED-O07-WORKFLOW_SPECIFIC_STATE_COHERENCE'},
 'O08': {'node_id': 'R08',
         'edge_id': None,
         'path': 'records/R08_measurement_policy.json',
         'json_pointer': '',
         'obligation_id': 'O08',
         'predicate_instance_id': 'P3BENCH-PRED-O08-MEASUREMENT_POLICY_STAGE_AUTHORITY'},
 'O09': {'node_id': 'R09',
         'edge_id': 'TARGET_METHOD',
         'path': 'records/R09_estimand.json',
         'json_pointer': '/actual_method',
         'obligation_id': 'O09',
         'predicate_instance_id': 'P3BENCH-PRED-O09-TARGET_ACTUAL_METHOD_RELATION'},
 'O10': {'node_id': 'R10',
         'edge_id': None,
         'path': 'records/R10_design_profile.json',
         'json_pointer': '/requested_operation',
         'obligation_id': 'O10',
         'predicate_instance_id': 'P3BENCH-PRED-O10-SUPPORTED_OPERATION_APPLICABILITY'},
 'O11': {'node_id': 'R11',
         'edge_id': 'FORMULA_RESULT',
         'path': 'records/R11_result.json',
         'json_pointer': '/values',
         'obligation_id': 'O11',
         'predicate_instance_id': 'P3BENCH-PRED-O11-RETAINED_FORMULA_RELATION'},
 'O12': {'node_id': 'R12',
         'edge_id': 'RESULT_CONSUMER',
         'path': 'records/R12_consumer.json',
         'json_pointer': '',
         'obligation_id': 'O12',
         'predicate_instance_id': 'P3BENCH-PRED-O12-AUTHORITATIVE_CONSUMER_RELATION'},
 'O13': {'node_id': 'R13',
         'edge_id': 'TASK_UNIVERSE_PARTITION',
         'path': 'records/R13.json',
         'json_pointer': '',
         'obligation_id': 'O13',
         'predicate_instance_id': 'P3BENCH-PRED-O13-FROZEN_TASK_PARTITION_DENOMINATOR'},
 'O14': {'node_id': 'R14',
         'edge_id': 'WAIT_TERMINAL',
         'path': 'records/R14.json',
         'json_pointer': '/claimed_terminal_status',
         'obligation_id': 'O14',
         'predicate_instance_id': 'P3BENCH-PRED-O14-WAIT_OUTPUT_TERMINAL_RELATION'},
 'O15': {'node_id': 'R15',
         'edge_id': 'CLAIM_SOURCE',
         'path': 'records/R15_claims.json',
         'json_pointer': '/claims',
         'obligation_id': 'O15',
         'predicate_instance_id': 'P3BENCH-PRED-O15-QUANTIFIED_CLAIM_SOURCE_EDGE'},
 'O16': {'node_id': 'R16',
         'edge_id': 'ASSURANCE_SCOPE',
         'path': 'records/R16.json',
         'json_pointer': '',
         'obligation_id': 'O16',
         'predicate_instance_id': 'P3BENCH-PRED-O16-ARTEFACT_ASSURANCE_SCOPE'}}
PREDICATES = {'O01': 'P3BENCH-PRED-O01-SEMANTIC_COMMITMENT_R01',
 'O02': 'P3BENCH-PRED-O02-RAW_INVENTORY_MEMBERSHIP',
 'O03': 'P3BENCH-PRED-O03-CONFIG_RESOLUTION_TRIPLE',
 'O04': 'P3BENCH-PRED-O04-APPROVED_SOURCE_RUNTIME_ANCHOR',
 'O05': 'P3BENCH-PRED-O05-KEYED_FACTS_POSITIONAL_RECEIPT',
 'O06': 'P3BENCH-PRED-O06-DECLARED_POPULATION_MEMBERSHIP',
 'O07': 'P3BENCH-PRED-O07-WORKFLOW_SPECIFIC_STATE_COHERENCE',
 'O08': 'P3BENCH-PRED-O08-MEASUREMENT_POLICY_STAGE_AUTHORITY',
 'O09': 'P3BENCH-PRED-O09-TARGET_ACTUAL_METHOD_RELATION',
 'O10': 'P3BENCH-PRED-O10-SUPPORTED_OPERATION_APPLICABILITY',
 'O11': 'P3BENCH-PRED-O11-RETAINED_FORMULA_RELATION',
 'O12': 'P3BENCH-PRED-O12-AUTHORITATIVE_CONSUMER_RELATION',
 'O13': 'P3BENCH-PRED-O13-FROZEN_TASK_PARTITION_DENOMINATOR',
 'O14': 'P3BENCH-PRED-O14-WAIT_OUTPUT_TERMINAL_RELATION',
 'O15': 'P3BENCH-PRED-O15-QUANTIFIED_CLAIM_SOURCE_EDGE',
 'O16': 'P3BENCH-PRED-O16-ARTEFACT_ASSURANCE_SCOPE'}


class AssertionChecker:
    def __init__(self, bundle, profile):
        self.bundle = Bundle(bundle)
        self.profile = profile
        self.vector = {o: 'U' for o in OBLIGATIONS}
        self.diagnostics = []
        header = self.bundle.values.get('bundle.json')
        self.workflow = header.get('workflow') if type(header) is dict else None
        self.context_blocked = set()
        for path, obj in self.bundle.values.items():
            schema = profile['schemas'].get(path)
            if schema is None or path in self.bundle.errors:
                continue
            if self.workflow not in profile['workflow_ids'] and schema_uses_workflow(schema):
                self.context_blocked.add(path)
                continue
            try:
                admit_schema(obj, schema, self.workflow)
            except AdmissionError as exc:
                self.bundle.errors[path] = exc
        if 'bundle.json' not in self.bundle.errors and header is not None:
            if self.workflow not in profile['workflow_ids']:
                self.bundle.errors['bundle.json'] = AdmissionError('UNSUPPORTED_WORKFLOW', '/workflow', self.workflow)
            elif header['schema'] != 'nsc-p4-evidence/2':
                self.bundle.errors['bundle.json'] = AdmissionError('BUNDLE_SCHEMA_ID', '/schema', header['schema'])
            elif header['profile_id'] != profile['profile_id']:
                self.bundle.errors['bundle.json'] = AdmissionError('PROFILE_ID', '/profile_id', header['profile_id'])

    def doc(self, path):
        if path in self.context_blocked:
            self.require_workflow()
        return self.bundle.need(path)

    def require_workflow(self):
        if self.workflow not in self.profile['workflow_ids']:
            raise MissingEvidence('bundle.json', reason='UNAVAILABLE_WORKFLOW_CONTEXT')

    def diagnostic(self, obligation, kind, reason, observed, expected, *, path=None, pointer=None, file_node=False):
        loc = dict(LOCATORS[obligation])
        if path is not None:
            loc.update(path=path, json_pointer=pointer if pointer is not None else '')
        if file_node:
            loc.update(node_id='FILE:' + loc['path'], edge_id=None)
        self.diagnostics.append({**loc, 'kind': kind, 'reason_code': reason,
                                 'observed': observed, 'expected': expected,
                                 'numerical_policy': 'C01/C02' if obligation in ('O11','O12','O15') else 'C00/C03'})

    def check(self):
        for oid in OBLIGATIONS:
            try:
                getattr(self, oid.lower())()
                self.vector[oid] = 'S'
            except Contradiction as exc:
                self.vector[oid] = 'V'
                self.diagnostic(oid, 'DIRECT_VIOLATION', exc.reason, exc.observed, exc.expected,
                                path=exc.path, pointer=exc.pointer)
            except MissingEvidence as exc:
                self.vector[oid] = 'U'
                self.diagnostic(oid, 'DEPENDENCY_U', exc.reason, None, 'Sufficient admitted local evidence',
                                path=exc.path, pointer=exc.pointer, file_node=True)
            except AdmissionDecisionAlreadyRecorded:
                self.vector[oid] = 'V'
        aggregate = 'REJECT' if 'V' in self.vector.values() else ('INDETERMINATE' if 'U' in self.vector.values() else 'ALLOW_WITHIN_SCOPE')
        return {'obligation_vector': self.vector, 'coverage_mask': {o: True for o in OBLIGATIONS},
                'aggregate': aggregate, 'diagnostics': self.diagnostics}

    def o01(self):
        if self.bundle.errors:
            for path, exc in sorted(self.bundle.errors.items()):
                self.diagnostic('O01', 'DIRECT_VIOLATION', exc.reason, exc.observed,
                                'Admitted strict typed JSON under the fixed profile', path=path,
                                pointer=exc.pointer, file_node=True)
            # Mark the obligation without appending a duplicate canonical digest allegation.
            self.vector['O01'] = 'V'
            raise AdmissionDecisionAlreadyRecorded()
        independently(self.require_workflow, self.semantic_digest_domain, self.semantic_digest_value)

    def semantic_digest_domain(self):
        record = self.doc('records/R01.json')['semantic_digest']
        require(record['domain'] == 'canonical-json-v1' and record['algorithm'] == 'sha256',
                'UNSUPPORTED_SEMANTIC_DIGEST_DOMAIN', record,
                {'domain': 'canonical-json-v1', 'algorithm': 'sha256'})

    def semantic_digest_value(self):
        semantic = self.doc('semantic_payload.json')
        record = self.doc('records/R01.json')['semantic_digest']
        expected = {'domain': 'canonical-json-v1', 'algorithm': 'sha256', 'value': digest(canonical(semantic))}
        require(equal(record, expected), 'SEMANTIC_COMMITMENT_MISMATCH', record, expected)

    def o02(self):
        record = self.doc('inventory.json')['members']
        actual = [{'path': p, 'bytes': len(data), 'sha256': digest(data)} for p, data in sorted(self.bundle.raw.items()) if p != 'inventory.json']
        required = set(self.profile['required_paths'])
        present = set(self.bundle.raw)
        permitted = required | set(self.profile['optional_paths'])
        require(not self.bundle.unsafe, 'UNSAFE_BUNDLE_MEMBER', self.bundle.unsafe, [])
        require(required <= present and present <= permitted, 'CLOSED_MEMBER_SET', sorted(present), sorted(required))
        require(all(safe_relative(x['path']) for x in record), 'UNSAFE_INVENTORY_PATH', [x['path'] for x in record], 'Safe relative paths')
        require(equal(record, actual), 'RAW_INVENTORY_MISMATCH', record, actual)

    def o03(self):
        independently(self.config_record_local, self.config_effective_local,
                      self.config_executed_resolution, self.config_resolution)

    def config_record_local(self):
        record = self.doc('records/R03.json')
        declared = record['declared']
        keys = {'config_id', 'method', 'strict'}
        require(set(declared) <= keys, 'UNSUPPORTED_EXECUTABLE_KEY', sorted(declared), sorted(keys))
        for key, value in declared.items():
            want = bool if key == 'strict' else str
            require(type(value) is want and (key == 'strict' or bool(value)), 'DECLARED_SETTING_TYPE', {key: value}, want.__name__)
        self.require_workflow()
        require(record['executed']['method'] in self.profile['supported_methods'][self.workflow], 'UNSUPPORTED_METHOD', record['executed']['method'], self.profile['supported_methods'][self.workflow])

    def config_effective_local(self):
        effective = self.doc('records/R03_effective.json')['effective']
        self.require_workflow()
        require(effective['method'] in self.profile['supported_methods'][self.workflow], 'UNSUPPORTED_METHOD', effective['method'], self.profile['supported_methods'][self.workflow])

    def config_resolution(self):
        record = self.doc('records/R03.json')
        declared = record['declared']
        effective = self.doc('records/R03_effective.json')['effective']
        self.require_workflow()
        resolved = {**self.profile['configuration_defaults'][self.workflow], **declared}
        require(equal(effective, resolved) and equal(record['executed'], resolved), 'CONFIG_RESOLUTION_MISMATCH', {'effective': effective, 'executed': record['executed']}, resolved)

    def config_executed_resolution(self):
        record = self.doc('records/R03.json')
        self.require_workflow()
        resolved = {**self.profile['configuration_defaults'][self.workflow], **record['declared']}
        require(equal(record['executed'], resolved), 'EXECUTED_CONFIG_RESOLUTION_MISMATCH', record['executed'], resolved)

    def o04(self):
        independently(self.source_anchor_domain, self.source_identity)

    def source_anchor_domain(self):
        anchor = self.doc('records/R04_expected_anchor.json')
        expected = {'source_sha256': self.profile['source_sha256'], 'runtime_id': self.profile['runtime_id']}
        require(equal(anchor, expected), 'FIXED_SOURCE_RUNTIME_ANCHOR_MISMATCH', anchor, expected)

    def source_identity(self):
        record = self.doc('records/R04.json')
        anchor = self.doc('records/R04_expected_anchor.json')
        if 'source/producer.txt' not in self.bundle.raw:
            raise MissingEvidence('source/producer.txt')
        actual = digest(self.bundle.raw['source/producer.txt'])
        expected = {'source_sha256': self.profile['source_sha256'], 'runtime_id': self.profile['runtime_id']}
        require(equal(anchor, expected) and record['executed_source_sha256'] == actual == anchor['source_sha256'] and record['runtime_id'] == anchor['runtime_id'],
                'SOURCE_RUNTIME_IDENTITY_MISMATCH', {'record': record, 'anchor': anchor, 'actual_source_sha256': actual}, expected)

    def o05(self):
        independently(lambda: self.unique_frame('data/rows.json'),
                      lambda: self.unique_frame('data/states_or_change_facts.json'),
                      self.alignment_assurance, self.alignment_sequences)

    def unique_frame(self, path):
        identifiers = [x['id'] for x in self.doc(path)['rows']]
        require(len(set(identifiers)) == len(identifiers), 'DUPLICATE_STABLE_ID',
                {'path': path, 'ids': identifiers}, 'Unique identifiers in each frame')

    def alignment_assurance(self):
        receipt = self.doc('records/R05_alignment_receipt.json')
        require(receipt['producer_authenticated'] is False and receipt['initial_pairing_verified'] is False,
                'UNSUPPORTED_ALIGNMENT_ASSURANCE', receipt, 'No producer or original-pairing authentication')

    def alignment_sequences(self):
        data = self.doc('data/rows.json')['rows']
        states = self.doc('data/states_or_change_facts.json')['rows']
        receipt = self.doc('records/R05_alignment_receipt.json')
        data_ids, state_ids = [x['id'] for x in data], [x['id'] for x in states]
        require(data_ids == state_ids == receipt['data_ids'] == receipt['state_ids'], 'POSITIONAL_RECEIPT_MISMATCH', {'data': data_ids, 'state': state_ids, 'receipt': receipt}, 'Equal physical identifier sequences')

    def o06(self):
        populations = self.doc('records/R06_materialisation.json')['populations']
        names = [x['population_id'] for x in populations]
        require(len(names) == len(set(names)), 'DUPLICATE_POPULATION', names, 'Unique population IDs')
        for pop in populations:
            ids, positions = pop['ids'], pop['local_to_source_positions']
            require(len(ids) == len(positions) and len(set(ids)) == len(ids) and len(set(positions)) == len(positions) and all(x >= 0 for x in positions),
                    'INVALID_POPULATION_LOCAL_MAP', pop, 'Unique equally sized IDs and nonnegative source positions')
        data = self.doc('data/rows.json')['rows']
        states = self.doc('data/states_or_change_facts.json')['rows']
        dm, sm = keyed(data, 'data/rows.json'), keyed(states, 'data/states_or_change_facts.json')
        if set(dm) != set(sm):
            raise MissingEvidence('data/states_or_change_facts.json', '/rows', 'INCOMPLETE_KEYED_CORRESPONDENCE')
        if self.workflow == 'W1':
            if any(x['state'] not in self.profile['response_states'] for x in states):
                raise MissingEvidence('data/states_or_change_facts.json', '/rows', 'UNKNOWN_ELIGIBILITY_STATE')
            expected = {'eligible': {x['id'] for x in states if x['state'] == 'observed' and dm[x['id']]['readiness'] in self.profile['category_order']}}
        else:
            if any(x[k] not in self.profile['input_states'] for x in states for k in ('staff_input', 'turnover_input')):
                raise MissingEvidence('data/states_or_change_facts.json', '/rows', 'UNKNOWN_ELIGIBILITY_STATE')
            expected = {
                'staff_available': {x['id'] for x in states if x['staff_input'] == 'available'},
                'turnover_available': {x['id'] for x in states if x['turnover_input'] == 'available'},
                'staff_imputation': {x['id'] for x in states if x['staff_input'] == 'missing' and x['turnover_input'] == 'available'},
            }
        require(set(names) == set(expected), 'POPULATION_SET_MISMATCH', names, sorted(expected))
        source_positions = {row['id']: i for i, row in enumerate(data)}
        for pop in populations:
            require(set(pop['ids']) == expected[pop['population_id']], 'POPULATION_MEMBERSHIP_MISMATCH', pop, sorted(expected[pop['population_id']]))
            wanted = [source_positions[x] for x in pop['ids']]
            require(pop['local_to_source_positions'] == wanted, 'SOURCE_POSITION_MISMATCH', pop['local_to_source_positions'], wanted)

    def o07(self):
        independently(self.state_domain, self.data_domain, self.state_coherence)

    def state_domain(self):
        states = self.doc('data/states_or_change_facts.json')['rows']
        if self.workflow == 'W1':
            require(all(x['state'] in self.profile['response_states'] for x in states), 'UNKNOWN_RESPONSE_STATE', states, self.profile['response_states'])
        else:
            require(all(x[k] in self.profile['input_states'] for x in states for k in ('staff_input','turnover_input')), 'UNKNOWN_INPUT_STATE', states, self.profile['input_states'])
            require(all(x[k] in self.profile['change_states'] for x in states for k in ('staff_change','other_rev_change')), 'UNKNOWN_CHANGE_STATE', states, self.profile['change_states'])

    def data_domain(self):
        if self.workflow == 'W1':
            data = self.doc('data/rows.json')['rows']
            require(all(x['readiness'] is None or x['readiness'] in self.profile['category_order'] for x in data), 'UNKNOWN_CATEGORY', data, self.profile['category_order'])

    def state_coherence(self):
        states = self.doc('data/states_or_change_facts.json')['rows']
        data = self.doc('data/rows.json')['rows']
        outputs = self.doc('data/output_rows.json')['rows']
        dm, sm, om = keyed(data, 'data/rows.json'), keyed(states, 'data/states_or_change_facts.json'), keyed(outputs, 'data/output_rows.json')
        if set(dm) != set(sm) or set(dm) != set(om):
            raise MissingEvidence('data/states_or_change_facts.json', '/rows', 'INCOMPLETE_KEYED_CORRESPONDENCE')
        for ident, row in dm.items():
            state, output = sm[ident], om[ident]
            if self.workflow == 'W1':
                require((state['state'] == 'observed') == (row['readiness'] is not None), 'RESPONSE_VALUE_STATE_MISMATCH', {'row':row,'state':state}, 'Observed iff readiness is physically present')
            else:
                require(state['staff_input'] == ('missing' if row['staff'] is None else 'available') and state['turnover_input'] == ('missing' if row['turnover'] is None else 'available'),
                        'ORIGINAL_AVAILABILITY_MISMATCH', {'row':row,'state':state}, 'Availability reflects original nullness')
                staff = output['staff']
                defined = 'numerator' in staff
                require(defined or staff['status'] == 'UNDEFINED', 'UNSUPPORTED_OUTPUT_VALUE_STATE', staff, 'An exact rational or explicit UNDEFINED value')
                if not defined:
                    staff_change = 'undefined'
                elif row['staff'] is None:
                    staff_change = 'imputed'
                else:
                    staff_change = 'unchanged' if equal(staff, fraction_value(row['staff'])) else 'edited'
                other_change = 'imputed' if row['other.rev'] is None else ('unchanged' if equal(output['other.rev'], fraction_value(row['other.rev'])) else 'edited')
                require(state['staff_change'] == staff_change and state['other_rev_change'] == other_change,
                        'OUTPUT_CHANGE_STATE_MISMATCH', state, {'staff_change':staff_change,'other_rev_change':other_change})

    def o08(self):
        record = self.doc('records/R08_measurement_policy.json')
        if self.workflow == 'W1':
            categories = self.profile['category_order']
            codes = record['display_codes']
            ordered = [codes[x] for x in categories] if set(codes) == set(categories) else []
            require(record['category_order'] == categories and set(codes) == set(categories) and all(a < b for a,b in zip(ordered, ordered[1:])) and record['allows_arithmetic_mean'] is False,
                    'ORDINAL_MEASUREMENT_POLICY', record, 'Fixed categories, increasing display codes and no interval-mean permission')
        else:
            require(not record['executed_staff_imputation'] or (record['allow_staff_imputation'] and record['input_and_change_states_separate']),
                    'IMPUTATION_PERMISSION_MISMATCH', record, 'Executed imputation explicitly permitted with separate input/change facts')

    def o09(self):
        record = self.doc('records/R09_estimand.json')
        self.require_workflow()
        representations = ('counts_and_denominator','exact_proportions') if self.workflow == 'W1' else ('separate_supports','explicit_ratio')
        require(record['target'] == self.profile['target_method'][self.workflow] and record['actual_method'] in self.profile['supported_methods'][self.workflow] and record['representation'] in representations,
                'UNSUPPORTED_TARGET_METHOD', record, {'target':self.profile['target_method'][self.workflow],'methods':self.profile['supported_methods'][self.workflow],'representations':list(representations)})
        require(len(set(record['population_ids'])) == len(record['population_ids']) and set(record['population_ids']) == set(self.profile['population_ids'][self.workflow]),
                'TARGET_POPULATION_NAMES', record['population_ids'], self.profile['population_ids'][self.workflow])
        material = self.doc('records/R06_materialisation.json')
        self.doc('data/states_or_change_facts.json')
        require(set(x['population_id'] for x in material['populations']) == set(record['population_ids']), 'TARGET_MATERIALISATION_NAMES', material['populations'], record['population_ids'])
        require(record['actual_method'] == self.profile['target_method'][self.workflow], 'ACTUAL_METHOD_TARGET_MISMATCH', record['actual_method'], self.profile['target_method'][self.workflow])

    def o10(self):
        record = self.doc('records/R10_design_profile.json')
        require(record['supported_operations'] == self.profile['supported_operations'] and record['requested_operation'] in self.profile['supported_operations'] and not record['population_generalisation'] and not record['causal_claim'],
                'UNSUPPORTED_DESIGN_OR_ASSURANCE', record, self.profile['supported_operations'])

    def o11(self):
        independently(self.formula_arithmetic_and_binding, self.formula_registry_version)

    def formula_registry_version(self):
        registry = self.doc('records/R11_formula_registry.json')
        require(registry['formula_version'] == self.profile['formula_version'],
                'FIXED_FORMULA_VERSION_MISMATCH', registry['formula_version'], self.profile['formula_version'])

    def formula_arithmetic_and_binding(self):
        result = self.doc('records/R11_result.json')
        require(result['status'] == 'COMPLETE', 'RESULT_STATUS_MISMATCH', result['status'], 'COMPLETE')
        method, operands = result['method'], result['operands']
        require(method in self.profile['supported_methods'][self.workflow], 'UNSUPPORTED_FORMULA_METHOD', method, self.profile['supported_methods'][self.workflow])
        if self.workflow == 'W1':
            labels = operands['selected_labels']
            categories = self.profile['category_order']
            require(operands['category_order'] == categories and all(x in categories for x in labels), 'INVALID_RETAINED_CATEGORY_OPERAND', operands, categories)
            codes = operands['display_codes']
            require(set(codes) == set(categories), 'DISPLAY_CODE_DOMAIN', sorted(codes), categories)
            counts = {label: labels.count(label) for label in categories}
            denominator = len(labels)
            proportions = {label: fraction_value(counts[label], denominator) if denominator else undefined('EMPTY_SUPPORT') for label in categories}
            expected = {'counts': counts, 'denominator': denominator, 'proportions': proportions}
            if method == 'ordinal_mean':
                expected['mean_code'] = fraction_value(sum(codes[x] for x in labels), denominator) if denominator else undefined('EMPTY_SUPPORT')
        else:
            rows = operands['rows']
            identifiers = [x['id'] for x in rows]
            require(len(set(identifiers)) == len(identifiers), 'AMBIGUOUS_RETAINED_ARITHMETIC_ROWS', identifiers, 'Unique retained operand IDs')
            mean_staff = mean_available([x['staff'] for x in rows])
            mean_turnover = mean_available([x['turnover'] for x in rows])
            if method == 'ratio_of_means':
                if mean_staff is None or mean_turnover is None:
                    ratio = None
                    ratio_record = undefined('EMPTY_SUPPORT')
                elif mean_turnover == 0:
                    ratio = None
                    ratio_record = undefined('ZERO_DENOMINATOR')
                else:
                    ratio = mean_staff / mean_turnover
                    ratio_record = retained_fraction(ratio)
            else:
                ratios = [Fraction(x['staff'],x['turnover']) for x in rows if x['staff'] is not None and x['turnover'] is not None and x['turnover'] != 0]
                ratio = sum(ratios,Fraction(0)) / len(ratios) if ratios else None
                ratio_record = retained_fraction(ratio) if ratio is not None else undefined('EMPTY_SUPPORT')
            expected = {
                'mean_staff': retained_fraction(mean_staff) if mean_staff is not None else undefined('EMPTY_SUPPORT'),
                'mean_turnover': retained_fraction(mean_turnover) if mean_turnover is not None else undefined('EMPTY_SUPPORT'),
                'ratio': ratio_record,
                'staff_output': {}, 'other_rev_output': {}, 'turnover_ratio': {},
            }
            for row in rows:
                ident = row['id']
                if row['staff'] is not None:
                    staff = fraction_value(row['staff'])
                elif row['turnover'] is not None and ratio is not None:
                    staff = retained_fraction(ratio * row['turnover'])
                else:
                    staff = undefined('MISSING_INPUT')
                expected['staff_output'][ident] = staff
                expected['other_rev_output'][ident] = fraction_value(abs(row['other.rev']) if row['other.rev'] is not None else 0)
                expected['turnover_ratio'][ident] = undefined('MISSING_TURNOVER') if row['turnover'] is None else ratio_value(row['turnover'],row['total.rev'])
        require(equal(result['values'], expected), 'RETAINED_ARITHMETIC_MISMATCH', result['values'], expected)
        for pointer, rendered in result.get('displays', {}).items():
            try:
                reference = resolve_pointer(result['values'], pointer)
                wanted = six_places(reference)
            except (KeyError, IndexError, ValueError, TypeError, AdmissionError):
                raise Contradiction('UNRESOLVED_OR_UNDEFINED_DISPLAY', {'pointer':pointer,'display':rendered}, 'A rational value with exact six-place rendering')
            require(rendered == wanted, 'SIX_PLACE_DISPLAY_MISMATCH', rendered, wanted)
        registry = self.doc('records/R11_formula_registry.json')
        require(registry['method'] == method and registry['formula_version'] == self.profile['formula_version'], 'FORMULA_REGISTRY_BINDING', registry, {'method':method,'formula_version':self.profile['formula_version']})

    def o12(self):
        consumer = self.doc('records/R12_consumer.json')
        source = self.doc('records/R11_result.json')
        wanted = {k: source[k] for k in ('result_id','status','values')}
        if 'displays' in source:
            wanted['displays'] = source['displays']
        require(equal(consumer, wanted), 'RESULT_CONSUMER_MISMATCH', consumer, wanted)

    def o13(self):
        independently(self.task_accounting_and_universe, self.task_universe_uniqueness)

    def task_universe_uniqueness(self):
        universe = self.doc('records/R13_task_universe.json')['task_ids']
        require(len(universe) == len(set(universe)), 'DUPLICATE_UNIVERSE_TASK_ID', universe, 'Unique frozen task IDs')

    def task_accounting_and_universe(self):
        record = self.doc('records/R13.json')
        tasks = record['tasks']
        rows = [{'task_id':k,'status':v} for k,v in tasks.items()] if type(tasks) is dict else tasks
        identifiers = [x['task_id'] for x in rows]
        require(len(identifiers) == len(set(identifiers)), 'DUPLICATE_TASK_ID', identifiers, 'Unique task IDs')
        statuses = self.profile['terminal_statuses']
        require(all(x['status'] in statuses for x in rows), 'UNSUPPORTED_TASK_DISPOSITION', rows, statuses)
        counts = {s:sum(x['status'] == s for x in rows) for s in statuses}
        require(equal(record['counts'], counts) and record['reported_attempted_denominator'] == counts['SUCCEEDED'] + counts['FAILED'],
                'TASK_ACCOUNTING_DENOMINATOR', record, {'counts':counts,'reported_attempted_denominator':counts['SUCCEEDED']+counts['FAILED']})
        universe = self.doc('records/R13_task_universe.json')['task_ids']
        require(len(universe) == len(set(universe)) and set(identifiers) == set(universe), 'TASK_UNIVERSE_MISMATCH', identifiers, universe)

    def o14(self):
        record = self.doc('records/R14.json')
        require(record['claimed_terminal_status'] in ('SUCCEEDED','FAILED'), 'UNSUPPORTED_TERMINAL_CLAIM', record['claimed_terminal_status'], ['SUCCEEDED','FAILED'])
        wait = self.doc('records/R14_wait_receipt.json')
        universe = self.doc('records/R13_task_universe.json')['task_ids']
        require(record['task_id'] == wait['task_id'] and record['task_id'] in universe, 'TERMINAL_TASK_BINDING', {'record':record['task_id'],'wait':wait['task_id']}, universe)
        success = wait['exit_code'] == 0 and wait['result_present'] and wait['guard_closed']
        wanted = 'SUCCEEDED' if success else 'FAILED'
        require(record['claimed_terminal_status'] == wanted and record['claimed_closed'] == wait['guard_closed'] and (success or not record['claimed_closed']),
                'WAIT_TERMINAL_MISMATCH', {'claim':record,'wait':wait}, {'claimed_terminal_status':wanted,'claimed_closed':bool(success)})

    def o15(self):
        independently(self.claim_identifiers, self.claim_result_binding, self.claim_sources)

    def claim_identifiers(self):
        claims = self.doc('records/R15_claims.json')['claims']
        identifiers = [x['claim_id'] for x in claims]
        require(len(identifiers) == len(set(identifiers)), 'DUPLICATE_CLAIM_ID', identifiers, 'Unique claim IDs')

    def claim_result_binding(self):
        edges = self.doc('records/R15_edges.json')
        result = self.doc('records/R11_result.json')
        require(edges['result_id'] == result['result_id'], 'CLAIM_RESULT_BINDING', edges['result_id'], result['result_id'])

    def claim_sources(self):
        claims = self.doc('records/R15_claims.json')['claims']
        edges = self.doc('records/R15_edges.json')
        result = self.doc('records/R11_result.json')
        for claim in claims:
            try:
                pointer, wanted = resolve_claim_reference(result, edges['aliases'], claim['source_pointer'])
                metadata = edges['field_metadata'][pointer]
            except (KeyError, IndexError, ValueError, TypeError):
                raise Contradiction('UNRESOLVED_CLAIM_SOURCE', claim['source_pointer'], 'One explicit alias or direct pointer designating a result value with metadata')
            expected_meta = {key: claim[key] for key in ('unit','denominator','scope')}
            require(equal(claim['value'], wanted) and equal(expected_meta, metadata), 'CLAIM_VALUE_OR_SCOPE_MISMATCH', claim, {'value':wanted,**metadata})

    def o16(self):
        independently(self.assurance_claim, self.assurance_limitations)

    def assurance_claim(self):
        record = self.doc('records/R16.json')
        flags = ('producer_authenticated','initial_pairing_verified','scientific_validity_certified','programme_complete')
        expected = {key:False for key in flags}
        expected['historical_P1'] = 'FAIL_CLOSED'
        require(all(record[key] is False for key in flags) and record['historical_P1'] == 'FAIL_CLOSED' and record['scope'] == 'consistency_within_declared_profile',
                'EXCESSIVE_ASSURANCE_SCOPE', record, {**expected,'scope':'consistency_within_declared_profile'})

    def assurance_limitations(self):
        expected = {key: False for key in ('producer_authenticated','initial_pairing_verified','scientific_validity_certified','programme_complete')}
        expected['historical_P1'] = 'FAIL_CLOSED'
        limitations = self.doc('records/R16_limitations.json')
        require(equal(limitations, expected), 'INDEPENDENT_LIMITATIONS_MISMATCH', limitations, expected)


def evaluate(bundle, profile, case_id, invocation_id, arm_id='B_ASSERT'):
    if arm_id != 'B_ASSERT':
        raise ValueError('B_ASSERT supports only its own arm identity')
    if type(profile) is not dict:
        raise ValueError('fixed profile must be a JSON object')
    if (profile.get('schema') != 'nsc-p5-fixed-profile/1'
            or profile.get('profile_id') != 'NSC-P5-CORE-1'
            or profile.get('active_obligations') != list(OBLIGATIONS)
            or not equal(profile.get('alias_grammar'), ALIAS_GRAMMAR)):
        raise ValueError('unsupported fixed obligation profile')
    result = AssertionChecker(bundle, profile).check()
    return {'schema':'nsc-p4-checker-report/2', 'case_id':case_id, 'invocation_id':invocation_id,
            'arm_id':arm_id, **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case-bundle', required=True, type=Path)
    parser.add_argument('--profile', required=True, type=Path)
    parser.add_argument('--case-id', required=True)
    parser.add_argument('--invocation-id', required=True)
    parser.add_argument('--arm-id', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        profile = strict_json(args.profile.read_bytes())
        report = evaluate(args.case_bundle, profile, args.case_id, args.invocation_id, args.arm_id)
        create_report(args.output, report, args.case_bundle)
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        print('B_ASSERT_OPERATIONAL_ERROR:' + type(exc).__name__ + ':' + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
