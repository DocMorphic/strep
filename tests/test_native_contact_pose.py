"""Synthetic pose relaxations and hard edit bounds, not motion approval."""
from pathlib import Path
import copy
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from native_contact_pose import ContactPose, rotation_ball, fit
from native_surface_contact import evaluate
from native_scene_contacts import SceneContacts
from test_native_scene_contacts import setup
from test_native_surface_contact import policy
from strep import save, sha256


def prepare(tmp_path):
    _, _, _, spec = setup(tmp_path, rotating=True, mode='touch'); path = tmp_path / 'contacts.json'; save(path, spec)
    scene = SceneContacts(spec, tmp_path); p = policy(path, spec)
    permission = dict(schema='strep-native-contact-pose-permissions-v1', contacts_sha256=sha256(path), actors=dict(A=dict(
        rotation_tracks=[dict(node=0, maximum_change_degrees=45.)], maximum_joint_displacement_m=.22)))
    return spec, path, scene, p, permission


def test_rotation_ball_bounds_every_visited_vector_without_component_clipping():
    raw = np.random.default_rng(2).uniform(-100, 100, (100, 3)); limits = np.linspace(.01, .7, 100)
    actual = rotation_ball(raw, limits)
    assert np.all(np.linalg.norm(actual, axis=1) < limits)
    np.testing.assert_allclose(actual / np.linalg.norm(actual, axis=1)[:, None], raw / np.linalg.norm(raw, axis=1)[:, None])
    np.testing.assert_array_equal(rotation_ball(np.zeros((1, 3)), [1]), [[0., 0, 0]])


def test_zero_pose_reconstructs_source_skin_and_existing_normal_audit(tmp_path):
    _, path, scene, p, permissions = prepare(tmp_path); pose = ContactPose(scene, p, sha256(path), 1., permissions)
    residual, report, worlds, vertices = pose.measure(np.zeros(pose.size))
    source_report, _ = evaluate(scene, p, sha256(path))
    np.testing.assert_allclose(worlds['A'], pose.source['A'], atol=1e-14, rtol=0)
    np.testing.assert_allclose(vertices['A'], scene.actors['A']['rig'].vertices(pose.source['A']), atol=1e-14, rtol=0)
    expected = source_report['contacts'][0]['samples'][0]['points'][0]
    assert report['contacts'][0]['opposition_errors_degrees'][0] == pytest.approx(expected['opposition_error_degrees'])
    assert report['maximum_normalized_violation'] == 0 and np.all(residual <= 0)


def test_changes_preserve_local_translations_and_respect_geodesic_rotation_limit(tmp_path):
    _, path, scene, p, permission = prepare(tmp_path); pose = ContactPose(scene, p, sha256(path), 1., permission)
    world, _ = pose.worlds(np.array([20., 20., -20.]))
    old = pose.local['A']; parents = scene.actors['A']['rig'].parents
    current = np.array([np.linalg.solve(world['A'][j], world['A'][i]) if j >= 0 else world['A'][i] for i, j in enumerate(parents)])
    np.testing.assert_allclose(current[:, :3, 3], old[:, :3, 3], atol=1e-14, rtol=0)
    angles = Rotation.from_matrix(old[:, :3, :3].transpose(0, 2, 1) @ current[:, :3, :3]).magnitude()
    assert np.rad2deg(angles[0]) < 45 and np.rad2deg(angles[0]) > 44
    np.testing.assert_allclose(angles[1:], 0, atol=1e-14)


def test_contact_guidance_can_improve_a_pose_without_claiming_animation(tmp_path):
    spec, path, _, p, permissions = prepare(tmp_path)
    spec['contacts'][0]['limits']['position_m'] = .5; save(path, spec)
    scene = SceneContacts(spec, tmp_path); p['contacts_sha256'] = permissions['contacts_sha256'] = sha256(path)
    p['contacts'][spec['contacts'][0]['id']]['target_normal']['normals'] = [Rotation.from_euler('x', 20, degrees=True).apply([0., 1, 0]).tolist()]
    pose = ContactPose(scene, p, sha256(path), 1., permissions)
    before = pose.measure(np.zeros(pose.size))[1]['maximum_normalized_violation']
    candidate, solver = fit(pose, evaluations=12)
    after = pose.measure(candidate)[1]
    assert after['maximum_normalized_violation'] < before
    assert not after['temporal_constraints_checked'] and not solver['full_triangle_geometry_checked']
    assert not after['quality_approved'] and not solver['release_approved']


def test_budget_keeps_seed_and_reports_exhaustion_instead_of_solver_success(tmp_path):
    _, path, scene, p, permissions = prepare(tmp_path); pose = ContactPose(scene, p, sha256(path), 1., permissions)
    candidate, result = fit(pose, maximum_calls=1)
    assert result['budget_exhausted'] and not result['solver_success'] and result['objective_calls'] == 1
    np.testing.assert_array_equal(candidate, np.zeros(pose.size))


