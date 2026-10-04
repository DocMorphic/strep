"""Synthetic authored clocks and normal populations, never anatomy evidence."""
from pathlib import Path
import copy
import sys

import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import rigid_contact_preflight as preflight
from strep import save, read, sha256


def fixture():
    spec = dict(objects={'item': {}, 'other': {}}, contacts=[])
    policy = dict(contacts={}, limits=dict(maximum_opposition_error_degrees=15.))
    arrays = {}
    add(spec, policy, arrays, 'left', [[-2**-.5, 2**-.5, 0]], [[0., -1, 0]], [0., 1.])
    add(spec, policy, arrays, 'right', [[2**-.5, 2**-.5, 0]], [[0., -1, 0]], [0., 1.])
    return spec, policy, arrays


def add(spec, policy, arrays, name, sources, targets, times, *, space='object', obj='item', reduction='individual'):
    i = len(spec['contacts']); count = len(sources)
    spec['contacts'].append(dict(id=name, actor=name + '-actor', vertices=[[0, 0, k] for k in range(count)], reduction=reduction,
        target=dict(space=space, object=obj)))
    policy['contacts'][name] = dict(target_normal=dict(space=space, normals=targets))
    for mode in preflight.MODES:
        prefix = f'{mode}_contact_{i}_'
        arrays[prefix + 'times_s'] = np.asarray(times, float)
        arrays[prefix + 'source_normals_world'] = np.tile(sources, (len(times), 1, 1))
        arrays[prefix + 'normal_available'] = np.ones((len(times), count), bool)


def test_overlapping_actor_contacts_share_one_rigid_target_frame():
    spec, policy, arrays = fixture(); result = preflight.analyze(spec, policy, arrays, 'native-authoring')
    assert result['status'] == 'incompatible_fixed_surfaces' and result['incompatible_object_times'] == 2
    assert result['contacts'] == 2 and result['contact_samples'] == result['point_normal_observations'] == 4
    row = result['objects'][0]['worst_conflict']
    assert row['lower_bound_degrees'] == pytest.approx(45.)
    assert [p['contact'] for p in row['witness']['points']] == ['left', 'right']
    assert 'left:0' in preflight.describe(result) and 'right:0' in preflight.describe(result)
    assert not result['source_or_target_edits_ruled_out'] and not result['rotation_feasibility_proven']
    assert not result['quality_approved'] and not result['release_approved']


def test_different_objects_and_disjoint_clocks_do_not_spuriously_constrain_each_other():
    spec, policy, arrays = fixture()
    spec['contacts'][1]['target']['object'] = 'other'
    result = preflight.analyze(spec, policy, arrays, 'native-authoring')
    assert result['status'] == 'not_ruled_out' and len(result['objects']) == 2
    spec['contacts'][1]['target']['object'] = 'item'
    for mode in preflight.MODES:
        arrays[f'{mode}_contact_1_times_s'] += 2
    result = preflight.analyze(spec, policy, arrays, 'native-authoring')
    assert result['status'] == 'not_ruled_out' and result['objects'][0]['samples'] == 4
    assert all(f['active_points'] == 1 for f in result['objects'][0]['frames'])


def test_nearby_times_are_preserved_without_rounding_or_interpolation():
    spec, policy, arrays = fixture()
    for mode in preflight.MODES:
        arrays[f'{mode}_contact_1_times_s'] += 1e-10
    result = preflight.analyze(spec, policy, arrays, 'native-authoring')
    assert result['status'] == 'not_ruled_out' and result['objects'][0]['samples'] == 4
    np.testing.assert_array_equal([f['time_s'] for f in result['objects'][0]['frames']], [0., 1e-10, 1., 1. + 1e-10])


def test_missing_normal_keeps_whole_population_unknown_instead_of_dropping_it():
    spec, policy, arrays = fixture()
    arrays['native-authoring_contact_1_normal_available'][0, 0] = False
    arrays['native-authoring_contact_1_source_normals_world'][0, 0] = 0
    result = preflight.analyze(spec, policy, arrays, 'native-authoring')
    assert result['status'] == 'incompatible_fixed_surfaces' and result['unknown_object_times'] == 1
    frame = result['objects'][0]['frames'][0]
    assert frame['status'] == 'unknown_normal_unavailable' and frame['active_points'] == 2
    assert frame['lower_bound_degrees'] is None and frame['witness'] is None
    arrays['native-authoring_contact_1_normal_available'][:] = False
    result = preflight.analyze(spec, policy, arrays, 'native-authoring')
    assert result['status'] == 'unknown_normal_unavailable' and result['unknown_object_times'] == 2


def test_world_and_partner_targets_stay_explicitly_outside_the_test():
    spec, policy, arrays = fixture()
    spec['contacts'][0]['target']['space'] = 'world'; spec['contacts'][1]['target']['space'] = 'actor'
    result = preflight.analyze(spec, policy, arrays, 'native-authoring')
    assert result['status'] == 'not_applicable' and not result['objects']
    assert [r['target_space'] for r in result['not_applicable_contacts']] == ['world', 'actor']
    assert result['point_normal_observations'] == 4


def test_centroid_keeps_all_source_vertices_as_one_authored_normal_point():
    spec, policy, arrays = fixture()
    spec['contacts'][0]['reduction'] = 'centroid'; spec['contacts'][0]['vertices'].append([0, 0, 10])
    result = preflight.analyze(spec, policy, arrays, 'native-authoring')
    identity = result['objects'][0]['frames'][0]['point_identities'][0]
    assert identity['source_vertices'] == [[0, 0, 0], [0, 0, 10]] and identity['reduction'] == 'centroid'


