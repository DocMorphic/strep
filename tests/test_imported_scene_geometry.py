"""Full topology/clock replay and rejection of modified engine evidence."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from test_scene_import_measurements import fixture
from imported_scene_geometry import ImportedGeometryScene, geometry_policy
from native_engine_clock import clock_wire
from native_scene_geometry import evaluate_to_archive
from native_observation_archive import verify


def setup(tmp_path):
    scene, request, observed, actors, skin, reference = fixture(tmp_path)
    scene.update(schema_version=1, fps=30)
    source = tmp_path / 'source.glb'
    request['frames'] = len(request['sample_times_s'])
    request['sample_clock'] = clock_wire(request['sample_times_s'])
    request['actors'] = {n: dict(path=str(source), transform=a[2]) for n, a in actors.items()}
    scene['actors'] = {n: dict(transform=a[2]) for n, a in actors.items()}
    return scene, request, observed, actors


def policy():
    return dict(schema='strep-imported-scene-geometry-policy-v1', producer_result_sha256='digest',
        limits=dict(penetration_m=.005, depth_resolution_m=1e-6, surface_tolerance_m=1e-8),
        planes=dict(floor=dict(normal_world=[0., 1., 0.], offset_m=-10.)))


def test_complete_imported_clock_topology_and_partner_volume_replay(tmp_path):
    original, request, observed, _ = setup(tmp_path)
    scene = ImportedGeometryScene(original, request, observed)
    def forbidden_source_skin(*args): raise AssertionError('Geometry must use the imported skin provider')
    for actor in scene.actors.values(): actor['rig'].vertices = forbidden_source_skin
    np.testing.assert_array_equal(scene.times, request['sample_times_s'])
    result, archive = evaluate_to_archive(scene, geometry_policy(policy(), scene, 'digest'), 'digest',
        tmp_path/'geometry.npz', actor_vertices=scene.actor_vertices, object_poses=scene.object_poses)
    assert len(result['samples']) == request['frames']
    assert all(t['faces'] == 12 and t['vertices'] == 8 for t in result['topology'].values())
    assert all(len(f['actor_pairs']) == 1 and len(f['world_planes']) == 2 for f in result['samples'])
    assert all(f['actor_pairs'][0]['surface']['whole_bounds_rejected'] for f in result['samples'])
    assert all(all(r['available'] for r in f['actor_pairs'][0]['vertex_containment']) for f in result['samples'])
    assert result['sampled_conditions_pass'] and not result['collision_verified'] and not result['quality_approved']
    assert verify(tmp_path/'geometry.npz')['all_values_exact']


def test_post_skin_placement_preserves_actual_weight_deficit(tmp_path):
    original, request, observed, actors = setup(tmp_path)
    scene = ImportedGeometryScene(original, request, observed)
    skin = scene.skins['A']; p, r = scene.actors['A']['placement']
    expected = skin.vertices(actors['A'][1].sample(1.)[actors['A'][0].joints]) @ r.T + p
    np.testing.assert_allclose(scene.actor_vertices('A', 1.), expected, atol=1e-14)
    with pytest.raises(ValueError): scene.actor_vertices('A', .123456789)
    assert not np.allclose(skin.weights.sum(1), 1., rtol=0, atol=1e-6)


@pytest.mark.parametrize('fault', ['clock_bytes', 'frame_count', 'placement', 'actor_population', 'pose', 'weight', 'id'])
def test_changed_raw_scene_clock_pose_or_skin_rejected(tmp_path, fault):
    original, request, observed, _ = setup(tmp_path)
    if fault == 'clock_bytes': request['sample_clock']['bytes_hex'] = '00' * (8 * request['frames'])
    if fault == 'frame_count': request['source_frame_count'] -= 1
    if fault == 'placement': request['actors']['A']['transform'] = dict(translation_m=[0, 0, 0], rotation_xyzw=[0, 0, 0, 1])
    if fault == 'actor_population': del original['actors']['B']
    if fault == 'pose': observed['frames'][0]['A'][0][3][0] += .01
    if fault == 'weight': observed['actors']['A']['meshes'][0]['weights'][0] += .01
    if fault == 'id': original['id'] = 'changed'
    with pytest.raises(ValueError): ImportedGeometryScene(original, request, observed)


@pytest.mark.parametrize('fault', ['digest', 'schema', 'extra'])
def test_policy_requires_exact_terminal_producer_binding(tmp_path, fault):
    original, request, observed, _ = setup(tmp_path); scene = ImportedGeometryScene(original, request, observed)
    value = policy()
    if fault == 'digest': value['producer_result_sha256'] = 'changed'
    if fault == 'schema': value['schema'] = 'other'
    if fault == 'extra': value['omit_partner'] = True
    with pytest.raises(ValueError): geometry_policy(value, scene, 'digest')


def test_no_source_pose_substitution_can_hide_an_imported_crossing(tmp_path):
    from test_native_scene_engine import serialized
    original, request, observed, _ = setup(tmp_path)
    # Both actual actor placements intentionally overlap. The source native
    # pose is otherwise unchanged, so this remains a passing pose import.
    original['actors']['B']['transform'] = copy.deepcopy(original['actors']['A']['transform'])
    request['actors']['B']['transform'] = copy.deepcopy(request['actors']['A']['transform'])
    for frame in observed['frames']: frame['B'] = copy.deepcopy(frame['A'])
    scene = ImportedGeometryScene(original, request, observed)
    result, _ = evaluate_to_archive(scene, geometry_policy(policy(), scene, 'digest'), 'digest',
        tmp_path/'overlap.npz', actor_vertices=scene.actor_vertices, object_poses=scene.object_poses)
    assert not result['sampled_conditions_pass']
    assert all(f['actor_pairs'][0]['surface']['records'] for f in result['samples'])


def test_missing_imported_mesh_receipt_rejected_before_measurement(tmp_path):
    original, request, observed, _ = setup(tmp_path)
    observed['actors']['A']['meshes'] = []
    with pytest.raises(ValueError): ImportedGeometryScene(original, request, observed)


def producer_fixture(tmp_path):
    from strep import save, sha256
    original, request, observed, _ = setup(tmp_path)
    folder = tmp_path/'producer'; folder.mkdir()
    manifest = tmp_path/'manifest.json'; scene_path = tmp_path/'scene.json'
    save(manifest, dict(scenes=[dict(id=original['id'], variants=dict(palm='scene.json'))]))
    save(scene_path, dict(scene=original))
    save(folder/'request.json', dict(scenes=[request]))
    save(folder/'engine-output.json', dict(scenes=[observed]))
    save(folder/'pipeline.json', dict(status='complete'))
    save(folder/'skin.json', dict(test_fixture=True)); (folder/'skin.npz').write_bytes(b'fixture-only receipt')
    implementation = folder/'implementation'; implementation.mkdir()
    method = implementation/'fixture.py'; method.write_text('# Synthetic protocol fixture, not an engine run.\n')
    result = dict(status='complete', imported_skin_measurements=True, all_precision_screens_passed=True,
        inputs_sha256={str(p): sha256(p) for p in (manifest, scene_path, tmp_path/'source.glb')},
        implementation_sha256={'fixture.py': sha256(method)}, request_sha256=sha256(folder/'request.json'),
        engine_output_sha256=sha256(folder/'engine-output.json'), rows=[dict(id=original['id'], skin_measurements=dict(
            path='skin.json', sha256=sha256(folder/'skin.json'), observations_path='skin.npz', observations_sha256=sha256(folder/'skin.npz')))])
    save(folder/'result.json', result)
    return folder


@pytest.mark.parametrize('fault', ['processing', 'result_failed', 'request', 'engine_output', 'asset', 'method',
                                 'skin_receipt', 'skin_arrays', 'missing_skin_mode', 'scene_population'])
def test_terminal_producer_reuse_rejects_corruption_or_missing_evidence(tmp_path, fault):
    from imported_scene_geometry import load_producer
    from strep import save, read, sha256
    folder = producer_fixture(tmp_path)
    if fault == 'processing': save(folder/'pipeline.json', dict(status='processing'))
    elif fault in ('result_failed', 'missing_skin_mode', 'scene_population'):
        r = read(folder/'result.json')
        if fault == 'result_failed': r['status'] = 'failed'
        if fault == 'missing_skin_mode': r['imported_skin_measurements'] = False
        if fault == 'scene_population': r['rows'] = []
        save(folder/'result.json', r)
    else:
        path = {'request': folder/'request.json', 'engine_output': folder/'engine-output.json',
                'asset': tmp_path/'source.glb', 'method': folder/'implementation/fixture.py',
                'skin_receipt': folder/'skin.json', 'skin_arrays': folder/'skin.npz'}[fault]
        path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises(ValueError): load_producer(folder)


def test_whole_geometry_runner_reuses_bound_observations_and_retains_source_bytes(tmp_path, monkeypatch):
    import action_worker_lock
    from imported_scene_geometry import run
    from strep import save, sha256
    monkeypatch.setattr(action_worker_lock, 'ROOT', tmp_path/'lock-root')
    folder = producer_fixture(tmp_path); value = policy()
    value['producer_result_sha256'] = sha256(folder/'result.json')
    policy_path = tmp_path/'policy.json'; save(policy_path, value)
    before = {p: sha256(p) for p in folder.rglob('*') if p.is_file()}
    result = run(folder, policy_path, tmp_path/'audit')
    assert result['sampled_conditions_pass'] and len(result['rows']) == 1
    assert not result['release_approved'] and result['producer_result_sha256'] == sha256(folder/'result.json')
    assert all(sha256(p) == h for p, h in before.items())
    assert verify(tmp_path/'audit/geometry-0.npz')['all_values_exact']
