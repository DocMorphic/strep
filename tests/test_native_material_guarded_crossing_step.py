"""Worst triangle support cannot be bought with deeper vertices or looser motion."""
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy import sparse
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows
import native_material_guarded_crossing_step as crossing
from native_triangle_separation_guards import SeparationGuards


def constant_guards():
    return SeparationGuards(np.array([.01]), sparse.csr_matrix((1,1)), np.array([.001]),
        [{}], dict(complete_pair_partition=True, controls=1))

def call(*a, **kw):
    kw.setdefault('separation_guards', constant_guards())
    return crossing.direction(*a, **kw)

def args(repeats=1):
    gaps = np.r_[-.02, np.full(repeats, -.01), -.003]
    return [NormRows([[0., 0., 0.]], [.01], [1.]),
        sparse.csr_matrix([[1.], [0.], [0.]]), gaps,
        sparse.csr_matrix(np.r_[1., np.full(repeats, -1.), 0.][:, None]),
        [{'kind': 'triangle-separation'}]*(1+repeats)+[{'kind': 'penetrating-vertex'}],
        np.zeros(1), -np.ones(1), np.ones(1), .02]


def test_worst_triangle_support_rebalances_conflicting_pairs_without_changing_depth():
    delta, info = call(*args())
    assert delta is not None and .00499 < delta[0] < .00501
    assert .01509 < info['selected_worst_triangle_deficit_m'] < .01511
    assert info['selected_material_peak_depth_m'] == info['original_material_depth_ceiling_m'] == .003
    assert info['triangle_rows'] == [0, 1] and info['containment_rows'] == [2]
    assert info['all_guide_rows_retained'] and not info['solver_optimality_verified']
    assert not info['quality_approved'] and not info['release_approved']


def test_one_hundred_repeated_pairs_do_not_buy_extra_objective_weight():
    one, _ = call(*args())
    repeated, info = call(*args(100))
    assert one is not None and repeated is not None
    np.testing.assert_allclose(repeated, one, rtol=0., atol=1e-8)
    assert info['complete_guide_rows'] == 102 and len(info['triangle_rows']) == 101


def test_every_coupled_original_norm_and_scale_limits_the_direction():
    a = args()
    a[0] = NormRows([[0., 0., 0.], [0., 0., 0.], [.001, 0., 0.]], [.01, .0002, .001], [1., .1, 1.])
    a[1] = sparse.csr_matrix([[1.], [0.], [0.], [2.], [3.], [0.], [0.], [0.], [0.]])
    delta, info = call(*a)
    assert delta is not None and 0 < np.sqrt(13)*delta[0] <= .0002
    assert np.all(a[0].residual(a[1], delta) <= 0)
    assert info['original_norm_rows'] == 3 and info['active_original_norm_cones'] == 2
    assert info['omitted_exactly_fixed_passing_norms'] == 1


def test_no_containment_witness_still_allows_complete_triangle_guidance():
    a = args(); a[4][-1] = {'kind': 'triangle-separation'}
    delta, info = call(*a)
    assert delta is not None and info['containment_rows'] == []
    assert info['selected_material_peak_depth_m'] == info['original_material_depth_ceiling_m'] == 0.


def test_depth_ceiling_is_a_hard_conic_row_instead_of_an_objective_weight():
    a = args(); a[3] = sparse.csr_matrix([[1.], [-1.], [-1.]])
    captured = []
    delta, info = call(*a, solver_sink=captured.append)
    sample = captured[0]
    # Native box: 2 rows; original norm: 4; one containment: 1.
    assert sample['matrix'][6, 0] == .02/.005 and sample['matrix'][6, 1] == 0.
    assert sample['rhs'][6] == 0.
    if delta is not None:
        assert info['selected_material_peak_depth_m'] <= .003
    assert not info['quality_approved']


def test_original_control_and_trust_bounds_remain_hard():
    a = args(); a[7][0] = .0001
    delta, info = call(*a)
    assert delta is not None and 0 < delta[0] <= .0001
    assert info['selected_native_maximum_excess'] <= 0


def test_homogeneous_parameter_rows_are_preserved_without_export_claims():
    delta, info = call(*args(), parameter_rows=[[1.]])
    if delta is not None:
        assert abs(delta[0]) <= 1e-9
    assert info['parameter_proposal_tolerance'] == 1e-9 and not info['release_approved']


