import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_pair_angular_constraints import append_rows, linearize_angular
from test_scene_pair_problem import actors, samples
from scene_pair_problem import ScenePairProblem
from angular_motion_rows import AngularMotionRows
from coupled_pair_proposal import check_step
from strep import ROOT


def base():
    return dict(gaps=np.array([-.01]), gap_jacobian=np.array([[1., 0, 0, 0, 0, 0]]), depth_caps=np.array([.01]),
        vectors=np.zeros((0, 3)), jacobians=np.zeros((0, 3, 6)), radii=np.zeros(0), kinds=np.array([], dtype='U20'))


def test_angular_cone_prevents_position_only_clearance_improvement():
    original = base(); value = np.zeros((1, 3)); derivative = np.eye(3)[None]
    result = append_rows(original, [(0, value, derivative, np.array([0.]), np.array(['angular_speed']))])
    checks = check_step(np.array([.001, 0, 0, 0, 0, 0]), **{k:result[k] for k in ['gaps', 'gap_jacobian', 'depth_caps', 'vectors', 'jacobians', 'radii']}, trust=.002)
    assert checks['predicted_peak_m'] == pytest.approx(.009)
    assert checks['norm_excess'] == pytest.approx(.001)
    np.testing.assert_array_equal(result['jacobians'][:, :, 3:], 0)
    assert len(original['radii']) == 0


def test_actor_column_offsets_and_preexisting_constraints_are_preserved():
    original = base(); original.update(vectors=np.ones((1, 3)), jacobians=np.ones((1, 3, 6)), radii=np.array([2.]), kinds=np.array(['speed']))
    result = append_rows(original, [(3, np.zeros((1, 3)), np.eye(3)[None], np.array([1.]), np.array(['angular_acceleration']))])
    for key in ['vectors', 'jacobians', 'radii', 'kinds']: np.testing.assert_array_equal(result[key][:1], original[key])
    np.testing.assert_array_equal(result['jacobians'][1, :, :3], 0)
    np.testing.assert_array_equal(result['jacobians'][1, :, 3:], np.eye(3))


def test_unequal_actor_layouts_append_valid_angular_rows():
    pair = actors(); problem = ScenePairProblem(pair, samples(pair)); original = problem.linearize(np.zeros(problem.size))
    policies = [AngularMotionRows(a['model'], a['rig'].joints) for a in pair]
    result, proofs = linearize_angular(pair, policies, original)
    assert len(result['radii']) == len(original['radii'])+sum(len(p.radii) for p in policies)
    assert len(proofs) == 2 and all(max(p['directional_errors'].values()) < 1e-5 for p in proofs)
    for key in ['vectors', 'jacobians', 'radii', 'kinds']: np.testing.assert_array_equal(result[key][:len(original[key])], original[key])


@pytest.mark.parametrize('fault', ['offset', 'radius', 'kind', 'shape', 'nan'])
def test_invalid_angular_rows_are_rejected(fault):
    offset = 0; values = np.zeros((1, 3)); jac = np.zeros((1, 3, 3)); caps = np.ones(1); labels = np.array(['angular_speed'])
    if fault == 'offset': offset = 5
    if fault == 'radius': caps *= -1
    if fault == 'kind': labels = np.array(['speed'])
    if fault == 'shape': jac = np.zeros((1, 2, 3))
    if fault == 'nan': values[0, 0] = np.nan
    with pytest.raises(ValueError): append_rows(base(), [(offset, values, jac, caps, labels)])


@pytest.mark.skipif(not (ROOT/'reports/conic-solver-bootstrap-v1.json').exists(), reason='Locally pinned conic solver required')
def test_real_conic_solver_obeys_added_stationary_angular_constraint():
    from coupled_pair_proposal import solve
    original = base()
    baseline, baseline_report = solve(
        **{k:original[k] for k in ['gaps', 'gap_jacobian', 'depth_caps', 'vectors', 'jacobians', 'radii']}, trust=.001)
    constrained = append_rows(original, [(0, np.zeros((1, 3)), np.eye(3)[None], np.zeros(1), np.array(['angular_speed']))])
    step, report = solve(**{k:constrained[k] for k in ['gaps', 'gap_jacobian', 'depth_caps', 'vectors', 'jacobians', 'radii']}, trust=.001)
    assert baseline is not None and step is not None
    assert baseline_report['predicted_peak_m'] < .00901
    assert report['predicted_peak_m'] == pytest.approx(.01, abs=1e-8)
    np.testing.assert_allclose(step[:3], 0., atol=1e-8)
