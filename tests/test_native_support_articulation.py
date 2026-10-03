"""Analytical local tracks, exact full-weight patch evidence and binding guards."""
from pathlib import Path
import copy
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from test_native_support import fixture
from native_support_articulation import local_track, inspect, run
from native_support_clock import NativeSupportSampler
from native_support_spec import validate
from rig_asset import RigAsset
from gltf_tools import append_accessor, write_glb
from strep import sha256, save, read


def test_analytical_local_slerp_preserves_exact_endpoints_and_native_speed_clock():
    clock = np.array([0., .5, 1., 1.5, 2.], dtype=np.float32)
    q = Rotation.from_euler('z', [0, 5, 10, 15, 20], degrees=True).as_quat().astype(np.float32)
    result = local_track(clock, q, [.6, 1.4])
    assert result['stance_angle_sample_times_s'] == [.6, 1., 1.4]
    assert result['native_segments_overlapping_stance'] == 2
    assert result['maximum_sampled_local_angle_from_stance_start_degrees'] == pytest.approx(8, abs=1e-6)
    assert result['maximum_overlapping_native_local_speed_rad_s'] == pytest.approx(np.deg2rad(10), abs=1e-8)
    q[1::2] *= -1
    signed = local_track(clock, q, [.6, 1.4])
    assert signed == result


def test_nearly_coincident_boundary_never_becomes_a_velocity_segment():
    clock = np.array([0., .5, 1., 1.5, 2.], dtype=np.float32)
    q = Rotation.from_euler('x', [0, 5, 10, 15, 20], degrees=True).as_quat().astype(np.float32)
    result = local_track(clock, q, [np.nextafter(1., 0), 1.5])
    assert result['stance_angle_sample_times_s'][0] != result['stance_angle_sample_times_s'][1]
    assert result['maximum_overlapping_native_local_speed_rad_s'] < .175
    assert result['native_segments_overlapping_stance'] == 2


@pytest.mark.parametrize('fault', ['duplicate', 'reverse', 'shape', 'nan', 'zero', 'outside', 'empty'])
def test_invalid_rotation_tracks_are_rejected(fault):
    clock = np.array([0., .5, 1.])
    q = np.tile([0., 0., 0., 1.], (3, 1)); stance = [.25, .75]
    if fault == 'duplicate': clock[1] = 0
    if fault == 'reverse': clock = clock[::-1]
    if fault == 'shape': q = q[:, :3]
    if fault == 'nan': q[1, 0] = np.nan
    if fault == 'zero': q[1] = 0
    if fault == 'outside': stance = [-.1, .75]
    if fault == 'empty': stance = [.5, .5]
    with pytest.raises(ValueError): local_track(clock, q, stance)


def test_shorter_track_reports_source_clamps_without_extending_or_retiming_keys():
    clock = np.array([.5, 1.], dtype=np.float32)
    q = Rotation.from_euler('x', [5, 10], degrees=True).as_quat().astype(np.float32)
    result = local_track(clock, q, [.25, 1.5])
    assert result['native_clock_bounds_s'] == [.5, 1.]
    assert result['stance_angle_sample_times_s'] == [.25, .5, 1., 1.5]
    assert result['clamped_before_first_key_s'] == .25
    assert result['clamped_after_last_key_s'] == .5
    assert result['maximum_sampled_local_angle_from_stance_start_degrees'] == pytest.approx(5, abs=1e-6)
    assert result['maximum_overlapping_native_local_speed_rad_s'] == pytest.approx(np.deg2rad(10), abs=1e-8)


def test_single_key_track_is_a_real_constant_channel_with_no_speed_intervals():
    result = local_track(np.array([.5], dtype=np.float32), np.array([[0., 0., 0., 1.]]), [.25, 1.5])
    assert result['native_segments_overlapping_stance'] == 0
    assert result['maximum_overlapping_native_local_speed_rad_s'] == 0
    assert result['maximum_sampled_local_angle_from_stance_start_degrees'] == 0
    assert result['clamped_before_first_key_s'] == .25 and result['clamped_after_last_key_s'] == 1


def toe_fixture(tmp_path, *, animated=True, mixed=False):
    source, rig, reader, spec = fixture(tmp_path)
    doc = copy.deepcopy(rig.document); data = bytearray(rig.binary)
    primitive = doc['meshes'][0]['primitives'][0]
    # Repeated toe slots and zero-weight unrelated slots are deliberate.
    slots = np.array([[4, 4, 0, 0], [4, 3, 0, 0], [3, 4, 5, 0]], dtype='<u2')
    item = doc['accessors'][primitive['attributes']['JOINTS_0']]
    view = doc['bufferViews'][item['bufferView']]; start = view['byteOffset'] + item.get('byteOffset', 0)
    data[start:start + slots.nbytes] = slots.tobytes()
    weights = [[.25, .75, 0, 0], [.75, .25, 0, 0], [1., 0, 0, 0]]
    if mixed:
        weights = [[.9, 0, .1, 0], [.75, 0, .25, 0], [.9, 0, .1, 0]]
    primitive['attributes']['WEIGHTS_0'] = append_accessor(doc, data, weights, 'VEC4')
    if animated:
        animation = doc['animations'][0]
        values = Rotation.from_euler('z', np.linspace(0, 10, 11), degrees=True).as_quat()
        index = len(animation['samplers'])
        animation['samplers'].append(dict(input=animation['samplers'][0]['input'],
            output=append_accessor(doc, data, values, 'VEC4'), interpolation='LINEAR'))
        animation['channels'].append(dict(sampler=index, target=dict(node=4, path='rotation')))
    write_glb(source, doc, data)
    spec['glb_sha256'] = sha256(source)
    rig = RigAsset.load(source); reader = NativeSupportSampler(rig.document, rig.binary, 0)
    _, rows = validate(spec, rig, reader, sha256(source))
    return source, rig, reader, spec, rows