def test_capture_is_complete_and_mutating_it_does_not_change_the_record():
    a = args(); seen = []
    def sink(sample):
        seen.append(sample['matrix'].shape)
        sample['rhs'].fill(np.nan); sample['record']['returned_point'].clear()
        sample['record']['witnesses'].clear()
    delta, info = call(*a, solver_sink=sink)
    assert delta is not None and seen == [(11, 2)]
    assert len(info['returned_point']) == 2 and len(info['witnesses']) == 3
    assert np.isfinite(a[2]).all()


@pytest.mark.parametrize('kind', ['anchor', 'no-triangle', 'already-clear'])
def test_unusable_anchor_or_missing_deficit_never_calls_solver(monkeypatch, kind):
    a = args()
    if kind == 'anchor': a[0].vectors[0, 0] = .02
    elif kind == 'no-triangle': a[4] = [{'kind': 'penetrating-vertex'}]*3
    else: a[2][:2] = .001
    monkeypatch.setattr(crossing, 'solver_module', lambda: pytest.fail('No triangle proposal'))
    delta, _ = call(*a); assert delta is None


@pytest.mark.parametrize('fault', ['native-jac', 'guide-jac', 'population', 'kind', 'gap-sign', 'gap-nan',
    'cap', 'scale', 'box', 'trust', 'clearance', 'metric-scale', 'parameters', 'sink'])
def test_invalid_complete_model_rejects_before_solver(monkeypatch, fault):
    a = args(); kw = {}
    if fault == 'native-jac': a[1] = sparse.eye(3)
    elif fault == 'guide-jac': a[3] = sparse.eye(2)
    elif fault == 'population': a[4].pop()
    elif fault == 'kind': a[4][0] = {'kind': 'invented'}
    elif fault == 'gap-sign': a[2][-1] = .001
    elif fault == 'gap-nan': a[2][0] = np.nan
    elif fault == 'cap': a[0].caps[0] = -1.
    elif fault == 'scale': a[0].scales[0] = 0.
    elif fault == 'box': a[6] = a[7].copy()
    elif fault == 'trust': a[8] = True
    elif fault == 'clearance': kw['clearance_m'] = True
    elif fault == 'metric-scale': kw['scale_m'] = np.nan
    elif fault == 'parameters': kw['parameter_rows'] = [[1., 0.]]
    else: kw['solver_sink'] = True
    monkeypatch.setattr(crossing, 'solver_module', lambda: pytest.fail('Invalid complete model'))
    with pytest.raises(ValueError): call(*a, **kw)


def fake_solver(monkeypatch, status, point):
    class Settings: pass
    fake = SimpleNamespace(__version__='0.11.1', NonnegativeConeT=lambda n: n,
        SecondOrderConeT=lambda n: n, ZeroConeT=lambda n: n, DefaultSettings=Settings,
        DefaultSolver=lambda *a: SimpleNamespace(solve=lambda: SimpleNamespace(status=status, x=point, iterations=1)))
    monkeypatch.setattr(crossing, 'solver_module', lambda: fake)


@pytest.mark.parametrize('status,point,expected', [
    ('PrimalInfeasible', [.1, .1], 'NotMotionIterateStatus'),
    ('NumericalError', [.1, .1], 'NotMotionIterateStatus'),
    ('Solved', [np.nan, .1], 'InvalidReturnedPoint'),
    ('Solved', [0.], 'InvalidReturnedPoint'),
    ('InsufficientProgress', [2., .1], 'IterateOutsideOriginalBox'),
])
def test_invalid_iterates_never_reach_the_ray(monkeypatch, status, point, expected):
    fake_solver(monkeypatch, status, point)
    class ForbiddenRay:
        def __iter__(self):pytest.fail('Invalid iterate cannot start ray')
    monkeypatch.setattr(crossing, 'FRACTIONS', ForbiddenRay())
    delta, info = call(*args())
    assert delta is None and info['status'] == expected and info['solver_status'] == status


def test_stalled_finite_iterate_keeps_status_and_requires_strict_improvement(monkeypatch):
    fake_solver(monkeypatch, 'InsufficientProgress', [.1, .1])
    delta, info = call(*args())
    assert delta is not None and delta[0] == .002 and info['solver_status'] == 'InsufficientProgress'
    assert info['selected_worst_triangle_deficit_m'] < info['initial_worst_triangle_deficit_m']
    assert not info['solver_optimality_verified']


