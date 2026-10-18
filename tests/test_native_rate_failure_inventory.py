from pathlib import Path
import copy
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from native_rate_failure_inventory import rate_failure_inventory, METRICS


def populations(actors=('A',), joints=2, frames=4):
    result = []; first = 10
    for actor in actors:
        for metric in METRICS:
            order = 2 if metric.endswith('acceleration') else 1
            caps = np.zeros((frames - order, joints)); rates = np.zeros_like(caps)
            margins = -((rates - caps - .125) / np.maximum(caps, .001))
            result.append(dict(actor=actor, metric=metric, first_row=first,
                times_s=np.arange(frames, dtype=float) / 4, joint_nodes=np.arange(joints),
                joint_names=[f'joint-{j}' for j in range(joints)], caps=caps, tolerance=.125,
                raw_margins=margins.copy(), saved_margins=margins.copy(), saved_rates=rates))
            first += caps.size + 1
    return result


def saved_value(g, i, j, value):
    g['saved_rates'][i, j] = value
    g['saved_margins'] = -((g['saved_rates'] - g['caps'] - g['tolerance']) / np.maximum(g['caps'], .001))


def test_every_actor_metric_and_joint_population_is_accounted():
    p = populations(('A', 'B')); r = rate_failure_inventory(p, ['A', 'B'])
    assert r['report']['complete_rows'] == 40 and r['report']['complete_groups'] == 8
    assert len(r['joint_groups']) == 16 and len(r['groups']) == 8 and r['failures'] == []
    assert all(g['rows'] in [4, 6] for g in r['groups'])
    assert not r['report']['quality_approved'] and not r['report']['release_approved']


def test_union_modes_keeps_last_stencil_joint_and_exact_global_row_identity():
    p = populations(('A', 'B')); last = p[-1]; saved_value(last, 1, 1, .25)
    p[0]['raw_margins'][0, 0] = -3.
    r = rate_failure_inventory(p, ['A', 'B']); rows = r['failures']
    assert len(rows) == 2 and rows[0]['row'] == 10
    assert rows[0]['fails_raw'] and not rows[0]['fails_saved']
    assert rows[1]['row'] == last['first_row'] + 3 and rows[1]['joint_node'] == 1
    assert rows[1]['times_s'] == [.25, .5, .75] and rows[1]['units'] == 'rad/s^2'
    assert rows[1]['saved_measured_rate'] == .25 and rows[1]['saved_signed_excess'] == .125
    assert rows[1]['fails_saved'] and not rows[1]['fails_raw']
    assert r['report']['raw_failed'] == r['report']['saved_failed'] == 1 and r['report']['both_failed'] == 0


def test_exact_zero_cap_is_distinct_from_small_positive_cap():
    p = populations(); p[0]['caps'][0, 1] = 1e-18
    saved_value(p[0], 0, 0, 1.); saved_value(p[0], 0, 1, 1.)
    r = rate_failure_inventory(p, ['A'])
    assert [v['original_cap_exactly_zero'] for v in r['failures']] == [True, False]
    assert r['report']['zero_cap_failed'] == r['report']['positive_cap_failed'] == 1


def test_exact_original_tolerance_boundary_is_not_changed():
    p = populations(); saved_value(p[0], 0, 0, .125)
    before = p[0]['saved_margins'].tobytes(); r = rate_failure_inventory(p, ['A'])
    assert not r['failures'] and p[0]['saved_margins'].tobytes() == before
    assert r['report']['physical_margin_tolerance_added'] == 0


def test_all_512_joints_and_final_time_are_retained():
    p = populations(joints=512); saved_value(p[-1], 1, 511, .25)
    r = rate_failure_inventory(p, ['A']); last = r['failures'][0]
    assert last['joint_node'] == 511 and last['row'] == p[-1]['first_row'] + 1023
    assert len(r['joint_groups']) == 2048 and r['report']['failure_records'] == 1


def test_inputs_are_immutable():
    p = populations(); saved_value(p[0], 0, 0, .25); old = copy.deepcopy(p)
    rate_failure_inventory(p, ['A'])
    for a, b in zip(p, old):
        for key in a:
            if isinstance(a[key], np.ndarray): assert a[key].tobytes() == b[key].tobytes()
            else: assert a[key] == b[key]


def test_record_budget_rejects_every_failure_instead_of_selecting_subset():
    p = populations(); saved_value(p[0], 0, 0, .25); saved_value(p[-1], 1, 1, .25)
    with pytest.raises(ValueError, match='no failure selection'): rate_failure_inventory(p, ['A'], maximum_records=1)


@pytest.mark.parametrize('kind', ['input', 'rows', 'records', 'bool_budget', 'oversized_budget'])
def test_explicit_budgets_reject_whole_inventory(kind):
    kw = {'input': {'maximum_array_bytes': 1}, 'rows': {'maximum_rows': 1},
          'records': {'maximum_records': 0}, 'bool_budget': {'maximum_array_bytes': True},
          'oversized_budget': {'maximum_array_bytes': 64 * 1024**2 + 1}}[kind]
    with pytest.raises(ValueError): rate_failure_inventory(populations(), ['A'], **kw)


@pytest.mark.parametrize('kind', ['missing_metric', 'undeclared_actor', 'duplicate_metric', 'overlap',
    'names', 'nodes', 'different_clock', 'nonuniform_clock', 'negative_cap', 'negative_rate',
    'nan', 'infinite_margin', 'shape', 'bool_tolerance', 'negative_tolerance', 'extra_field',
    'changed_canonical_byte', 'float32_margin', 'empty_actors', 'duplicate_actors', 'unknown_metric'])
def test_invalid_or_incomplete_source_populations_reject(kind):
    p = populations(); actors = ['A']
    if kind == 'missing_metric': p.pop()
    elif kind == 'undeclared_actor': p[0]['actor'] = 'B'
    elif kind == 'duplicate_metric': p[0]['metric'] = p[1]['metric']
    elif kind == 'overlap': p[1]['first_row'] = p[0]['first_row']
    elif kind == 'names': p[1]['joint_names'][0] = 'different-joint'
    elif kind == 'nodes': p[0]['joint_nodes'][1] = 0
    elif kind == 'different_clock': p[1]['times_s'] += .01
    elif kind == 'nonuniform_clock': p[0]['times_s'][1] += .01
    elif kind == 'negative_cap': p[0]['caps'][0, 0] = -1.
    elif kind == 'negative_rate': p[0]['saved_rates'][0, 0] = -1.
    elif kind == 'nan': p[0]['saved_rates'][0, 0] = np.nan
    elif kind == 'infinite_margin': p[0]['raw_margins'][0, 0] = np.inf
    elif kind == 'shape': p[0]['saved_rates'] = p[0]['saved_rates'][:, :1]
    elif kind == 'bool_tolerance': p[0]['tolerance'] = True
    elif kind == 'negative_tolerance': p[0]['tolerance'] = -.1
    elif kind == 'extra_field': p[0]['source_changed'] = True
    elif kind == 'changed_canonical_byte': p[0]['saved_margins'][0, 0] = np.nextafter(p[0]['saved_margins'][0, 0], np.inf)
    elif kind == 'float32_margin': p[0]['saved_margins'] = p[0]['saved_margins'].astype(np.float32)
    elif kind == 'empty_actors': actors = []
    elif kind == 'duplicate_actors': actors = ['A', 'A']
    elif kind == 'unknown_metric': p[0]['metric'] = 'fitness'
    with pytest.raises(ValueError): rate_failure_inventory(p, actors)