def test_object_targets_use_authored_local_points_and_normals(tmp_path):
    spec, path, scene, p, permission = prepare(tmp_path)
    source = scene.actors['A']['rig'].vertices(scene.actors['A']['sampler'].sample(1.))[0]
    rotation = Rotation.from_euler('z', 30, degrees=True)
    position = source - rotation.apply([0., .2, 0])
    spec['objects']['item'] = dict(geometry=dict(schema='strep-object-geometry-v1', shape='sphere', radius_m=.2),
        keyframes=[dict(time_s=t, translation_m=position.tolist(), rotation_xyzw=rotation.as_quat().tolist()) for t in [0., 2.]])
    spec['contacts'][0]['target'] = dict(space='object', object='item', points_m=[[0., .2, 0]])
    save(path, spec); scene = SceneContacts(spec, tmp_path)
    p['contacts_sha256'] = permission['contacts_sha256'] = sha256(path)
    p['contacts'][spec['contacts'][0]['id']]['target_normal']['space'] = 'object'
    pose = ContactPose(scene, p, sha256(path), 1., permission)
    record = pose.measure(np.zeros(pose.size))[1]['contacts'][0]
    expected = evaluate(scene, p, sha256(path))[0]['contacts'][0]['samples'][0]['points'][0]
    assert record['position_errors_m'][0] < 1e-14
    assert record['opposition_errors_degrees'][0] == pytest.approx(expected['opposition_error_degrees'])
    fit(pose, evaluations=1)  # Exercise the complete primitive vertex guide.


def test_partner_normals_use_target_skin_and_unpermitted_actor_stays_exact(tmp_path):
    spec, path, scene, p, permission = prepare(tmp_path)
    point = scene.actors['A']['rig'].vertices(scene.actors['A']['sampler'].sample(1.))[0]
    rotation = Rotation.from_euler('z', 180, degrees=True)
    spec['actors']['B'] = copy.deepcopy(spec['actors']['A'])
    spec['actors']['B']['placement'] = dict(translation_m=(point-rotation.apply(point)).tolist(), rotation_xyzw=rotation.as_quat().tolist())
    spec['contacts'][0]['target'] = dict(space='actor', actor='B', vertices=spec['contacts'][0]['vertices'], reduction='individual')
    save(path, spec); scene = SceneContacts(spec, tmp_path)
    p['contacts_sha256'] = permission['contacts_sha256'] = sha256(path)
    p['contacts'][spec['contacts'][0]['id']]['target_normal'] = dict(space='partner-surface')
    pose = ContactPose(scene, p, sha256(path), 1., permission)
    _, report, _, _ = pose.measure(np.zeros(pose.size))
    assert report['contacts'][0]['position_errors_m'][0] < 1e-14
    assert report['contacts'][0]['opposition_errors_degrees'][0] == pytest.approx(0)
    worlds, _ = pose.worlds(np.ones(pose.size))
    np.testing.assert_array_equal(worlds['B'], pose.source['B'])


def test_unavailable_normals_cannot_pass_or_emit_nonstandard_json(tmp_path):
    import json
    _, path, scene, p, permission = prepare(tmp_path); pose = ContactPose(scene, p, sha256(path), 1., permission)
    pose.faces['A'][0] = [0, 0, 1]
    residual, report, _, _ = pose.measure(np.zeros(pose.size))
    assert not all(report['contacts'][0]['normals_available']) and residual.max() >= 100
    assert report['contacts'][0]['opposition_errors_degrees'][0] is None
    json.dumps(report, allow_nan=False)


def test_explicit_time_budget_stops_after_retaining_the_seed(tmp_path, monkeypatch):
    import native_contact_pose
    _, path, scene, p, permission = prepare(tmp_path); pose = ContactPose(scene, p, sha256(path), 1., permission)
    ticks = iter([0., 2., 3.])
    monkeypatch.setattr(native_contact_pose.time, 'monotonic', lambda: next(ticks))
    candidate, result = fit(pose, maximum_seconds=1.)
    assert result['budget_exhausted'] and result['objective_calls'] == 1
    np.testing.assert_array_equal(candidate, np.zeros(pose.size))


def test_scipy_evaluation_limit_is_reported_as_budget_exhaustion(tmp_path):
    _, path, scene, p, permission = prepare(tmp_path)
    p['contacts'][scene.rows[0]['authored']['id']]['target_normal']['normals'] = [[0., 0, 1.]]
    pose = ContactPose(scene, p, sha256(path), 1., permission)
    _, result = fit(pose, evaluations=1)
    assert result['budget_exhausted'] and result['evaluation_budget_exhausted'] and not result['time_or_call_budget_exhausted']
    assert not result['solver_success'] and result['evaluations'] == 1


@pytest.mark.parametrize('fault', ['binding', 'actor', 'node', 'boolean_node', 'duplicate', 'static', 'limit', 'extra'])
def test_invalid_permissions_do_not_grant_hidden_pose_freedom(tmp_path, fault):
    _, path, scene, p, permission = prepare(tmp_path); actor = permission['actors']['A']; track = actor['rotation_tracks'][0]
    if fault == 'binding': permission['contacts_sha256'] = '0' * 64
    if fault == 'actor': permission['actors']['missing'] = permission['actors'].pop('A')
    if fault == 'node': track['node'] = 999
    if fault == 'boolean_node': track['node'] = True
    if fault == 'duplicate': actor['rotation_tracks'] *= 2
    if fault == 'static': track['node'] = 5
    if fault == 'limit': track['maximum_change_degrees'] = 45.01
    if fault == 'extra': actor['root_lift'] = 1
    with pytest.raises(ValueError): ContactPose(scene, p, sha256(path), 1., permission)


@pytest.mark.parametrize('fault', ['nan', 'large', 'shape', 'zero_limit'])
def test_invalid_rotation_coordinates_fail(fault):
    raw = np.ones((1, 3)); limit = [1.]
    if fault == 'nan': raw[0, 0] = np.nan
    if fault == 'large': raw *= 101
    if fault == 'shape': raw = raw.ravel()
    if fault == 'zero_limit': limit = [0.]
    with pytest.raises(ValueError): rotation_ball(raw, limit)
