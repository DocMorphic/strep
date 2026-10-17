"""Original rows remain exact; every cached off-grid pose gains joint bands."""
from pathlib import Path
import copy
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from native_evaluated_world_rows import EvaluatedWorldRows
from native_scene_world_rows import SceneWorldRows
from native_scene_world_derivatives import SceneWorldDerivatives
from test_native_scene_world_rows import fixture
from strep import sha256


@pytest.mark.parametrize('rotation', [False, True])
@pytest.mark.parametrize('space', ['world', 'object', 'actor'])
def test_every_old_scalar_is_byte_identical_prefix_and_extra_joint_order_is_exact(tmp_path, rotation, space):
    scene, edits, legacy, caps = fixture(tmp_path, rotation, space)
    original = SceneWorldRows(scene, caps)
    expanded = EvaluatedWorldRows(original)
    assert expanded.report['appended_rows'] > 0
    extra_ids = np.searchsorted(original.times, expanded.additional_times)
    for fraction in [0., .013]:
        worlds = legacy.worlds(edits.initial + fraction)
        actual = expanded.violations(worlds)
        prefix = original.violations(worlds)
        assert actual[:len(prefix)].tobytes() == prefix.tobytes()
        cursor = len(prefix)
        references = original.source_worlds()
        for name in caps:
            joints = scene.actors[name]['rig'].joints
            current = worlds[name][extra_ids]
            reference = references[name][extra_ids]
            limits = original._problem.edits.actors[name]['displacement']
            distances = np.linalg.norm(current[:, joints, :3, 3] - reference[:, joints, :3, 3], axis=2)
            expected = ((distances - limits) / limits).ravel()
            assert actual[cursor:cursor + len(expected)].tobytes() == expected.tobytes()
            cursor += len(expected)
        assert cursor == len(actual) == expanded.report['rows']
    assert expanded.layout[:len(original.layout)] == original.layout
    assert expanded.layout[-1][-1] == expanded.report['rows']


def test_off_grid_counterexample_cannot_hide_between_original_displacement_times(tmp_path):
    scene, _, _, caps = fixture(tmp_path)
    original = SceneWorldRows(scene, caps)
    expanded = EvaluatedWorldRows(original)
    key = next(float(t) for channel in scene.actors['A']['sampler'].channels for t in channel[2]
               if float(t) in expanded.additional_times)
    nearest = original._problem.uniform[np.argmin(abs(original._problem.uniform - key))]
    assert key != nearest
    worlds = original.source_worlds()
    joint = scene.actors['A']['rig'].joints[0]
    limits = original._problem.edits.actors['A']['displacement']
    worlds['A'][np.searchsorted(original.times, key), joint, 0, 3] += limits[0, 0] * 1.00001
    old = original.violations(worlds)
    new = expanded.violations(worlds)
    first, last = original.layout[0][-2:]
    assert np.all(old[first:last] <= 0)
    assert np.count_nonzero(new[len(old):] > 0) == 1
    assert new[:len(old)].tobytes() == old.tobytes()
    assert key in expanded.times and nearest in expanded.times


def test_unequal_caps_stay_joint_major_at_all_extra_times(tmp_path):
    scene, _, _, _ = fixture(tmp_path)
    limits = np.linspace(.01, .03, len(scene.actors['A']['rig'].joints))
    original = SceneWorldRows(scene, {'A': limits})
    expanded = EvaluatedWorldRows(original)
    worlds = expanded.source_worlds()
    worlds['A'][:, :, 0, 3] += .004
    result = expanded.violations(worlds)[original.report['rows']:]
    expected = np.repeat((.004 - limits) / limits, len(expanded.additional_times))
    np.testing.assert_allclose(result, expected, rtol=0, atol=1e-13)


def test_snapshot_and_public_outputs_cannot_mutate_original_caps_or_clock(tmp_path):
    scene, _, _, caps = fixture(tmp_path)
    original = SceneWorldRows(scene, caps)
    expanded = EvaluatedWorldRows(original)
    before = expanded.violations(expanded.source_worlds())
    original._problem.edits.actors['A']['displacement'][:] = 9
    original._problem.source_world['A'][:] = 0
    expanded.times[:] = 0
    expanded.additional_times[:] = 0
    expanded.report['rows'] = 0
    np.testing.assert_array_equal(expanded.violations(expanded.source_worlds()), before)
    assert not expanded.report['derivatives_included']
    assert not expanded.report['continuous_time_coverage']
    assert not expanded.report['quality_approved'] and expanded.report['original_selected']


