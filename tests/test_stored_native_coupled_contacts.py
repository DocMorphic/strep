"""Stored native secants retain every source row; exports remain authoritative."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from test_native_contact_norms import prepared
from native_scene_norms import rows, linearize
from native_contact_norms import ContactNorms
from central_coupled_contacts import CentralCoupledContactModel
from stored_native_coupled_contacts import StoredNativeCoupledContactModel


@pytest.mark.parametrize('partner', [False, True])
@pytest.mark.parametrize('hold', [False, True])
def test_all_native_rows_and_contact_guards_survive_storage_secants(tmp_path, partner, hold):
    problem, policy, digest = prepared(tmp_path, partner=partner, hold=hold)
    x = problem.initial.copy()
    worlds = problem.worlds(x)
    native = rows(problem, x, worlds)
    contact = ContactNorms(problem, policy, digest).residual(worlds)
    model = StoredNativeCoupledContactModel(problem, policy, digest)
    system, jac, meta = model.linearize(x, worlds, .02, step=.001)
    n, count = len(native.caps), len(contact)
    assert len(system.caps) == n + 2 * count and meta['hard_rows'] == n + count
    np.testing.assert_array_equal(system.vectors[:n], native.vectors)
    np.testing.assert_array_equal(system.caps[:n], native.caps)
    np.testing.assert_array_equal(system.scales[:n], native.scales)
    np.testing.assert_allclose(system.residual()[:n], problem.constraints(x, worlds), atol=1e-9, rtol=0)
    np.testing.assert_allclose(system.residual()[n:n + count], np.minimum(contact, 0), atol=1e-9, rtol=0)
    np.testing.assert_allclose(system.residual()[-count:], contact, atol=1e-9, rtol=0)
    np.testing.assert_array_equal(jac[3 * n:3 * (n + count)].toarray(), jac[-3 * count:].toarray())
    assert meta['native']['difference_source'] == 'stored'
    assert meta['native']['difference_scheme'] == 'central'
    assert meta['native']['central_difference_columns'] == problem.size
    assert meta['contact']['difference_source'] == 'continuous'
    assert meta['native_difference_keys_quantized'] and not meta['contact_difference_keys_quantized']
    assert meta['finite_storage_secants'] and not meta['uniform_quantization_error_bound']
    assert not meta['nonlinear_feasibility_certified'] and not meta['quality_approved'] and not meta['release_approved']


def test_every_native_column_matches_actually_exported_plus_minus_probe_curves(tmp_path):
    problem, policy, digest = prepared(tmp_path)
    problem.edits.rotation_storage_policy = 'source-scale'
    x = problem.initial.copy()
    model = StoredNativeCoupledContactModel(problem, policy, digest)
    system, jac, meta = model.linearize(x, problem.worlds(x), .02, step=.001)
    n = meta['complete_native_rows']
    for column, offsets in enumerate(meta['native']['actual_difference_offsets']):
        assert offsets == [.001, -.001]
        probes = []
        for offset in offsets:
            other = x.copy()
            other[column] += offset
            path = tmp_path / f'probe-{column}-{offset}.glb'
            problem.edits.export('A', other, path)
            _, decoded = problem.decoded({'A': path}, other)
            probes.append(rows(problem, other, decoded).vectors)
        expected = ((probes[0] - probes[1]) / .002).ravel()
        np.testing.assert_allclose(jac[:3 * n, column].toarray().ravel(), expected, atol=2e-7, rtol=1e-10)
    assert meta['native_rotation_storage_policy'] == 'source-scale'


@pytest.mark.parametrize('centroid', [False, True])
def test_moving_object_contact_keeps_all_positions_speed_clocks_and_surface_guards(tmp_path, centroid):
    from scipy.spatial.transform import Rotation
    from test_native_surface_contact import scene_fixture, policy as make_policy
    from test_cached_contact_norms import make
    from strep import save
    _, rig, reader, spec, path, _ = scene_fixture(tmp_path)
    row = spec['contacts'][0]
    q = Rotation.from_euler('z', 60, degrees=True)
    vertex = rig.vertices(reader.sample(1.))[0]
    local = np.array([0, .2, 0.])
    position = vertex - q.apply(local)
    spec['objects']['prop'] = dict(geometry=dict(schema='strep-object-geometry-v1', shape='sphere', radius_m=.2),
        keyframes=[dict(time_s=t, translation_m=position.tolist(),
                       rotation_xyzw=Rotation.from_euler('z', angle, degrees=True).as_quat().tolist())
                   for t, angle in [(0., 0), (2., 120)]])
    row['target'] = dict(space='object', object='prop', points_m=[local.tolist()])
    if centroid: row.update(vertices=[[6, 0, 0], [6, 0, 1]], reduction='centroid')
    row.update(mode='hold', interval_s=[.8, 1.2], limits=dict(position_m=.5, relative_speed_m_s=.5))
    save(path, spec)
    problem, policy, digest = make(spec, path, make_policy(path, spec))
    model = StoredNativeCoupledContactModel(problem, policy, digest)
    x = problem.initial.copy(); worlds = problem.worlds(x)
    system, jac, meta = model.linearize(x, worlds, .02)
    native = rows(problem, x, worlds); contacts = ContactNorms(problem, policy, digest).residual(worlds)
    n, c = len(native.caps), len(contacts)
    assert len(problem.rows[0]['populations']) == 12 and len(system.caps) == n + 2 * c
    np.testing.assert_array_equal(system.caps[:n], native.caps)
    np.testing.assert_allclose(system.residual()[:n], problem.constraints(x, worlds), atol=1e-9, rtol=0)
    np.testing.assert_allclose(system.residual()[-c:], contacts, atol=1e-9, rtol=0)
    np.testing.assert_array_equal(jac[3 * n:3 * (n + c)].toarray(), jac[-3 * c:].toarray())


def test_both_edited_partner_actors_keep_their_complete_native_prefix_and_column_order(tmp_path):
    import copy
    from native_scene_edit import SceneEdits
    from native_scene_fit import SceneProblem
    problem, policy, digest = prepared(tmp_path, partner=True, hold=True)
    declaration = dict(window_s=[0, 2], protected_s=[], knots_s=[0, 1, 2],
        tracks=[dict(node=3, path='rotation', maximum_change=5)], maximum_joint_displacement_m=.02)
    permissions = dict(schema='strep-native-scene-edit-v1', contacts_sha256=digest,
                       actors=dict(B=copy.deepcopy(declaration), A=declaration))
    problem = SceneProblem(problem.scene, SceneEdits(permissions, problem.scene, digest))
    model = StoredNativeCoupledContactModel(problem, policy, digest)
    x = problem.initial.copy(); worlds = problem.worlds(x)
    system, jac, meta = model.linearize(x, worlds, .02)
    native = rows(problem, x, worlds)
    reference, reference_jac, _ = linearize(problem, x, step=.001, difference_source='stored',
        base_worlds=worlds, difference_scheme='central')
    assert list(problem.edits.actors) == ['B', 'A'] and problem.size == 6
    assert meta['native']['central_difference_columns'] == 6
    assert meta['complete_native_rows'] == len(native.caps)
    np.testing.assert_array_equal(system.vectors[:len(native.caps)], native.vectors)
    np.testing.assert_array_equal(jac[:native.vectors.size].toarray(), reference_jac.toarray())
    np.testing.assert_array_equal(system.caps[:len(native.caps)], reference.caps)


@pytest.mark.parametrize('side', [-1, 1])
def test_one_sided_boundary_probe_uses_matching_stored_origin_not_decoded_shift(tmp_path, side):
    problem, policy, digest = prepared(tmp_path)
    x = problem.initial.copy()
    x[0] = float(side)
    # Direct native secants isolate the boundary stencil; this endpoint need
    # not be feasible enough to start a coupled contact-improvement solve.
    decoded = problem.worlds(x)
    anchor = {name: value.copy() for name, value in decoded.items()}
    anchor['A'][:, 3, 1, 3] += .00001
    system, jac, meta = linearize(problem, x, step=.001, difference_source='stored',
                                 base_worlds=anchor, difference_scheme='central')
    h = -side * .001
    other = x.copy(); other[0] += h
    a = rows(problem, other, problem.worlds(other)).vectors
    b = rows(problem, x, problem.worlds(x)).vectors
    np.testing.assert_array_equal(jac[:, 0].toarray().ravel(), ((a - b) / h).ravel())
    np.testing.assert_array_equal(system.vectors, rows(problem, x, anchor).vectors)
    assert meta['actual_difference_offsets'][0] == [h]
    assert meta['central_difference_columns'] == problem.size - 1 and meta['one_sided_difference_columns'] == 1


def test_native_stored_secants_differ_from_continuous_while_contact_secants_stay_identical(tmp_path):
    problem, policy, digest = prepared(tmp_path, hold=True)
    x = problem.initial.copy(); worlds = problem.worlds(x)
    stored = StoredNativeCoupledContactModel(problem, policy, digest)
    continuous = CentralCoupledContactModel(problem, policy, digest)
    a, aj, am = stored.linearize(x, worlds, .02, step=.001)
    b, bj, bm = continuous.linearize(x, worlds, .02, step=.001)
    n = am['complete_native_rows']
    np.testing.assert_array_equal(a.vectors, b.vectors)
    np.testing.assert_array_equal(a.caps, b.caps)
    np.testing.assert_array_equal(a.scales, b.scales)
    assert np.max(np.abs((aj[:3 * n] - bj[:3 * n]).data)) > 1e-7
    np.testing.assert_array_equal(aj[3 * n:].toarray(), bj[3 * n:].toarray())


@pytest.mark.parametrize('option, bad', [('step', True), ('step', 0), ('step', .02), ('step', np.nan),
    ('trust', True), ('trust', 0), ('trust', np.inf), ('maximum_native_nonzeros', True),
    ('maximum_native_nonzeros', 0)])
def test_invalid_parameters_reject_before_a_native_probe(tmp_path, monkeypatch, option, bad):
    problem, policy, digest = prepared(tmp_path)
    model = StoredNativeCoupledContactModel(problem, policy, digest)
    def unexpected(*args, **kwargs): raise AssertionError('No probe should run')
    monkeypatch.setattr(problem, 'constraints', unexpected)
    kwargs = dict(step=.001, maximum_native_nonzeros=60_000_000)
    trust = .02
    if option == 'trust': trust = bad
    else: kwargs[option] = bad
    with pytest.raises(ValueError): model.linearize(problem.initial, problem.worlds(problem.initial), trust, **kwargs)


def test_nonzero_resource_limit_rejects_without_partial_model(tmp_path):
    problem, policy, digest = prepared(tmp_path)
    model = StoredNativeCoupledContactModel(problem, policy, digest)
    with pytest.raises(ValueError, match='resource limit'):
        model.linearize(problem.initial, problem.worlds(problem.initial), .02, maximum_native_nonzeros=1)


def test_real_bounded_checked_conic_interface_does_not_approve_a_serialized_candidate(tmp_path):
    from checked_native_proposal import direction
    from coupled_native_contacts import acceptable
    problem, policy, digest = prepared(tmp_path)
    model = StoredNativeCoupledContactModel(problem, policy, digest)
    x = problem.initial.copy(); worlds = problem.worlds(x)
    native = problem.constraints(x, worlds)
    contacts = model.contact.residual(worlds)
    system, jac, meta = model.linearize(x, worlds, .005, step=.001)
    delta, proposal = direction(system, jac, x, problem.lower, problem.upper, .005,
        hard_rows=meta['hard_rows'], phase_seconds=5., maximum_iterations=100, affine_backoffs=5)
    assert proposal['independently_decoded_candidate_required']
    if delta is None:
        checked = proposal['checked_affine_proposal']
        assert checked is None or checked['selected_backoff'] is None
        return
    assert np.all(system.residual(jac, delta)[:meta['hard_rows']] <= 0)
    assert np.max(np.abs(delta)) <= .005
    assert np.all(x + delta >= problem.lower) and np.all(x + delta <= problem.upper)
    path = tmp_path / 'conic-candidate.glb'
    problem.edits.export('A', x + delta, path)
    after, decoded = problem.decoded({'A': path}, x + delta)
    contact_after = model.contact.residual(decoded)
    # No geometry evidence was obtained in this interface test. Even a useful
    # affine proposal with a decoded pass cannot become retained motion here.
    assert not acceptable(native, after, contacts, contact_after, None)
    assert not proposal['checked_affine_proposal']['release_approved']


@pytest.mark.parametrize('fault', ['cap', 'clock', 'tolerance', 'asset', 'infeasible-start', 'nan-start'])
def test_mutated_caps_assets_or_infeasible_start_cannot_bypass_native_protection(tmp_path, fault):
    problem, policy, digest = prepared(tmp_path)
    model = StoredNativeCoupledContactModel(problem, policy, digest)
    x = problem.initial.copy(); worlds = problem.worlds(x)
    if fault == 'cap': problem.caps['A'].caps[0][0, 0] += .001
    if fault == 'clock': problem.uniform[1] += .001
    if fault == 'tolerance': problem.caps['A'].tolerance += .001
    if fault == 'asset':
        path = Path(next(iter(problem.scene.inputs)))
        path.write_bytes(path.read_bytes() + b'changed')
    if fault == 'infeasible-start':
        worlds['A'][:, 3, 1, 3] += .03
    if fault == 'nan-start': worlds['A'][:, 3, 1, 3] = np.nan
    with pytest.raises(ValueError): model.linearize(x, worlds, .02)
