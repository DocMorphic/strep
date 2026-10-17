"""Complete exact-time guidance, unchanged original groups and full columns."""
from pathlib import Path
import hashlib
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from native_evaluated_world_rows import EvaluatedWorldRows
from native_evaluated_world_derivatives import EvaluatedWorldDerivatives
from test_native_scene_world_derivatives import prepare


@pytest.mark.parametrize('space', ['world', 'object', 'actor'])
@pytest.mark.parametrize('centroid', [False, True])
def test_original_rows_groups_and_gradients_remain_exact_and_extra_directions_match(tmp_path, space, centroid):
    _, oracle, old, callbacks, _ = prepare(tmp_path, space, centroid)
    expanded = EvaluatedWorldRows(oracle)
    model = EvaluatedWorldDerivatives(expanded, 4, temperature=.03)
    point = np.array([.012, -.018, .027, .008])
    before = old.evaluate(callbacks(point))
    result = model.evaluate(callbacks(point))
    rows = oracle.report['rows']
    groups = old.report['groups']
    assert result['original_violations'][:rows].tobytes() == before['original_violations'].tobytes()
    for key in ['exact_margins', 'smooth_margins', 'smooth_jacobian', 'maximum_smoothing_error']:
        assert result[key][:groups].tobytes() == before[key].tobytes()
    assert result['report']['groups'][:groups] == before['report']['groups']
    assert model.partition[:groups] == old.partition
    assert sum(group['rows'] for group in model.partition) == expanded.report['rows']
    assert model.report['appended_rows'] == expanded.report['appended_rows'] > 0
    for group, receipt in zip(model.partition, result['report']['groups']):
        values = result['original_violations'][group['first']:group['last']]
        assert receipt['values_sha256'] == hashlib.sha256(values.astype('<f8').tobytes()).hexdigest()
        assert receipt['rows_seen'] == receipt['rows'] == len(values)
        assert result['exact_margins'][int(group['id'][1:])] == -values.max()
    assert result['report']['original_scalar_conditions_pass'] == bool(np.all(result['original_violations'] <= 0))
    for seed in [13, 31]:
        direction = np.random.default_rng(seed).normal(size=4)
        direction /= np.linalg.norm(direction)
        step = 2e-6
        plus = model.values(callbacks(point + step * direction))
        minus = model.values(callbacks(point - step * direction))
        finite = (plus['smooth_margins'][groups:] - minus['smooth_margins'][groups:]) / (2 * step)
        np.testing.assert_allclose(result['smooth_jacobian'][groups:] @ direction, finite, rtol=2e-5, atol=2e-5)
    assert result['composition']['peak_world_cache_bytes'] <= model.report['maximum_world_cache_bytes']
    assert not result['composition']['quality_approved'] and not result['composition']['release_approved']


def test_every_extra_time_for_every_edited_actor_requests_all_derivatives(tmp_path):
    _, oracle, _, make, _ = prepare(tmp_path, 'actor')
    expanded = EvaluatedWorldRows(oracle)
    model = EvaluatedWorldDerivatives(expanded, 4)
    callbacks = make(np.array([.01, .02, -.01, .003]))
    seen = {name: set() for name in callbacks}
    wrapped = {}
    for name, callback in callbacks.items():
        def sample(time, derivatives, name=name, callback=callback):
            if derivatives:
                seen[name].add(time)
            return callback(time, derivatives)
        wrapped[name] = sample
    result = model.evaluate(wrapped)
    assert all(set(expanded.additional_times) <= times for times in seen.values())
    assert result['composition']['additional_displacement_times'] == len(expanded.additional_times)


