"""Original moving triangle points, complete derivatives and preflight budgets."""
import copy, sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from native_material_witness_guides import MaterialWitnessGuides, linearize_material_guides
from native_scene_geometry import faces_for
from native_scene_norms import rows, linearize
from test_native_pair_clearance_guide import setup


def descriptors():
    return [dict(actor_a='A', vertex_a=0, actor_b='B', face_b=0, barycentric_b=[.2, .3, .5],
                 time_s=1., axis_world=[.6, 0., .8], clearance_m=.0001, scale_m=.03),
            dict(actor_a='B', vertex_a=3, actor_b='A', face_b=1, barycentric_b=[0., .4, .6],
                 time_s=2., axis_world=[-1., 0., 0.], clearance_m=.002, scale_m=.007)]


def direct(problem, worlds, guides):
    points, gaps = [], []
    for guide in guides:
        frame = int(np.flatnonzero(problem.times == guide['time_s'])[0])
        actor = problem.scene.actors[guide['actor_a']]
        p, r = actor['placement']
        source = actor['rig'].vertices(worlds[guide['actor_a']][frame])[guide['vertex_a']] @ r.T + p
        actor = problem.scene.actors[guide['actor_b']]
        p, r = actor['placement']
        ids = faces_for(actor['rig'])[0][guide['face_b']]
        triangle = actor['rig'].vertices(worlds[guide['actor_b']][frame])[ids] @ r.T + p
        target = sum(weight*corner for weight, corner in zip(guide['barycentric_b'], triangle))
        points.append(np.concatenate([source[None], triangle]).ravel())
        gaps.append(float((source-target) @ guide['axis_world']))
    return np.concatenate(points), np.array(gaps)


def test_moving_material_points_and_every_original_native_stencil_match_direct_geometry(tmp_path):
    problem, x, decoded, _ = setup(tmp_path)
    guides, samples, calls = descriptors(), {}, []
    original = problem.worlds
    def trace(value, quantized=True):
        if not quantized and np.count_nonzero(value-x) == 1: calls.append(value.copy())
        return original(value, quantized=quantized)
    problem.worlds = trace
    model = linearize_material_guides(problem, x, decoded, guides, stencil_sink=lambda c, s, v: samples.update({(c, s): v}))
    assert len(calls) == len(samples) == model.identity['column_proxy_evaluations'] == 2*len(x)
    native, jac, _ = linearize(problem, x, step=.001, difference_source='continuous', difference_scheme='central', base_worlds=decoded)
    for key in ('vectors', 'caps', 'scales'): np.testing.assert_array_equal(getattr(model.native, key), getattr(native, key))
    np.testing.assert_array_equal(model.native_jacobian.toarray(), jac.toarray())
    points, gaps = direct(problem, decoded, guides)
    np.testing.assert_allclose(points, model.points, atol=2e-16, rtol=0)
    np.testing.assert_allclose(gaps, model.gaps_m, atol=2e-16, rtol=0)
    scales = np.array([g['scale_m'] for g in guides])
    np.testing.assert_array_equal(model.guide_residual, (model.gaps_m-np.array([g['clearance_m'] for g in guides]))/scales)
    for c in range(len(x)):
        vectors, differences = [], []
        for h, sign in ((.001, 1), (-.001, -1)):
            value = x.copy(); value[c] += h
            worlds = original(value, quantized=False)
            actual = rows(problem, value, worlds)
            points, gaps = direct(problem, worlds, guides)
            sample = samples[c, sign]
            np.testing.assert_array_equal(value, sample['controls'])
            np.testing.assert_allclose(points, sample['points'], atol=2e-16, rtol=0)
            np.testing.assert_allclose(gaps, sample['gaps_m'], atol=2e-16, rtol=0)
            for key in ('vectors', 'caps', 'scales'): np.testing.assert_array_equal(getattr(actual, key), sample[key])
            vectors.append(actual.vectors); differences.append(sample['gaps_m'])
        np.testing.assert_array_equal((differences[0]-differences[1])/.002/scales, model.guide_jacobian.getcol(c).toarray().ravel())
        np.testing.assert_array_equal(((vectors[0]-vectors[1])/.002).ravel(), model.native_jacobian.getcol(c).toarray().ravel())
    assert model.identity['point_coordinate_offsets'] == [0, 12, 24]
    assert model.identity['target_triangle_vertices'] == [faces_for(problem.scene.actors[g['actor_b']]['rig'])[0][g['face_b']].tolist() for g in guides]
    assert model.identity['all_original_native_norm_rows_retained'] and model.identity['all_original_caps_scales_unchanged']
    assert not model.identity['quality_approved'] and not model.identity['release_approved']
    guides[0]['barycentric_b'].clear()
    assert model.identity['guides'][0]['barycentric_b'] == [.2, .3, .5]


