"""Complete native row attribution; diagnostic comparisons never approve motion."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from test_native_scene_fit import prepare
from test_native_scene_contacts import setup, object_target
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from native_scene_fit import SceneProblem
from native_scene_norms import rows, rate_vectors
from sampled_motion_caps import features
from native_condition_ledger import NativeConditionLedger, compare, RATE_METRICS
from strep import save, sha256


@pytest.mark.parametrize('rotation', [False, True])
def test_all_blocks_match_complete_scalar_vector_population_and_physical_units(tmp_path, rotation):
    _, _, _, _, _, scene, edits = prepare(tmp_path, rotation=rotation)
    problem = SceneProblem(scene, edits)
    ledger = NativeConditionLedger(scene, edits)
    value = edits.initial.copy()
    value.reshape(-1, 3)[:, 0] = .02
    world = problem.worlds(value)
    vector = rows(problem, value, world)
    assert ledger.total_rows == len(problem.constraints(value, world)) == len(vector.caps)
    assert ledger.edit_and_rate_rows == problem.protected_rows
    np.testing.assert_array_equal(ledger.uniform, problem.uniform)
    assert ledger.blocks[0]['start'] == 0 and ledger.blocks[-1]['stop'] == ledger.total_rows
    for left, right in zip(ledger.blocks, ledger.blocks[1:]):
        assert left['stop'] == right['start']
    for block in ledger.blocks:
        for i in {block['start'], block['stop'] - 1, (block['start'] + block['stop'] - 1) // 2}:
            row = ledger.locate(i)
            sample, item = divmod(i - block['start'], len(block['items']))
            assert row['kind'] == block['kind']
            assert row['sample_times_s'] == block['times_s'][sample:sample + block['order'] + 1]
            assert all(row[k] == v for k, v in block['items'][item].items())
    # Independently measure each complete joint rate block with its own units.
    actor = scene.actors['A']
    measured = rate_vectors(features(world['A'][problem.rate_ids], actor['rig'].joints), 1 / 120)
    for (kind, order, unit), actual in zip(RATE_METRICS, measured):
        block = next(b for b in ledger.blocks if b['kind'] == kind)
        assert block['unit'] == unit and block['order'] == order
        np.testing.assert_array_equal(vector.vectors[block['start']:block['stop']], actual.reshape(-1, 3))
        assert ledger.locate(block['start'])['sample_times_s'] == problem.uniform[:order + 1].tolist()


@pytest.mark.parametrize('target', ['world', 'object', 'actor'])
@pytest.mark.parametrize('reduction', ['individual', 'centroid'])
def test_complete_contact_correspondences_and_every_declared_speed_clock(tmp_path, target, reduction):
    _, rig, reader, spec = setup(tmp_path, rotating=True)
    row = spec['contacts'][0]
    if target == 'object':
        object_target(spec, reader, rig)
    row['vertices'] = [[6, 0, 0], [6, 0, 1]]
    row['reduction'] = reduction
    if target == 'actor':
        spec['actors']['B'] = copy.deepcopy(spec['actors']['A'])
        row['target'] = dict(space='actor', actor='B', vertices=copy.deepcopy(row['vertices']), reduction=reduction)
    else:
        # Repeated target points are allowed; every corresponding effector remains distinct.
        row['target']['points_m'] *= 2 if reduction == 'individual' else 1
    path = tmp_path / 'contacts.json'
    save(path, spec)
    scene = SceneContacts(spec, tmp_path)
    declaration = dict(window_s=[0, 2], protected_s=[], knots_s=[0, .5, 1, 1.5, 2],
        tracks=[dict(node=0, path='translation', maximum_change=.02)], maximum_joint_displacement_m=.02)
    permissions = dict(schema='strep-native-scene-edit-v1', contacts_sha256=sha256(path), actors={'A': declaration})
    if target == 'actor':
        # Different actor declaration order must remain intact in the native population.
        permissions['actors'] = dict(B=copy.deepcopy(declaration), A=declaration)
    edits = SceneEdits(permissions, scene, sha256(path))
    problem = SceneProblem(scene, edits)
    ledger = NativeConditionLedger(scene, edits)
    assert ledger.total_rows == len(rows(problem, problem.initial).caps)
    assert ledger.edit_and_rate_rows == problem.protected_rows
    if target == 'actor':
        assert ledger.locate(0)['actor'] == 'B'
    position = next(b for b in ledger.blocks if b['kind'] == 'contact_position')
    point_count = 2 if reduction == 'individual' else 1
    assert len(position['items']) == point_count
    np.testing.assert_array_equal(position['times_s'], problem.rows[0]['times'])
    record = ledger.locate(position['start'] + point_count - 1)
    assert record['contact_id'] == row['id'] and record['target'] == row['target']
    assert record['effector_vertices'] == ([row['vertices'][-1]] if reduction == 'individual' else row['vertices'])
    assert record['coordinate_frame'] == ('object local' if target == 'object' else 'placed world')
    speeds = [b for b in ledger.blocks if b['kind'] == 'contact_relative_speed']
    assert len(speeds) == 12
    for block, population in zip(speeds, problem.rows[0]['populations']):
        assert block['stop'] - block['start'] == (len(population['times_s']) - 1) * point_count
        for index in (block['start'], block['stop'] - 1):
            record = ledger.locate(index)
            sample = record['sample_index']
            assert record['tick_indices'] == population['tick_indices'][sample:sample + 2].tolist()
            assert record['sample_times_s'] == population['times_s'][sample:sample + 2].tolist()
            assert record['population']['id'] == population['id']


def test_missing_speed_population_is_one_unavailable_row_per_clock_not_per_vertex(tmp_path):
    _, spec, path, permissions, _, _, _ = prepare(tmp_path)
    spec['contacts'][0]['interval_s'] = [.853725, .853726]
    spec['contacts'][0]['vertices'] = [[6, 0, 0], [6, 0, 1]]
    spec['contacts'][0]['target']['points_m'] *= 2
    save(path, spec)
    permissions['contacts_sha256'] = sha256(path)
    scene = SceneContacts(spec, tmp_path)
    edits = SceneEdits(permissions, scene, sha256(path))
    problem = SceneProblem(scene, edits)
    ledger = NativeConditionLedger(scene, edits)
    vector = rows(problem, problem.initial)
    missing = [b for b in ledger.blocks if b['kind'] == 'contact_speed_unavailable']
    assert len(missing) == 12 and ledger.total_rows == len(vector.caps)
    for block in missing:
        identity = ledger.locate(block['start'])
        assert block['stop'] == block['start'] + 1
        assert identity['unit'] is None and not identity['available']
        assert identity['sample_times_s'] == block['population']['times_s']
        assert 'point_index' not in identity and 'sample_index' not in identity
        assert vector.caps[block['start']] == -1
    result = compare(ledger, vector.residual(), vector.vectors, vector.caps, vector.scales,
                     baseline_residuals=vector.residual())
    unavailable = [r for r in result['failures'] if r['kind'] == 'contact_speed_unavailable']
    assert len(unavailable) == 12
    assert all(r['unscaled_decoded_excess'] is None for r in unavailable)


def test_touch_has_only_exact_position_samples_and_no_speed_populations(tmp_path):
    _, spec, path, permissions, _, _, _ = prepare(tmp_path)
    spec['contacts'][0].update(mode='touch', interval_s=[.853725, .853725], limits=dict(position_m=.001))
    save(path, spec)
    permissions['contacts_sha256'] = sha256(path)
    scene = SceneContacts(spec, tmp_path)
    edits = SceneEdits(permissions, scene, sha256(path))
    ledger = NativeConditionLedger(scene, edits)
    assert ledger.blocks[-1]['kind'] == 'contact_position'
    assert ledger.locate(ledger.total_rows - 1)['sample_times_s'] == [.853725]
    assert not any('speed' in b['kind'] for b in ledger.blocks)


def test_all_failed_rows_including_one_ulp_and_affine_misses_are_reported_without_slack(tmp_path):
    _, _, _, _, _, scene, edits = prepare(tmp_path)
    ledger = NativeConditionLedger(scene, edits)
    n = ledger.total_rows
    decoded = np.full(n, -1.)
    baseline = decoded.copy()
    vectors = np.zeros((n, 3))
    caps = np.ones(n)
    scales = np.full(n, .1)
    selected = [0, ledger.edit_and_rate_rows - 1, n - 1]
    decoded[selected] = [np.spacing(1.), .01, .03]
    vectors[selected[-1], 0] = 2
    result = compare(ledger, decoded, vectors, caps, scales, baseline_residuals=baseline)
    assert [r['row_index'] for r in result['failures']] == selected
    assert result['decoded_failed_rows'] == 3 and result['affine_false_negative_rows'] == 2
    assert result['failures'][0]['decoded_residual'] == np.spacing(1.)
    assert result['failures'][1]['kind'] == 'joint_angular_acceleration'
    assert result['failures'][1]['unit'] == 'rad/s^2'
    assert len(result['failures'][1]['sample_times_s']) == 3
    assert result['failures'][1]['unscaled_decoded_excess'] == .001
    assert not result['tolerance_added'] and not result['physical_measurements_recomputed']
    assert not result['release_approved'] and not result['geometry_checked']
    np.testing.assert_array_equal(decoded[selected], [np.spacing(1.), .01, .03])


@pytest.mark.parametrize('fault', ['decoded-short', 'baseline-short', 'vector-short', 'vector-width',
    'cap-short', 'scale-short', 'scale-zero', 'scale-negative', 'decoded-nan', 'baseline-inf',
    'vector-nan', 'cap-inf', 'scale-nan', 'norm-overflow', 'excess-overflow'])
def test_incomplete_or_nonfinite_diagnostic_population_rejects(tmp_path, fault):
    _, _, _, _, _, scene, edits = prepare(tmp_path)
    ledger = NativeConditionLedger(scene, edits)
    n = ledger.total_rows
    decoded, baseline, vectors, caps, scales = np.zeros(n), np.zeros(n), np.zeros((n, 3)), np.ones(n), np.ones(n)
    if fault == 'decoded-short': decoded = decoded[:-1]
    if fault == 'baseline-short': baseline = baseline[:-1]
    if fault == 'vector-short': vectors = vectors[:-1]
    if fault == 'vector-width': vectors = vectors[:, :2]
    if fault == 'cap-short': caps = caps[:-1]
    if fault == 'scale-short': scales = scales[:-1]
    if fault == 'scale-zero': scales[0] = 0
    if fault == 'scale-negative': scales[0] = -1
    if fault == 'decoded-nan': decoded[0] = np.nan
    if fault == 'baseline-inf': baseline[0] = np.inf
    if fault == 'vector-nan': vectors[0, 0] = np.nan
    if fault == 'cap-inf': caps[0] = np.inf
    if fault == 'scale-nan': scales[0] = np.nan
    if fault == 'norm-overflow': vectors[0, 0] = 1e308
    if fault == 'excess-overflow': decoded[0] = scales[0] = 1e308
    with np.errstate(over='ignore'), pytest.raises(ValueError):
        compare(ledger, decoded, vectors, caps, scales, baseline_residuals=baseline)


@pytest.mark.parametrize('index', [-1, True, 1.0, None, '0', 10**9])
def test_invalid_row_indices_reject(tmp_path, index):
    _, _, _, _, _, scene, edits = prepare(tmp_path)
    with pytest.raises(ValueError): NativeConditionLedger(scene, edits).locate(index)


def test_manifest_and_returned_identities_cannot_mutate_the_ledger(tmp_path):
    _, _, _, _, _, scene, edits = prepare(tmp_path)
    ledger = NativeConditionLedger(scene, edits)
    original = ledger.manifest()
    record = ledger.locate(ledger.total_rows - 1)
    record['target']['points_m'][0][0] += 100
    other = ledger.manifest()
    other['blocks'][-1]['items'][0]['effector_vertices'][0][0] = 999
    assert ledger.manifest() == original
    assert not original['motion_evaluated'] and not original['derivative_evaluated']


def test_unsorted_skin_joint_and_native_track_order_is_preserved(tmp_path):
    _, _, path, permissions, _, scene, _ = prepare(tmp_path, rotation=True)
    scene.actors['A']['rig'].joints = list(reversed(scene.actors['A']['rig'].joints))
    permissions['actors']['A']['tracks'] = [dict(node=3, path='rotation', maximum_change=5),
                                          dict(node=0, path='translation', maximum_change=.02)]
    edits = SceneEdits(permissions, scene, sha256(path))
    ledger = NativeConditionLedger(scene, edits)
    problem = SceneProblem(scene, edits)
    assert [b['items'][0]['node'] for b in ledger.blocks[:2]] == [3, 0]
    assert ledger.total_rows == len(rows(problem, problem.initial).caps)
    block = next(b for b in ledger.blocks if b['kind'] == 'joint_angular_acceleration')
    for position, node in enumerate(scene.actors['A']['rig'].joints):
        identity = ledger.locate(block['start'] + position)
        assert identity['joint_index'] == position and identity['node'] == node
