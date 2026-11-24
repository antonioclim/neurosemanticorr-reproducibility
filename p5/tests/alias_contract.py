"""Independent O15 literal and CLI contract checks for prospective P5 fixtures.

This module reads evidence fixtures and reports. It never imports or reads either
candidate implementation. All fixture/invocation identities come from the P5
pipeline. The original P4 benchmark is neither executed nor rescored.
"""
from pathlib import Path
import copy
import json
import re

ARMS = ('T_FULL', 'B_ASSERT')
COMMON = (
    ('direct', 'S'), ('alias_primary', 'S'), ('renamed_unicode', 'S'),
    ('nested_name_once_positive', 'S'), ('unused_chain', 'S'),
    ('nested_name_no_recursive_peel', 'V'), ('full_token_key_only', 'V'),
    ('bare_name', 'V'), ('unresolved', 'V'), ('chain', 'V'), ('cycle', 'V'),
    ('wrong_case', 'V'), ('empty_alias_name', 'V'),
    ('empty_reference', 'U'), ('empty_target', 'U'),
    ('wrong_value', 'V'), ('wrong_unit', 'V'), ('wrong_denominator', 'V'),
    ('wrong_scope', 'V'), ('metadata_raw_alias_only', 'V'),
    ('scalar_traversal', 'V'), ('missing_pointer', 'V'),
)
EXTRA = {
    'W1': (('escaped_key', 'S'), ('decode_once', 'S'), ('bad_escape_2', 'V'),
           ('unicode_object_key', 'S')),
    'W2': (('array_0', 'S'), ('array_00', 'V'), ('array_arabic', 'V'),
           ('array_fullwidth', 'V'), ('array_plus', 'V'), ('array_negative', 'V'),
           ('array_append', 'V'), ('array_out_of_range', 'V')),
}
SMOKE_VARIANTS = {'direct', 'alias_primary', 'unresolved'}


def literal_resolve(document, reference, aliases):
    """Small independent known-answer interpreter, not candidate code."""
    if not isinstance(reference, str) or not reference:
        raise ValueError('Reference must be a nonempty string')
    pointer = reference
    if pointer.startswith('alias:'):
        name = pointer[6:]
        if not name or name not in aliases:
            raise ValueError('Unresolved exact suffix')
        pointer = aliases[name]
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise ValueError('A direct nonempty pointer is required')
    current = document
    for raw in pointer[1:].split('/'):
        if re.search(r'~(?:[^01]|$)', raw):
            raise ValueError('Invalid pointer escape')
        token = raw.replace('~1', '/').replace('~0', '~')
        if isinstance(current, dict):
            current = current[token]
        elif isinstance(current, list):
            if re.fullmatch(r'0|[1-9][0-9]*', token) is None:
                raise ValueError('Noncanonical ASCII array index')
            current = current[int(token)]
        else:
            raise ValueError('Scalar traversal')
    return current


def _literal_checks():
    document = {'a/b~c': 7, '~1': 8, '٠': 9, 'items': [11, 12], '': 13}
    samples = [
        ('suffix_lookup', 'alias:primary', {'primary': '/items/0'}, 11),
        ('unicode_name', 'alias:Δ primary:one ', {'Δ primary:one ': '/items/1'}, 12),
        ('opaque_nested_name', 'alias:alias:primary', {'alias:primary': '/items/0'}, 11),
        ('escaped_key', '/a~1b~0c', {}, 7),
        ('decode_once', '/~01', {}, 8),
        ('unicode_object_key', '/٠', {}, 9),
        ('empty_object_key', '/', {}, 13),
    ]
    negatives = [
        ('full_token_key_only', 'alias:primary', {'alias:primary': '/items/0'}),
        ('no_recursive_peel', 'alias:alias:primary', {'primary': '/items/0'}),
        ('chain', 'alias:a', {'a': 'alias:b', 'b': '/items/0'}),
        ('empty_alias', 'alias:', {'': '/items/0'}),
        ('bare_name', 'primary', {'primary': '/items/0'}),
        ('bad_escape', '/a~2b', {}),
        ('leading_zero', '/items/00', {}),
        ('arabic_index', '/items/٠', {}),
        ('fullwidth_index', '/items/０', {}),
        ('signed_index', '/items/+0', {}),
        ('negative_index', '/items/-1', {}),
        ('append_index', '/items/-', {}),
        ('out_of_range', '/items/99', {}),
        ('scalar_traversal', '/items/0/x', {}),
    ]
    checks = []
    for name, ref, aliases, expected in samples:
        try:
            observed = literal_resolve(document, ref, aliases)
            ok = type(observed) is type(expected) and observed == expected
            detail = {'expected': expected, 'observed': observed}
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            ok, detail = False, {'unexpected': type(exc).__name__}
        checks.append({'id': 'alias.literal.' + name, 'ok': ok, 'detail': detail})
    for name, ref, aliases in negatives:
        try:
            literal_resolve(document, ref, aliases)
            ok, detail = False, {'error': 'Unexpectedly resolved'}
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            ok, detail = True, {'rejected': type(exc).__name__}
        checks.append({'id': 'alias.literal.' + name, 'ok': ok, 'detail': detail})
    return checks


