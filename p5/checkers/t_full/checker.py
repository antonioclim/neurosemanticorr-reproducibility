"""Detached finite-profile checker, P5 v1 successor of the retained P4 v2 source.

Standard library only. This module never executes a supplied producer or reads
an expected-vector file. Internal exact arithmetic has no retained-input bound.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

OBLIGATIONS = tuple(f'O{i:02d}' for i in range(1, 17))
ARMS = ('T_FULL', 'A0_SYNTAX', 'A1_STRUCTURE', 'A2_LOCAL', 'A3_PROVENANCE')
MAX_BYTES = 1048576
MAX_INT = 10**9
IMPLEMENTATION_VERSION = 'P5-TFULL-1'
PROFILE_ID = 'NSC-P5-CORE-1'
ALIAS_GRAMMAR = {'version':'NSC-O15-ALIAS-1', 'prefix':'alias:',
                 'lookup_key':'exact_nonempty_suffix', 'max_hops':1,
                 'pointer_escapes':['~0','~1'],
                 'array_index':'canonical_nonnegative_decimal',
                 'clause_id':'O15.claim_source'}


class AdmissionError(ValueError):
    def __init__(self, code, pointer='', observed=None):
        super().__init__(code)
        self.code, self.pointer, self.observed = code, pointer, observed


class ObjectPairs(list):
    pass


class NumberToken:
    def __init__(self, text, kind):
        self.text, self.kind = text, kind


def pointer_part(value):
    return str(value).replace('~', '~0').replace('/', '~1')


def parse_json(raw, *, structure=True):
    """Find a rejected token's actual JSON pointer without accepting the record."""
    if len(raw) > MAX_BYTES:
        raise AdmissionError('BYTE_BOUND')
    try:
        text = raw.decode('utf-8')
        value = json.loads(text, object_pairs_hook=ObjectPairs,
                           parse_int=lambda s: NumberToken(s, 'INTEGER'),
                           parse_float=lambda s: NumberToken(s, 'FLOAT'),
                           parse_constant=lambda s: NumberToken(s, 'NONFINITE'))
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise AdmissionError('INVALID_JSON', '', str(exc)[:180]) from exc
    nodes = 0
    def visit(item, pointer, depth):
        nonlocal nodes
        nodes += 1
        if depth > 32 or nodes > 20000:
            raise AdmissionError('TREE_BOUND', pointer)
        if isinstance(item, NumberToken):
            if item.kind == 'INTEGER':
                if not structure:
                    return item.text
                digits = item.text.lstrip('-')
                if len(digits) > 10 or (len(digits) == 10 and digits > '1000000000'):
                    observed = (item.text if len(item.text) <= 128 else
                                {'lexeme_prefix':item.text[:64], 'digit_count':len(digits), 'truncated':True})
                    raise AdmissionError('INTEGER_BOUND', pointer, observed)
                return int(item.text)
            if item.kind == 'NONFINITE' or structure:
                raise AdmissionError('NONFINITE' if item.kind == 'NONFINITE' else 'FLOAT_FORBIDDEN', pointer, item.text)
            # A syntax-only arm keeps the lexical token and never evaluates it.
            return item.text
        if isinstance(item, ObjectPairs):
            result = {}
            for key, child in item:
                point = pointer + '/' + pointer_part(key)
                if key in result:
                    raise AdmissionError('DUPLICATE_KEY', point, key)
                visit(key, pointer, depth + 1)
                result[key] = visit(child, point, depth + 1)
            return result
        if isinstance(item, list):
            return [visit(child, pointer + '/' + str(index), depth + 1)
                    for index, child in enumerate(item)]
        if isinstance(item, str):
            if len(item) > 10000:
                raise AdmissionError('STRING_BOUND', pointer)
            try:
                item.encode('utf-8')
            except UnicodeError as exc:
                raise AdmissionError('UNICODE_SCALAR', pointer) from exc
        if type(item) is int and structure and abs(item) > MAX_INT:
            raise AdmissionError('INTEGER_BOUND', pointer, str(item))
        return item
    return visit(value, '', 0)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def exact_equal(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(exact_equal(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(exact_equal(a, b) for a, b in zip(left, right))
    return left == right


def rational(value, *, retained=True):
    if type(value) is not dict or set(value) != {'numerator', 'denominator'}:
        raise AdmissionError('RATIONAL_SHAPE')
    n, d = value['numerator'], value['denominator']
    if type(n) is not int or type(d) is not int or d < 1:
        raise AdmissionError('RATIONAL_COMPONENT')
    if retained and (abs(n) > MAX_INT or d > MAX_INT):
        raise AdmissionError('RATIONAL_BOUND')
    return Fraction(n, d)


def rational_object(value):
    value = Fraction(value)
    return {'numerator': value.numerator, 'denominator': value.denominator}


def decimal_six(value):
    value = Fraction(value)
    n, d = value.numerator, value.denominator
    q, remainder = divmod(abs(n) * 1000000, d)
    if 2 * remainder > d or (2 * remainder == d and q % 2):
        q += 1
    return ('-' if n < 0 and q else '') + str(q // 1000000) + '.' + str(q % 1000000).zfill(6)


def semantic_equal(actual, reference):
    """Retained actuals bounded; a derived Fraction reference is unbounded."""
    if isinstance(reference, Fraction):
        try:
            return rational(actual) == reference
        except AdmissionError:
            return False
    if type(reference) is dict and set(reference) == {'numerator', 'denominator'}:
        try:
            return rational(actual) == rational(reference, retained=False)
        except AdmissionError:
            return False
    if type(actual) is not type(reference):
        return False
    if isinstance(reference, dict):
        return actual.keys() == reference.keys() and all(semantic_equal(actual[k], reference[k]) for k in reference)
    if isinstance(reference, list):
        return len(actual) == len(reference) and all(semantic_equal(a, b) for a, b in zip(actual, reference))
    return actual == reference


def read_safe_bundle(path):
    path = Path(path)
    if path.is_symlink() or not path.is_dir():
        raise AdmissionError('UNSAFE_BUNDLE_ROOT')
    entries, total = {}, 0
    for parent, dirs, files in os.walk(path, followlinks=False):
        for name in dirs + files:
            member = Path(parent) / name
            mode = member.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise AdmissionError('UNSAFE_MEMBER', '', str(member.relative_to(path)))
        for name in files:
            member = Path(parent) / name
            relative = member.relative_to(path).as_posix()
            data = member.read_bytes()
            total += len(data)
            if total > MAX_BYTES or len(entries) >= 128:
                raise AdmissionError('BUNDLE_BOUND')
            entries[relative] = data
    return entries


def aggregate(vector):
    if 'V' in vector.values():
        return 'REJECT'
    if 'U' in vector.values():
        return 'INDETERMINATE'
    return 'ALLOW_WITHIN_SCOPE'


def exclusive_report(path, report):
    data = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8') + b'\n'
    if len(data) > MAX_BYTES:
        raise ValueError('REPORT_BOUND')
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, 'wb', closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(descriptor)


class Unavailable(Exception):
    def __init__(self, path, reason='MISSING_REQUIRED_EVIDENCE', pointer=''):
        super().__init__(reason)
        self.path, self.reason, self.pointer = path, reason, pointer


def shape(value, specification, pointer=''):
    """Structural admission only; enum/domain disagreements belong to predicates."""
    if isinstance(specification, str):
        alternatives = specification.split('|')
        for alternative in alternatives:
            good = ((alternative == 'any') or
                    (alternative == 'str' and type(value) is str) or
                    (alternative == 'int' and type(value) is int) or
                    (alternative == 'bool' and type(value) is bool) or
                    (alternative == 'null' and value is None) or
                    (alternative == 'dict' and type(value) is dict) or
                    (alternative == 'list' and type(value) is list))
            if good:
                return
            if alternative == 'rational':
                try:
                    rational(value)
                    return
                except AdmissionError:
                    pass
        raise AdmissionError('WRONG_FIELD_TYPE', pointer, type(value).__name__)
    if isinstance(specification, list):
        if type(value) is not list:
            raise AdmissionError('WRONG_FIELD_TYPE', pointer, type(value).__name__)
        for index, item in enumerate(value):
            shape(item, specification[0], pointer + '/' + str(index))
        return
    if type(value) is not dict:
        raise AdmissionError('WRONG_FIELD_TYPE', pointer, type(value).__name__)
    required = {name for name in specification if not name.endswith('?')}
    if not required <= set(value):
        key = min(required - set(value))
        raise AdmissionError('MISSING_FIELD', pointer + '/' + pointer_part(key), None)
    for key, subspec in specification.items():
        actual_key = key[:-1] if key.endswith('?') else key
        if actual_key in value:
            shape(value[actual_key], subspec, pointer + '/' + pointer_part(actual_key))


def scan_rationals(value, pointer=''):
    """A denominator field alone need not be a fraction (counts also use it)."""
    if type(value) is dict:
        if 'numerator' in value:
            try:
                rational(value)
            except AdmissionError as exc:
                raise AdmissionError(exc.code, pointer, value) from exc
        for key, item in value.items():
            scan_rationals(item, pointer + '/' + pointer_part(key))
    elif type(value) is list:
        for index, item in enumerate(value):
            scan_rationals(item, pointer + '/' + str(index))


def unique_strings(values):
    return (type(values) is list and all(type(value) is str and value for value in values)
            and len(values) == len(set(values)))


def integers(values):
    return type(values) is list and all(type(value) is int and value >= 0 for value in values)


def json_pointer(document, pointer, *, canonical_indices=False):
    if pointer == '':
        return document
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise KeyError('INVALID_POINTER')
    value = document
    for encoded in pointer[1:].split('/'):
        # Only the two RFC6901 escapes are allowed.
        index = 0
        while index < len(encoded):
            if encoded[index] == '~':
                if index + 1 >= len(encoded) or encoded[index + 1] not in '01':
                    raise KeyError('INVALID_ESCAPE')
                index += 2
            else:
                index += 1
        key = encoded.replace('~1', '/').replace('~0', '~')
        if type(value) is list:
            if ((not key or any(char not in '0123456789' for char in key)) if canonical_indices else not key.isdigit()) or (len(key) > 1 and key.startswith('0')):
                raise KeyError('INVALID_ARRAY_INDEX')
            value = value[int(key)]
        elif type(value) is dict:
            value = value[key]
        else:
            raise KeyError('POINTER_THROUGH_SCALAR')
    return value


def resolve_claim_reference(reference, aliases):
    """Decode the explicit P5 alias grammar once; never traverse alias chains."""
    if type(reference) is not str:
        raise KeyError('INVALID_CLAIM_REFERENCE')
    if reference.startswith('/'):
        return reference
    if not reference.startswith('alias:') or not reference[6:]:
        raise KeyError('INVALID_CLAIM_REFERENCE')
    pointer = aliases.get(reference[6:])
    if type(pointer) is not str or not pointer.startswith('/'):
        raise KeyError('UNRESOLVED_OR_NONPOINTER_ALIAS')
    return pointer


# Declarative constants copied from the shared normative interface, not another implementation.
PREDICATES = {'O01': 'P3BENCH-PRED-O01-SEMANTIC_COMMITMENT_R01', 'O02': 'P3BENCH-PRED-O02-RAW_INVENTORY_MEMBERSHIP', 'O03': 'P3BENCH-PRED-O03-CONFIG_RESOLUTION_TRIPLE', 'O04': 'P3BENCH-PRED-O04-APPROVED_SOURCE_RUNTIME_ANCHOR', 'O05': 'P3BENCH-PRED-O05-KEYED_FACTS_POSITIONAL_RECEIPT', 'O06': 'P3BENCH-PRED-O06-DECLARED_POPULATION_MEMBERSHIP', 'O07': 'P3BENCH-PRED-O07-WORKFLOW_SPECIFIC_STATE_COHERENCE', 'O08': 'P3BENCH-PRED-O08-MEASUREMENT_POLICY_STAGE_AUTHORITY', 'O09': 'P3BENCH-PRED-O09-TARGET_ACTUAL_METHOD_RELATION', 'O10': 'P3BENCH-PRED-O10-SUPPORTED_OPERATION_APPLICABILITY', 'O11': 'P3BENCH-PRED-O11-RETAINED_FORMULA_RELATION', 'O12': 'P3BENCH-PRED-O12-AUTHORITATIVE_CONSUMER_RELATION', 'O13': 'P3BENCH-PRED-O13-FROZEN_TASK_PARTITION_DENOMINATOR', 'O14': 'P3BENCH-PRED-O14-WAIT_OUTPUT_TERMINAL_RELATION', 'O15': 'P3BENCH-PRED-O15-QUANTIFIED_CLAIM_SOURCE_EDGE', 'O16': 'P3BENCH-PRED-O16-ARTEFACT_ASSURANCE_SCOPE'}
LOCATORS = {'O01': {'node_id': 'R01', 'edge_id': None, 'path': 'records/R01.json', 'json_pointer': '/semantic_digest/value', 'obligation_id': 'O01', 'predicate_instance_id': 'P3BENCH-PRED-O01-SEMANTIC_COMMITMENT_R01'}, 'O02': {'node_id': 'INVENTORY', 'edge_id': None, 'path': 'inventory.json', 'json_pointer': '/members', 'obligation_id': 'O02', 'predicate_instance_id': 'P3BENCH-PRED-O02-RAW_INVENTORY_MEMBERSHIP'}, 'O03': {'node_id': 'R03', 'edge_id': 'CONFIG_RESOLUTION', 'path': 'records/R03.json', 'json_pointer': '/executed', 'obligation_id': 'O03', 'predicate_instance_id': 'P3BENCH-PRED-O03-CONFIG_RESOLUTION_TRIPLE'}, 'O04': {'node_id': 'R04', 'edge_id': 'SOURCE_ANCHOR', 'path': 'records/R04.json', 'json_pointer': '/executed_source_sha256', 'obligation_id': 'O04', 'predicate_instance_id': 'P3BENCH-PRED-O04-APPROVED_SOURCE_RUNTIME_ANCHOR'}, 'O05': {'node_id': 'R05', 'edge_id': 'DATA_STATE_ALIGNMENT', 'path': 'records/R05_alignment_receipt.json', 'json_pointer': '', 'obligation_id': 'O05', 'predicate_instance_id': 'P3BENCH-PRED-O05-KEYED_FACTS_POSITIONAL_RECEIPT'}, 'O06': {'node_id': 'R06', 'edge_id': 'POPULATION_SOURCE_MAP', 'path': 'records/R06_materialisation.json', 'json_pointer': '/populations', 'obligation_id': 'O06', 'predicate_instance_id': 'P3BENCH-PRED-O06-DECLARED_POPULATION_MEMBERSHIP'}, 'O07': {'node_id': 'STATES', 'edge_id': 'DATA_STATE_COHERENCE', 'path': 'data/states_or_change_facts.json', 'json_pointer': '/rows', 'obligation_id': 'O07', 'predicate_instance_id': 'P3BENCH-PRED-O07-WORKFLOW_SPECIFIC_STATE_COHERENCE'}, 'O08': {'node_id': 'R08', 'edge_id': None, 'path': 'records/R08_measurement_policy.json', 'json_pointer': '', 'obligation_id': 'O08', 'predicate_instance_id': 'P3BENCH-PRED-O08-MEASUREMENT_POLICY_STAGE_AUTHORITY'}, 'O09': {'node_id': 'R09', 'edge_id': 'TARGET_METHOD', 'path': 'records/R09_estimand.json', 'json_pointer': '/actual_method', 'obligation_id': 'O09', 'predicate_instance_id': 'P3BENCH-PRED-O09-TARGET_ACTUAL_METHOD_RELATION'}, 'O10': {'node_id': 'R10', 'edge_id': None, 'path': 'records/R10_design_profile.json', 'json_pointer': '/requested_operation', 'obligation_id': 'O10', 'predicate_instance_id': 'P3BENCH-PRED-O10-SUPPORTED_OPERATION_APPLICABILITY'}, 'O11': {'node_id': 'R11', 'edge_id': 'FORMULA_RESULT', 'path': 'records/R11_result.json', 'json_pointer': '/values', 'obligation_id': 'O11', 'predicate_instance_id': 'P3BENCH-PRED-O11-RETAINED_FORMULA_RELATION'}, 'O12': {'node_id': 'R12', 'edge_id': 'RESULT_CONSUMER', 'path': 'records/R12_consumer.json', 'json_pointer': '', 'obligation_id': 'O12', 'predicate_instance_id': 'P3BENCH-PRED-O12-AUTHORITATIVE_CONSUMER_RELATION'}, 'O13': {'node_id': 'R13', 'edge_id': 'TASK_UNIVERSE_PARTITION', 'path': 'records/R13.json', 'json_pointer': '', 'obligation_id': 'O13', 'predicate_instance_id': 'P3BENCH-PRED-O13-FROZEN_TASK_PARTITION_DENOMINATOR'}, 'O14': {'node_id': 'R14', 'edge_id': 'WAIT_TERMINAL', 'path': 'records/R14.json', 'json_pointer': '/claimed_terminal_status', 'obligation_id': 'O14', 'predicate_instance_id': 'P3BENCH-PRED-O14-WAIT_OUTPUT_TERMINAL_RELATION'}, 'O15': {'node_id': 'R15', 'edge_id': 'CLAIM_SOURCE', 'path': 'records/R15_claims.json', 'json_pointer': '/claims', 'obligation_id': 'O15', 'predicate_instance_id': 'P3BENCH-PRED-O15-QUANTIFIED_CLAIM_SOURCE_EDGE'}, 'O16': {'node_id': 'R16', 'edge_id': 'ASSURANCE_SCOPE', 'path': 'records/R16.json', 'json_pointer': '', 'obligation_id': 'O16', 'predicate_instance_id': 'P3BENCH-PRED-O16-ARTEFACT_ASSURANCE_SCOPE'}}
CLAUSES = [('O01.syntax', 'O01', 0), ('O01.types', 'O01', 1), ('O01.semantic_digest', 'O01', 3), ('O02.inventory', 'O02', 3), ('O03.local', 'O03', 2), ('O03.resolution', 'O03', 4), ('O04.source', 'O04', 3), ('O05.local', 'O05', 2), ('O05.alignment', 'O05', 3), ('O06.local', 'O06', 2), ('O06.membership', 'O06', 4), ('O07.domain', 'O07', 2), ('O07.coherence', 'O07', 4), ('O08.policy', 'O08', 2), ('O09.local', 'O09', 2), ('O09.target_method', 'O09', 4), ('O10.support', 'O10', 2), ('O11.arithmetic', 'O11', 2), ('O11.formula_binding', 'O11', 4), ('O12.consumer', 'O12', 3), ('O13.local', 'O13', 2), ('O13.universe', 'O13', 3), ('O14.local', 'O14', 2), ('O14.lifecycle', 'O14', 3), ('O15.local', 'O15', 2), ('O15.claim_source', 'O15', 4), ('O16.scope', 'O16', 2)]


def validate_schema(value, spec, workflow, pointer=''):
    if type(spec) is str:
        ok = ((spec == 'str' and type(value) is str and bool(value)) or
              (spec == 'int' and type(value) is int and abs(value) <= MAX_INT) or
              (spec == 'posint' and type(value) is int and 1 <= value <= MAX_INT) or
              (spec == 'bool' and type(value) is bool) or
              (spec == 'null' and value is None))
        if not ok:
            raise AdmissionError('SCHEMA_TYPE', pointer, type(value).__name__)
        return
    if 'workflow_variant' in spec:
        if workflow not in spec['workflow_variant']:
            raise AdmissionError('UNKNOWN_WORKFLOW', '/workflow', workflow)
        return validate_schema(value, spec['workflow_variant'][workflow], workflow, pointer)
    if 'one_of' in spec:
        failures = []
        for alternative in spec['one_of']:
            try:
                validate_schema(value, alternative, workflow, pointer)
                return
            except AdmissionError as exc:
                failures.append(exc)
        raise max(failures, key=lambda exc: len(exc.pointer.split('/')))
    if 'list' in spec:
        if type(value) is not list:
            raise AdmissionError('SCHEMA_ARRAY', pointer, type(value).__name__)
        for index, item in enumerate(value):
            validate_schema(item, spec['list'], workflow, pointer + '/' + str(index))
        return
    if type(value) is not dict:
        raise AdmissionError('SCHEMA_OBJECT', pointer, type(value).__name__)
    if 'map' in spec:
        for key, item in value.items():
            if not key:
                raise AdmissionError('EMPTY_MAP_KEY', pointer + '/')
            validate_schema(item, spec['map'], workflow, pointer + '/' + pointer_part(key))
        return
    required, optional = spec['fields'], spec.get('optional', {})
    for key, child in required.items():
        point = pointer + '/' + pointer_part(key)
        if key not in value:
            raise AdmissionError('MISSING_FIELD', point)
        validate_schema(value[key], child, workflow, point)
    for key in value:
        point = pointer + '/' + pointer_part(key)
        if key not in required and key not in optional:
            raise AdmissionError('EXTRA_FIELD', point, key)
        if key in optional:
            validate_schema(value[key], optional[key], workflow, point)


def undefined(reason):
    return {'status': 'UNDEFINED', 'reason': reason}


def mean(values):
    return Fraction(sum(values), len(values)) if values else undefined('EMPTY_SUPPORT')


def divide(numerator, denominator, missing='MISSING_INPUT'):
    if numerator is None or denominator is None:
        return undefined(missing)
    if isinstance(numerator, dict):
        return numerator
    if isinstance(denominator, dict):
        return denominator
    if denominator == 0:
        return undefined('ZERO_DENOMINATOR')
    return Fraction(numerator) / Fraction(denominator)


class Checker:
    def __init__(self, bundle, profile, arm):
        self.profile, self.arm = profile, arm
        self.level = {'A0_SYNTAX': 0, 'A1_STRUCTURE': 1, 'A2_LOCAL': 2, 'A3_PROVENANCE': 3, 'T_FULL': 4}[arm]
        self.raw = read_safe_bundle(bundle)
        self.documents, self.syntax_errors, self.type_errors, self.context_unavailable = {}, {}, {}, {}
        for name, raw in sorted(self.raw.items()):
            if name.endswith('.json'):
                try:
                    parse_json(raw, structure=False)
                except AdmissionError as exc:
                    self.syntax_errors[name] = exc
                try:
                    self.documents[name] = parse_json(raw)
                except AdmissionError as exc:
                    if name not in self.syntax_errors:
                        self.type_errors[name] = exc
        header = self.documents.get('bundle.json')
        workflow = header.get('workflow') if isinstance(header, dict) else None
        self.workflow = workflow if type(workflow) is str and workflow in profile['workflow_ids'] else None
        for name, document in list(self.documents.items()):
            if name in profile['schemas']:
                if self.workflow is None and 'workflow_variant' in profile['schemas'][name]:
                    reason = 'MISSING_REQUIRED_EVIDENCE' if 'bundle.json' not in self.raw else 'INADMISSIBLE_LOCAL_EVIDENCE'
                    self.context_unavailable[name] = Unavailable('bundle.json', reason)
                    continue
                try:
                    validate_schema(document, profile['schemas'][name], self.workflow)
                    scan_rationals(document)
                    if name == 'bundle.json':
                        if document['schema'] != 'nsc-p4-evidence/2':
                            raise AdmissionError('BUNDLE_SCHEMA', '/schema', document['schema'])
                        if document['workflow'] not in profile['workflow_ids']:
                            raise AdmissionError('WORKFLOW', '/workflow', document['workflow'])
                        if document['profile_id'] != profile['profile_id']:
                            raise AdmissionError('PROFILE_ID', '/profile_id', document['profile_id'])
                except AdmissionError as exc:
                    self.type_errors[name] = exc
            else:
                self.type_errors[name] = AdmissionError('UNREGISTERED_JSON_FILE', '')
        self.oid = self.cid = None

    def record(self, path):
        if path not in self.raw:
            raise Unavailable(path)
        if path in self.syntax_errors or path in self.type_errors:
            raise Unavailable(path, 'INADMISSIBLE_LOCAL_EVIDENCE')
        if path in self.context_unavailable:
            raise self.context_unavailable[path]
        return self.documents[path]

    def workflow_ready(self):
        self.record('bundle.json')
        return self.workflow

    def diagnostic(self, kind, reason, observed=None, expected=None, path=None, pointer=None):
        base = LOCATORS[self.oid]
        if path is None:
            node, edge, path, pointer = base['node_id'], base['edge_id'], base['path'], base['json_pointer']
        else:
            node, edge = 'FILE:' + path, None
            pointer = '' if pointer is None else pointer
        return {'obligation_id': self.oid, 'predicate_instance_id': PREDICATES[self.oid],
                'kind': kind, 'node_id': node, 'edge_id': edge, 'path': path,
                'json_pointer': pointer, 'reason_code': reason, 'observed': observed,
                'expected': expected, 'numerical_policy': 'C01/C02' if self.oid in ('O11','O12','O15') else 'C00/C03',
                'clause_id': self.cid}

    def decision(self, valid, reason, observed=None, expected=None):
        return ('S', []) if valid else ('V', [self.diagnostic('DIRECT_VIOLATION', reason, observed, expected)])

    def keyed(self, path):
        rows = self.record(path)['rows']
        ids = [row['id'] for row in rows]
        if not unique_strings(ids):
            raise Unavailable(path, 'AMBIGUOUS_STABLE_IDS', '/rows')
        return {row['id']: row for row in rows}

    def state_vocabulary(self, states, *, eligibility_only=False):
        if self.workflow == 'W1':
            return all(row['state'] in self.profile['response_states'] for row in states.values())
        keys = ('staff_input', 'turnover_input') if eligibility_only else ('staff_input','turnover_input','staff_change','other_rev_change')
        return all(row[key] in self.profile['input_states' if key.endswith('_input') else 'change_states']
                   for row in states.values() for key in keys)

    def o01_syntax(self):
        findings = [self.diagnostic('DIRECT_VIOLATION', exc.code, exc.observed,
                                    'Strict bounded UTF8 JSON', path, exc.pointer)
                    for path, exc in self.syntax_errors.items()]
        return ('V', findings) if findings else ('S', [])

    def o01_types(self):
        findings = [self.diagnostic('DIRECT_VIOLATION', exc.code, exc.observed,
                                    'Fixed typed schema and C00-C03', path, exc.pointer)
                    for path, exc in self.type_errors.items()]
        if findings:
            return 'V', findings
        if self.syntax_errors:
            path = sorted(self.syntax_errors)[0]
            raise Unavailable(path, 'INADMISSIBLE_LOCAL_EVIDENCE')
        if self.context_unavailable:
            raise next(iter(self.context_unavailable.values()))
        return 'S', []

    def o01_semantic_digest(self):
        descriptor = self.record('records/R01.json')['semantic_digest']
        if descriptor['domain'] != 'canonical-json-v1' or descriptor['algorithm'] != 'sha256':
            return self.decision(False, 'SEMANTIC_DESCRIPTOR_DOMAIN', descriptor, 'canonical-json-v1 / sha256')
        payload = self.record('semantic_payload.json')
        expected = {'domain':'canonical-json-v1','algorithm':'sha256','value':digest(canonical(payload))}
        return self.decision(exact_equal(descriptor, expected), 'SEMANTIC_COMMITMENT_MISMATCH', descriptor, expected)

    def o02_inventory(self):
        inventory = self.record('inventory.json')['members']
        observed = [{'path':name,'bytes':len(raw),'sha256':digest(raw)}
                    for name, raw in sorted(self.raw.items()) if name != 'inventory.json']
        required, optional = set(self.profile['required_paths']), set(self.profile['optional_paths'])
        actual = set(self.raw)
        good = exact_equal(inventory, observed) and required <= actual <= required | optional
        return self.decision(good, 'RAW_INVENTORY_OR_REQUIRED_MEMBER_MISMATCH', inventory, observed)

    def o03_local(self):
        workflow = self.workflow_ready()
        missing = []
        allowed = set(self.profile['configuration_defaults'][workflow])
        try:
            cfg = self.record('records/R03.json')
            declared, executed = cfg['declared'], cfg['executed']
            good = set(declared) <= allowed
            for key, value in declared.items():
                good = good and (type(value) is bool if key == 'strict' else type(value) is str)
                if key == 'method':
                    good = good and value in self.profile['supported_methods'][workflow]
            good = good and executed['method'] in self.profile['supported_methods'][workflow]
            if not good:
                return self.decision(False, 'UNSUPPORTED_EXECUTABLE_CONFIGURATION', cfg, sorted(allowed))
        except Unavailable as exc:
            missing.append(exc)
        try:
            effective = self.record('records/R03_effective.json')['effective']
            if effective['method'] not in self.profile['supported_methods'][workflow]:
                return self.decision(False, 'UNSUPPORTED_EFFECTIVE_METHOD', effective['method'], self.profile['supported_methods'][workflow])
        except Unavailable as exc:
            missing.append(exc)
        if missing:
            raise missing[0]
        return 'S', []

    def o03_resolution(self):
        workflow = self.workflow_ready()
        cfg = self.record('records/R03.json')
        expected = dict(self.profile['configuration_defaults'][workflow])
        expected.update(cfg['declared'])
        if not exact_equal(expected, cfg['executed']):
            return self.decision(False, 'CONFIGURATION_RESOLUTION_MISMATCH', cfg['executed'], expected)
        effective = self.record('records/R03_effective.json')['effective']
        return self.decision(exact_equal(expected, effective), 'CONFIGURATION_RESOLUTION_MISMATCH', effective, expected)

    def o04_source(self):
        missing, observed = [], {}
        expected = {'source':self.profile['source_sha256'],'runtime':self.profile['runtime_id']}
        if 'source/producer.txt' in self.raw:
            observed['source'] = digest(self.raw['source/producer.txt'])
            if observed['source'] != expected['source']:
                return self.decision(False, 'SOURCE_OR_RUNTIME_ANCHOR_MISMATCH', observed, expected)
        else:
            missing.append(Unavailable('source/producer.txt'))
        for path, key, hash_key in (('records/R04.json','run','executed_source_sha256'),
                                    ('records/R04_expected_anchor.json','anchor','source_sha256')):
            try:
                record = self.record(path)
                observed[key] = record
                if record[hash_key] != expected['source'] or record['runtime_id'] != expected['runtime']:
                    return self.decision(False, 'SOURCE_OR_RUNTIME_ANCHOR_MISMATCH', observed, expected)
            except Unavailable as exc:
                missing.append(exc)
        if missing:
            raise missing[0]
        return 'S', []

    def o05_local(self):
        missing = []
        for path in ('data/rows.json','data/states_or_change_facts.json'):
            try:
                ids = [row['id'] for row in self.record(path)['rows']]
                if not unique_strings(ids):
                    return self.decision(False, 'DUPLICATE_STABLE_ID', ids, 'Unique stable identifiers')
            except Unavailable as exc:
                missing.append(exc)
        try:
            receipt = self.record('records/R05_alignment_receipt.json')
            if receipt['producer_authenticated'] or receipt['initial_pairing_verified']:
                return self.decision(False, 'ALIGNMENT_ASSURANCE_OVERCLAIM', receipt, 'Both assurance flags false')
        except Unavailable as exc:
            missing.append(exc)
        if missing:
            raise missing[0]
        return 'S', []

    def o05_alignment(self):
        data = [row['id'] for row in self.record('data/rows.json')['rows']]
        states = [row['id'] for row in self.record('data/states_or_change_facts.json')['rows']]
        receipt = self.record('records/R05_alignment_receipt.json')
        return self.decision(data == states == receipt['data_ids'] == receipt['state_ids'],
                             'PHYSICAL_ALIGNMENT_MISMATCH', {'data':data,'states':states,'receipt':receipt}, 'Identical ordered IDs')

    def o06_local(self):
        populations = self.record('records/R06_materialisation.json')['populations']
        good = unique_strings([row['population_id'] for row in populations])
        for row in populations:
            ids, positions = row['ids'], row['local_to_source_positions']
            good = good and unique_strings(ids) and integers(positions) and len(positions) == len(set(positions)) and len(ids) == len(positions)
        return self.decision(good, 'POPULATION_LOCAL_STRUCTURE', populations, 'Unique names/IDs/positions with equal lengths')

    def o06_membership(self):
        workflow = self.workflow_ready()
        data = self.keyed('data/rows.json')
        states = self.keyed('data/states_or_change_facts.json')
        if not self.state_vocabulary(states, eligibility_only=True):
            raise Unavailable('data/states_or_change_facts.json','UNKNOWN_ELIGIBILITY_STATE','/rows')
        if set(data) != set(states):
            raise Unavailable('data/states_or_change_facts.json','UNMATCHED_STABLE_IDS','/rows')
        if workflow == 'W1':
            expected = {'eligible':{key for key, state in states.items() if state['state'] == 'observed' and data[key]['readiness'] in self.profile['category_order']}}
        else:
            expected = {'staff_available':{key for key, state in states.items() if state['staff_input'] == 'available'},
                        'turnover_available':{key for key, state in states.items() if state['turnover_input'] == 'available'},
                        'staff_imputation':{key for key, state in states.items() if state['staff_input'] == 'missing' and state['turnover_input'] == 'available'}}
        populations = self.record('records/R06_materialisation.json')['populations']
        order = [row['id'] for row in self.record('data/rows.json')['rows']]
        good = len(populations) == len(expected) and {row['population_id'] for row in populations} == set(expected)
        for row in populations:
            ids, positions, name = row['ids'], row['local_to_source_positions'], row['population_id']
            good = good and name in expected and set(ids) == expected.get(name, set()) and len(ids) == len(positions)
            good = good and all(0 <= position < len(order) and order[position] == identifier for identifier, position in zip(ids, positions))
        return self.decision(good, 'POPULATION_MEMBERSHIP_OR_SOURCE_MAP_MISMATCH', populations,
                             {key:sorted(value) for key,value in expected.items()})

    def o07_domain(self):
        workflow = self.workflow_ready()
        missing = []
        try:
            states = self.record('data/states_or_change_facts.json')['rows']
            if not self.state_vocabulary({str(i): row for i,row in enumerate(states)}):
                return self.decision(False, 'UNSUPPORTED_SEMANTIC_STATE', states, 'Frozen response/input/change vocabulary')
        except Unavailable as exc:
            missing.append(exc)
        if workflow == 'W1':
            try:
                data = self.record('data/rows.json')['rows']
                if not all(row['readiness'] is None or row['readiness'] in self.profile['category_order'] for row in data):
                    return self.decision(False, 'UNSUPPORTED_ORDINAL_VALUE', data, self.profile['category_order'])
            except Unavailable as exc:
                missing.append(exc)
        if missing:
            raise missing[0]
        return 'S', []

    def o07_coherence(self):
        workflow = self.workflow_ready()
        data = self.keyed('data/rows.json')
        states = self.keyed('data/states_or_change_facts.json')
        output = self.keyed('data/output_rows.json')
        if set(data) != set(states) or set(data) != set(output):
            raise Unavailable('data/states_or_change_facts.json','UNMATCHED_STABLE_IDS','/rows')
        if not self.state_vocabulary(states):
            raise Unavailable('data/states_or_change_facts.json','UNKNOWN_SEMANTIC_STATE','/rows')
        good = True
        for key, row in data.items():
            state, out = states[key], output[key]
            if workflow == 'W1':
                good = good and ((row['readiness'] is not None) == (state['state'] == 'observed'))
            else:
                good = good and state['staff_input'] == ('missing' if row['staff'] is None else 'available')
                good = good and state['turnover_input'] == ('missing' if row['turnover'] is None else 'available')
                output_undefined = out['staff'].get('status') == 'UNDEFINED'
                if output_undefined:
                    expected_change = 'undefined'
                elif row['staff'] is None:
                    expected_change = 'imputed'
                elif semantic_equal(out['staff'], Fraction(row['staff'])):
                    expected_change = 'unchanged'
                else:
                    expected_change = 'edited'
                good = good and state['staff_change'] == expected_change
                expected_other = ('imputed' if row['other.rev'] is None else
                                  'unchanged' if semantic_equal(out['other.rev'], Fraction(row['other.rev'])) else 'edited')
                good = good and state['other_rev_change'] == expected_other
        return self.decision(good, 'VALUE_STATE_CHANGE_INCOHERENCE', states, 'Workflow-specific availability and change facts')

    def o08_policy(self):
        workflow = self.workflow_ready()
        policy = self.record('records/R08_measurement_policy.json')
        if workflow == 'W1':
            order, codes = policy['category_order'], policy['display_codes']
            good = order == self.profile['category_order'] and set(codes) == set(order) and not policy['allows_arithmetic_mean']
            if good:
                good = all(codes[left] < codes[right] for left,right in zip(order,order[1:]))
        else:
            good = not policy['executed_staff_imputation'] or (policy['allow_staff_imputation'] and policy['input_and_change_states_separate'])
        return self.decision(good, 'MEASUREMENT_OR_IMPUTATION_AUTHORITY_MISMATCH', policy, 'Frozen stage policy')

    def o09_local(self):
        workflow = self.workflow_ready()
        record = self.record('records/R09_estimand.json')
        representations = ('counts_and_denominator','exact_proportions') if workflow == 'W1' else ('separate_supports','explicit_ratio')
        good = (record['target'] in self.profile['supported_methods'][workflow] and
                record['actual_method'] in self.profile['supported_methods'][workflow] and
                record['representation'] in representations and
                unique_strings(record['population_ids']) and set(record['population_ids']) == set(self.profile['population_ids'][workflow]))
        return self.decision(good, 'UNSUPPORTED_ESTIMAND_DECLARATION', record, 'Supported methods, representation and populations')

    def o09_target_method(self):
        workflow = self.workflow_ready()
        record = self.record('records/R09_estimand.json')
        if record['target'] != self.profile['target_method'][workflow] or record['actual_method'] != record['target']:
            return self.decision(False, 'ACTUAL_METHOD_TARGET_MISMATCH', record, self.profile['target_method'][workflow])
        populations = self.record('records/R06_materialisation.json')['populations']
        self.record('data/states_or_change_facts.json')
        names = [row['population_id'] for row in populations]
        return self.decision(set(record['population_ids']) == set(names), 'ESTIMAND_POPULATION_NAME_MISMATCH', record['population_ids'], names)

    def o10_support(self):
        record = self.record('records/R10_design_profile.json')
        good = (record['supported_operations'] == self.profile['supported_operations'] and
                record['requested_operation'] in self.profile['supported_operations'] and
                not record['population_generalisation'] and not record['causal_claim'])
        return self.decision(good, 'UNSUPPORTED_DESIGN_OR_ASSURANCE', record, self.profile['supported_operations'])

    def w1_expected(self, result):
        operands = result['operands']
        labels, order, codes = operands['selected_labels'], operands['category_order'], operands['display_codes']
        if order != self.profile['category_order'] or set(codes) != set(order) or any(label not in order for label in labels):
            return None
        counts = {category:labels.count(category) for category in order}
        size = len(labels)
        values = {'counts':counts, 'denominator':size,
                  'proportions':{category:Fraction(count,size) if size else undefined('EMPTY_SUPPORT') for category,count in counts.items()}}
        if result['method'] == 'ordinal_mean':
            values['mean_code'] = Fraction(sum(codes[label] for label in labels),size) if size else undefined('EMPTY_SUPPORT')
        return values

    def w2_expected(self, result):
        rows = result['operands']['rows']
        if not unique_strings([row['id'] for row in rows]):
            return None
        ms = mean([row['staff'] for row in rows if row['staff'] is not None])
        mt = mean([row['turnover'] for row in rows if row['turnover'] is not None])
        if result['method'] == 'mean_of_ratios':
            ratios = [Fraction(row['staff'],row['turnover']) for row in rows if row['staff'] is not None and row['turnover'] not in (None,0)]
            ratio = sum(ratios,Fraction())/len(ratios) if ratios else undefined('EMPTY_SUPPORT')
        else:
            ratio = divide(ms, mt)
        staff, other, turnover = {}, {}, {}
        for row in rows:
            key = row['id']
            if row['staff'] is not None:
                staff[key] = Fraction(row['staff'])
            elif row['turnover'] is None:
                staff[key] = undefined('MISSING_INPUT')
            elif isinstance(ratio, dict):
                staff[key] = ratio
            else:
                staff[key] = row['turnover'] * ratio
            other[key] = Fraction(abs(row['other.rev'] or 0))
            turnover[key] = (undefined('MISSING_TURNOVER') if row['turnover'] is None
                             else divide(row['turnover'], row['total.rev']))
        return {'mean_staff':ms,'mean_turnover':mt,'ratio':ratio,'staff_output':staff,
                'other_rev_output':other,'turnover_ratio':turnover}

    def displays_valid(self, result):
        for pointer, display in result.get('displays', {}).items():
            try:
                value = rational(json_pointer(result['values'], pointer))
            except (KeyError, IndexError, AdmissionError, ValueError, TypeError):
                return False
            if display != decimal_six(value):
                return False
        return True

    def o11_arithmetic(self):
        workflow = self.workflow_ready()
        result = self.record('records/R11_result.json')
        if result['status'] != 'COMPLETE' or result['method'] not in self.profile['supported_methods'][workflow]:
            return self.decision(False, 'RESULT_STATUS_OR_METHOD', result['status'], 'COMPLETE and supported method')
        reference = self.w1_expected(result) if workflow == 'W1' else self.w2_expected(result)
        if reference is None:
            return self.decision(False, 'INVALID_RETAINED_ARITHMETIC_OPERANDS', result['operands'], 'Supported self-contained operands')
        keys = tuple(reference) if workflow == 'W1' else ('mean_staff','mean_turnover','other_rev_output','turnover_ratio')
        good = all(semantic_equal(result['values'][key], reference[key]) for key in keys)
        if workflow == 'W1':
            good = good and set(result['values']) == set(reference)
        good = good and self.displays_valid(result)
        return self.decision(good, 'RETAINED_LOCAL_ARITHMETIC_MISMATCH', result['values'], 'Exact recomputation from retained operands')

    def o11_formula_binding(self):
        workflow = self.workflow_ready()
        registry = self.record('records/R11_formula_registry.json')
        if registry['formula_version'] != self.profile['formula_version'] or registry['method'] not in self.profile['supported_methods'][workflow]:
            return self.decision(False, 'REGISTERED_FORMULA_DOMAIN_MISMATCH', registry, self.profile['formula_version'])
        result = self.record('records/R11_result.json')
        good = registry['method'] == result['method'] and result['method'] in self.profile['supported_methods'][workflow]
        reference = self.w1_expected(result) if workflow == 'W1' else self.w2_expected(result)
        good = good and reference is not None
        if good:
            if workflow == 'W1':
                good = semantic_equal(result['values'], reference)
            else:
                good = all(semantic_equal(result['values'][key], reference[key]) for key in ('ratio','staff_output'))
        return self.decision(good, 'REGISTERED_FORMULA_RESULT_MISMATCH', result['values'], registry)

    def o12_consumer(self):
        result = self.record('records/R11_result.json')
        consumer = self.record('records/R12_consumer.json')
        expected = {key:result[key] for key in ('result_id','status','values')}
        if 'displays' in result:
            expected['displays'] = result['displays']
        return self.decision(semantic_equal(consumer, expected), 'CONSUMER_RESULT_MISMATCH', consumer, expected)

    def tasks(self, record):
        if type(record['tasks']) is dict:
            return [{'task_id':key,'status':value} for key,value in record['tasks'].items()]
        return record['tasks']

    def o13_local(self):
        record = self.record('records/R13.json')
        tasks = self.tasks(record)
        statuses = self.profile['terminal_statuses']
        counts = {status:sum(row['status'] == status for row in tasks) for status in statuses}
        good = (unique_strings([row['task_id'] for row in tasks]) and all(row['status'] in statuses for row in tasks)
                and record['counts'] == counts and record['reported_attempted_denominator'] == counts['SUCCEEDED'] + counts['FAILED'])
        return self.decision(good, 'TASK_COUNTS_OR_ATTEMPTED_DENOMINATOR_MISMATCH', record, counts)

    def o13_universe(self):
        universe = self.record('records/R13_task_universe.json')['task_ids']
        if not unique_strings(universe):
            return self.decision(False, 'TASK_UNIVERSE_NOT_UNIQUE', universe, 'Unique fixed task identifiers')
        tasks = self.tasks(self.record('records/R13.json'))
        ids = [row['task_id'] for row in tasks]
        good = unique_strings(ids) and set(universe) == set(ids)
        return self.decision(good, 'TASK_UNIVERSE_MISMATCH', ids, universe)

    def o14_local(self):
        record = self.record('records/R14.json')
        return self.decision(record['claimed_terminal_status'] in ('SUCCEEDED','FAILED'), 'UNSUPPORTED_TERMINAL_CLAIM',
                             record['claimed_terminal_status'], ['SUCCEEDED','FAILED'])

    def o14_lifecycle(self):
        record = self.record('records/R14.json')
        wait = self.record('records/R14_wait_receipt.json')
        universe = self.record('records/R13_task_universe.json')['task_ids']
        success = wait['exit_code'] == 0 and wait['result_present'] and wait['guard_closed']
        expected_status = 'SUCCEEDED' if success else 'FAILED'
        good = (record['task_id'] == wait['task_id'] and record['task_id'] in universe and
                record['claimed_terminal_status'] == expected_status and
                record['claimed_closed'] == wait['guard_closed'] and (success or not record['claimed_closed']))
        return self.decision(good, 'WAIT_TERMINAL_OR_CLOSURE_MISMATCH', record, {'wait':wait,'expected_status':expected_status})

    def o15_local(self):
        missing = []
        claims = None
        try:
            claims = self.record('records/R15_claims.json')['claims']
            good = unique_strings([claim['claim_id'] for claim in claims])
            good = good and all(claim['source_pointer'] and claim['unit'] and claim['scope'] and claim['denominator'] >= 0 for claim in claims)
            if not good:
                return self.decision(False, 'CLAIM_LOCAL_STRUCTURE', claims, 'Unique supported structured claims')
        except Unavailable as exc:
            missing.append(exc)
        try:
            edges = self.record('records/R15_edges.json')
            result = self.record('records/R11_result.json')
            if edges['result_id'] != result['result_id']:
                return self.decision(False, 'EDGE_RESULT_IDENTITY_MISMATCH', edges['result_id'], result['result_id'])
        except Unavailable as exc:
            missing.append(exc)
        if missing:
            raise missing[0]
        return 'S', []

    def o15_claim_source(self):
        claims = self.record('records/R15_claims.json')['claims']
        edges = self.record('records/R15_edges.json')
        result = self.record('records/R11_result.json')
        good = edges['result_id'] == result['result_id']
        for claim in claims:
            try:
                pointer = resolve_claim_reference(claim['source_pointer'], edges['aliases'])
                value = json_pointer(result, pointer, canonical_indices=True)
                metadata = edges['field_metadata'][pointer]
                good = good and semantic_equal(claim['value'], value) and all(claim[key] == metadata[key] for key in ('unit','denominator','scope'))
            except (KeyError, IndexError, TypeError, ValueError):
                good = False
        return self.decision(good, 'QUANTIFIED_CLAIM_SOURCE_MISMATCH', claims, 'Designated immutable result field and metadata')

    def o16_scope(self):
        flags = ('producer_authenticated','initial_pairing_verified','scientific_validity_certified','programme_complete')
        missing = []
        for path in ('records/R16.json','records/R16_limitations.json'):
            try:
                record = self.record(path)
                good = not any(record[flag] for flag in flags) and record['historical_P1'] == 'FAIL_CLOSED'
                if path == 'records/R16.json':
                    good = good and record['scope'] == 'consistency_within_declared_profile'
                if not good:
                    return self.decision(False, 'ARTEFACT_ASSURANCE_OVERCLAIM', record,
                                         'Declared consistency only, P1 FAIL_CLOSED, false assurance flags')
            except Unavailable as exc:
                missing.append(exc)
        if missing:
            raise missing[0]
        return 'S', []

    def run(self, case_id, invocation_id):
        vectors, coverage, diagnostics = {}, {}, []
        by_obligation = {oid:[] for oid in OBLIGATIONS}
        for cid, oid, level in CLAUSES:
            self.cid, self.oid = cid, oid
            if level > self.level:
                by_obligation[oid].append(('U', False))
                diagnostics.append({'obligation_id':oid,'predicate_instance_id':PREDICATES[oid],
                                    'kind':'NOT_EVALUATED_BY_ABLATION','node_id':None,'edge_id':None,
                                    'path':None,'json_pointer':None,'reason_code':'CLAUSE_NOT_EVALUATED',
                                    'observed':None,'expected':cid,'numerical_policy':None,'clause_id':cid})
                continue
            method = getattr(self, cid.lower().replace('.', '_'))
            try:
                status, evidence = method()
            except Unavailable as exc:
                status = 'U'
                evidence = [self.diagnostic('DEPENDENCY_U',exc.reason,None,'Available unambiguous local premise',exc.path,exc.pointer)]
            by_obligation[oid].append((status, True))
            diagnostics.extend(evidence)
        for oid, states in by_obligation.items():
            values = [status for status, _ in states]
            vectors[oid] = 'V' if 'V' in values else 'U' if 'U' in values else 'S'
            coverage[oid] = all(covered for _, covered in states)
        # Several clauses may cite the same evidence; preserve distinct clauses.
        return {'schema':'nsc-p4-checker-report/2','case_id':case_id,'invocation_id':invocation_id,
                'arm_id':self.arm,'obligation_vector':vectors,'coverage_mask':coverage,
                'aggregate':aggregate(vectors),'diagnostics':diagnostics}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('case-bundle','profile','case-id','invocation-id','arm-id','output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    try:
        if args.arm_id not in ARMS:
            raise ValueError('UNKNOWN_ARM')
        bundle, output = Path(args.case_bundle), Path(args.output)
        if output.resolve().is_relative_to(bundle.resolve()):
            raise ValueError('OUTPUT_INSIDE_EVIDENCE')
        profile = parse_json(Path(args.profile).read_bytes())
        if (type(profile) is not dict or profile.get('schema') != 'nsc-p5-fixed-profile/1'
                or profile.get('profile_id') != PROFILE_ID
                or not exact_equal(profile.get('alias_grammar'), ALIAS_GRAMMAR)
                or profile.get('active_obligations') != list(OBLIGATIONS)):
            raise ValueError('UNSUPPORTED_PROFILE')
        report = Checker(bundle, profile, args.arm_id).run(args.case_id,args.invocation_id)
        exclusive_report(output, report)
        return 0
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
        sys.stderr.write('OPERATIONAL_ERROR:' + type(exc).__name__ + ':' + str(exc)[:180] + '\n')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