def test_repeated_positive_weights_report_frozen_articulation_without_permission_changes(tmp_path):
    source, rig, reader, spec, rows = toe_fixture(tmp_path)
    before = sha256(source)
    result = inspect(rig, reader, rows); support = result['supports'][0]
    by_node = {i['node']: i for i in support['foot_descendants']}
    assert support['fixed_patch_vertices'] == support['fully_foot_bound_region_vertices'] == 3
    assert support['patch_vertex_references'] == [[6, 0, 0], [6, 0, 1], [6, 0, 2]]
    assert support['protected_patch_weight_by_vertex'] == [1., .75, 0.]
    assert by_node[4]['patch_weight_by_vertex'] == [1., .75, 0.]
    assert by_node[3]['patch_weight_by_vertex'] == [0., .25, 1.]
    assert by_node[4]['patch_vertices_with_positive_weight'] == 2
    assert not by_node[4]['editable_under_original_leg_contract']
    assert by_node[3]['editable_under_original_leg_contract']
    assert by_node[4]['local_rotation']['maximum_sampled_local_angle_from_stance_start_degrees'] > 1.9
    assert not result['permissions_changed'] and not result['correction_generated']
    assert all(result[k] is False for k in ('quality_approved', 'training_admitted', 'release_approved'))
    assert sha256(source) == before


def test_static_descendant_has_weights_but_no_fabricated_rotation_track(tmp_path):
    _, rig, reader, _, rows = toe_fixture(tmp_path, animated=False)
    leaf = next(i for i in inspect(rig, reader, rows)['supports'][0]['foot_descendants'] if i['node'] == 4)
    assert leaf['patch_vertices_with_positive_weight'] == 2
    assert not leaf['rotation_channel'] and leaf['local_rotation'] is None


def test_report_identifies_loaded_weight_normalization_instead_of_claiming_stored_payload(tmp_path):
    source, rig, reader, spec, rows = toe_fixture(tmp_path)
    doc = copy.deepcopy(rig.document); data = bytearray(rig.binary)
    primitive = doc['meshes'][0]['primitives'][0]
    primitive['attributes']['WEIGHTS_0'] = append_accessor(doc, data,
        np.array([[.25, .75, 0, 0], [.75, .25, 0, 0], [1., 0, 0, 0]]) * 1.0005, 'VEC4')
    write_glb(source, doc, data); rig = RigAsset.load(source)
    reader = NativeSupportSampler(rig.document, rig.binary, 0)
    result = inspect(rig, reader, rows)
    assert 'RigAsset validates then normalizes' in result['skin_weight_semantics']
    support = result['supports'][0]
    np.testing.assert_allclose(support['protected_patch_weight_by_vertex'], [1., .75, 0.], atol=2e-8, rtol=0)


def test_fully_bound_region_guard_keeps_mixed_soles_unsupported(tmp_path):
    _, rig, reader, _, rows = toe_fixture(tmp_path, mixed=True)
    with pytest.raises(ValueError, match='fully foot-bound'): inspect(rig, reader, rows)


def test_actual_report_binds_source_draft_and_method_archives_and_rejects_reuse(tmp_path):
    source, rig, reader, spec, rows = toe_fixture(tmp_path)
    draft = tmp_path / 'draft.json'; save(draft, spec)
    output = tmp_path / 'inspection'; result = run(source, draft, output)
    assert read(output / 'pipeline.json')['status'] == 'complete'
    assert result['inputs_sha256'] == {str(source.resolve()): sha256(source), str(draft.resolve()): sha256(draft)}
    assert result == read(output / 'result.json')
    for path, digest in result['implementation_sha256'].items():
        assert sha256(output / 'implementation' / Path(path).name) == digest == sha256(path)
    with pytest.raises(ValueError, match='fresh'): run(source, draft, output)
    spec['glb_sha256'] = '0' * 64; save(draft, spec)
    missing = tmp_path / 'wrong-source'
    with pytest.raises(ValueError, match='belongs'): run(source, draft, missing)
    assert not missing.exists()


def test_input_change_during_inspection_fails_instead_of_saving_success(tmp_path, monkeypatch):
    source, rig, reader, spec, rows = toe_fixture(tmp_path)
    draft = tmp_path / 'draft.json'; save(draft, spec)
    import native_support_articulation as module
    original = module.inspect
    def changed(*args):
        result = original(*args)
        source.write_bytes(source.read_bytes() + b'changed')
        return result
    monkeypatch.setattr(module, 'inspect', changed)
    output = tmp_path / 'changed'
    with pytest.raises(ValueError, match='changed'): run(source, draft, output)
    assert read(output / 'pipeline.json')['status'] == 'failed'
    assert not (output / 'result.json').exists()