def _read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True,
                               separators=(',', ':')) + '\n', encoding='utf-8')


def prepare_fixture(bundle, workflow, variant):
    """Mutate only fresh copied evidence, never the saved P4 fixtures."""
    bundle = Path(bundle)
    claims_path = bundle / 'records/R15_claims.json'
    edges_path = bundle / 'records/R15_edges.json'
    result_path = bundle / 'records/R11_result.json'
    claims, edges, result = _read(claims_path), _read(edges_path), _read(result_path)
    claim = claims['claims'][0]
    direct = claim['source_pointer']
    metadata = copy.deepcopy(edges['field_metadata'][direct])
    edges['aliases'] = {'primary': direct}
    if variant == 'direct':
        pass
    elif variant == 'alias_primary':
        claim['source_pointer'] = 'alias:primary'
    elif variant == 'renamed_unicode':
        claim['source_pointer'] = 'alias:Δ primary:one '
        edges['aliases'] = {'Δ primary:one ': direct}
    elif variant == 'nested_name_once_positive':
        claim['source_pointer'] = 'alias:alias:primary'
        edges['aliases'] = {'alias:primary': direct}
    elif variant == 'unused_chain':
        edges['aliases']['unused'] = 'alias:other'
    elif variant == 'nested_name_no_recursive_peel':
        claim['source_pointer'] = 'alias:alias:primary'
    elif variant == 'full_token_key_only':
        claim['source_pointer'] = 'alias:primary'
        edges['aliases'] = {'alias:primary': direct}
    elif variant == 'bare_name':
        claim['source_pointer'] = 'primary'
    elif variant == 'unresolved':
        claim['source_pointer'] = 'alias:absent'
    elif variant == 'chain':
        claim['source_pointer'] = 'alias:primary'
        edges['aliases'] = {'primary': 'alias:secondary', 'secondary': direct}
    elif variant == 'cycle':
        claim['source_pointer'] = 'alias:primary'
        edges['aliases'] = {'primary': 'alias:primary'}
    elif variant == 'wrong_case':
        claim['source_pointer'] = 'alias:Primary'
    elif variant == 'empty_alias_name':
        claim['source_pointer'] = 'alias:'
    elif variant == 'empty_reference':
        claim['source_pointer'] = ''
    elif variant == 'empty_target':
        claim['source_pointer'] = 'alias:primary'
        edges['aliases']['primary'] = ''
    elif variant == 'wrong_value':
        if isinstance(claim['value'], dict):
            claim['value']['numerator'] += 1
        else:
            claim['value'] += 1
    elif variant == 'wrong_unit':
        claim['unit'] += '_wrong'
    elif variant == 'wrong_denominator':
        claim['denominator'] += 1
    elif variant == 'wrong_scope':
        claim['scope'] += '_wrong'
    elif variant == 'metadata_raw_alias_only':
        claim['source_pointer'] = 'alias:primary'
        edges['field_metadata']['alias:primary'] = edges['field_metadata'].pop(direct)
    elif variant == 'scalar_traversal':
        claim['source_pointer'] = direct + '/unexpected'
    elif variant == 'missing_pointer':
        claim['source_pointer'] = '/values/absent'
    elif workflow == 'W1' and variant in {'escaped_key', 'decode_once', 'bad_escape_2', 'unicode_object_key'}:
        key, token = {'escaped_key': ('a/b~c', 'a~1b~0c'),
                      'decode_once': ('~1', '~01'),
                      'bad_escape_2': ('a~2b', 'a~2b'),
                      'unicode_object_key': ('٠', '٠')}[variant]
        result['operands']['display_codes'][key] = 7
        pointer = '/operands/display_codes/' + token
        claim['source_pointer'] = 'alias:escaped'
        claim['value'] = 7
        edges['aliases'] = {'escaped': pointer}
        edges['field_metadata'][pointer] = metadata
    elif workflow == 'W2' and variant.startswith('array_'):
        token = {'array_0': '0', 'array_00': '00', 'array_arabic': '٠',
                 'array_fullwidth': '０', 'array_plus': '+0', 'array_negative': '-1',
                 'array_append': '-', 'array_out_of_range': '999999999'}[variant]
        pointer = '/operands/rows/' + token + '/staff'
        claim['source_pointer'] = 'alias:array'
        claim['value'] = result['operands']['rows'][0]['staff']
        edges['aliases'] = {'array': pointer}
        edges['field_metadata'][pointer] = metadata
    else:
        raise ValueError('Unknown fixture variant: ' + variant)
    _write(claims_path, claims)
    _write(edges_path, edges)
    _write(result_path, result)


