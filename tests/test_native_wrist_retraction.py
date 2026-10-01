import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_wrist_retraction import NativeWristRetraction, key_influence, repair
from gltf_tools import append_accessor, read_glb
from rig_clip_import import AnimationSampler


def fixture():
    doc = dict(asset=dict(version='2.0'), buffers=[{}], bufferViews=[], accessors=[],
        nodes=[dict(name='Root', children=[1]), dict(name='Upper', children=[2]),
            dict(name='Elbow', translation=[.3, 0, 0], children=[3]),
            dict(name='Wrist', translation=[0, .3, 0], children=[4]),
            dict(name='Finger', translation=[.02, 0, 0])],
        skins=[dict(joints=list(range(5)))], animations=[dict(channels=[], samplers=[])])
    binary = bytearray(); clock = np.array([0., .4, .8, 1.2, 1.6, 2., 2.4, 2.8, 3.], np.float32)
    time = append_accessor(doc, binary, clock, 'SCALAR')
    values = append_accessor(doc, binary, np.tile([0., 0, 0, 1], (len(clock), 1)).astype(np.float32), 'VEC4')
    doc['animations'][0]['samplers'] = [dict(input=time, output=values, interpolation='LINEAR')]
    doc['animations'][0]['channels'] = [dict(sampler=0, target=dict(node=n, path='rotation')) for n in [1, 2, 3, 4]]
    return doc, binary


def test_native_retraction_preserves_contact_keys_and_exports_actual_reach(tmp_path):
    doc, binary = fixture(); times = np.unique(np.r_[np.linspace(0, 3, 61), 1.4])
    model = NativeWristRetraction(doc, binary, ['Upper', 'Elbow', 'Wrist'], times,
        [0., 3.], [], 1.4, (doc, binary), [0, 0, -1])
    zero = np.zeros(len(model.ids)); before = model.quaternions(zero)
    for e in model.model.entries: np.testing.assert_array_equal(before[e['node']], e['source'])
    amounts = np.full(len(model.ids), .005); q = model.quaternions(amounts)
    for e in model.model.entries:
        np.testing.assert_array_equal(q[e['node']][[3, 4]], e['source'][[3, 4]])
    path = tmp_path/'changed.glb'; model.export(amounts, path)
    out, payload = read_glb(path); decoder = AnimationSampler(out, payload, 0)
    old = AnimationSampler(doc, binary, 0)
    np.testing.assert_array_equal(decoder.sample(1.4), old.sample(1.4))
    for k in model.ids:
        actual, original = decoder.sample(float(model.clock[k])), old.sample(float(model.clock[k]))
        np.testing.assert_allclose(actual[3, :3, 3], original[3, :3, 3]+[0, 0, -.005], atol=1e-7)
        np.testing.assert_allclose(actual[3, :3, :3], original[3, :3, :3], atol=1e-7)
    np.testing.assert_allclose(model.world(amounts), np.array([decoder.sample(t) for t in times]), rtol=0, atol=1e-12)
    np.testing.assert_array_equal(decoder.channels[-1][3], old.channels[-1][3])


def test_influence_respects_frozen_contact_bracket():
    weights = key_influence(np.array([0., 1, 2, 3, 4], np.float32), [1, 4], [0., .5, 1, 2.5, 3.5, 4])
    np.testing.assert_array_equal(weights, [[0, 0], [.5, 0], [1, 0], [0, 0], [0, .5], [0, 1]])


def test_repair_reports_frozen_plane_failure_separately():
    influence = np.array([[1., 0], [.5, .5], [0., 0]])
    values, report = repair(lambda x: np.array([.001, .003, .0001])-influence@x, influence)
    assert report['active_plane_pass'] and not report['all_planes_pass']
    assert report['inactive_samples'] == 1 and not report['quality_approved']
    assert values.max() < .004


def test_repair_refreshes_nonlinear_response_and_keeps_caps():
    values, report = repair(lambda x: np.array([.004-2*x[0]+30*x[0]**2]), [[1.]])
    assert report['active_plane_pass'] and values[0] <= .02
    values, report = repair(lambda x: np.array([.1-x[0]]), [[1.]])
    assert not report['active_plane_pass'] and values[0] == .02 and report['error']


def test_invalid_or_unreachable_proposals_are_not_accepted():
    def evaluate(x):
        if x[0] > 0: raise ValueError('Original budget exceeded')
        return [.01]
    values, report = repair(evaluate, [[1.]])
    assert values[0] == 0 and not report['active_plane_pass'] and report['error']
    with pytest.raises(ValueError): repair(lambda x: [float('nan')], [[1.]])
    with pytest.raises(ValueError): repair(lambda x: [0], [[1.2]])


def test_clear_source_needs_no_correction():
    values, report = repair(lambda x: [-.001], [[1.]])
    assert values[0] == 0 and report['iterations'] == [] and report['all_planes_pass']