def test_tiny_depth_ceiling_violation_cannot_be_accepted_after_native_ray(monkeypatch):
    a = args(); a[3] = sparse.csr_matrix([[1.], [-1.], [-1e-12]])
    fake_solver(monkeypatch, 'AlmostSolved', [.1, .1])
    delta, info = call(*a)
    assert info['records'][0]['material_peak_depth_m'] > info['original_material_depth_ceiling_m']
    if delta is not None:
        assert info['selected_material_peak_depth_m'] <= info['original_material_depth_ceiling_m']
        assert info['selected_fraction'] < 1.
    assert info['strict_material_depth_tolerance_m'] == 0.


def test_worst_triangle_regression_cannot_be_hidden_by_improving_other_rows(monkeypatch):
    fake_solver(monkeypatch, 'Solved', [-.1, .1])
    delta, info = call(*args(100))
    assert delta is None and info['status'] == 'NoStrictImprovingGuardedRay'


def test_nonzero_parameter_residual_cannot_be_hidden_by_crossing_improvement(monkeypatch):
    fake_solver(monkeypatch, 'Solved', [.1, .1])
    delta, info = call(*args(), parameter_rows=[[1.]])
    assert info['records'][0]['parameter_maximum_absolute_residual'] > 1e-9
    if delta is not None:
        assert info['parameter_maximum_absolute_residual'] <= 1e-9 and info['selected_fraction'] < 1.


def test_every_guard_is_hard_and_zero_excess_required_after_solver_status():
    guard=SeparationGuards(np.array([.0002,.005]),sparse.csr_matrix([[-1.],[-10.]]),
        np.array([1e-8,1e-8]),[{},{}],dict(complete_pair_partition=True,controls=1))
    delta,info=call(*args(),separation_guards=guard)
    assert delta is not None and 0<delta[0]<=.0002-1e-8
    assert np.all(guard.gaps_m+guard.jacobian@delta>=guard.clearances_m)
    assert info['complete_separation_guard_rows']==2 and info['selected_separation_guard_maximum_excess_m']<=0.


def test_rounded_solver_guard_violation_forces_an_explicit_checked_ray_retreat(monkeypatch):
    guard=SeparationGuards(np.array([.001]),sparse.csr_matrix([[-1.]]),np.array([.0001]),
        [{}],dict(complete_pair_partition=True,controls=1))
    fake_solver(monkeypatch,'Solved',[.1,.1])
    delta,info=call(*args(),separation_guards=guard)
    assert delta is not None and 0<delta[0]<=.0009
    assert info['records'][0]['separation_guard_maximum_excess_m']>0
    assert info['selected_fraction']<1. and info['selected_separation_guard_maximum_excess_m']<=0.
    assert info['strict_separation_guard_tolerance_m']==0.


@pytest.mark.parametrize('fault',['type','shape','nan','margin','partition','control-count','descriptors','anchor'])
def test_invalid_or_nonpassing_complete_guard_contract_cannot_call_a_solver(monkeypatch,fault):
    guard=constant_guards()
    if fault=='type':guard={}
    elif fault=='shape':guard.jacobian=sparse.csr_matrix((1,2))
    elif fault=='nan':guard.gaps_m[0]=np.nan
    elif fault=='margin':guard.clearances_m[0]=0.
    elif fault=='partition':guard.report['complete_pair_partition']=False
    elif fault=='control-count':guard.report['controls']=2
    elif fault=='descriptors':guard.descriptors=[]
    else:guard.gaps_m[0]=0.
    monkeypatch.setattr(crossing,'solver_module',lambda:pytest.fail('Invalid guard'))
    if fault=='anchor':
        delta,info=call(*args(),separation_guards=guard)
        assert delta is None and info['status']=='OriginalSeparationGuardAnchorNotPassing'
    else:
        with pytest.raises(ValueError):call(*args(),separation_guards=guard)


def test_empty_whole_box_certified_guard_population_is_explicit_and_usable():
    guard=SeparationGuards(np.empty(0),sparse.csr_matrix((0,1)),np.empty(0),[],dict(complete_pair_partition=True,controls=1))
    delta,info=call(*args(),separation_guards=guard)
    assert delta is not None and info['complete_separation_guard_rows']==0 and info['selected_separation_guard_maximum_excess_m']==0.
