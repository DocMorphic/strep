"""Complete affine constraints, active subsets and fixed original references."""
import copy
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_affine_region_pose import RegionPoseRows
from native_partitioned_affine_pose import PartitionedAffineKeyPose
from native_key_contact_initializer import encode
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from test_native_partitioned_affine_pose import large_actor


def inputs(tmp_path, *, stamp=1.):
    actor, nodes = large_actor(tmp_path)
    actor['placement'] = (np.array([5., -2., 3.]), Rotation.from_euler('xyz', [12., 31., -7.], degrees=True).as_matrix())
    model = PartitionedAffineKeyPose(actor, stamp, nodes, [20.]*len(nodes))
    base = np.linspace(-.08, .08, model.size)
    active = [nodes[-1], nodes[0]]
    caps = np.linspace(.06, .15, len(model.rig.joints))
    normal = (np.array([1., 2., 3.])/np.sqrt(14)).tolist()
    regions = [dict(vertices=[2, 0, 1], normal_world=[0., 1., 0.], offset_m=.4, sign=1, minimum_gap_m=.001),
               dict(vertices=[0, 2], normal_world=normal, offset_m=-.2, sign=-1, minimum_gap_m=.004)]
    return model, base, active, caps, regions


@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('homogeneous', [False, True])
def test_complete_affine_rows_and_nonprefix_active_derivatives(tmp_path, reverse, homogeneous):
    model, base, active, caps, regions = inputs(tmp_path)
    if reverse: active.reverse()
    if homogeneous:
        model.skin.points[:, :, 3] *= np.linspace(.95, 1.05, model.skin.points.shape[1])
    problem = RegionPoseRows(model, 1., base, active, caps, regions)
    value = base[problem.coordinates]+np.linspace(-.01, .02, problem.size)
    rows, jac, world, points, full = problem.evaluate(value)
    reference = base.copy(); reference[problem.coordinates] = value
    expected_world, local, *_ = model.evaluate(reference)
    position, rotation = model.actor['placement']; expected_points = local@rotation.T+position
    np.testing.assert_array_equal(world, expected_world)
    np.testing.assert_array_equal(points, expected_points)
    np.testing.assert_array_equal(full, reference)
    delta = world[model.rig.joints, :3, 3]-model.source[model.rig.joints, :3, 3]
    expected = [1-np.linalg.norm(full.reshape(-1, 3), axis=1)**2,
                1-(np.linalg.norm(delta, axis=1)/caps)**2]
    for region in regions:
        signed = region['sign']*(points[region['vertices']]@np.array(region['normal_world'])-region['offset_m'])
        expected.append((signed-region['minimum_gap_m'])/.01)
    np.testing.assert_allclose(rows, np.concatenate(expected), atol=1e-12, rtol=0)
    for column in range(problem.size):
        step = np.eye(problem.size)[column]*1e-6
        difference = (problem.evaluate(value+step)[0]-problem.evaluate(value-step)[0])/2e-6
        np.testing.assert_allclose(jac[:, column], difference, atol=3e-7, rtol=3e-6)
    fixed = sorted(set(range(len(model.nodes)))-set(problem.node_indices))
    assert np.count_nonzero(jac[fixed]) == 0
    assert problem.report['region_rows'] == 5
    assert len(rows) == len(model.nodes)+len(model.rig.joints)+5
    assert problem.report['jacobian_bytes'] == jac.nbytes
    assert not problem.report['quality_approved'] and not problem.report['release_approved']


def test_input_copies_and_relinearization_never_recenter_source(tmp_path):
    model, base, active, caps, regions = inputs(tmp_path)
    saved = (base.copy(), caps.copy(), copy.deepcopy(regions))
    problem = RegionPoseRows(model, 1., base, active, caps, regions)
    value = base[problem.coordinates].copy(); original = problem.evaluate(value)
    base[:] = 0; caps[:] = 1; regions[0]['vertices'].reverse(); regions[0]['normal_world'][0] = 2; active.reverse()
    problem.evaluate(value+.04)
    for before, after in zip(original, problem.evaluate(value)): np.testing.assert_array_equal(after, before)
    fresh = RegionPoseRows(model, 1., saved[0], [model.nodes[-1], model.nodes[0]], saved[1], saved[2])
    for before, after in zip(fresh.evaluate(value-.03), problem.evaluate(value-.03)): np.testing.assert_array_equal(after, before)
    np.testing.assert_array_equal(problem.source, model.source)
    original[-1][:] = 0
    assert np.any(problem.evaluate(value)[-1])


def test_failed_rotation_ball_stays_observable_with_all_fixed_rows(tmp_path):
    model, base, active, caps, regions = inputs(tmp_path)
    problem = RegionPoseRows(model, 1., base, active, caps, regions)
    value = base[problem.coordinates].copy(); value[:3] = [1.01, 0, 0]
    rows, jac, *_ = problem.evaluate(value)
    assert rows[problem.node_indices[0]] < 0
    assert jac[problem.node_indices[0], 0] == pytest.approx(-2.02)
    assert len(rows) == problem.report['rows']


