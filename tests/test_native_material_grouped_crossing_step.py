"""One complete pair contribution, hard original bounds and explicit ray checks."""
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy import sparse
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows
from native_triangle_separation_guards import SeparationGuards
import native_material_grouped_crossing_step as grouped


def args():
    gaps = np.r_[np.full(18, -.001), np.full(9, -.02), -.003]
    model = [NormRows([[0., 0., 0.]], [.01], [1.]), sparse.csr_matrix([[1.], [0.], [0.]]),
        gaps, sparse.csr_matrix(np.r_[np.ones(18), -np.ones(9), 0.][:, None]),
        [{'kind': 'triangle-separation'}]*27+[{'kind': 'penetrating-vertex'}],
        np.zeros(1), -np.ones(1), np.ones(1), .02]
    guard = SeparationGuards(np.array([.01]), sparse.csr_matrix((1, 1)), np.array([.001]), [{}],
                             dict(controls=1, complete_pair_partition=True))
    return model, dict(separation_guards=guard, triangle_groups=[list(range(i, i+9)) for i in (0, 9, 18)])


def test_easy_pairs_can_improve_while_one_deeper_triangle_remains_unresolved():
    a, kw = args(); delta, info = grouped.direction(*a, **kw)
    assert delta is not None and .00109 < delta[0] < .00111
    assert info['selected_grouped_deficit_sum_m'] < info['initial_grouped_deficit_sum_m']
    assert info['selected_worst_triangle_deficit_m'] > info['initial_worst_triangle_deficit_m']
    assert info['selected_material_peak_depth_m'] == info['original_material_depth_ceiling_m'] == .003
    assert info['triangle_group_count'] == 3 and info['complete_guide_rows'] == 28
    assert not info['solver_optimality_verified'] and not info['quality_approved'] and not info['release_approved']


def test_each_corner_still_constrains_its_complete_pair_maximum():
    a, kw = args(); a[2][0] = -.003
    seen = []
    delta, info = grouped.direction(*a, **kw, solver_sink=seen.append)
    assert delta is not None
    sample = seen[0]
    assert sample['quadratic'].shape == (4, 4)
    np.testing.assert_array_equal(sample['linear'], [0., 1., 1., 1.])
    # Two box rows, four native cone rows, one containment, one guard.
    slack = sample['matrix'][8:35, 1:].toarray()
    np.testing.assert_array_equal(slack, -np.repeat(np.eye(3), 9, axis=0))
    assert info['selected_grouped_deficit_sum_m'] == sum(info['selected_group_deficits_m'])


def test_original_native_cap_and_complete_guard_both_remain_hard():
    a, kw = args(); a[0].caps[0] = .0002
    kw['separation_guards'].gaps_m[0] = .00011
    kw['separation_guards'].clearances_m[0] = .0001
    kw['separation_guards'].jacobian = sparse.csr_matrix([[-1.]])
    delta, info = grouped.direction(*a, **kw)
    assert delta is not None and 0 < delta[0] <= .0002 and delta[0] <= .00011-.0001
    assert info['selected_native_maximum_excess'] <= 0 and info['selected_separation_guard_maximum_excess_m'] <= 0
    assert np.all(a[0].residual(a[1], delta) <= 0)


def test_unequal_corner_values_are_not_summed_as_extra_pair_weight():
    a, kw = args(); a[2][1:9] = .1
    delta, info = grouped.direction(*a, **kw)
    assert delta is not None and .00109 < delta[0] < .00111
    assert info['initial_group_deficits_m'] == [.0011, .0011, .0201]


def test_capture_mutation_does_not_change_guard_groups_or_returned_point():
    a, kw = args(); seen = []
    def sink(sample):
        seen.append(sample['matrix'].shape)
        sample['rhs'].fill(np.nan); sample['record']['triangle_groups'].clear(); sample['record']['returned_point'].clear()
    delta, info = grouped.direction(*a, **kw, solver_sink=sink)
    assert delta is not None and len(seen) == 1 and len(info['triangle_groups']) == 3 and len(info['returned_point']) == 4


