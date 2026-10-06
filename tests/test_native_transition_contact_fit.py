"""Input/cap/probe integrity checks; full numerical pipeline is a separate study."""
import copy
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import native_transition_contact_fit as fitting
from native_contact_reserve import SCHEMA as RESERVE_SCHEMA
from strep import save, sha256


@pytest.fixture
def bound_request(tmp_path, monkeypatch):
    folder = tmp_path / 'source'
    save(folder / 'scene.json', dict(contacts=[]))
    recipe = tmp_path / 'recipe.json'
    save(recipe, dict(schema='test-only'))
    row = dict(entry=dict(authored=dict(id='touch', limits=dict(position_m=.001))))
    def controls(value):
        value = np.asarray(value, float)
        if value.shape != (2,) or not np.isfinite(value).all():
            raise ValueError('Finite matching controls')
        return value
    motion = SimpleNamespace(rows=[row], initial=np.zeros(2), lower=-np.ones(2), upper=np.ones(2),
                             edits=SimpleNamespace(controls=controls))
    problem = SimpleNamespace(folder=folder, motion=motion)
    monkeypatch.setattr(fitting.correction, 'Problem', lambda recipe, base: problem)
    value = dict(schema=fitting.SCHEMA, recipe=dict(path='recipe.json', sha256=sha256(recipe)),
                 reserve=dict(schema=RESERVE_SCHEMA, contacts_sha256=sha256(folder / 'scene.json'), reserves_m={'touch': .0001}),
                 seed=None)
    return tmp_path, value, problem


def test_preparation_retains_original_acceptance_and_uses_a_bound_copy(bound_request):
    root, value, problem = bound_request
    original = copy.deepcopy(problem.motion.rows)
    actual, guide, binding, recipe, seed = fitting.prepare(value, root)
    assert actual is problem and seed is None and recipe == root / 'recipe.json'
    assert problem.motion.rows == original
    assert guide.rows[0]['entry']['authored']['limits']['position_m'] == .0009
    assert binding['original_acceptance_limits_unchanged'] and not binding['release_approved']


def test_seed_file_is_bound_and_copied_without_claiming_continuation(bound_request):
    root, value, _ = bound_request
    save(root / 'probe.json', dict(controls=[.1, -.2], label='prior-epoch'))
    value['seed'] = dict(path='probe.json', sha256=sha256(root / 'probe.json'))
    _, guide, _, _, seed = fitting.prepare(value, root)
    assert seed == root / 'probe.json' and guide.initial.tolist() == [.1, -.2]
    save(seed, dict(controls=[0., 0.]))
    with pytest.raises(ValueError, match='changed'):
        fitting.prepare(value, root)


@pytest.mark.parametrize('controls', [[True, 0.], ['.1', 0.], [float('nan'), 0.], [2., 0.], [.1], {'x': .1}])
def test_invalid_seed_controls_cannot_initialize_a_new_epoch(bound_request, controls):
    root, value, _ = bound_request
    path = root / 'seed.json'
    # NaN case exercises explicit parser validation, not strep.save's JSON guard.
    import json
    path.write_text(json.dumps(dict(controls=controls)), encoding='utf-8')
    value['seed'] = dict(path='seed.json', sha256=sha256(path))
    with pytest.raises(ValueError):
        fitting.prepare(value, root)


@pytest.mark.parametrize('fault', ['schema', 'extra', 'digest', 'unknown-contact', 'zero-reserve'])
def test_invalid_request_rejects_without_output_creation(bound_request, fault):
    root, value, _ = bound_request
    if fault == 'schema': value['schema'] = 'wrong'
    elif fault == 'extra': value['approve'] = True
    elif fault == 'digest': value['reserve']['contacts_sha256'] = '0' * 64
    elif fault == 'unknown-contact': value['reserve']['reserves_m'] = {'missing': .0001}
    else: value['reserve']['reserves_m']['touch'] = 0
    with pytest.raises(ValueError):
        fitting.prepare(value, root)
    assert not (root / 'candidate').exists()


@pytest.mark.parametrize('fault', ['digest', 'extra', 'path', 'missing'])
def test_file_bindings_require_exact_bytes_and_fields(tmp_path, fault):
    path = tmp_path / 'input.json'
    save(path, dict(value=1))
    binding = dict(path='input.json', sha256=sha256(path))
    if fault == 'digest': binding['sha256'] = 'x' * 64
    elif fault == 'extra': binding['mtime'] = 1
    elif fault == 'path': binding['path'] = ''
    else: path.unlink()
    with pytest.raises(ValueError):
        fitting.bound_file(binding, tmp_path)


def test_complete_file_tree_detects_added_removed_and_changed_bytes(tmp_path):
    save(tmp_path / 'a.json', dict(value=1))
    baseline = fitting.file_tree(tmp_path)
    save(tmp_path / 'nested/b.json', dict(value=2))
    assert set(fitting.file_tree(tmp_path)) == {'a.json', 'nested/b.json'}
    (tmp_path / 'nested/b.json').unlink()
    assert fitting.file_tree(tmp_path) == baseline
    save(tmp_path / 'a.json', dict(value=3))
    assert fitting.file_tree(tmp_path) != baseline


def test_missing_artifact_directory_is_not_an_empty_valid_snapshot(tmp_path):
    with pytest.raises(ValueError, match='directory'):
        fitting.file_tree(tmp_path / 'missing')


@pytest.mark.parametrize('fault', ['population', 'dtype', 'shape', 'value'])
def test_cap_replay_requires_complete_typed_byte_equal_arrays(tmp_path, fault):
    expected = {'times_s': np.array([0., .5, 1.]), 'A_metric_0': np.array([1., 2.])}
    path = tmp_path / 'caps.npz'
    np.savez(path, **expected)
    fitting.arrays_equal(path, expected)
    forged = {k: a.copy() for k, a in expected.items()}
    if fault == 'population': forged.pop('A_metric_0')
    elif fault == 'dtype': forged['A_metric_0'] = forged['A_metric_0'].astype(np.float32)
    elif fault == 'shape': forged['A_metric_0'] = forged['A_metric_0'][:, None]
    else: forged['A_metric_0'][0] += .1
    np.savez(path, **forged)
    with pytest.raises(ValueError, match='arrays changed'):
        fitting.arrays_equal(path, expected)


def test_probe_rejects_control_bound_violation_before_export(bound_request, tmp_path):
    _, _, problem = bound_request
    problem.edits = problem.motion.edits
    with pytest.raises(ValueError, match='control bounds'):
        fitting.probe(problem, problem.motion, [2., 0.], tmp_path / 'probe', 'start', write=True)
    assert not (tmp_path / 'probe').exists()
