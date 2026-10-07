"""Complete track groups, budgets and parameter/world behavior on native clips."""
import copy
import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from native_uniform_control_increment import parameter_rows
from native_scene_boundary_edit import BoundarySceneEdits
from native_rotation_storage_repair import StorageAdjustedEdits, authoring_digest, SCHEMA
from test_native_stored_pair_model import fixture


def editor(tmp_path, *, preserve=False):
    problem, _, _, _, _, _ = fixture(tmp_path)
    request = copy.deepcopy(problem.edits.base.request)
    if not preserve:
        request['boundary_keys']['A'] = dict(start='edit', end='edit')
        request['acknowledge_changed_boundary_compatibility'] = True
        request['permissions']['actors']['B'] = copy.deepcopy(request['permissions']['actors']['A'])
        request['boundary_keys']['B'] = dict(start='edit', end='edit')
    return BoundarySceneEdits(request, problem.scene, request['permissions']['contacts_sha256'], rotation_storage_policy='source-scale')


def test_all_tracks_knots_and_components_retain_exact_complete_population_and_offsets(tmp_path):
    base = editor(tmp_path)
    rows, identity = parameter_rows(base)
    assert base.size == 18 and rows.shape == (12, 18)
    assert [(g['actor'], g['node'], g['path']) for g in identity['groups']] == [('A', 0, 'translation'), ('B', 0, 'translation')]
    assert [(g['row_start'], g['row_end']) for g in identity['groups']] == [(0, 6), (6, 12)]
    values = np.arange(base.size, dtype=float)
    expected = []
    for group in identity['groups']:
        ids = np.array(group['controls'])
        expected.extend((values[ids[1:]] - values[ids[0]]).ravel())
    np.testing.assert_array_equal(rows @ values, expected)
    assert np.linalg.matrix_rank(rows) == 12
    assert identity['all_original_controls_grouped_once'] and not identity['quality_approved'] and not identity['release_approved']


def test_equal_translation_parameter_increment_shifts_actual_continuous_native_worlds_consistently(tmp_path):
    base = editor(tmp_path)
    rows, identity = parameter_rows(base)
    step = np.zeros(base.size)
    increments = {'A': np.array([.001, -.002, .003]), 'B': np.array([-.003, .001, .002])}
    for group in identity['groups']:
        step[np.array(group['controls'])] = increments[group['actor']]
    np.testing.assert_array_equal(rows @ step, np.zeros(len(rows)))
    times = np.array([0., .123, .8, 1., 1.7, 2.])
    for name, actor in base.actors.items():
        before = base.worlds(name, base.initial, times, quantized=False)
        after = base.worlds(name, base.initial + step, times, quantized=False)
        amount = actor['tracks'][0]['maximum'] * increments[name]
        parents = base.scene.actors[name]['rig'].parents
        root = actor['tracks'][0]['node']
        affected = []
        for node in range(len(parents)):
            ancestor = node
            while ancestor >= 0 and ancestor != root:
                ancestor = int(parents[ancestor])
            affected.append(ancestor == root)
        assert any(affected) and not all(affected)
        expected = np.zeros_like(after[:, :, :3, 3])
        expected[:, affected] = amount
        # Matrix/interpolation arithmetic and subtraction of metre-scale
        # coordinates introduce a few Float64 rounding errors. Bound those
        # errors from the operands; this is not a motion acceptance tolerance.
        difference = after[:, :, :3, 3] - before[:, :, :3, 3]
        roundoff = 8 * np.finfo(float).eps * np.maximum(
            1., np.abs(after[:, :, :3, 3]) + np.abs(before[:, :, :3, 3]))
        assert np.all(np.abs(difference - expected) <= roundoff)
        np.testing.assert_array_equal(after[:, :, :3, :3], before[:, :, :3, :3])


def test_single_interior_knot_and_storage_wrapper_have_no_invented_rows(tmp_path):
    base = editor(tmp_path, preserve=True)
    policy = dict(schema=SCHEMA, authoring_sha256=authoring_digest(base), maximum_component_steps=1,
                  maximum_corrections=64, acknowledge_storage_adjustment=True)
    wrapped = StorageAdjustedEdits(base, policy, [])
    a, ia = parameter_rows(base, maximum_rows=0)
    b, ib = parameter_rows(wrapped, maximum_rows=0)
    assert a.shape == b.shape == (0, 3) and ia == ib


@pytest.mark.parametrize('fault', ['duplicate', 'omitted', 'outside', 'bool-indices', 'float-indices', 'path',
                                 'row-budget', 'bool-budget', 'negative-budget', 'oversized-budget', 'plain'])
def test_no_truncated_or_malformed_control_groups_return(tmp_path, fault):
    base = editor(tmp_path)
    kwargs = {}
    track = base.actors['A']['tracks'][0]
    if fault == 'duplicate': track['controls'][1, 0] = track['controls'][0, 0]
    elif fault == 'omitted': track['controls'] = track['controls'][:-1]
    elif fault == 'outside': track['controls'][0, 0] = base.size
    elif fault == 'bool-indices': track['controls'] = track['controls'].astype(bool)
    elif fault == 'float-indices': track['controls'] = track['controls'].astype(float)
    elif fault == 'path': track['path'] = 'scale'
    elif fault == 'row-budget': kwargs['maximum_rows'] = 11
    elif fault == 'bool-budget': kwargs['maximum_rows'] = True
    elif fault == 'negative-budget': kwargs['maximum_rows'] = -1
    elif fault == 'oversized-budget': kwargs['maximum_rows'] = 97
    elif fault == 'plain': base = object()
    with pytest.raises(ValueError):
        parameter_rows(base, **kwargs)
