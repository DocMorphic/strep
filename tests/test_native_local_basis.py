"""Local temporal search keeps cumulative limits, frozen bytes and all columns."""
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from native_key_basis import NativeKeyBasis
from native_local_basis import localized_native_basis
from test_native_key_basis import declaration


def parent_case():
    seed = np.zeros((7, 2, 3))
    seed[:, :, 1] = -0.
    seed[5, 0, 0] = .2
    parent = NativeKeyBasis(**declaration(seed_controls=seed))
    point = np.linspace(-.1, .1, parent.size)
    return parent, point


def test_zero_origin_is_exact_even_for_unfrozen_negative_zero_components():
    parent, point = parent_case()
    warm = parent.export_coefficients(point)
    local, report = localized_native_basis(parent, point, 3, 5, 6)
    zero = np.zeros(local.size)
    assert local.coefficients(zero).tobytes() == warm.tobytes()
    assert local.endpoint_map(zero, list(range(7)), jacobian=False)[0].tobytes() == warm.tobytes()
    # Also cover zero components not produced by the parent's matrix addition.
    local._seed.setflags(write=True)
    local._seed[5, 1, 2] = -0.
    local._seed.setflags(write=False)
    assert np.signbit(local.coefficients(zero)[5, 1, 2])
    assert np.signbit(local.endpoint_map(zero, [5])[0][0, 1, 2])
    assert report['zero_coefficients_byte_identical'] and report['original_frozen_controls_byte_identical']
    assert report['exact_native_times_s'] == [.8, 1.8, 2.]


def test_local_support_preserves_all_unchanged_components_and_parent_frozen_keys():
    parent, point = parent_case()
    local, report = localized_native_basis(parent, point, 3, 5, 6)
    value = np.array([.1, 0, -.2, 0, .08, 0])
    baseline = local.coefficients(np.zeros(local.size))
    changed = local.coefficients(value)
    assert changed[:4].tobytes() == baseline[:4].tobytes()
    assert changed[6:].tobytes() == baseline[6:].tobytes()
    assert changed[parent.report['frozen_keys']].tobytes() == parent._seed[parent.report['frozen_keys']].tobytes()
    assert local.parameters == tuple((5, node, axis) for node in [17, 3] for axis in range(3))
    assert local.size == 6 and report['complete_node_axis_population']
    expected = baseline.copy()
    for key in [4, 5]:
        weight = (parent._clock[key] - parent._clock[3]) / (parent._clock[5] - parent._clock[3])
        expected[key] += weight * value.reshape(2, 3)
    np.testing.assert_allclose(changed, expected, rtol=0, atol=3e-17)


def test_every_local_column_matches_endpoint_and_cumulative_ball_differences():
    parent, point = parent_case()
    local, _ = localized_native_basis(parent, point, 3, 5, 6)
    value = np.linspace(-.04, .06, local.size)
    keys = [6, 3, 5, 1, 4]
    _, matrix = local.endpoint_map(value, keys)
    rows, derivative = local.native_chunk(value, 0, 7)
    np.testing.assert_array_equal(rows, 1 - np.sum(local.coefficients(value)**2, axis=2).ravel())
    for column in range(local.size):
        step = np.eye(local.size)[column] * 1e-6
        finite = (local.endpoint_map(value + step, keys, jacobian=False)[0] - local.endpoint_map(value - step, keys, jacobian=False)[0]).ravel() / 2e-6
        np.testing.assert_allclose(matrix[:, column], finite, rtol=0, atol=3e-11)
        finite = (local.native_chunk(value + step, 0, 7, jacobian=False)[0] - local.native_chunk(value - step, 0, 7, jacobian=False)[0]) / 2e-6
        np.testing.assert_allclose(derivative[:, column], finite, rtol=0, atol=1e-10)


def test_warm_start_never_resets_the_cumulative_rotation_ball():
    seed = np.zeros((7, 2, 3))
    seed[5, 0, 0] = .8
    parent = NativeKeyBasis(**declaration(seed_controls=seed))
    local, report = localized_native_basis(parent, np.zeros(parent.size), 3, 5, 6)
    value = np.zeros(local.size)
    value[0] = .3
    assert local.coefficients(value)[5, 0, 0] == 1.1
    assert np.any(local.native_chunk(value, 0, 7)[0] < 0)
    with pytest.raises(ValueError, match='not clipped'):
        local.export_coefficients(value)
    assert report['cumulative_ball_limit'] == 1.