def test_native_float32_save_reload_preserves_affine_geometry_and_source(tmp_path):
    model, base, active, caps, regions = inputs(tmp_path)
    channel = next(c for c in model.actor['sampler'].channels if c[:2] == (model.nodes[0], 'rotation'))
    key = 5; stamp = float(channel[2][key])
    model = PartitionedAffineKeyPose(model.actor, stamp, model.nodes, [20.]*len(model.nodes))
    problem = RegionPoseRows(model, stamp, base, active, caps, regions)
    _, _, expected_world, expected_points, full = problem.evaluate(base[problem.coordinates]+.01)
    channels = [next(c for c in model.actor['sampler'].channels if c[:2] == (n, 'rotation')) for n in model.nodes]
    controls = np.zeros((len(channel[2]), len(model.nodes), 3)); controls[key] = full.reshape(-1, 3)
    output = tmp_path/'proposal.glb'
    index = encode(model.rig, model.actor['animation_index'], model.nodes, channels, controls, [20.]*len(model.nodes), output)
    decoded = RigAsset.load(output); reader = NativeSupportSampler(decoded.document, decoded.binary, index)
    world = reader.sample(stamp); position, rotation = model.actor['placement']
    np.testing.assert_allclose(world, expected_world, atol=2e-6, rtol=0)
    np.testing.assert_allclose(decoded.vertices(world)@rotation.T+position, expected_points, atol=2e-6, rtol=0)
    assert decoded.document['nodes'] == model.rig.document['nodes']
    assert decoded.binary[:len(model.rig.binary)] == model.rig.binary


@pytest.mark.parametrize('fault', [
    'time-negative', 'time-nan', 'time-bool', 'changed-source-reference', 'no-active', 'duplicate-active', 'unknown-active',
    'bad-base-shape', 'base-nan', 'base-outside', 'bad-caps-shape', 'cap-zero', 'cap-tiny', 'cap-large',
    'no-region', 'duplicate-vertex', 'invalid-vertex', 'bool-vertex', 'bad-normal', 'normal-nan',
    'sign-bool', 'sign-zero', 'gap-negative', 'gap-large', 'offset-infinite', 'extra-region-field',
    'row-budget', 'jacobian-budget', 'bool-budget', 'scale-zero',
])
def test_invalid_or_incomplete_conditions_reject_before_evaluation(tmp_path, monkeypatch, fault):
    model, base, active, caps, regions = inputs(tmp_path); stamp = 1.; settings = {}
    if fault == 'time-negative': stamp = -1.
    elif fault == 'time-nan': stamp = float('nan')
    elif fault == 'time-bool': stamp = True
    elif fault == 'changed-source-reference': model.source[3, 0, 3] += .01
    elif fault == 'no-active': active = []
    elif fault == 'duplicate-active': active = [active[0], active[0]]
    elif fault == 'unknown-active': active = [99999]
    elif fault == 'bad-base-shape': base = base[:-1]
    elif fault == 'base-nan': base[0] = np.nan
    elif fault == 'base-outside': base[:3] = [1.01, 0, 0]
    elif fault == 'bad-caps-shape': caps = caps[:-1]
    elif fault == 'cap-zero': caps[0] = 0
    elif fault == 'cap-tiny': caps[0] = 1e-300
    elif fault == 'cap-large': caps[0] = 1.01
    elif fault == 'no-region': regions = []
    elif fault == 'duplicate-vertex': regions[0]['vertices'] = [0, 0]
    elif fault == 'invalid-vertex': regions[0]['vertices'] = [99999]
    elif fault == 'bool-vertex': regions[0]['vertices'] = [True]
    elif fault == 'bad-normal': regions[0]['normal_world'] = [2, 0, 0]
    elif fault == 'normal-nan': regions[0]['normal_world'] = [np.nan, 0, 0]
    elif fault == 'sign-bool': regions[0]['sign'] = True
    elif fault == 'sign-zero': regions[0]['sign'] = 0
    elif fault == 'gap-negative': regions[0]['minimum_gap_m'] = -.001
    elif fault == 'gap-large': regions[0]['minimum_gap_m'] = .11
    elif fault == 'offset-infinite': regions[0]['offset_m'] = np.inf
    elif fault == 'extra-region-field': regions[0]['extra'] = 0
    elif fault == 'row-budget': settings['maximum_rows'] = 1
    elif fault == 'jacobian-budget': settings['maximum_jacobian_bytes'] = 1
    elif fault == 'bool-budget': settings['maximum_rows'] = True
    else: settings['length_scale_m'] = 0
    def forbidden(*args): raise AssertionError('Invalid condition reached numerical evaluation')
    monkeypatch.setattr(model, 'evaluate', forbidden)
    with pytest.raises(ValueError): RegionPoseRows(model, stamp, base, active, caps, regions, **settings)


@pytest.mark.parametrize('field', ['source', 'local', 'caps', 'nodes', 'placement'])
def test_changed_constructor_reference_rejects(tmp_path, field):
    model, base, active, caps, regions = inputs(tmp_path)
    problem = RegionPoseRows(model, 1., base, active, caps, regions)
    if field == 'source': model.source[0, 0, 3] += .01
    elif field == 'local': model.local[0, 0, 3] += .01
    elif field == 'caps': model.caps[0] *= .9
    elif field == 'nodes': model.nodes.reverse()
    else: model.actor['placement'][0][0] += .01
    with pytest.raises(ValueError, match='reference changed'): problem.evaluate(base[problem.coordinates])
