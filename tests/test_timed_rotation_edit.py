import copy
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from timed_rotation_edit import TimedRotationEdit, editable_keys, sampled_rotations
from gltf_tools import append_accessor, read_glb
from paired_temporal_neighbor import rotation_channels
from rig_clip_import import AnimationSampler


def fixture():
    # Arm and its unselected sibling intentionally share a sampler.
    doc = dict(asset=dict(version='2.0'), buffers=[{}], bufferViews=[], accessors=[],
        nodes=[dict(name='Root', children=[1, 3]), dict(name='Arm', translation=[0, 1, 0], children=[2]),
               dict(name='Finger', translation=[0, 1, 0]), dict(name='Twin', translation=[1, 0, 0])],
        skins=[dict(joints=[0, 1, 2, 3])], animations=[dict(channels=[], samplers=[])])
    binary = bytearray(); clock = np.array([0., .1, .25, .5, .7, 1., 1.3, 1.5], np.float32)
    time = append_accessor(doc, binary, clock, 'SCALAR')
    values = append_accessor(doc, binary, Rotation.from_euler('z', clock*.1).as_quat(), 'VEC4')
    doc['animations'][0]['samplers'] = [dict(input=time, output=values, interpolation='LINEAR')]
    doc['animations'][0]['channels'] = [dict(sampler=0, target=dict(node=n, path='rotation')) for n in [1, 3]]
    return doc, binary


def model(document, binary, **kwargs):
    return TimedRotationEdit(document, binary, ['Arm'], np.unique(np.r_[np.linspace(0, 1.5, 181), .7]), [.1, 1.3], [[.7, .7]], **kwargs)


def test_support_guards_protect_between_key_contacts_and_entire_outside_interval():
    np.testing.assert_array_equal(editable_keys([0, 1, 2, 3, 4, 5, 6], [1.25, 5.5], [[3.5, 3.5]]), [])
    np.testing.assert_array_equal(editable_keys([0, 1, 2, 3, 4, 5, 6], [0, 6], [[3, 3]]), [1, 2, 4, 5])
    np.testing.assert_array_equal(editable_keys([0, 1, 2, 3, 4, 5, 6], [0, 6], [[2.5, 3.5]]), [1, 5])


def test_irregular_curve_edits_keep_protected_time_and_other_shared_sampler(tmp_path):
    doc, binary = fixture(); edit = model(doc, binary); controls = np.tile([.015, -.01, .005], edit.size//3)
    before = edit.source_world; after = edit.world(controls)
    frozen = (edit.times <= .1) | (edit.times >= 1.3) | (edit.times == .7)
    np.testing.assert_allclose(after[frozen], before[frozen], atol=1e-12, rtol=0)
    assert np.abs(after-before).max() > .001
    path = tmp_path/'changed.glb'; edit.export(controls, path)
    exported, payload = read_glb(path); channels = rotation_channels(exported, payload); original = rotation_channels(doc, binary)
    np.testing.assert_array_equal(channels[3][2], original[3][2])
    np.testing.assert_array_equal(channels[1][1], original[1][1])
    sampler = AnimationSampler(exported, payload, 0)
    observed = np.array([sampler.sample(t) for t in edit.times])
    np.testing.assert_allclose(after, observed, atol=2e-7, rtol=0)
    np.testing.assert_allclose(observed[frozen], before[frozen], atol=1e-12, rtol=0)


def test_edit_mapping_and_world_derivatives_are_consistent():
    doc, binary = fixture(); edit = model(doc, binary)
    control = np.arange(edit.size)*.0004; values, jac = edit.edit_rows(control)
    zero, _ = edit.edit_rows(np.zeros(edit.size))
    np.testing.assert_allclose(values, zero+np.einsum('nid,d->ni', jac, control), atol=1e-15)
    world, derivative = edit.world_pair(control)
    direction = np.linspace(-1, 1, edit.size)*2e-6
    np.testing.assert_allclose(edit.world(control+direction), world+np.einsum('tnijd,d->tnij', derivative, direction), atol=1e-10, rtol=0)


def test_resuming_does_not_reset_original_rotation_budget(tmp_path):
    doc, binary = fixture(); edit = model(doc, binary)
    step = np.tile([0., 0., np.deg2rad(4.)], edit.size//3)
    path = tmp_path/'first.glb'; edit.export(step, path)
    changed, payload = read_glb(path); resumed = model(changed, payload, reference=(doc, binary))
    with pytest.raises(ValueError, match='Cumulative export'):
        resumed.export(step, tmp_path/'too-far.glb')
    # A small continued edit remains measured from the original rotations.
    resumed.export(step*.05, tmp_path/'second.glb')


@pytest.mark.parametrize('change', ['duplicate_name', 'ambiguous_name', 'matrix_joint', 'step_rotation', 'bad_window', 'no_keys', 'bad_budget'])
def test_unsupported_requests_fail_explicitly(change):
    doc, binary = fixture(); names = ['Arm']; window = [.1, 1.3]; budget = 5.
    if change == 'duplicate_name': names = ['Arm', 'Arm']
    if change == 'ambiguous_name': doc['nodes'][3]['name'] = 'Arm'
    if change == 'matrix_joint': doc['nodes'][1]['matrix'] = np.eye(4).T.ravel().tolist()
    if change == 'step_rotation': doc['animations'][0]['samplers'][0]['interpolation'] = 'STEP'
    if change == 'bad_window': window = [1., .1]
    if change == 'no_keys': window = [.11, .12]
    if change == 'bad_budget': budget = float('nan')
    with pytest.raises(ValueError):
        TimedRotationEdit(doc, binary, names, [0., 1.5], window, limit_degrees=budget)


def test_zero_controls_do_not_rewrite_frozen_quaternion_values():
    doc, binary = fixture(); edit = model(doc, binary)
    np.testing.assert_array_equal(edit.quaternions(np.zeros(edit.size))[1], rotation_channels(doc, binary)[1][2])
    np.testing.assert_allclose(edit.world(np.zeros(edit.size)), edit.source_world, atol=1e-12, rtol=0)


def test_batched_rotation_sampling_matches_native_clock_and_antipodal_decoder():
    clock = np.array([0., .07, .3, .72, 1.1], np.float32)
    q = Rotation.from_rotvec(np.array([[0, 0, 0], [1e-8, 0, 0], [.2, -.3, .1], [.3, .5, -.1], [.2, .4, 0]])).as_quat()
    q[2] *= -1
    times = np.unique(np.r_[np.linspace(0, 1.2, 103), clock])
    expected = Rotation.from_quat([AnimationSampler.value('rotation', clock, q, 'LINEAR', t) for t in times]).as_matrix()
    np.testing.assert_allclose(sampled_rotations(clock, q, times), expected, atol=1e-12, rtol=0)
