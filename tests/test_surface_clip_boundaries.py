from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import surface_clip_job as jobs
from surface_clip import SurfaceClip
from surface_pose_key_export import replace_keys
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from strep import read, sha256
from test_surface_clip_job import fixture, config, attempt


def key_values(path, index):
    rig = RigAsset.load(path); reader = NativeSupportSampler(rig.document, rig.binary, 0)
    return [c[3][index].tobytes() for c in reader.channels]


def test_middle_contact_repair_preserves_nonzero_initial_end_exactly(tmp_path):
    source, rig, reader, _ = fixture(tmp_path, 3)
    initial = tmp_path/'initial.glb'; x = np.zeros(12); x[1] = .01
    replace_keys(rig, rig, root=0, rotations=[1,2,3], edits={2:x}, preserve_through=1, output=initial)
    cfg = config(); cfg['clip']['limits']['contact_error_m'] = .002
    t = float(reader.channels[0][2][1]); target = rig.vertices(reader.sample(t))[0].copy(); target[1] += .025
    cfg['clip']['contacts'] = [dict(vertex=0, target_m=target.tolist(), start_time_s=t, end_time_s=t)]
    folder = jobs.prepare(tmp_path/'job', source, initial, **cfg)
    result = attempt(folder)
    assert result['status'] == 'complete_numerical_candidate' and result['end_policy'] == 'preserve'
    assert result['transition_review_required']  # Fixed poses do not freeze entry/exit velocity.
    output = folder/result['state']['current_clip']
    assert key_values(output, 0) == key_values(initial, 0)
    assert key_values(output, -1) == key_values(initial, -1) != key_values(source, -1)
    assert key_values(output, 1) != key_values(initial, 1)
    record = jobs.artifact(folder, result['state']['accepted'][0]['path'])
    assert read(record.parent/'export.json')['edited_keys'] == [1]
    assert attempt(folder)['status'] == 'complete_numerical_candidate'


def endpoint_contact(tmp_path):
    source, rig, reader, _ = fixture(tmp_path, 3); cfg = config()
    t = reader.duration; target = rig.vertices(reader.sample(t))[0].copy(); target[1] += .025
    cfg['clip']['limits']['contact_error_m'] = .002
    cfg['clip']['contacts'] = [dict(vertex=0, target_m=target.tolist(), start_time_s=t, end_time_s=t)]
    return source, cfg


def test_conflicting_protected_end_is_reported_without_edit(tmp_path):
    source, cfg = endpoint_contact(tmp_path); original = source.read_bytes()
    folder = jobs.prepare(tmp_path/'job', source, source, **cfg)
    result = attempt(folder)
    assert result['status'] == 'unresolved' and result['reason'] == 'invalid_preserved_end'
    assert result['state'] is None and not (folder/'state.json').exists()
    assert not list(folder.glob('attempts/*/window-*'))
    assert source.read_bytes() == original
    audit = read(next(folder.glob('attempts/*/protected-end-audit.json')))
    assert not audit['passed'] and audit['maximum_contact_error_m'] > .024


def test_explicit_acknowledged_end_edit_can_repair_endpoint_contact(tmp_path):
    source, cfg = endpoint_contact(tmp_path)
    folder = jobs.prepare(tmp_path/'job', source, source, **cfg, end_policy='edit', acknowledge_changed_end=True)
    result = attempt(folder)
    assert result['status'] == 'complete_numerical_candidate' and result['transition_review_required']
    output = folder/result['state']['current_clip']
    assert key_values(output, -1) != key_values(source, -1)
    assert key_values(output, 0) == key_values(source, 0)
    assert not result['quality_approved'] and not result['release_approved']


def test_two_fixed_keys_with_failed_interior_contact_keep_exact_clip(tmp_path):
    source, rig, reader, _ = fixture(tmp_path, 2); cfg = config()
    t = reader.duration/2; target = rig.vertices(reader.sample(t))[0].copy(); target[0] += 5
    cfg['clip']['contacts'] = [dict(vertex=0, target_m=target.tolist(), start_time_s=t, end_time_s=t)]
    cfg['solver']['epochs'] = 1
    folder = jobs.prepare(tmp_path/'job', source, source, **cfg)
    result = attempt(folder)
    assert result['status'] == 'unresolved' and result['reason'] == 'unresolved_window'
    candidate = next(folder.glob('attempts/*/window-*/candidate.glb'))
    assert sha256(candidate) == sha256(source)
    assert read(candidate.parent/'export.json')['edited_keys'] == []
    assert not result['state']['accepted']


@pytest.mark.parametrize('index', [0,2])
def test_changed_protected_key_is_rejected_from_decoded_channel_values(tmp_path, index):
    source, rig, _, _ = fixture(tmp_path, 3); context = SurfaceClip(rig, **config()['clip'])
    x = np.zeros(12); x[1] = .01; output = tmp_path/'changed.glb'
    replace_keys(rig, rig, root=0, rotations=[1,2,3], edits={index:x}, preserve_through=index-1, output=output)
    with pytest.raises(ValueError, match='Protected boundary'):
        jobs.preserved_boundaries(context, source, output, 'preserve')
    if index == 2: jobs.preserved_boundaries(context, source, output, 'edit')
    else:
        with pytest.raises(ValueError, match='Protected boundary'):
            jobs.preserved_boundaries(context, source, output, 'edit')


@pytest.mark.parametrize('policy,ack', [('edit',False),('preserve',True),('edit',1),(True,False),('free',True),('preserve',None),('',False)])
def test_invalid_or_unacknowledged_policy_rejected_before_copy(tmp_path, policy, ack):
    with pytest.raises(ValueError):
        jobs.prepare(tmp_path/'job', tmp_path/'unused.glb', tmp_path/'unused.glb', **config(), end_policy=policy, acknowledge_changed_end=ack)
    assert not (tmp_path/'job').exists()


def test_window_only_allows_explicit_final_key_protection(tmp_path):
    _, rig, _, _ = fixture(tmp_path, 5); context = SurfaceClip(rig, **config()['clip'])
    for frames, value in [([0,1,2],True),([2,3,4],1)]:
        with pytest.raises(ValueError): context.build_window(frames, context.controls(rig, frames), preserve_last=value)
    frames = [2,3,4]; seed = context.controls(rig, frames)
    native, _, _, _ = context.build_window(frames, seed, preserve_last=True)
    bounds = np.asarray(native.bounds).reshape(3,12,2)
    np.testing.assert_array_equal(bounds[-1,:,0], seed[-1]); np.testing.assert_array_equal(bounds[-1,:,1], seed[-1])
    assert np.any(bounds[1,:,0] != bounds[1,:,1])
