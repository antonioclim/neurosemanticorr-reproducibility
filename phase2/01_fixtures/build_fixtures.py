"""Generate the hand-adjudicated Phase 2 fixture set without a checker."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
POLICY_ORDER = ('literal_only', 'suffix_only', 'either_unique', 'prefer_literal', 'prefer_suffix')


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def metadata(unit, denominator, scope='finite_table'):
    return {'unit': unit, 'denominator': denominator, 'scope': scope}


def claim(source_pointer, value, meta):
    return {'claims': [{'claim_id': 'claim', 'source_pointer': source_pointer, 'value': value, **meta}]}


def edges(aliases, fields, result_id):
    return {'aliases': aliases, 'field_metadata': fields, 'result_id': result_id}


def result(values, result_id):
    return {'values': values, 'result_id': result_id}


def emit_case(cases, case_id, group, claim_record, edge_record, result_record, expected, rationale):
    records = {'R15_claims.json': claim_record, 'R15_edges.json': edge_record}
    if result_record is not None:
        records['R11_result.json'] = result_record
    for name, record in records.items():
        write_json(ROOT / 'dockets' / case_id / 'records' / name, record)
    cases[case_id] = {'group': group, 'expected': dict(zip(POLICY_ORDER, expected, strict=True)),
                      'rationale': rationale}


def alias_cases(cases):
    literal = '/values/mean_staff'
    suffix = '/values/turnover_ratio/row01'
    aliases = {'alias:claim': literal, 'claim': suffix}
    staff = metadata('staff', 5)
    ratio = metadata('ratio', 1)
    edge = edges(aliases, {literal: staff, suffix: ratio}, 'F2-MIRROR-result')
    retained = result({'mean_staff': 26, 'turnover_ratio': {'row01': {'numerator': 142, 'denominator': 205}}},
                      'F2-MIRROR-result')
    literal_claim = claim('alias:claim', 26, staff)
    emit_case(cases, 'F2-MIRROR-LITERAL', 'alias_mirror', literal_claim, edge, retained, 'SVVSV',
              'Literal lookup matches value and metadata. Suffix lookup selects the distinct ratio. '
              'Unique-target lookup rejects the two destinations.')
    suffix_claim = claim('alias:claim', {'numerator': 142, 'denominator': 205}, ratio)
    emit_case(cases, 'F2-MIRROR-SUFFIX', 'alias_mirror', suffix_claim, edge, retained, 'VSVVS',
              'Suffix lookup matches the claim to the second value and its metadata. '
              'Literal lookup fails. Unique-target lookup rejects the two destinations.')
    emit_case(cases, 'F2-CONTEXT-SUFFIX', 'model_scope', literal_claim, edge, retained, 'SVVSV',
              'All three raw records are byte-identical to F2-MIRROR-LITERAL. A distinct '
              'synthetic context declares the suffix-local rule for its transcript adjudication.')


def direct_cases(cases):
    count = metadata('count', 3, 'cohort-a')
    alternate_count = metadata('count', 3, 'cohort-b')
    decoded_target = '/values/~01'
    slash_target = '/values/~1'
    escape_fields = {decoded_target: count, slash_target: count}
    escape_result = result({'~1': 73, '/': 97}, 'F2-ESCAPE-result')
    emit_case(cases, 'F2-RFC-ESCAPE-ORDER', 'non_alias', claim(decoded_target, 73, count),
              edges({}, escape_fields, 'F2-ESCAPE-result'), escape_result, 'SSSSS',
              'RFC 6901 transforms ~1 before ~0, so token ~01 denotes key ~1. The deliberately '
              'distinct value at key / exposes reversal of the decoding order.')
    paired_result = result({'~1': 73, '/': 73}, 'F2-IDENTITY-result')
    paired_edges = edges({}, {decoded_target: count, slash_target: alternate_count}, 'F2-IDENTITY-result')
    emit_case(cases, 'F2-IDENTITY-CORRECT', 'non_alias', claim(decoded_target, 73, count), paired_edges,
              paired_result, 'SSSSS', 'The intended target preserves the value and cohort-a field metadata.')
    emit_case(cases, 'F2-IDENTITY-WRONG-TARGET', 'non_alias', claim(slash_target, 73, count),
              paired_edges, paired_result, 'VVVVV', 'Both targets have value 73, but the changed pointer '
              'selects cohort-b and conflicts with the claim metadata for cohort-a.')
    array_index = '/values/rows/1'
    padded_index = '/values/rows/01'
    index_fields = {array_index: count, padded_index: count}
    array_edges = edges({}, index_fields, 'F2-ARRAY-result')
    array_result = result({'rows': [17, 73]}, 'F2-ARRAY-result')
    emit_case(cases, 'F2-RFC-ARRAY-INDEX', 'non_alias', claim(array_index, 73, count), array_edges,
              array_result, 'SSSSS', 'Array index /1 resolves to the second element.')
    emit_case(cases, 'F2-RFC-ARRAY-PADDED', 'non_alias', claim(padded_index, 73, count), array_edges,
              array_result, 'VVVVV', 'An array index with a leading zero violates RFC 6901. '
              'Matching field metadata is present so the expected failure is specifically resolution.')
    emit_case(cases, 'F2-RFC-OBJECT-PADDED', 'non_alias', claim(padded_index, 73, count),
              edges({}, index_fields, 'F2-OBJECT-result'), result({'rows': {'01': 73}}, 'F2-OBJECT-result'),
              'SSSSS', 'Object member 01 is a literal key and the array index restriction does not apply.')
    emit_case(cases, 'F2-MISSING-RESULT', 'missing_evidence', claim(array_index, 73, count),
              array_edges, None, 'UUUUU', 'R11 is absent. The claim syntax and metadata do not establish '
              'a conflict, but the referenced result cannot be verified.')


def build():
    cases = {}
    alias_cases(cases)
    direct_cases(cases)
    facts = {
        'direct_controls_underdetermined': {
            'classification': 'compatible', 'identification': 'underdetermined',
            'labels': {'F2-RFC-ESCAPE-ORDER': 'S', 'F2-RFC-ARRAY-PADDED': 'V', 'F2-MISSING-RESULT': 'U'},
            'remaining_policies': list(POLICY_ORDER),
            'rationale': 'The direct pointer and missing-evidence controls agree across every alias policy.'},
        'mirror_suffix_identifies_set': {
            'classification': 'compatible', 'identification': 'underdetermined',
            'labels': {'F2-MIRROR-SUFFIX': 'S'}, 'remaining_policies': ['suffix_only', 'prefer_suffix'],
            'rationale': 'The alias claim agrees only with the suffix destination. Two policies remain '
                         'because both select that destination in this case.'},
        'differing_local_rules_out_of_model': {
            'classification': 'out_of_model', 'identification': 'incompatible',
            'labels': {'F2-MIRROR-LITERAL': 'S', 'F2-CONTEXT-SUFFIX': 'V'}, 'remaining_policies': [],
            'synthetic_local_policies': {'F2-MIRROR-LITERAL': 'literal_only', 'F2-CONTEXT-SUFFIX': 'suffix_only'},
            'rationale': 'Independent manual assessments under the two declared local policies disagree '
                         'on byte-identical raw evidence. No single global policy yields that transcript.'},
    }
    write_json(ROOT / 'EXPECTED.json', {'schema': 'neurosemanticorr-r4-f2-expected/1',
                                      'policy_order': list(POLICY_ORDER), 'cases': cases, 'transcripts': facts})


if __name__ == '__main__':
    build()
