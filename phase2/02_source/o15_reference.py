"""Prospective O15 reference logic with an explicit resolver parameter.

Derived from NSC_PROS_v1/reference/oracle.py; historical source remains frozen.
The original resolver remains the default.
"""

from fractions import Fraction
import json
from pathlib import Path
import re


RECORDS = {
    'claims': 'records/R15_claims.json',
    'edges': 'records/R15_edges.json',
    'result': 'records/R11_result.json',
}
ALIAS_PREFIX = 'alias:'


def unique_object(items):
    candidate = {}
    for key, value in items:
        if key in candidate:
            raise ValueError(f'duplicate JSON key {key!r}')
        candidate[key] = value
    return candidate


def invalid_number(token):
    raise ValueError(f'inexact JSON number {token!r}')


def required_text(record, key):
    value = record.get(key)
    if type(value) is not str or not value:
        raise ValueError(f'{key} must be a nonempty string')
    return value


def validate_metadata(record):
    if type(record) is not dict:
        raise ValueError('metadata must be an object')
    denominator = record.get('denominator')
    if type(denominator) is not int or denominator < 0:
        raise ValueError('denominator must be a nonnegative integer')
    return required_text(record, 'unit'), denominator, required_text(record, 'scope')


def exact_value(value):
    if type(value) is int:
        return ('number', Fraction(value))
    if type(value) is dict and set(value) == {'numerator', 'denominator'}:
        numerator, denominator = value['numerator'], value['denominator']
        if type(numerator) is int and type(denominator) is int and denominator > 0:
            return ('number', Fraction(numerator, denominator))
    if type(value) in (str, bool, type(None)):
        return (type(value).__name__, value)
    raise ValueError('value must be an exact scalar or a rational with positive denominator')


def pointer_tokens(pointer):
    if not pointer.startswith('/'):
        raise ValueError('a source pointer must start with /')
    tokens = pointer[1:].split('/')
    if any(re.search(r'~(?![01])', token) for token in tokens):
        raise ValueError('source pointer contains an invalid tilde escape')
    return [token.replace('~1', '/').replace('~0', '~') for token in tokens]


def pointer_value(document, pointer):
    node = document
    for token in pointer_tokens(pointer):
        if type(node) is dict and token in node:
            node = node[token]
        elif type(node) is list and re.fullmatch(r'0|[1-9][0-9]*', token) and int(token) < len(node):
            node = node[int(token)]
        else:
            raise ValueError(f'pointer {pointer!r} does not resolve')
    return node


def resolve_source(source, aliases):
    if source.startswith(ALIAS_PREFIX):
        key = source[len(ALIAS_PREFIX):]
        if not key:
            raise ValueError('empty alias key')
        targets = {aliases[name] for name in (key, source) if name in aliases}
        if not targets:
            raise ValueError('no mapping for alias')
        if len(targets) != 1:
            raise ValueError('alias spellings map to different pointers')
        source = targets.pop()
    pointer_tokens(source)
    return source


def read_record(path):
    with path.open(encoding='utf-8', errors='strict') as stream:
        parsed = json.load(stream, object_pairs_hook=unique_object,
                           parse_constant=invalid_number, parse_float=invalid_number)
    if type(parsed) is not dict:
        raise ValueError('document must be an object')
    return parsed


def claim_records(document):
    records = document.get('claims')
    if type(records) is not list or not records:
        raise ValueError('claims must be a nonempty array')
    if any(type(claim) is not dict for claim in records):
        raise ValueError('each claim must be an object')
    ids = [required_text(claim, 'claim_id') for claim in records]
    if len(ids) != len(set(ids)):
        raise ValueError('claim identifiers must be unique')
    return list(zip(ids, records))


def edge_records(document):
    aliases = document.get('aliases')
    fields = document.get('field_metadata')
    if type(aliases) is not dict or any(type(target) is not str for target in aliases.values()):
        raise ValueError('aliases must be a map to strings')
    if type(fields) is not dict:
        raise ValueError('field_metadata must be an object')
    return aliases, fields


def adjudicate(dossier_dir: Path, resolver=resolve_source):
    """Return the O15 verdict and trace from the three required documentary records."""
    dossiers = {}
    missing = []
    violations = []
    resolved = []
    for kind, relative_path in RECORDS.items():
        try:
            dossiers[kind] = read_record(dossier_dir / relative_path)
        except FileNotFoundError:
            missing.append(relative_path)
        except (UnicodeError, ValueError) as error:
            violations.append({'record': relative_path, 'problem': str(error)})

    claims = []
    aliases = fields = None
    result_ids = {}
    for kind in ('edges', 'result'):
        if kind in dossiers:
            try:
                result_ids[kind] = required_text(dossiers[kind], 'result_id')
            except ValueError as error:
                violations.append({'record': RECORDS[kind], 'problem': str(error)})
    if len(set(result_ids.values())) > 1:
        violations.append({'record': RECORDS['edges'], 'problem': 'result_id does not match R11'})
    if 'claims' in dossiers:
        try:
            claims = claim_records(dossiers['claims'])
        except ValueError as error:
            violations.append({'record': RECORDS['claims'], 'problem': str(error)})
    if 'edges' in dossiers:
        try:
            aliases, fields = edge_records(dossiers['edges'])
        except ValueError as error:
            violations.append({'record': RECORDS['edges'], 'problem': str(error)})

    for claim_id, claim in claims:
        try:
            source = required_text(claim, 'source_pointer')
            metadata = validate_metadata(claim)
            if 'value' not in claim:
                raise ValueError('missing claimed value')
            claim_value = exact_value(claim['value'])
            if source.startswith(ALIAS_PREFIX) and aliases is None:
                if source == ALIAS_PREFIX:
                    raise ValueError('empty alias key')
                continue
            pointer = resolver(source, aliases)
            if fields is not None:
                if pointer not in fields:
                    raise ValueError(f'no field metadata for {pointer!r}')
                if metadata != validate_metadata(fields[pointer]):
                    raise ValueError('unit, denominator or scope does not match field metadata')
            if 'result' in dossiers and claim_value != exact_value(pointer_value(dossiers['result'], pointer)):
                raise ValueError('claimed value does not match the resolved result')
            resolved.append({'claim_id': claim_id, 'pointer': pointer})
        except ValueError as error:
            violations.append({'claim_id': claim_id, 'problem': str(error)})

    return {
        'expected': 'V' if violations else 'U' if missing else 'S',
        'rationale': {'violations': violations, 'missing': missing, 'resolved': resolved},
    }
