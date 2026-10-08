"""Hierarchy, synchronization and incomplete-population rejection fixtures."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from gltf_tools import append_accessor
from rig_clip_import import AnimationSampler
from scene_import_clock import shared_clock, verify_scene


def exact_time(time):
    return np.array([time], dtype='<f8').tobytes().hex()


def fixture():
    document = dict(nodes=[dict(name='root', children=[1]), dict(name='hand', translation=[1, 0, 0])],
                    buffers=[], bufferViews=[], accessors=[])
    binary = bytearray()
    times = append_accessor(document, binary, [0., 1.], 'SCALAR')
    rotations = Rotation.from_euler('z', [0., 90.], degrees=True).as_quat()
    values = append_accessor(document, binary, rotations, 'VEC4')
    document['animations'] = [dict(name='turn', samplers=[dict(input=times, output=values)],
                                  channels=[dict(sampler=0, target=dict(node=0, path='rotation'))])]
    sampler = AnimationSampler(document, binary, 0)
    rig = SimpleNamespace(document=document, joints=[0, 1])
    placement = dict(translation_m=[3., 0, -2.], rotation_xyzw=[0., 0, 0., 1.])
    actors = {'A': (rig, sampler, placement), 'B': (rig, sampler, {**placement, 'translation_m': [-3., 1., 2.]})}
    clock = shared_clock(31, 60, [sampler])
    request = dict(id='pair', source_frame_count=31, sample_times_s=clock.tolist())
    observed = dict(id='pair', actors={}, frames=[], object_frames=[], clock_samples=[])
    for name in actors:
        observed['actors'][name] = dict(bone_names=['hand', 'root'], animation_index=0, loop_mode=0, duration_s=1.)
    for time in clock:
        frame = {}
        for name, (_, animation, pose) in actors.items():
            world = animation.sample(time)[[1, 0]].copy()
            world[:, :3, 3] += pose['translation_m']
            frame[name] = np.concatenate([world[:, :3, :3].transpose(0, 2, 1), world[:, :3, 3][:, None]], axis=1).tolist()
        observed['frames'].append(frame)
        observed['object_frames'].append({})
        observed['clock_samples'].append(dict(requested_time_s=float(time), actors=dict(A=float(time), B=float(time)),
            objects_time_s=None, requested_time_f64le=exact_time(time),
            actor_times_f64le=dict(A=exact_time(time), B=exact_time(time)), objects_time_f64le=None))
    return sampler, request, observed, actors


def test_all_shared_samples_and_reordered_bones_match_hierarchy():
    _, request, observed, actors = fixture()
    found = verify_scene(request, observed, actors)
    assert found['all_precision_screens_passed'] and not found['quality_approved']
    assert [a['samples'] for a in found['actors']] == [61, 61]
    assert all(a['maximum_position_error_m'] == 0 for a in found['actors'])


def test_global_endpoint_position_lerp_cannot_replace_local_rotation_fk():
    _, request, observed, actors = fixture()
    start = np.array(observed['frames'][0]['A'][0][3])
    end = np.array(observed['frames'][-1]['A'][0][3])
    observed['frames'][30]['A'][0][3] = ((start + end) / 2).tolist()
    found = verify_scene(request, observed, actors)
    assert not found['all_precision_screens_passed']
    assert found['actors'][0]['maximum_position_error_m'] == pytest.approx(np.sqrt(.5) - .5)


def test_uniform_clock_keeps_nominal_keys_and_distinct_float32_source_keys():
    sampler, _, _, _ = fixture()
    sampler = copy.deepcopy(sampler)
    keys = np.arange(31, dtype=np.float32) / 30
    sampler.channels[0] = (*sampler.channels[0][:2], keys, *sampler.channels[0][3:])
    found = shared_clock(31, 240, [sampler])
    assert np.isin(np.arange(31) / 30, found).all()
    assert np.isin(keys.astype(float), found).all()
    assert len(found) > 241 and found[0] == 0 and found[-1] == 1


@pytest.mark.parametrize('rate', [True, 0, 29, 31, 241, 60., '60'])
def test_invalid_rate_rejected(rate):
    sampler, _, _, _ = fixture()
    with pytest.raises(ValueError): shared_clock(31, rate, [sampler])


@pytest.mark.parametrize('frames', [True, 1, 1801, 31., '31'])
def test_invalid_frame_count_rejected(frames):
    sampler, _, _, _ = fixture()
    with pytest.raises(ValueError): shared_clock(frames, 120, [sampler])


def test_missing_or_different_duration_rejected():
    sampler, _, _, _ = fixture()
    with pytest.raises(ValueError): shared_clock(31, 120, [])
    with pytest.raises(ValueError): shared_clock(32, 120, [sampler])


@pytest.mark.parametrize('fault', ['missing_scene', 'missing_actor', 'missing_frame', 'missing_object_frame',
    'missing_clock', 'changed_actor_frame', 'changed_object_frame', 'changed_requested_time',
    'changed_actor_time', 'extra_actor_clock', 'unexpected_object_clock', 'missing_bone',
    'duplicate_bone', 'looping', 'duration', 'animation_index', 'nan_pose', 'nonunit_placement'])
def test_incomplete_changed_or_nonfinite_observations_rejected(fault):
    _, request, actual, actors = fixture()
    if fault == 'missing_scene': actual['id'] = 'other'
    if fault == 'missing_actor': del actual['actors']['B']
    if fault == 'missing_frame': actual['frames'].pop()
    if fault == 'missing_object_frame': actual['object_frames'].pop()
    if fault == 'missing_clock': actual['clock_samples'].pop()
    if fault == 'changed_actor_frame': del actual['frames'][10]['A']
    if fault == 'changed_object_frame': actual['object_frames'][10]['box'] = []
    if fault == 'changed_requested_time': actual['clock_samples'][10]['requested_time_f64le'] = exact_time(request['sample_times_s'][10] + 1e-8)
    if fault == 'changed_actor_time': actual['clock_samples'][10]['actor_times_f64le']['B'] = exact_time(request['sample_times_s'][10] + 1e-8)
    if fault == 'extra_actor_clock': actual['clock_samples'][10]['actors']['C'] = 0.
    if fault == 'unexpected_object_clock': actual['clock_samples'][10]['objects_time_s'] = 0.
    if fault == 'missing_bone': actual['actors']['A']['bone_names'].pop()
    if fault == 'duplicate_bone': actual['actors']['A']['bone_names'] = ['hand', 'hand']
    if fault == 'looping': actual['actors']['A']['loop_mode'] = 1
    if fault == 'duration': actual['actors']['A']['duration_s'] += .01
    if fault == 'animation_index': actual['actors']['A']['animation_index'] = 1
    if fault == 'nan_pose': actual['frames'][10]['A'][0][3][0] = float('nan')
    if fault == 'nonunit_placement': actors['A'][2]['rotation_xyzw'] = [0., 0., 0., 2.]
    with pytest.raises(ValueError): verify_scene(request, actual, actors)


def test_object_clock_and_pose_are_independent_conditions():
    sampler, request, actual, actors = fixture()
    objects = {'box': (sampler, 1)}
    for time, frame, clock in zip(request['sample_times_s'], actual['object_frames'], actual['clock_samples']):
        matrix = sampler.sample(time)[1]
        frame['box'] = np.concatenate([matrix[:3, :3].T, matrix[:3, 3][None]]).tolist()
        clock['objects_time_s'] = time
        clock['objects_time_f64le'] = exact_time(time)
    assert verify_scene(request, actual, actors, objects)['all_precision_screens_passed']
    actual['object_frames'][10]['box'][3][0] += .01
    assert not verify_scene(request, actual, actors, objects)['all_precision_screens_passed']
    actual['clock_samples'][10]['objects_time_f64le'] = exact_time(request['sample_times_s'][10] + .01)
    with pytest.raises(ValueError): verify_scene(request, actual, actors, objects)


def test_rounded_decimal_clock_does_not_replace_binary_engine_clock():
    _, request, actual, actors = fixture()
    for c in actual['clock_samples']:
        c['requested_time_s'] = float(format(c['requested_time_s'], '.15g'))
        c['actors'] = {k: float(format(v, '.15g')) for k, v in c['actors'].items()}
    assert verify_scene(request, actual, actors)['all_precision_screens_passed']


@pytest.mark.parametrize('value', ['', '0', 'gg' * 8, '00' * 9, '00 ' * 8,
                                 exact_time(float('nan')), exact_time(-.01)])
def test_invalid_binary_clock_rejected(value):
    from scene_import_clock import exact_echo
    with pytest.raises(ValueError): exact_echo(value)


def test_only_declared_nominal_terminal_seek_can_snap_to_exact_source_end():
    _, request, actual, actors = fixture()
    for name in actors:
        actors[name][1].duration = 1.00000002
        actual['actors'][name]['duration_s'] = 1.00000002
        actual['clock_samples'][-1]['actor_times_f64le'][name] = exact_time(1.00000002)
    found = verify_scene(request, actual, actors)
    assert found['all_precision_screens_passed'] and len(found['terminal_seek_snaps']) == 2
    actual['clock_samples'][-2]['actor_times_f64le']['A'] = exact_time(1.00000002)
    with pytest.raises(ValueError): verify_scene(request, actual, actors)


def test_terminal_time_drift_cannot_snap_to_arbitrary_nearby_time():
    _, request, actual, actors = fixture()
    actual['clock_samples'][-1]['actor_times_f64le']['A'] = exact_time(1.00000002)
    with pytest.raises(ValueError): verify_scene(request, actual, actors)


def test_both_existing_asset_manifest_forms_require_one_exact_binding():
    from run_scene_playback import bound_asset_digest
    assert bound_asset_digest({'assets/a.glb': {'sha256': 'abc'}}, 'assets/a.glb') == 'abc'
    assert bound_asset_digest({'motion-hash': {'file': 'assets/a.glb', 'sha256': 'abc'}}, 'assets/a.glb') == 'abc'
    with pytest.raises(ValueError): bound_asset_digest({}, 'assets/a.glb')
    with pytest.raises(ValueError):
        bound_asset_digest({'a': {'file': 'assets/a.glb', 'sha256': 'abc'},
                            'b': {'file': 'assets/a.glb', 'sha256': 'abc'}}, 'assets/a.glb')
