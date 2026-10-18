from pathlib import Path
import sys
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import native_precise_conic_step as module


def args():
    return dict(margins=np.array([-.2]), jacobian=np.array([[0., 1.]]),
        lower_delta=np.array([-.2, -.2]), upper_delta=np.array([.2, .2]),
        native_vectors=np.array([[.99, 0., 0.]]),
        native_matrix=sparse.csr_matrix([[1., 0.], [0., 1.], [0., 0.]]),
        native_radii=np.ones(1), l1_penalty=.1)


def test_exact_curvature_requires_inward_step():
    kw = args(); delta, report = module.conic_hinge_step(**kw)
    assert delta is not None, report
    assert abs(delta[1] - .2) < 1e-7
    assert abs(delta[0] - (np.sqrt(.96) - .99)) < 1e-7
    assert np.linalg.norm(kw['native_vectors'] + (kw['native_matrix'] @ delta).reshape(-1, 3)) <= 1 + 1e-8
    assert report['predicted_sum_model_violation'] < 1e-7
    assert report['native_cones'] == 1 and report['omitted_native_cones'] == 0
    assert report['sparse_matrix_bytes'] <= report['estimated_sparse_matrix_bytes']
    assert report['original_selected'] and not report['quality_approved'] and not report['release_approved']


def test_fixed_cones_are_retained_and_report_conflict():
    kw = args(); kw['native_matrix'] = sparse.csr_matrix((3, 2)); kw['native_vectors'] = np.array([[1.01, 0., 0.]])
    delta, report = module.conic_hinge_step(**kw)
    assert delta is None and report['native_cones'] == report['fixed_native_cones'] == 1
    assert report['solver_status'] in ('PrimalInfeasible', 'AlmostPrimalInfeasible')


def test_last_column_extra_row_and_peak_ceiling():
    kw = args(); kw.update(extra_matrix=np.array([[0., 1.]]), extra_upper=np.array([.1]), maximum_model_violation=.100001)
    delta, report = module.conic_hinge_step(**kw)
    assert delta is not None, report
    assert abs(delta[-1] - .1) < 1e-7
    assert report['extra_proposal_rows'] == 1 and report['complete_columns'] == 2
    assert .099999 <= report['predicted_sum_model_violation'] <= .100001


def test_all_model_rows_and_fixed_passing_cones_survive():
    kw = args(); kw.update(margins=np.array([-.2, -.1]), jacobian=np.array([[0., 1.], [0., -1.]]),
        native_vectors=np.array([[.99, 0., 0.], [1., 0., 0.]]), native_radii=np.ones(2),
        native_matrix=sparse.vstack([kw['native_matrix'], sparse.csr_matrix((3, 2))], format='csc'))
    delta, report = module.conic_hinge_step(**kw)
    assert delta is not None, report
    assert report['model_rows'] == report['native_cones'] == 2 and report['fixed_native_cones'] == 1
    assert report['predicted_sum_model_violation'] >= .3 - 1e-8


@pytest.mark.parametrize('field,value', [
    ('margins', [float('nan')]), ('margins', [1e7]), ('margins', [1, 2]),
    ('jacobian', [[float('inf'), 0]]), ('jacobian', np.empty((0, 2))),
    ('lower_delta', [.1, -.2]), ('upper_delta', [.2, -.1]),
    ('lower_delta', [-3., -.2]), ('upper_delta', [.2]),
    ('native_vectors', [[0., 1.]]), ('native_vectors', [[float('nan'), 0., 0.]]),
    ('native_matrix', np.zeros((3, 2))), ('native_matrix', sparse.csr_matrix((6, 2))),
    ('native_matrix', sparse.csr_matrix([[float('inf'), 0], [0, 0], [0, 0]])),
    ('native_radii', [0.]), ('native_radii', [-1.]), ('native_radii', [1, 1]),
    ('extra_matrix', [[0., 1.]]), ('extra_upper', [1.]),
    ('l1_penalty', 0.), ('l1_penalty', True), ('maximum_model_violation', -1.),
    ('maximum_matrix_bytes', True), ('maximum_matrix_bytes', 64 * 1024**2 + 1),
    ('time_limit_seconds', 0.), ('maximum_iterations', 0),
    ('solver_box_reserve', -1.), ('solver_box_reserve', 1e-4),
    ('solver_box_reserve', True), ('solver_box_reserve', float('nan')),
])
def test_invalid_complete_inputs(field, value):
    kw = args(); kw[field] = value
    with pytest.raises(ValueError): module.conic_hinge_step(**kw)


