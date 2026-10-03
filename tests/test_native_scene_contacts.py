"""Independent skin/clock checks for body, moving-object and partner contacts."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from test_native_support import fixture
from test_native_support_articulation import toe_fixture
from native_scene_contacts import SceneContacts, run
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_support_skin import NativeSupportSkin
from gltf_tools import append_accessor, write_glb
from strep import save, read, sha256


def setup(tmp_path, *, rotating=False, mode='hold'):
    source, rig, reader, _ = fixture(tmp_path)
    if rotating:
        doc = copy.deepcopy(rig.document); data = bytearray(rig.binary); animation = doc['animations'][0]
        q = Rotation.from_euler('y', np.linspace(0, 80, 11), degrees=True).as_quat()
        animation['channels'].append(dict(sampler=len(animation['samplers']), target=dict(node=0, path='rotation')))
        animation['samplers'].append(dict(input=animation['samplers'][0]['input'],
            output=append_accessor(doc, data, q, 'VEC4'), interpolation='LINEAR'))
        write_glb(source, doc, data); rig = RigAsset.load(source); reader = NativeSupportSampler(rig.document, rig.binary, 0)
    spec = dict(schema='strep-native-scene-contacts-v1', duration_s=reader.duration, actors=dict(A=dict(
        glb=source.name, sha256=sha256(source), animation_index=0,
        placement=dict(translation_m=[0, 0, 0], rotation_xyzw=[0, 0, 0, 1]))), objects={}, contacts=[])
    point = rig.vertices(reader.sample(1.))[0].tolist()
    spec['contacts'].append(dict(id='arbitrary-body-patch', actor='A', vertices=[[6, 0, 0]], reduction='individual',
        target=dict(space='world', points_m=[point]), mode=mode, interval_s=[1., 1.] if mode == 'touch' else [.8, 1.2],
        limits=dict(position_m=1e-6) if mode == 'touch' else dict(position_m=1e-6, relative_speed_m_s=1e-6)))
    return source, rig, reader, spec


def object_target(spec, reader, rig, *, gap=0):
    clock = reader.channels[0][2]
    keys = []
    for time in clock:
        root = reader.sample(float(time))[0]
        keys.append(dict(time_s=float(time), translation_m=root[:3, 3].tolist(),
            rotation_xyzw=Rotation.from_matrix(root[:3, :3]).as_quat().tolist()))
    spec['objects']['crate'] = dict(geometry=dict(schema='strep-object-geometry-v1', shape='box', size_m=[4, 2.02, 4]), keyframes=keys)
    # Bind-frame skin positions relative to the animated root; no joint-name or
    # dominant-weight approximation is used by the independent oracle.
    local = rig.primitives[0]['positions'][0] - np.array([0, 1.2, 0])
    local[0] += gap
    spec['contacts'][0]['target'] = dict(space='object', object='crate', points_m=[local.tolist()])
    spec['contacts'][0]['interval_s'] = [.3, 1.7]
    spec['contacts'][0]['limits'] = dict(position_m=.002, relative_speed_m_s=1e-5)


def test_world_body_hold_and_exact_touch_use_declared_conditions(tmp_path):
    source, rig, reader, spec = setup(tmp_path)
    result, arrays = SceneContacts(spec, tmp_path).evaluate()
    assert result['passed'] and len(result['contacts'][0]['relative_speed_populations']) == 12
    assert all(not result[k] for k in ('engine_playback_verified', 'collision_verified', 'quality_approved', 'training_admitted', 'release_approved'))
    spec['contacts'][0].update(mode='touch', interval_s=[.853725, .853725], limits=dict(position_m=1e-6))
    event, arrays = SceneContacts(spec, tmp_path).evaluate()
    assert event['passed'] and event['contacts'][0]['samples'] == 1
    assert not event['contacts'][0]['relative_speed_populations']
    np.testing.assert_array_equal(arrays['contact_0_times_s'], [.853725])
    assert sha256(source) == spec['actors']['A']['sha256']


def test_moving_rotating_object_measures_slip_in_object_coordinates(tmp_path):
    source, rig, reader, spec = setup(tmp_path, rotating=True)
    object_target(spec, reader, rig, gap=.001)
    result, arrays = SceneContacts(spec, tmp_path).evaluate(); row = result['contacts'][0]
    assert result['passed'] and row['relative_speed_frame'] == 'object local'
    assert abs(row['maximum_position_error_m'] - .001) < 1e-7
    assert max(p['maximum_relative_speed_m_s'] for p in row['relative_speed_populations']) < 1e-5
    # World error rotates, so world difference would falsely measure slip.
    times = arrays['contact_0_times_s']; world_error = arrays['contact_0_effector_world_m'] - arrays['contact_0_target_world_m']
    assert np.max(np.linalg.norm(np.diff(world_error, axis=0), axis=2) / np.diff(times)[:, None]) > .0005
    oracle = np.array([rig.vertices(reader.sample(float(t)))[[0]] for t in times])
    np.testing.assert_allclose(arrays['contact_0_effector_world_m'], oracle, atol=2e-15, rtol=0)


def test_partner_correspondence_and_placement_preserve_separation_failures(tmp_path):
    source, rig, reader, spec = setup(tmp_path, rotating=True)
    spec['actors']['B'] = copy.deepcopy(spec['actors']['A'])
    spec['contacts'][0]['target'] = dict(space='actor', actor='B', vertices=[[6, 0, 0]], reduction='individual')
    result, _ = SceneContacts(spec, tmp_path).evaluate()
    assert result['passed']
    spec['actors']['B']['placement']['translation_m'][0] = .05
    failed, arrays = SceneContacts(spec, tmp_path).evaluate()
    assert not failed['passed'] and abs(failed['contacts'][0]['maximum_position_error_m'] - .05) < 1e-15
    assert all(p['passed'] for p in failed['contacts'][0]['relative_speed_populations'])
    # No averaging across contacts or patch vertices can hide a failed condition.
    spec['contacts'].append(copy.deepcopy(spec['contacts'][0])); spec['contacts'][1]['id'] = 'loose'
    spec['contacts'][1]['limits']['position_m'] = .1
    result, _ = SceneContacts(spec, tmp_path).evaluate()
    assert [r['passed'] for r in result['contacts']] == [False, True] and not result['passed']


def test_short_hold_retains_unavailable_frame_populations(tmp_path):
    _, _, _, spec = setup(tmp_path)
    spec['contacts'][0]['interval_s'] = [1., 1.000001]
    result, _ = SceneContacts(spec, tmp_path).evaluate()
    assert not result['passed']
    assert any(not p['available'] and p['maximum_relative_speed_m_s'] is None
               for p in result['contacts'][0]['relative_speed_populations'])


@pytest.mark.parametrize('fault', ['schema', 'extra', 'hash', 'index-bool', 'duration', 'pose-scale', 'pose-bool',
    'vertex-bool', 'vertex-missing', 'vertex-duplicate', 'id-duplicate', 'actor-missing', 'same-partner',
    'partner-count', 'object-missing', 'object-interior', 'object-time', 'object-coverage', 'touch-range',
    'hold-event', 'limit-bool', 'limit-nan', 'limits-missing', 'interval-negative', 'target-count', 'reduction',
    'actor-list', 'partner-list', 'object-list'])
def test_invalid_authored_contacts_reject_instead_of_simplifying(tmp_path, fault):
    _, rig, reader, spec = setup(tmp_path); row = spec['contacts'][0]; actor = spec['actors']['A']
    if fault == 'schema': spec['schema'] = 'old-foot-only'
    if fault == 'extra': spec['anatomy_approved'] = True
    if fault == 'hash': actor['sha256'] = '0' * 64
    if fault == 'index-bool': actor['animation_index'] = True
    if fault == 'duration': spec['duration_s'] = 1.9
    if fault == 'pose-scale': actor['placement']['scale'] = 2
    if fault == 'pose-bool': actor['placement']['translation_m'][0] = True
    if fault == 'vertex-bool': row['vertices'][0][2] = True
    if fault == 'vertex-missing': row['vertices'][0][2] = 99
    if fault == 'vertex-duplicate': row['vertices'] *= 2
    if fault == 'id-duplicate': spec['contacts'] *= 2
    if fault == 'actor-missing': row['actor'] = 'missing'
    if fault == 'actor-list': row['actor'] = []
    if fault == 'same-partner': row['target'] = dict(space='actor', actor='A', vertices=[[6, 0, 0]], reduction='individual')
    if fault == 'partner-list': row['target'] = dict(space='actor', actor=[], vertices=[[6, 0, 0]], reduction='individual')
    if fault == 'partner-count':
        spec['actors']['B'] = copy.deepcopy(actor); row['target'] = dict(space='actor', actor='B', vertices=[[6, 0, 0], [6, 0, 1]], reduction='individual')
    if fault.startswith('object-'):
        object_target(spec, reader, rig)
        if fault == 'object-missing': row['target']['object'] = 'missing'
        if fault == 'object-list': row['target']['object'] = []
        if fault == 'object-interior': row['target']['points_m'] = [[0, 0, 0]]
        if fault == 'object-time': spec['objects']['crate']['keyframes'][1]['time_s'] = 0
        if fault == 'object-coverage': spec['objects']['crate']['keyframes'].pop()
    if fault == 'touch-range': row['mode'] = 'touch'
    if fault == 'hold-event': row['interval_s'] = [1, 1]
    if fault == 'limit-bool': row['limits']['position_m'] = True
    if fault == 'limit-nan': row['limits']['relative_speed_m_s'] = float('nan')
    if fault == 'limits-missing': row['limits'].pop('relative_speed_m_s')
    if fault == 'interval-negative': row['interval_s'][0] = -.01
    if fault == 'target-count': row['target']['points_m'] *= 2
    if fault == 'reduction': row['reduction'] = 'dominant-bone'
    with pytest.raises(ValueError): SceneContacts(spec, tmp_path)


def test_archive_records_sources_methods_and_arrays_and_rejects_reuse(tmp_path):
    source, _, _, spec = setup(tmp_path); path = tmp_path / 'contacts.json'; save(path, spec)
    output = tmp_path / 'audit'; result = run(path, output)
    assert result == read(output / 'result.json') and sha256(output / 'spec.json') == sha256(path)
    assert sha256(output / 'input/actor-0.glb') == sha256(source)
    assert result['observations_sha256'] == sha256(output / 'observations.npz')
    for name, digest in result['implementation_sha256'].items(): assert sha256(output / 'implementation' / name) == digest
    with pytest.raises(ValueError, match='Fresh'): run(path, output)


def test_changed_source_during_measurement_rejects(tmp_path, monkeypatch):
    source, _, _, spec = setup(tmp_path); scene = SceneContacts(spec, tmp_path)
    original = scene.actor_points
    def mutate(*args):
        result = original(*args); source.write_bytes(source.read_bytes() + b'changed'); return result
    monkeypatch.setattr(scene, 'actor_points', mutate)
    with pytest.raises(ValueError, match='source changed'): scene.evaluate()


def test_explicit_centroid_is_distinct_from_distributed_vertex_contact(tmp_path):
    _, rig, reader, spec = setup(tmp_path); row = spec['contacts'][0]
    row.update(mode='touch', interval_s=[1., 1.], limits=dict(position_m=1e-6),
        vertices=[[6, 0, 0], [6, 0, 1]], reduction='centroid')
    row['target']['points_m'] = [rig.vertices(reader.sample(1.))[:2].mean(axis=0).tolist()]
    result, _ = SceneContacts(spec, tmp_path).evaluate()
    assert result['passed'] and result['contacts'][0]['vertices'] == 2 and result['contacts'][0]['measured_points'] == 1
    row['reduction'] = 'individual'; row['target']['points_m'] *= 2
    individual, _ = SceneContacts(spec, tmp_path).evaluate()
    assert not individual['passed'] and individual['contacts'][0]['maximum_position_error_m'] > .019


def test_multiple_primitives_eight_slots_and_repeated_influences_match_separate_decoder(tmp_path):
    source, rig, _, _, _ = toe_fixture(tmp_path)
    doc = copy.deepcopy(rig.document); binary = bytearray(rig.binary)
    primitive = doc['meshes'][0]['primitives'][0]
    weights = rig.primitives[0]['weights'] * .4999
    primitive['attributes']['WEIGHTS_0'] = append_accessor(doc, binary, weights, 'VEC4')
    primitive['attributes']['WEIGHTS_1'] = append_accessor(doc, binary, weights, 'VEC4')
    primitive['attributes']['JOINTS_1'] = primitive['attributes']['JOINTS_0']
    doc['meshes'][0]['primitives'].append(copy.deepcopy(primitive)); write_glb(source, doc, binary)
    rig = RigAsset.load(source); reader = NativeSupportSampler(rig.document, rig.binary, 0)
    spec = dict(schema='strep-native-scene-contacts-v1', duration_s=reader.duration,
        actors=dict(A=dict(glb=source.name, sha256=sha256(source), animation_index=0,
            placement=dict(translation_m=[.3, -.1, .2], rotation_xyzw=Rotation.from_euler('z', 15, degrees=True).as_quat().tolist()))),
        objects={}, contacts=[])
    scene_points = rig.vertices(reader.sample(.853725))[[0, 4]] @ Rotation.from_euler('z', 15, degrees=True).as_matrix().T + [.3, -.1, .2]
    spec['contacts'].append(dict(id='mixed-skin', actor='A', vertices=[[6, 0, 0], [6, 1, 1]], reduction='individual',
        target=dict(space='world', points_m=scene_points.tolist()), mode='touch', interval_s=[.853725, .853725], limits=dict(position_m=1e-12)))
    scene = SceneContacts(spec, tmp_path); result, arrays = scene.evaluate()
    assert result['passed'] and scene.actors['A']['skin'].weights.shape == (6, 8)
    np.testing.assert_allclose(arrays['contact_0_effector_world_m'][0], scene_points, atol=1e-15, rtol=0)