def test_target_point_moves_with_original_triangle_instead_of_freezing_world_location(tmp_path):
    problem, x, decoded, _ = setup(tmp_path)
    guide = descriptors()[1]
    observer = MaterialWitnessGuides(problem, [guide])
    before, _ = observer.observe(decoded)
    value = x.copy(); value[0] += .001
    after, _ = observer.observe(problem.worlds(value, quantized=False))
    # A is edited at this interior time; use t=1 to expose its material motion.
    guide['time_s'] = 1.
    observer = MaterialWitnessGuides(problem, [guide])
    before, gap = observer.observe(decoded)
    after, new_gap = observer.observe(problem.worlds(value, quantized=False))
    assert np.array_equal(before[:3], after[:3])
    assert np.any(before[3:] != after[3:]) and np.any(gap != new_gap)


def test_boundary_column_retains_the_recorded_one_sided_native_origin(tmp_path):
    problem, x, _, _ = setup(tmp_path)
    x[0] = problem.upper[0]
    decoded, guides, samples = problem.worlds(x), descriptors(), {}
    model = linearize_material_guides(problem, x, decoded, guides, stencil_sink=lambda c, s, v: samples.update({(c, s): v}))
    assert model.identity['actual_difference_offsets'][0] == [-.001]
    observer = MaterialWitnessGuides(problem, guides)
    origin, gaps = observer.observe(problem.worlds(x, quantized=False))
    value = x.copy(); value[0] -= .001
    _, other = observer.observe(problem.worlds(value, quantized=False))
    np.testing.assert_array_equal(model.continuous_origin_points, origin)
    np.testing.assert_array_equal(model.guide_jacobian.getcol(0).toarray().ravel(), (other-gaps)/-.001/observer.scales)
    assert (0, 1) not in samples and len(samples) == 2*len(x)-1
    assert all(np.all(v['controls'] >= problem.lower) and np.all(v['controls'] <= problem.upper) for v in samples.values())


@pytest.mark.parametrize('fault', ['empty', 'tuple', 'oversized', 'duplicate', 'extra', 'missing', 'actor', 'same-actor',
    'vertex-bool', 'vertex-range', 'face-bool', 'face-range', 'bary-type', 'bary-bool', 'bary-nonfinite', 'bary-negative',
    'bary-sum', 'time-bool', 'time-off-clock', 'axis-bool', 'axis-nonunit', 'axis-nonfinite', 'clearance-bool',
    'scale-nonfinite', 'sink', 'point-budget', 'point-budget-bool', 'native-budget', 'step', 'duplicate-policy-type'])