@pytest.mark.parametrize('keys', [(0, 3, 6), (1, 2, 5), (3, 3, 6), (-1, 5, 6), (3, 5, 7), (3, True, 6), (3, 5., 6)])
def test_frozen_or_invalid_declared_window_is_rejected(keys):
    parent, point = parent_case()
    with pytest.raises(ValueError):
        localized_native_basis(parent, point, *keys)


def test_invalid_or_failed_parent_point_cannot_become_a_new_valid_seed():
    parent, _ = parent_case()
    for point in [np.zeros(1), np.full(parent.size, np.nan), np.ones(parent.size, dtype=bool), np.ones(parent.size)]:
        with pytest.raises(ValueError):
            localized_native_basis(parent, point, 3, 5, 6)
    with pytest.raises(ValueError):
        localized_native_basis(object(), [], 3, 5, 6)


def test_snapshots_and_endpoint_budget_remain_complete(monkeypatch):
    parent, point = parent_case()
    local, report = localized_native_basis(parent, point, 3, 5, 6)
    baseline = local.coefficients(np.zeros(local.size))
    point[:] = .9
    report['original_frozen_keys'].clear()
    parent._seed.setflags(write=True)
    parent._seed[:] = 0
    parent._seed.setflags(write=False)
    assert local.coefficients(np.zeros(local.size)).tobytes() == baseline.tobytes()
    local._maximum_bytes = 1
    def forbidden(*args, **kwargs):
        raise AssertionError('Jacobian allocated before complete budget admission')
    monkeypatch.setattr(np, 'kron', forbidden)
    with pytest.raises(ValueError, match='budget'):
        local.endpoint_map(np.zeros(local.size), [5])
    assert local.endpoint_map(np.zeros(local.size), [5], jacobian=False)[1] is None


@pytest.mark.parametrize('mode', ['start', 'native', 'subkey', 'end'])
def test_original_actor_caps_pose_and_saved_baseline_are_preserved(tmp_path, mode):
    from test_native_basis_pose_rows import setup
    from native_key_pose_map import KeyPoseMap
    from native_basis_pose_rows import BasisPoseRows
    from native_key_contact_initializer import encode
    model, mapper, parent, caps, before, point = setup(tmp_path, mode)
    local, report = localized_native_basis(parent, point, 0, 5, len(mapper.clock) - 1)
    warm = local.coefficients(np.zeros(local.size))
    mapped = KeyPoseMap(model, mapper.time_s, warm, list(mapper.pairs))
    after = BasisPoseRows(mapped, local, caps)
    assert mapped.model.actor is mapper.model.actor
    assert mapped.original_quaternions.tobytes() == mapper.original_quaternions.tobytes()
    assert mapped.caps.tobytes() == mapper.caps.tobytes()
    assert mapped.source.tobytes() == mapper.source.tobytes()
    for encoded in [False, True]:
        a = before.evaluate(point, jacobian=False, encoded=encoded)
        b = after.evaluate(np.zeros(local.size), jacobian=False, encoded=encoded)
        np.testing.assert_allclose(a['world'], b['world'], rtol=0, atol=2e-12)
        np.testing.assert_allclose(a['margins'], b['margins'], rtol=0, atol=2e-12)
    assert parent.coefficients(point).tobytes() == warm.tobytes()
    actor = model.actor
    channels = [next(c for c in actor['sampler'].channels if c[:2] == (node, 'rotation')) for node in model.nodes]
    old_path = tmp_path / 'before.glb'
    new_path = tmp_path / 'after.glb'
    encode(actor['rig'], actor['animation_index'], list(model.nodes), channels,
           parent.export_coefficients(point), np.degrees(model.caps), old_path)
    encode(actor['rig'], actor['animation_index'], list(model.nodes), channels,
           local.export_coefficients(np.zeros(local.size)), np.degrees(model.caps), new_path)
    assert old_path.read_bytes() == new_path.read_bytes()