@pytest.mark.parametrize('fault', ['missing', 'extra', 'shape', 'nan', 'bool', 'unmodified'])
def test_complete_world_populations_and_unchanged_actors_are_mandatory(tmp_path, fault):
    scene, _, _, caps = fixture(tmp_path, space='actor')
    expanded = EvaluatedWorldRows(SceneWorldRows(scene, caps))
    worlds = expanded.source_worlds()
    if fault == 'missing':
        worlds.pop('B')
    elif fault == 'extra':
        worlds['C'] = worlds['A']
    elif fault == 'shape':
        worlds['A'] = worlds['A'][:-1]
    elif fault == 'nan':
        worlds['A'][0, 0, 0, 0] = np.nan
    elif fault == 'bool':
        worlds['A'] = np.zeros(worlds['A'].shape, dtype=bool)
    else:
        worlds['B'][:, :, 0, 3] += .001
    with pytest.raises(ValueError):
        expanded.violations(worlds)


@pytest.mark.parametrize('budget', [0, True, 2000001, '100', 1])
def test_budget_rejected_before_copying_or_sampling(tmp_path, monkeypatch, budget):
    scene, _, _, caps = fixture(tmp_path)
    original = SceneWorldRows(scene, caps)
    def forbidden(*args, **kwargs):
        raise AssertionError('Budget must be admitted before allocating the snapshot')
    monkeypatch.setattr(copy, 'deepcopy', forbidden)
    with pytest.raises(ValueError):
        EvaluatedWorldRows(original, maximum_rows=budget)


def test_exact_row_budget_passes_and_old_derivative_operator_explicitly_rejects(tmp_path):
    scene, _, _, caps = fixture(tmp_path)
    original = SceneWorldRows(scene, caps)
    expanded = EvaluatedWorldRows(original)
    assert EvaluatedWorldRows(original, maximum_rows=expanded.report['rows']).report == expanded.report
    with pytest.raises(ValueError):
        SceneWorldDerivatives(expanded, 3)
    with pytest.raises(ValueError):
        EvaluatedWorldRows(expanded)


def test_saved_file_matches_direct_expanded_sampling(tmp_path):
    from rig_asset import RigAsset
    from native_support_clock import NativeSupportSampler
    scene, edits, _, caps = fixture(tmp_path, True, 'object')
    expanded = EvaluatedWorldRows(SceneWorldRows(scene, caps))
    path = tmp_path / 'candidate.glb'
    edits.export('A', edits.initial + .013, path)
    rig = RigAsset.load(path)
    reader = NativeSupportSampler(rig.document, rig.binary, 0)
    worlds = expanded.source_worlds()
    worlds['A'] = np.array([reader.sample(float(t)) for t in expanded.times])
    result, report = expanded.evaluate_files({'A': dict(path=str(path), sha256=sha256(path), animation_index=0)})
    assert result.tobytes() == expanded.violations(worlds).tobytes()
    assert report['appended_rows'] == expanded.report['appended_rows']
    assert report['world_conditions_pass'] == bool(np.all(result <= 0))
    assert not report['quality_approved'] and not report['release_approved']


@pytest.mark.parametrize('fault', ['digest', 'index', 'missing', 'extra', 'static', 'new-clock'])
def test_saved_binding_static_payload_and_complete_key_clock_remain_required(tmp_path, fault):
    from gltf_tools import append_accessor, write_glb
    from rig_asset import RigAsset
    from native_support_clock import NativeSupportSampler
    scene, edits, _, caps = fixture(tmp_path)
    expanded = EvaluatedWorldRows(SceneWorldRows(scene, caps))
    path = tmp_path / 'candidate.glb'
    edits.export('A', edits.initial, path)
    entry = dict(path=str(path), sha256=sha256(path), animation_index=0)
    files = {'A': entry}
    if fault == 'digest':
        entry['sha256'] = '0' * 64
    elif fault == 'index':
        entry['animation_index'] = True
    elif fault == 'missing':
        files = {}
    elif fault == 'extra':
        entry['skip_checks'] = True
    else:
        rig = RigAsset.load(path)
        if fault == 'static':
            rig.document['nodes'][0]['name'] = 'changed-static-node'
        else:
            reader = NativeSupportSampler(rig.document, rig.binary, 0)
            clock = reader.channels[0][2].astype(float)
            clock[1] = float(np.float32(.21739))
            assert clock[1] not in expanded.times
            data = bytearray(rig.binary)
            index = append_accessor(rig.document, data, clock, 'SCALAR')
            rig.document['animations'][0]['samplers'][0]['input'] = index
            rig.binary = bytes(data)
        write_glb(path, rig.document, rig.binary)
        entry['sha256'] = sha256(path)
    with pytest.raises(ValueError):
        expanded.evaluate_files(files)


def test_mutated_original_file_cannot_reuse_old_world_cache(tmp_path):
    scene, _, _, caps = fixture(tmp_path)
    expanded = EvaluatedWorldRows(SceneWorldRows(scene, caps))
    worlds = expanded.source_worlds()
    path = Path(next(iter(scene.inputs)))
    path.write_bytes(path.read_bytes() + b'x')
    for operation in [expanded.source_worlds, lambda: expanded.violations(worlds)]:
        with pytest.raises(ValueError):
            operation()