def test_modes_remain_separate_and_comparison_reserve_does_not_change_authored_limit():
    spec, policy, arrays = fixture()
    arrays['default-import_contact_1_source_normals_world'][:] = arrays['default-import_contact_0_source_normals_world']
    assert preflight.analyze(spec, policy, arrays, 'default-import')['status'] == 'not_ruled_out'
    assert preflight.analyze(spec, policy, arrays, 'native-authoring')['status'] == 'incompatible_fixed_surfaces'
    policy['limits']['maximum_opposition_error_degrees'] = 45.
    result = preflight.analyze(spec, policy, arrays, 'native-authoring')
    assert result['status'] == 'not_ruled_out' and result['authored_maximum_error_degrees'] == 45.


@pytest.mark.parametrize('fault', ['empty', 'mode', 'unordered', 'omitted_point', 'missing_availability', 'nonunit_source', 'nonunit_target', 'policy_omission', 'unknown_object', 'boolean_limit'])
def test_incomplete_or_invalid_inputs_fail_explicitly(fault):
    spec, policy, arrays = fixture(); mode = 'native-authoring'
    if fault == 'empty': spec['contacts'] = []
    if fault == 'mode': mode = 'source'
    if fault == 'unordered': arrays['native-authoring_contact_0_times_s'] = np.array([1., 0.])
    if fault == 'omitted_point': arrays['native-authoring_contact_0_source_normals_world'] = np.zeros((2, 0, 3))
    if fault == 'missing_availability': arrays['native-authoring_contact_0_normal_available'] = np.ones((1, 1), bool)
    if fault == 'nonunit_source': arrays['native-authoring_contact_0_source_normals_world'] *= 2
    if fault == 'nonunit_target': policy['contacts']['left']['target_normal']['normals'][0][1] = -2.
    if fault == 'policy_omission': del policy['contacts']['right']
    if fault == 'unknown_object': spec['contacts'][0]['target']['object'] = 'missing'
    if fault == 'boolean_limit': policy['limits']['maximum_opposition_error_degrees'] = True
    with pytest.raises(ValueError): preflight.analyze(spec, policy, arrays, mode)


def transport_fixture(tmp_path, monkeypatch):
    spec, policy, arrays = fixture(); audit = tmp_path / 'audit'; audit.mkdir(); (audit / 'implementation').mkdir()
    contacts = tmp_path / 'contacts.json'; save(contacts, spec)
    policy.update(schema='strep-native-surface-contact-v1', contacts_sha256=sha256(contacts))
    save(audit / 'surface-policy.json', policy); np.savez_compressed(audit / 'observations.npz', **arrays)
    for name in preflight.AUDIT_METHODS:
        (audit / 'implementation' / name).write_bytes((preflight.ROOT / 'scripts' / name).read_bytes())
    methods = {n: sha256(audit / 'implementation' / n) for n in preflight.AUDIT_METHODS}
    inputs = {str(contacts): sha256(contacts)}
    request = dict(schema=preflight.AUDIT_SCHEMA, inputs_sha256=inputs, contacts_sha256=sha256(contacts), bound_scene=str(tmp_path / 'bound'), implementation_sha256=methods)
    save(audit / 'request.json', request); save(audit / 'pipeline.json', dict(status='complete'))
    save(audit / 'result.json', dict(schema=preflight.AUDIT_SCHEMA, status='complete', implementation_sha256=methods, inputs_sha256=inputs,
        original_selected=True, quality_approved=False, release_approved=False, actual_imported_observations_used=True,
        loaded_skin_weights_normalized=False, original_sampled_scene_conditions_pass=True,
        files_sha256={p.relative_to(audit).as_posix(): sha256(p) for p in audit.rglob('*') if p.is_file() and p.name != 'pipeline.json'}))
    monkeypatch.setattr(preflight, '_bound_scene', lambda path: (dict(contacts=str(contacts)), dict(bounded_scene_conditions_pass=True), object()))
    import native_surface_contact
    monkeypatch.setattr(native_surface_contact, 'policy_for', lambda *args: None)
    return audit


def test_complete_transport_preserves_audit_and_retains_conflict_receipts(tmp_path, monkeypatch):
    audit = transport_fixture(tmp_path, monkeypatch); before = sha256(audit / 'result.json')
    result = preflight.run(audit, tmp_path / 'preflight')
    assert result['status'] == 'incompatible_fixed_surfaces' and not result['engine_launched'] and not result['geometry_queries_rerun']
    assert before == sha256(audit / 'result.json')
    for name, digest in result['files_sha256'].items(): assert sha256(tmp_path / 'preflight' / name) == digest
    with pytest.raises(ValueError, match='Fresh'): preflight.run(audit, tmp_path / 'preflight')
    with pytest.raises(ValueError, match='preserve'): preflight.run(audit, tmp_path / 'bound' / 'preflight')


@pytest.mark.parametrize('fault', ['changed_file', 'extra_file', 'changed_method', 'pending', 'changed_input'])
def test_transport_rejects_changed_incomplete_or_unbound_inputs_before_analysis(tmp_path, monkeypatch, fault):
    audit = transport_fixture(tmp_path, monkeypatch)
    if fault == 'changed_file': (audit / 'observations.npz').write_bytes(b'changed')
    if fault == 'extra_file': (audit / 'unbound.txt').write_text('extra')
    if fault == 'changed_method': (audit / 'implementation' / preflight.AUDIT_METHODS[0]).write_bytes(b'changed')
    if fault == 'pending': save(audit / 'pipeline.json', dict(status='processing'))
    if fault == 'changed_input': (tmp_path / 'contacts.json').write_bytes(b'changed')
    monkeypatch.setattr(preflight, 'analyze', lambda *args: pytest.fail('Invalid transport reached analysis'))
    with pytest.raises(ValueError): preflight.run(audit, tmp_path / 'preflight')