def test_budget_refuses_before_sparse_assembly(monkeypatch):
    kw = args(); kw['maximum_matrix_bytes'] = 1
    monkeypatch.setattr(module.sparse, 'hstack', lambda *a, **k: pytest.fail('allocated before budget check'))
    with pytest.raises(ValueError, match='budget'): module.conic_hinge_step(**kw)


def test_sparse_estimate_refuses_before_assembly(monkeypatch):
    kw = args(); kw['maximum_matrix_bytes'] = 260
    monkeypatch.setattr(module.sparse, 'hstack', lambda *a, **k: pytest.fail('allocated before sparse estimate'))
    with pytest.raises(ValueError, match='budget'): module.conic_hinge_step(**kw)


def test_inputs_not_mutated_or_clipped():
    kw = args(); original = {k: v.copy() for k, v in kw.items() if isinstance(v, np.ndarray)}
    native_before = kw['native_matrix'].copy()
    delta, report = module.conic_hinge_step(**kw)
    assert delta is not None, report
    for key, before in original.items(): np.testing.assert_array_equal(kw[key], before)
    assert (native_before != kw['native_matrix']).nnz == 0
    assert np.all(delta >= kw['lower_delta']) and np.all(delta <= kw['upper_delta'])


def test_interior_box_is_explicit_search_restriction():
    kw = args(); kw['solver_box_reserve'] = 1e-5
    delta, report = module.conic_hinge_step(**kw)
    assert delta is not None, report
    assert abs(delta[-1] - (.2 - 1e-5)) < 1e-8
    assert report['solver_box_reserve'] == 1e-5
    assert report['maximum_box_excess'] < -1e-6


@pytest.mark.parametrize('value',[0.,-1e-12,1e-8,1.01e-10,1e-15,float('nan'),float('inf'),True,'1e-12'])
def test_feasibility_target_never_relaxes_previous_solver_target(value):
    kw=args();kw['solver_feasibility_tolerance']=value
    with pytest.raises(ValueError,match='Feasibility target'):module.conic_hinge_step(**kw)


def test_tighter_solver_setting_preserves_model_and_admission(monkeypatch):
    actual=module.solver_module();records=[]
    from types import SimpleNamespace
    def observed(*args):
        records.append(args[-1].tol_feas)
        return actual.DefaultSolver(*args)
    proxy=SimpleNamespace(__version__=actual.__version__,DefaultSettings=actual.DefaultSettings,NonnegativeConeT=actual.NonnegativeConeT,SecondOrderConeT=actual.SecondOrderConeT,DefaultSolver=observed)
    monkeypatch.setattr(module,'solver_module',lambda:proxy)
    for value in [1e-10,1e-12]:
        kw=args();kw['solver_feasibility_tolerance']=value
        direction,report=module.conic_hinge_step(**kw)
        assert direction is not None,report
        assert report['solver_feasibility_tolerance']==value and report['norms_exceeding_admission']==0 and report['worst_norm_row']==0
        assert np.linalg.norm(kw['native_vectors']+(kw['native_matrix']@direction).reshape(-1,3))<=1+1e-8
    assert records==[1e-10,1e-12]


def test_solver_solved_status_does_not_override_norm_admission(monkeypatch):
    from types import SimpleNamespace
    actual=module.solver_module()
    point=np.array([.01+2e-8,0.,.01+2e-8,0.,.2])
    class RejectedSolver:
        def __init__(self,*args):pass
        def solve(self):return SimpleNamespace(x=point,status='Solved',iterations=1)
    proxy=SimpleNamespace(__version__=actual.__version__,DefaultSettings=actual.DefaultSettings,NonnegativeConeT=actual.NonnegativeConeT,SecondOrderConeT=actual.SecondOrderConeT,DefaultSolver=RejectedSolver)
    monkeypatch.setattr(module,'solver_module',lambda:proxy)
    direction,report=module.conic_hinge_step(**args())
    assert direction is None and not report['usable_direction'] and report['norms_exceeding_admission']==1 and report['worst_norm_row']==0
    assert report['maximum_native_norm_excess']>1e-8


def test_all_norm_identities_survive_duplicate_fixed_boundary_cones():
    kw=args();count=257
    kw['native_vectors']=np.vstack([kw['native_vectors'],np.tile([1.,0.,0.],(count,1))]);kw['native_radii']=np.ones(count+1)
    kw['native_matrix']=sparse.vstack([kw['native_matrix'],sparse.csr_matrix((3*count,2))],format='csr')
    direction,report=module.conic_hinge_step(**kw)
    assert direction is not None,report
    assert report['native_cones']==258 and report['fixed_native_cones']==257 and report['omitted_native_cones']==0
    assert report['norms_exceeding_admission']==0 and report['worst_norm_row'] in range(258)