@pytest.mark.parametrize('fault', ['missing', 'length', 'duplicate', 'omitted', 'containment', 'bool', 'unknown-index', 'non-list'])
def test_group_population_must_cover_every_triangle_row_exactly_once(monkeypatch, fault):
    a, kw = args(); groups = kw['triangle_groups']
    if fault == 'missing': kw['triangle_groups'] = []
    elif fault == 'length': groups[0].pop()
    elif fault == 'duplicate': groups[1][0] = 0
    elif fault == 'omitted': groups.pop()
    elif fault == 'containment': groups[0][0] = 27
    elif fault == 'bool': groups[0][0] = True
    elif fault == 'unknown-index': groups[0][0] = 28
    else: kw['triangle_groups'] = np.array(groups)
    monkeypatch.setattr(grouped, 'solver_module', lambda: pytest.fail('Invalid groups'))
    with pytest.raises(ValueError): grouped.direction(*a, **kw)


def fake(monkeypatch, status, point):
    class Settings: pass
    solver = SimpleNamespace(__version__='0.11.1', NonnegativeConeT=lambda n: n, SecondOrderConeT=lambda n: n,
        ZeroConeT=lambda n: n, DefaultSettings=Settings,
        DefaultSolver=lambda *a: SimpleNamespace(solve=lambda: SimpleNamespace(status=status, x=point, iterations=1)))
    monkeypatch.setattr(grouped, 'solver_module', lambda: solver)


@pytest.mark.parametrize('status,point,expected', [
    ('PrimalInfeasible', [.1, .1, .1, .1], 'NotMotionIterateStatus'),
    ('NumericalError', [.1, .1, .1, .1], 'NotMotionIterateStatus'),
    ('Solved', [np.nan, .1, .1, .1], 'InvalidReturnedPoint'),
    ('Solved', [0.], 'InvalidReturnedPoint'),
    ('InsufficientProgress', [2., .1, .1, .1], 'IterateOutsideOriginalBox'),
])
def test_invalid_motion_iterates_never_start_the_ray(monkeypatch, status, point, expected):
    a, kw = args(); fake(monkeypatch, status, point)
    class ForbiddenRay:
        def __iter__(self): pytest.fail('Invalid iterate')
    monkeypatch.setattr(grouped, 'FRACTIONS', ForbiddenRay())
    delta, info = grouped.direction(*a, **kw)
    assert delta is None and info['status'] == expected and info['solver_status'] == status


def test_guard_failure_causes_strict_retreat_and_status_is_not_relabelled(monkeypatch):
    a, kw = args(); fake(monkeypatch, 'InsufficientProgress', [.025, .1, .1, .1])
    guard = kw['separation_guards']; guard.gaps_m[0] = .0002; guard.clearances_m[0] = .0001
    guard.jacobian = sparse.csr_matrix([[-1.]])
    delta, info = grouped.direction(*a, **kw)
    assert delta is not None and 0 < delta[0] <= .0001 and info['selected_fraction'] < 1.
    assert info['records'][0]['separation_guard_maximum_excess_m'] > 0
    assert info['solver_status'] == 'InsufficientProgress' and info['selected_separation_guard_maximum_excess_m'] <= 0


def test_regressing_grouped_merit_never_becomes_motion(monkeypatch):
    a, kw = args(); fake(monkeypatch, 'Solved', [-.1, .1, .1, .1])
    delta, info = grouped.direction(*a, **kw)
    assert delta is None and info['status'] == 'NoStrictImprovingGroupedRay'
    assert len(info['records']) == 81


def test_depth_ceiling_remains_strict_even_when_grouped_deficit_improves(monkeypatch):
    a, kw = args(); a[3] = a[3].tolil(); a[3][-1, 0] = -1.; a[3] = a[3].tocsr()
    fake(monkeypatch, 'Solved', [.1, .1, .1, .1])
    delta, info = grouped.direction(*a, **kw)
    assert info['records'][0]['material_peak_depth_m'] > .003
    if delta is not None: assert info['selected_material_peak_depth_m'] <= .003
