"""Native interpolation, exact fixed keys, complete constraints and budgets."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_key_pose_map import KeyPoseMap
from native_partitioned_affine_pose import PartitionedAffineKeyPose
from native_affine_region_pose import RegionPoseRows
from native_support_clock import NativeSupportSampler
from native_support_skin import NativeSupportSkin
from native_key_contact_initializer import encode
from gltf_tools import append_accessor, write_glb
from rig_asset import RigAsset
from test_native_partitioned_affine_pose import large_actor


def inputs(tmp_path, mode='subkey'):
    actor, nodes = large_actor(tmp_path)
    doc = copy.deepcopy(actor['rig'].document); binary = bytearray(actor['rig'].binary)
    animation = doc['animations'][actor['animation_index']]
    for j, node in enumerate(nodes):
        original = next(c for c in actor['sampler'].channels if c[:2] == (node, 'rotation'))
        clock = original[2]
        angles = np.column_stack([np.sin(clock+j*.13)*3, np.cos(clock*.7+j*.2)*4, clock*.8])
        q = (Rotation.from_quat(original[3])*Rotation.from_euler('xyz', angles, degrees=True)).as_quat()
        q[::2] *= -1  # Representational hemisphere changes must preserve actual interpolation.
        channel = next(c for c in animation['channels'] if c['target'] == dict(node=node, path='rotation'))
        sampler = copy.deepcopy(animation['samplers'][channel['sampler']])
        sampler['output'] = append_accessor(doc, binary, q, 'VEC4')
        channel['sampler'] = len(animation['samplers']); animation['samplers'].append(sampler)
    path = tmp_path/'moving-source.glb'; write_glb(path, doc, binary); rig = RigAsset.load(path)
    actor = dict(rig=rig, sampler=NativeSupportSampler(rig.document, rig.binary, actor['animation_index']),
                 animation_index=actor['animation_index'], skin=NativeSupportSkin(rig),
                 placement=(np.array([5., -2., 3.]), Rotation.from_euler('xyz', [12., 31., -7.], degrees=True).as_matrix()))
    clock = next(c[2] for c in actor['sampler'].channels if c[:2] == (nodes[0], 'rotation'))
    stamp = dict(start=float(clock[0]), native=float(clock[5]),
                 subkey=float(.25*clock[5]+.75*clock[6]), end=float(clock[-1]))[mode]
    model = PartitionedAffineKeyPose(actor, stamp, nodes, [20.]*len(nodes))
    seed = np.linspace(-.08, .08, len(clock)*len(nodes)*3).reshape(len(clock), len(nodes), 3)
    pairs = [(6, nodes[-1]), (5, nodes[0]), (1, nodes[2])]
    return model, stamp, seed, pairs


def problem(model, stamp, full, *, active=None):
    return RegionPoseRows(model, stamp, full, model.nodes if active is None else active,
                          np.linspace(.06, .15, len(model.rig.joints)),
                          [dict(vertices=[2, 0, 1], normal_world=[0., 1., 0.],
                                offset_m=.4, sign=1, minimum_gap_m=.001)])


@pytest.mark.parametrize('mode', ['start', 'native', 'subkey', 'end'])
def test_quantized_map_matches_actual_export_with_moving_source_and_hemispheres(tmp_path, mode):
    model, stamp, seed, pairs = inputs(tmp_path, mode)
    mapper = KeyPoseMap(model, stamp, seed, pairs)
    value = mapper.initial+np.linspace(-.01, .015, mapper.size)
    values = seed.copy()
    for i, (key, node) in enumerate(pairs): values[key, model.nodes.index(node)] = value[3*i:3*i+3]
    channels = [next(c for c in model.actor['sampler'].channels if c[:2] == (node, 'rotation')) for node in model.nodes]
    path = tmp_path/'candidate.glb'
    index = encode(model.rig, model.actor['animation_index'], model.nodes, channels, values, [20.]*len(model.nodes), path)
    decoded = RigAsset.load(path); reader = NativeSupportSampler(decoded.document, decoded.binary, index)
    full = mapper.controls(value, quantized=True); world, vertices, *_ = model.evaluate(full)
    np.testing.assert_allclose(world, reader.sample(stamp), atol=3e-13, rtol=0)
    np.testing.assert_allclose(vertices, decoded.vertices(reader.sample(stamp)), atol=3e-13, rtol=0)
    for old in channels:
        new = next(c for c in reader.channels if c[:2] == old[:2])
        np.testing.assert_array_equal(old[2], new[2])
    assert mapper.report['native_keys'] == len(channels[0][2])
    assert not mapper.report['quality_approved'] and not mapper.report['release_approved']


@pytest.mark.parametrize('homogeneous', [False, True])
def test_complete_region_chain_and_outside_key_ball_rows_match_differences(tmp_path, homogeneous):
    model, stamp, seed, pairs = inputs(tmp_path)
    if homogeneous: model.skin.points[:, :, 3] *= np.linspace(.95, 1.05, model.skin.points.shape[1])
    mapper = KeyPoseMap(model, stamp, seed, pairs)
    value = mapper.initial+np.linspace(-.01, .02, mapper.size)
    full, mapping = mapper.evaluate(value); rows = problem(model, stamp, full)
    result, jac, world, vertices, effective = mapper.region_rows(rows, value)
    reference = rows.evaluate(full)
    np.testing.assert_array_equal(result[:-len(pairs)], reference[0])
    np.testing.assert_array_equal(world, reference[2]); np.testing.assert_array_equal(vertices, reference[3])
    np.testing.assert_array_equal(effective, full)
    np.testing.assert_array_equal(jac[:-len(pairs)], reference[1]@mapping)
    assert np.count_nonzero(mapping[:, 6:9]) == 0  # Key 1 cannot affect a pose between 5 and 6.
    for column in range(mapper.size):
        delta = np.eye(mapper.size)[column]*2e-6
        difference = (mapper.region_rows(rows, value+delta)[0]-mapper.region_rows(rows, value-delta)[0])/4e-6
        np.testing.assert_allclose(jac[:, column], difference, atol=3e-6, rtol=4e-6)
    value[6:9] = [1.01, 0, 0]
    failed = mapper.region_rows(rows, value)[0]
    assert failed[-1] < 0 and np.count_nonzero(mapper.evaluate(value)[1][:, 6:9]) == 0
    assert len(result) == rows.report['rows']+len(pairs)


def test_input_copies_and_relinearization_never_recenter(tmp_path):
    model, stamp, seed, pairs = inputs(tmp_path); original_seed = seed.copy(); original_pairs = pairs.copy()
    mapper = KeyPoseMap(model, stamp, seed, pairs); value = mapper.initial.copy()
    before = mapper.evaluate(value); seed[:] = 0; pairs.reverse()
    mapper.evaluate(value+.1)
    for a, b in zip(before, mapper.evaluate(value)): np.testing.assert_array_equal(a, b)
    fresh = KeyPoseMap(model, stamp, original_seed, original_pairs)
    for a, b in zip(mapper.evaluate(value-.02), fresh.evaluate(value-.02)): np.testing.assert_array_equal(a, b)
    before[0][:] = 0
    assert np.any(mapper.evaluate(value)[0])
    np.testing.assert_array_equal(mapper.source, model.source)


@pytest.mark.parametrize('fault', [
    'model', 'time-bool', 'time-negative', 'time-nan', 'different-source',
    'seed-shape', 'seed-bool', 'seed-nan', 'seed-over-ball',
    'pairs-empty', 'pairs-duplicate', 'pair-key-bool', 'pair-node-bool',
    'pair-negative', 'pair-large', 'pair-unknown-node', 'pair-shape',
    'step-zero', 'step-nan', 'step-large', 'keys-zero', 'keys-small',
    'controls-zero', 'controls-small', 'jac-zero', 'jac-small',
])
def test_invalid_constructor_and_complete_budget_rejection(tmp_path, monkeypatch, fault):
    model, stamp, seed, pairs = inputs(tmp_path); kwargs = {}
    if fault == 'model': model = object()
    elif fault == 'time-bool': stamp = True
    elif fault == 'time-negative': stamp = -1.
    elif fault == 'time-nan': stamp = float('nan')
    elif fault == 'different-source': model.source[0, 0, 3] += .01
    elif fault == 'seed-shape': seed = seed[:-1]
    elif fault == 'seed-bool': seed = seed.astype(bool)
    elif fault == 'seed-nan': seed[0, 0, 0] = np.nan
    elif fault == 'seed-over-ball': seed[0, 0] = [1.01, 0, 0]
    elif fault == 'pairs-empty': pairs = []
    elif fault == 'pairs-duplicate': pairs.append(pairs[0])
    elif fault == 'pair-key-bool': pairs[0] = (True, pairs[0][1])
    elif fault == 'pair-node-bool': pairs[0] = (pairs[0][0], True)
    elif fault == 'pair-negative': pairs[0] = (-1, pairs[0][1])
    elif fault == 'pair-large': pairs[0] = (len(seed), pairs[0][1])
    elif fault == 'pair-unknown-node': pairs[0] = (6, 99999)
    elif fault == 'pair-shape': pairs[0] = (6,)
    elif fault == 'step-zero': kwargs['difference_step'] = 0.
    elif fault == 'step-nan': kwargs['difference_step'] = np.nan
    elif fault == 'step-large': kwargs['difference_step'] = .001
    elif fault == 'keys-zero': kwargs['maximum_keys'] = 0
    elif fault == 'keys-small': kwargs['maximum_keys'] = len(seed)-1
    elif fault == 'controls-zero': kwargs['maximum_controls'] = 0
    elif fault == 'controls-small': kwargs['maximum_controls'] = 2
    elif fault == 'jac-zero': kwargs['maximum_jacobian_bytes'] = 0
    elif fault == 'jac-small': kwargs['maximum_jacobian_bytes'] = 1
    if isinstance(model, PartitionedAffineKeyPose):
        monkeypatch.setattr(model, 'evaluate', lambda _: pytest.fail('Rejected request evaluated a pose'))
    with pytest.raises(ValueError): KeyPoseMap(model, stamp, seed, pairs, **kwargs)


@pytest.mark.parametrize('fault', ['pose', 'local', 'caps', 'nodes', 'placement', 'source-native-value', 'source-sign'])
def test_changed_bound_inputs_reject_without_recentering(tmp_path, fault):
    model, stamp, seed, pairs = inputs(tmp_path); mapper = KeyPoseMap(model, stamp, seed, pairs)
    if fault == 'pose': model.source[0, 0, 3] += .01
    elif fault == 'local': model.local[0, 0, 3] += .01
    elif fault == 'caps': model.caps[0] *= .9
    elif fault == 'nodes': model.nodes.reverse()
    elif fault == 'placement': model.actor['placement'][0][0] += .01
    else:
        c = next(c for c in model.actor['sampler'].channels if c[:2] == (model.nodes[0], 'rotation'))
        if fault == 'source-native-value': c[3][0, 0] += .01
        else: c[3][0] *= -1
    with pytest.raises(ValueError): mapper.evaluate(mapper.initial)


def test_composed_budget_and_wrong_pose_reject_before_pose_evaluation(tmp_path, monkeypatch):
    model, stamp, seed, pairs = inputs(tmp_path)
    mapper = KeyPoseMap(model, stamp, seed, pairs, maximum_jacobian_bytes=model.size*len(pairs)*3*8)
    full = mapper.controls(mapper.initial)
    rows = RegionPoseRows(model, stamp, full, model.nodes, np.full(len(model.rig.joints), .1),
                          [dict(vertices=[0,1,2],normal_world=[0.,1.,0.],offset_m=0.,sign=1,minimum_gap_m=0.) for _ in range(16)])
    with pytest.raises(ValueError): mapper.region_rows(problem(model, stamp, rows.base, active=[model.nodes[0]]), mapper.initial)
    other = PartitionedAffineKeyPose(model.actor, stamp, model.nodes, [20.]*len(model.nodes))
    with pytest.raises(ValueError): mapper.region_rows(problem(other, stamp, rows.base), mapper.initial)
    monkeypatch.setattr(model, 'evaluate', lambda _: pytest.fail('Over-budget composed request evaluated a pose'))
    with pytest.raises(ValueError): mapper.region_rows(rows, mapper.initial)


@pytest.mark.parametrize('value', [None, [True]*9, [float('nan')]*9, [3.]*9, [0.]*8])
def test_invalid_proposals_reject(tmp_path, value):
    model, stamp, seed, pairs = inputs(tmp_path); mapper = KeyPoseMap(model, stamp, seed, pairs)
    with pytest.raises(ValueError): mapper.controls(value)
