"""Read frozen prospective records for the R2 review. This launches no checker."""

import argparse
from collections import Counter
from fractions import Fraction
from hashlib import sha256
import json
from math import comb
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def probability_text(value):
    return {'fraction': str(value), 'decimal': float(value)}


def combine_distributions(left, right):
    totals = Counter()
    for a, wa in left.items():
        for b, wb in right.items():
            totals[a + b] += wa * wb
    return dict(totals)


def quantile(distribution, level):
    total = sum(distribution.values())
    seen = 0
    for value, count in sorted(distribution.items()):
        seen += count
        if Fraction(seen, total) >= level:
            return value
    raise ValueError('Empty distribution')


def worst_zero_tail(frames):
    """Maximise zero-hit probability over all allocations at each pooled count."""
    states = {0: (Fraction(1), ())}
    for population, sample in frames:
        choices = [Fraction(comb(population - errors, sample), comb(population, sample))
                   for errors in range(population + 1)]
        following = {}
        for previous, (probability, allocation) in states.items():
            for errors, miss in enumerate(choices):
                count, bound = previous + errors, probability * miss
                if count not in following or bound > following[count][0]:
                    following[count] = (bound, allocation + (errors,))
        states = following
    return states


def evaluate(root):
    selected_path = root / 'evaluation/BLIND_SELECTION.json'
    expected_path = root / '00_plan/O15_REFERENCE.json'
    results_path = root / 'evaluation/PROSPECTIVE_RESULTS.json'
    selection, expected, results = map(read, (selected_path, expected_path, results_path))
    assert digest(selected_path) == results['blind_selection_sha256']
    assert digest(expected_path) == results['reference_sha256']
    ref = {r['case_id']: r['expected'] for r in expected['cases']}
    assert set(ref) == set(selection['case_outputs']) and len(ref) == 192
    actual = {r['case_id'] for r in results['agreement_error_cases']}
    budget = results['per_context_budget']
    uniform_dist = {0: 1}
    expected_yield, expected_gain = Fraction(0), Fraction(0)
    precision_panels = []
    contexts = {}
    for context, values in sorted(results['contexts'].items()):
        frame = {case: record for case, record in selection['case_outputs'].items()
                 if record['context'] == context}
        assert all(row['comparable'] and len(set(row['O15'])) == 1 for row in frame.values())
        errors = {case for case, row in frame.items() if row['O15'][0] != ref[case]}
        assert errors == actual.intersection(frame)
        alias, flags = set(), set()
        for case, row in frame.items():
            dossier = root / 'dockets' / case / 'records/R15_claims.json'
            claims = read(dossier)['claims']
            if any(claim['source_pointer'].startswith('alias:') for claim in claims):
                alias.add(case)
            if row['screen']['status'] == 'flagged':
                flags.add(case)
        assert flags <= alias and len(alias) == budget
        population, failures, flag_failures = len(frame), len(errors), len(errors & flags)
        hits = {n: comb(failures, n) * comb(population - failures, budget - n)
                for n in range(failures + 1) if n <= budget}
        assert sum(hits.values()) == comb(population, budget)
        uniform_dist = combine_distributions(uniform_dist, hits)
        expected_uniform = Fraction(budget * failures, population)
        expected_screen = flag_failures + Fraction((budget - len(flags)) * (failures - flag_failures),
                                                   population - len(flags))
        expected_yield += expected_uniform
        expected_gain += expected_screen - expected_uniform
        screen = values['policy_results']['screen_and_uniform']
        uniform = values['policy_results']['uniform_completion']
        assert screen['residual_errors_sampled'] == 0
        precision_panels.append((screen['residual_population'], screen['residual_sample']))
        residual_draw = set(selection['context_selections'][context]['screen_and_uniform']['residual_draw'])
        assert len(residual_draw) == screen['residual_sample'] and not residual_draw & flags
        contexts[context] = {'population': population, 'errors_in_full_reference': failures,
                             'any_alias_reviewed': len(alias), 'any_alias_found': len(alias & errors),
                             'any_alias_deterministic_interval': [len(alias & errors),
                                                                   len(alias & errors) + population - len(alias)],
                             'screen_first_stage': len(flags), 'screen_first_stage_errors': flag_failures,
                             'screen_uniform_residual': screen['residual_sample'],
                             'screen_residual_cases_without_alias': len(residual_draw - alias),
                             'screen_observed': screen['agreement_errors_found'],
                             'uniform_observed': uniform['agreement_errors_found'],
                             'uniform_exact_upper': uniform['one_look_upper'],
                             'screen_exact_upper': screen['one_look_upper']}
    zero = worst_zero_tail(precision_panels)
    alpha = Fraction(1, 20)
    pooled_upper = max(count for count, (prob, _) in zero.items() if prob > alpha)
    assert pooled_upper == 6
    assert sum(row['any_alias_found'] for row in contexts.values()) == 32
    return {'scope': 'Post hoc sensitivity on the fixed prospective frame, no candidate execution',
            'source_sha256': {p.name: digest(p) for p in (selected_path, expected_path, results_path)},
            'contexts': contexts,
            'uniform_conditional_expectation': probability_text(expected_yield),
            'screen_minus_uniform_conditional_expectation': probability_text(expected_gain),
            'uniform_equal_tailed_central_95_percent_range': [quantile(uniform_dist, Fraction(1, 40)),
                                                              quantile(uniform_dist, Fraction(39, 40))],
            'design_assumptions_for_zero_hit_bound': 'Independent simple random samples within four fixed residual strata',
            'pooled_zero_hit_sample_counts': precision_panels,
            'pooled_maximum_zero_hit_at_boundary': {
                str(count): {'probability': probability_text(zero[count][0]), 'allocation': zero[count][1]}
                for count in (pooled_upper, pooled_upper + 1)},
            'pooled_post_hoc_residual_upper_95_percent': pooled_upper,
            'pooled_post_hoc_total_upper_95_percent': 32 + pooled_upper,
            'prespecified_screen_bonferroni_upper': results['primary_familywise_upper_sum']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prospective_root', type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.prospective_root), indent=2, sort_keys=True))