def test_invalid_complete_descriptor_or_budget_rejects_before_world_queries(tmp_path, fault):
    problem, x, decoded, _ = setup(tmp_path)
    guides = descriptors(); g = guides[-1]; kw = {}
    if fault == 'empty': guides = []
    elif fault == 'tuple': guides = tuple(guides)
    elif fault == 'oversized': guides = [g]*4097
    elif fault == 'duplicate': guides.append(copy.deepcopy(guides[0]))
    elif fault == 'extra': g['extra'] = True
    elif fault == 'missing': g.pop('scale_m')
    elif fault == 'actor': g['actor_b'] = 'missing'
    elif fault == 'same-actor': g['actor_b'] = g['actor_a']
    elif fault == 'vertex-bool': g['vertex_a'] = True
    elif fault == 'vertex-range': g['vertex_a'] = 10000
    elif fault == 'face-bool': g['face_b'] = True
    elif fault == 'face-range': g['face_b'] = 10000
    elif fault == 'bary-type': g['barycentric_b'] = (.2, .3, .5)
    elif fault == 'bary-bool': g['barycentric_b'] = [True, 0., 0.]
    elif fault == 'bary-nonfinite': g['barycentric_b'] = [np.nan, 0., 1.]
    elif fault == 'bary-negative': g['barycentric_b'] = [-1e-15, .5, .5+1e-15]
    elif fault == 'bary-sum': g['barycentric_b'] = [.2, .3, .6]
    elif fault == 'time-bool': g['time_s'] = True
    elif fault == 'time-off-clock': g['time_s'] = .1234567
    elif fault == 'axis-bool': g['axis_world'] = [True, 0., 0.]
    elif fault == 'axis-nonunit': g['axis_world'] = [2., 0., 0.]
    elif fault == 'axis-nonfinite': g['axis_world'] = [np.inf, 0., 0.]
    elif fault == 'clearance-bool': g['clearance_m'] = True
    elif fault == 'scale-nonfinite': g['scale_m'] = np.nan
    elif fault == 'sink': kw['stencil_sink'] = True
    elif fault == 'point-budget': kw['maximum_point_elements'] = 1
    elif fault == 'point-budget-bool': kw['maximum_point_elements'] = True
    elif fault == 'native-budget': kw['maximum_elements'] = 0
    elif fault == 'step': kw['step'] = True
    elif fault == 'duplicate-policy-type': kw['allow_duplicate_descriptors'] = 1
    def unexpected(*a, **kw): raise AssertionError('must validate the complete material population first')
    problem.worlds = unexpected
    with pytest.raises(ValueError): linearize_material_guides(problem, x, decoded, guides, **kw)


def test_repeated_rows_require_explicit_policy_and_retain_all_objective_contributions(tmp_path):
    problem, x, decoded, _ = setup(tmp_path)
    guide = descriptors()[0]
    model = linearize_material_guides(problem, x, decoded, [guide, copy.deepcopy(guide)], allow_duplicate_descriptors=True)
    assert model.identity['duplicate_policy'] == 'explicit repeated objective rows'
    assert model.guide_jacobian.shape == (2, len(x)) and model.identity['guide_scalar_rows'] == 2
    np.testing.assert_array_equal(model.guide_jacobian.getrow(0).toarray(), model.guide_jacobian.getrow(1).toarray())
    np.testing.assert_array_equal(model.guide_residual[0], model.guide_residual[1])
    np.testing.assert_array_equal(model.points[:12], model.points[12:])
    assert model.identity['column_proxy_evaluations'] == 2*len(x)


def test_observation_mutation_and_failure_leave_the_original_problem_intact(tmp_path):
    problem, x, decoded, _ = setup(tmp_path)
    before = problem.worlds
    def mutate(c, s, v):
        for a in v.values(): a.fill(np.nan)
    model = linearize_material_guides(problem, x, decoded, descriptors(), stencil_sink=mutate)
    assert np.isfinite(model.native_jacobian.data).all() and np.isfinite(model.guide_jacobian.data).all()
    assert problem.worlds == before
    def fail(*args): raise RuntimeError('material observer failure')
    with pytest.raises(RuntimeError, match='observer failure'):
        linearize_material_guides(problem, x, decoded, descriptors(), stencil_sink=fail)
    assert problem.worlds == before
