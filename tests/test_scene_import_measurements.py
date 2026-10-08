"""Imported-weight placement, partner targets and complete vertex diagnostics."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from test_native_scene_geometry import closed_fixture
from test_native_scene_engine import mock_actor, serialized
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from gltf_tools import append_accessor, write_glb
from scene_import_clock import shared_clock
from scene_import_measurements import measure
from native_scene_imported_skin import ImportedSceneSkin


def exact_time(time): return np.asarray([time], dtype='<f8').tobytes().hex()


def fixture(tmp_path):
    source, _, _ = closed_fixture(tmp_path)
    rig = RigAsset.load(source); document = copy.deepcopy(rig.document); binary = bytearray(rig.binary)
    attributes = document['meshes'][0]['primitives'][0]['attributes']
    attributes['WEIGHTS_0'] = append_accessor(document, binary, np.tile([.5, .5, 0., 0.], (8, 1)), 'VEC4')
    write_glb(source, document, binary)
    rig = RigAsset.load(source); sampler = AnimationSampler(rig.document, rig.binary, 0)
    a = dict(translation_m=[3., .4, -2.], rotation_xyzw=Rotation.from_euler('y', 45, degrees=True).as_quat().tolist())
    b = dict(translation_m=[-3., .8, 2.], rotation_xyzw=[0., 0., 0., 1.])
    actors = dict(A=(rig, sampler, a), B=(rig, sampler, b))
    times = shared_clock(61, 30, [sampler])
    request = dict(id='paired', source_frame_count=61, sample_times_s=times.tolist())
    observed = dict(id='paired', actors={}, frames=[{} for _ in times], object_frames=[{} for _ in times], clock_samples=[])
    for name, (_, _, placement) in actors.items():
        raw = mock_actor(rig, sampler, times)
        observed['actors'][name] = {k: raw[k] for k in ('bone_names', 'meshes', 'animation_index', 'loop_mode', 'duration_s')}
        transform = np.eye(4); transform[:3, :3] = Rotation.from_quat(placement['rotation_xyzw']).as_matrix(); transform[:3, 3] = placement['translation_m']
        for i, time in enumerate(times):
            names = [rig.document['nodes'][n]['name'] for n in rig.joints]
            order = [rig.joints[names.index(n)] for n in raw['bone_names']]
            observed['frames'][i][name] = [serialized(m) for m in transform @ sampler.sample(time)[order]]
    for time in times:
        observed['clock_samples'].append(dict(requested_time_s=float(time), requested_time_f64le=exact_time(time),
            actors=dict(A=float(time), B=float(time)), actor_times_f64le=dict(A=exact_time(time), B=exact_time(time)),
            objects_time_s=None, objects_time_f64le=None))
    skin = ImportedSceneSkin(rig, observed['actors']['A'])
    reference = skin.vertices(sampler.sample(1.)[rig.joints]) @ Rotation.from_quat(a['rotation_xyzw']).as_matrix().T + a['translation_m']
    scene = dict(id='paired', frame_count=61, actors={n: {} for n in actors}, objects={}, contacts=[dict(
        id='world-touch', actor='A', effector=dict(surface_vertex=0), target=dict(space='world', point_m=reference[0].tolist()),
        start_frame=30, end_frame=30, tolerance_m=1e-10)])
    return scene, request, observed, actors, skin, reference


def test_complete_skin_identity_and_post_skin_placement_keep_weight_deficit(tmp_path):
    scene, request, observed, actors, skin, reference = fixture(tmp_path)
    result, arrays = measure(scene, request, observed, actors, {}, floor_y_m=-10)
    assert result['point_contact_samples_passed'] and result['authored_requirements_fully_measured']
    assert result['imported_skins']['A']['source_vertex_coverage'] and result['imported_skins']['A']['triangle_population_pass']
    assert result['actor_placement_applied_after_skin'] and not result['raw_imported_weights_renormalized']
    assert np.any(skin.weights.sum(1) < 1)
    contact_time = np.flatnonzero(arrays['times_s'] == 1.)[0]
    np.testing.assert_allclose(arrays['contact_0_actual'][contact_time], reference[0], atol=1e-14)
    assert result['floor'][0]['maximum_imported_source_vertex_error_m'] > 0
    bad = reference[0] - (1 - skin.weights[0].sum()) * np.array(actors['A'][2]['translation_m'])
    assert np.linalg.norm(bad - arrays['contact_0_actual'][contact_time]) > 1e-5
    assert not result['collision_verified'] and not result['triangle_penetration_verified']


def test_partner_point_is_actual_other_actor_skin_on_same_clock(tmp_path):
    scene, request, observed, actors, _, _ = fixture(tmp_path)
    scene['contacts'][0]['target'] = dict(space='actor', actor='B', surface_vertex=0)
    result, arrays = measure(scene, request, observed, actors, {})
    assert not result['point_contact_samples_passed'] and result['contacts'][0]['first_valid_time_s'] is None
    assert result['contacts'][0]['normal_samples_available']
    expected = actors['A'][2]['translation_m'][0] - actors['B'][2]['translation_m'][0]
    assert np.abs(arrays['contact_0_actual'][:, 0] - arrays['contact_0_target'][:, 0]).min() > expected - 1
    assert not result['partner_collision_verified']


def test_declared_floor_queries_every_vertex_and_keeps_witness(tmp_path):
    scene, request, observed, actors, _, _ = fixture(tmp_path)
    result, arrays = measure(scene, request, observed, actors, {}, floor_y_m=10., penetration_limit_m=0.)
    assert all(not r['passed'] and r['vertices'] == 8 and r['samples_over_limit'] == len(arrays['times_s']) for r in result['floor'])
    assert arrays['actor_0_floor_depth_m'].shape == arrays['times_s'].shape
    assert 0 <= result['floor'][0]['worst_source_vertex'] < 8


def test_authored_normal_and_unsupported_region_are_never_hidden(tmp_path):
    scene, request, observed, actors, _, _ = fixture(tmp_path)
    scene['contacts'][0].update(normal_target=dict(space='world', direction=[0, 1., 0]), region_contact={})
    result, _ = measure(scene, request, observed, actors, {})
    row = result['contacts'][0]
    assert row['normal_samples_available'] and row['normal_maximum_error_degrees'] is not None
    assert row['unsupported_authored_requirements'] == ['region_contact']
    assert not result['authored_requirements_fully_measured'] and not result['quality_approved']


@pytest.mark.parametrize('fault', ['weight', 'face', 'missing_mesh', 'actor', 'interval', 'tolerance', 'vertex',
                                 'self_target', 'unknown_object', 'missing_joint', 'nonunit_normal'])
def test_changed_binding_or_invalid_contact_rejected(tmp_path, fault):
    scene, request, observed, actors, _, _ = fixture(tmp_path)
    c = scene['contacts'][0]
    if fault == 'weight': observed['actors']['A']['meshes'][0]['weights'][0] = .123
    if fault == 'face': observed['actors']['A']['meshes'][0]['indices'].pop()
    if fault == 'missing_mesh': observed['actors']['A']['meshes'] = []
    if fault == 'actor': c['actor'] = 'absent'
    if fault == 'interval': c['end_frame'] = 61
    if fault == 'tolerance': c['tolerance_m'] = float('nan')
    if fault == 'vertex': c['effector']['surface_vertex'] = 8
    if fault == 'self_target': c['target'] = dict(space='actor', actor='A', surface_vertex=0)
    if fault == 'unknown_object': c['target'] = dict(space='object', object='absent', point_m=[0, 0, 0])
    if fault == 'missing_joint': c['effector'] = dict(joint='absent', offset_m=[0, 0, 0])
    if fault == 'nonunit_normal': c['normal_target'] = dict(space='world', direction=[0, 2, 0])
    with pytest.raises(ValueError): measure(scene, request, observed, actors, {})


@pytest.mark.parametrize('limit', [True, -.001, float('inf'), 1.1])
def test_invalid_penetration_screen_rejected(tmp_path, limit):
    scene, request, observed, actors, _, _ = fixture(tmp_path)
    with pytest.raises(ValueError): measure(scene, request, observed, actors, {}, penetration_limit_m=limit)


@pytest.mark.parametrize('geometry', [dict(schema='strep-object-geometry-v1', shape='box', size_m=[.6, .8, 1.]),
    dict(schema='strep-object-geometry-v1', shape='sphere', radius_m=.3),
    dict(schema='strep-object-geometry-v1', shape='cylinder', radius_m=.3, height_m=.8)])
def test_moving_rotating_primitive_uses_imported_object_pose_and_every_actor_vertex(tmp_path, geometry):
    from object_geometry import Geometry
    scene, request, observed, actors, _, reference = fixture(tmp_path)
    document = dict(nodes=[dict(name='Object_prop')], buffers=[], bufferViews=[], accessors=[])
    binary = bytearray(); times = append_accessor(document, binary, [0., 1., 2.], 'SCALAR')
    q = Rotation.from_euler('y', [0., 45., 90.], degrees=True).as_quat()
    grip = np.array([.3, 0., 0.]); center = reference[0] - Rotation.from_quat(q[1]).apply(grip)
    p = center + np.array([[-.1, 0., 0.], [0., 0., 0.], [.1, 0., 0.]])
    animation = dict(name='moving_prop', channels=[], samplers=[])
    for path, values, kind in [('translation', p, 'VEC3'), ('rotation', q, 'VEC4')]:
        index = len(animation['samplers'])
        animation['samplers'].append(dict(input=times, output=append_accessor(document, binary, values, kind)))
        animation['channels'].append(dict(sampler=index, target=dict(node=0, path=path)))
    document['animations'] = [animation]
    sampler = AnimationSampler(document, binary, 0)
    objects = dict(prop=(sampler, 0))
    scene['objects']['prop'] = dict(geometry=geometry)
    scene['contacts'][0]['target'] = dict(space='object', object='prop', point_m=grip.tolist())
    scene['contacts'][0]['tolerance_m'] = 1e-6
    for i, time in enumerate(request['sample_times_s']):
        observed['object_frames'][i]['prop'] = serialized(sampler.sample(time)[0])
        observed['clock_samples'][i]['objects_time_s'] = time
        observed['clock_samples'][i]['objects_time_f64le'] = exact_time(time)
    result, arrays = measure(scene, request, observed, actors, objects)
    assert result['point_contact_samples_passed'] and len(result['actor_objects']) == 2
    k = np.flatnonzero(arrays['times_s'] == 1.)[0]
    matrix = sampler.sample(1.)[0]
    expected = Geometry.parse(geometry).penetration_depth(reference, matrix[:3, 3], matrix[:3, :3])
    assert arrays['actor_object_0_vertex_depth_m'][k] == pytest.approx(expected.max(), abs=1e-14)
    np.testing.assert_allclose(arrays['contact_0_target'][k], matrix[:3, 3] + matrix[:3, :3] @ grip)