@pytest.mark.parametrize('fault', ['pose', 'jacobian', 'nan', 'homogeneous'])
def test_callback_corruption_only_at_an_extra_time_is_rejected(tmp_path, fault):
    _, oracle, _, make, _ = prepare(tmp_path)
    expanded = EvaluatedWorldRows(oracle)
    model = EvaluatedWorldDerivatives(expanded, 4)
    callbacks = make(np.array([.01, .02, -.01, .003]))
    original = callbacks['A']
    target = float(expanded.additional_times[-1])
    reached = []
    def bad(time, derivatives):
        world, matrix = original(time, derivatives)
        if derivatives and time == target:
            reached.append(True)
            if fault == 'pose':
                world[0, 0, 3] += .001
            elif fault == 'jacobian':
                matrix = None
            elif fault == 'nan':
                matrix[0, 0, 0, 0] = np.nan
            else:
                matrix[0, 3, 0, 0] = .001
        return world, matrix
    with pytest.raises(ValueError):
        model.evaluate({'A': bad})
    assert reached


def test_minimum_cache_retains_exact_rows_and_all_group_gradients(tmp_path):
    _, oracle, _, callbacks, base = prepare(tmp_path, 'actor')
    expanded = EvaluatedWorldRows(oracle)
    budget = 3 * max(world[0].nbytes * 5 for world in base.values())
    regular = EvaluatedWorldDerivatives(expanded, 4, temperature=.03)
    small = EvaluatedWorldDerivatives(expanded, 4, temperature=.03, maximum_world_cache_bytes=budget)
    point = np.array([.01, .02, -.01, .003])
    expected = regular.evaluate(callbacks(point))
    actual = small.evaluate(callbacks(point))
    assert actual['original_violations'].tobytes() == expected['original_violations'].tobytes()
    assert actual['smooth_jacobian'].tobytes() == expected['smooth_jacobian'].tobytes()
    assert actual['composition']['peak_world_cache_bytes'] <= budget


def test_full_768_columns_are_retained_with_declared_zeros(tmp_path):
    _, oracle, _, make, _ = prepare(tmp_path)
    expanded = EvaluatedWorldRows(oracle)
    model = EvaluatedWorldDerivatives(expanded, 768)
    callback = make(np.array([.01, .02, -.01, .003]))['A']
    def full(time, derivatives):
        world, matrix = callback(time, derivatives)
        if derivatives:
            complete = np.zeros(world.shape + (768,))
            complete[..., :4] = matrix
            matrix = complete
        return world, matrix
    result = model.evaluate({'A': full})
    assert result['smooth_jacobian'].shape == (model.report['groups'], 768)
    assert not np.any(result['smooth_jacobian'][:, 4:])
    assert np.any(result['smooth_jacobian'][model.report['original_groups']:, :4])


@pytest.mark.parametrize('settings', [dict(columns=True), dict(columns=0), dict(columns=769),
    dict(maximum_jacobian_bytes=1), dict(maximum_world_cache_bytes=1),
    dict(maximum_contact_cache_bytes=1), dict(maximum_skin_bytes=1), dict(temperature=0)])
def test_complete_budget_admission_rejects(tmp_path, settings):
    _, oracle, _, _, _ = prepare(tmp_path)
    arguments = dict(columns=4)
    arguments.update(settings)
    with pytest.raises(ValueError):
        EvaluatedWorldDerivatives(EvaluatedWorldRows(oracle), **arguments)


def test_source_mutation_rejected_and_value_only_never_invents_derivatives(tmp_path):
    scene, oracle, _, make, _ = prepare(tmp_path)
    expanded = EvaluatedWorldRows(oracle)
    model = EvaluatedWorldDerivatives(expanded, 4)
    original = make(np.array([.01, .02, -.01, .003]))['A']
    called = []
    def value(time, derivatives):
        called.append(derivatives)
        assert not derivatives
        return original(time, derivatives)
    result = model.values({'A': value})
    assert called and not any(called) and result['smooth_jacobian'] is None
    assert result['report']['total_original_rows'] == expanded.report['rows']
    path = Path(next(iter(scene.inputs)))
    path.write_bytes(path.read_bytes() + b'x')
    called.clear()
    for operation in [model.values, model.evaluate]:
        with pytest.raises(ValueError):
            operation({'A': value})
    assert not called