def run_suite(context):
    """Pipeline API. Candidate invocations, limits and receipts are parent-owned."""
    checks = _literal_checks()
    mode = context.get('mode', 'full')
    reports = {}
    for workflow in ('W1', 'W2'):
        specs = COMMON + EXTRA[workflow]
        if mode == 'smoke':
            specs = tuple(x for x in specs if x[0] in SMOKE_VARIANTS)
        for variant, expected in specs:
            for arm in ARMS:
                label = 'alias-' + workflow + '-' + variant + '-' + arm
                bundle = Path(context['make_bundle'](workflow, label))
                prepare_fixture(bundle, workflow, variant)
                context['refresh_inventory'](bundle)
                actual = context['invoke'](bundle, workflow, arm, label)
                report, receipt = actual.get('report'), actual.get('receipt', {})
                vector = report.get('obligation_vector', {}) if isinstance(report, dict) else {}
                operational = receipt.get('execution_status') == 'COMPLETED'
                identity = isinstance(report, dict) and report.get('case_id', '').startswith('P5UNIT-')
                ok = operational and identity and vector.get('O15') == expected
                if expected == 'U':
                    ok = ok and vector.get('O01') == 'V'
                elif variant in {'direct', 'alias_primary', 'renamed_unicode', 'nested_name_once_positive', 'unused_chain', 'array_0'}:
                    ok = ok and len(vector) == 16 and set(vector.values()) == {'S'}
                if expected == 'V':
                    ok = ok and vector.get('O01') == 'S'
                    ok = ok and any(d.get('kind') == 'DIRECT_VIOLATION' and d.get('obligation_id') == 'O15'
                                    and d.get('path') == 'records/R15_claims.json' and d.get('json_pointer') == '/claims'
                                    for d in report.get('diagnostics', []))
                if expected != 'S':
                    ok = ok and report.get('aggregate') == 'REJECT'
                checks.append({'id': 'alias.cli.' + workflow + '.' + variant + '.' + arm,
                               'ok': bool(ok), 'detail': {'expected_O15': expected,
                               'observed_O15': vector.get('O15'), 'observed_O01': vector.get('O01'),
                               'execution_status': receipt.get('execution_status'),
                               'invocation_id': report.get('invocation_id') if isinstance(report, dict) else None,
                               'scope': 'O15 with original typed-admission precedence; full16S required for named neutral controls'}})
                reports[(workflow, variant, arm)] = report
    for workflow in ('W1', 'W2'):
        for arm in ARMS:
            direct = reports.get((workflow, 'direct', arm))
            alias = reports.get((workflow, 'alias_primary', arm))
            ok = isinstance(direct, dict) and isinstance(alias, dict)
            ok = ok and all(direct.get(k) == alias.get(k) for k in ('obligation_vector', 'coverage_mask', 'aggregate'))
            checks.append({'id': 'alias.metamorphic.direct_equivalent.' + workflow + '.' + arm,
                           'ok': bool(ok), 'detail': 'Identifier differences are excluded; all semantic vector/mask/aggregate fields must match.'})
    return checks
