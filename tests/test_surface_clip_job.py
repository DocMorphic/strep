"""Real decoded jobs, interruption/restart and stale-input rejection."""
from pathlib import Path
import json
import os
import subprocess
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import surface_clip_job as jobs
from surface_clip import SurfaceClip
from surface_pose_key_export import replace_keys
from rig_asset import RigAsset
from strep import read, save, sha256
from test_native_support import fixture as original_fixture
from gltf_tools import append_accessor, write_glb
from native_support_clock import NativeSupportSampler
from test_surface_clip import options


def config():
    return dict(clip=options(), solver=dict(epochs=3, iterations_per_epoch=40,
                floor_batch_size=16, maximum_new_samples_per_epoch=4))


def fixture(tmp_path, key_count=5):
    source, rig, reader, spec = original_fixture(tmp_path)
    # Five real native keys exercise three overlapping windows and continuation.
    doc = rig.document; data = bytearray(rig.binary)
    for sampler, channel in zip(doc['animations'][0]['samplers'], (reader.channels[0], reader.channels[-1])):
        sampler['input'] = append_accessor(doc, data, channel[2][:key_count], 'SCALAR')
        sampler['output'] = append_accessor(doc, data, channel[3][:key_count], 'VEC3' if channel[1]=='translation' else 'VEC4')
    write_glb(source, doc, data); rig = RigAsset.load(source)
    return source, rig, NativeSupportSampler(rig.document, rig.binary, 0), spec


def test_two_key_selected_animation_preserves_other_clip(tmp_path):
    import copy
    source, rig, _, _ = fixture(tmp_path, 2)
    doc = rig.document; doc['animations'].append(copy.deepcopy(doc['animations'][0]))
    doc['animations'][0]['samplers'][0]['interpolation'] = 'STEP'
    write_glb(source, doc, rig.binary); cfg = config(); cfg['clip']['animation_index'] = 1
    folder = jobs.prepare(tmp_path/'job', source, source, **cfg)
    result = attempt(folder)
    assert result['status'] == 'complete_numerical_candidate' and len(result['state']['accepted']) == 1
    current = RigAsset.load(folder/result['state']['current_clip'])
    assert current.document['animations'][0] == doc['animations'][0]


def prepared(tmp_path, **kwargs):
    source, rig, reader, _ = fixture(tmp_path)
    folder = jobs.prepare(tmp_path/'job', source, source, **(kwargs or config()))
    return folder, source, rig, reader


def attempt(folder, maximum_windows=20):
    # The test harness owns the shared numerical-worker lock for this process.
    return jobs._attempt(folder, maximum_windows=maximum_windows, soft_seconds=60)


def test_full_clip_and_window_continuation_match(tmp_path):
    folder, source, rig, _ = prepared(tmp_path)
    baseline = jobs.prepare(tmp_path/'baseline', source, source, **config())
    first = attempt(folder, 1)
    assert first['status'] == 'checkpointed' and first['state']['finalized_through'] == 1
    before = (folder/'state.json').read_bytes()
    result = attempt(folder)
    expected = attempt(baseline)
    assert result['status'] == expected['status'] == 'complete_numerical_candidate'
    assert result['whole_clip_sampled'] and len(result['state']['accepted']) == 3
    assert result['state']['clip_sha256'] == expected['state']['clip_sha256']
    assert not result['quality_approved'] and not result['release_approved'] and not result['scene_verified']
    assert result['state']['finalized_through'] == 4 and before != (folder/'state.json').read_bytes()
    current = RigAsset.load(folder/result['state']['current_clip'])
    np.testing.assert_array_equal(SurfaceClip(rig, **options()).controls(current, list(range(5))), np.zeros((5,12)))
    completed_state = (folder/'state.json').read_bytes()
    assert attempt(folder)['attempted_windows'] == 0
    assert (folder/'state.json').read_bytes() == completed_state


def test_real_contact_solve_is_decoded_before_advancement(tmp_path):
    source, rig, reader, _ = fixture(tmp_path); cfg = config()
    t = float(reader.channels[0][2][1]); target = rig.vertices(reader.sample(t))[0].copy(); target[1] += .025
    cfg['clip']['limits']['contact_error_m'] = .002
    cfg['clip']['contacts'] = [dict(vertex=0, target_m=target.tolist(), start_time_s=t, end_time_s=t)]
    folder = jobs.prepare(tmp_path/'job', source, source, **cfg)
    assert not SurfaceClip(rig, **cfg['clip']).audit(source, [0,1,2])['passed']
    result = attempt(folder, 1)
    assert result['status'] == 'checkpointed' and result['state']['finalized_through'] == 1
    record = jobs.artifact(folder, result['state']['accepted'][0]['path'])
    assert (record.parent/'optimizer-checkpoint.json').exists()
    audit = read(record.parent/'decoded-audit.json'); assert audit['passed']
    assert audit['maximum_contact_error_m'] <= .002
    current = RigAsset.load(record.parent/'candidate.glb')
    controls = SurfaceClip(rig, **cfg['clip']).controls(current, [0,1,2])
    np.testing.assert_array_equal(controls[0], np.zeros(12))
    assert np.linalg.norm(controls[1]) > .001


def test_invalid_incoming_pose_never_creates_checkpoint(tmp_path):
    source, rig, reader, _ = fixture(tmp_path); cfg = config()
    target = rig.vertices(reader.sample(0.))[0].tolist(); target[0] += 1
    cfg['clip']['contacts'] = [dict(vertex=0, target_m=target, start_time_s=0., end_time_s=0.)]
    folder = jobs.prepare(tmp_path/'job', source, source, **cfg)
    result = attempt(folder)
    assert result['status'] == 'unresolved' and result['reason'] == 'invalid_incoming_pose'
    assert result['state'] is None and not (folder/'state.json').exists()


def test_rejected_candidate_preserved_without_checkpoint_advancement(tmp_path):
    source, rig, reader, _ = fixture(tmp_path); cfg = config(); cfg['solver']['epochs'] = 1; cfg['solver']['iterations_per_epoch'] = 2
    t = float(reader.channels[0][2][1]); target = rig.vertices(reader.sample(t))[0].tolist(); target[0] += 5
    cfg['clip']['contacts'] = [dict(vertex=0, target_m=target, start_time_s=t, end_time_s=t)]
    folder = jobs.prepare(tmp_path/'job', source, source, **cfg)
    result = attempt(folder)
    assert result['status'] == 'unresolved' and result['reason'] == 'unresolved_window'
    assert result['state']['current_clip'] == 'initial.glb' and not result['state']['accepted']
    candidates = list(folder.glob('attempts/*/window-*/candidate.glb')); assert len(candidates) == 1
    raw = candidates[0].read_bytes(); state = (folder/'state.json').read_bytes()
    assert not read(candidates[0].parent/'decoded-audit.json')['passed']
    attempt(folder)
    assert candidates[0].read_bytes() == raw and (folder/'state.json').read_bytes() == state


@pytest.mark.parametrize('stage', ['before_commit', 'after_commit'])
def test_hard_process_exit_can_resume_without_losing_evidence(tmp_path, stage):
    folder, source, _, _ = prepared(tmp_path)
    baseline = jobs.prepare(tmp_path/'baseline', source, source, **config())
    # Parent guarded test worker owns the global lock; child is its fault probe.
    code = '''import os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import surface_clip_job as j
from threadpoolctl import threadpool_limits
original=j.save
def interrupted(path,data):
    original(path,data)
    if (sys.argv[3]=='before_commit' and Path(path).name=='result.json' and 'frames' in data
        or sys.argv[3]=='after_commit' and Path(path).name=='state.json' and len(data['accepted'])==1):os._exit(73)
j.save=interrupted
with threadpool_limits(limits=1):j._attempt(sys.argv[2],maximum_windows=20,soft_seconds=60)
'''
    child = subprocess.run([sys.executable, '-c', code, str(Path(jobs.__file__).parent), str(folder), stage], capture_output=True, text=True, timeout=60)
    assert child.returncode == 73, child.stderr
    saved = {p:sha256(p) for p in folder.glob('attempts/**/*') if p.is_file()}
    result = attempt(folder); expected = attempt(baseline)
    assert result['status'] == 'complete_numerical_candidate'
    assert result['state']['clip_sha256'] == expected['state']['clip_sha256']
    assert all(sha256(p) == digest for p,digest in saved.items())


@pytest.mark.parametrize('fault', ['input', 'request', 'runtime', 'methods', 'receipt', 'candidate', 'position', 'escape'])
def test_changed_inputs_or_checkpoint_refused(tmp_path, fault, monkeypatch):
    folder, _, _, _ = prepared(tmp_path); attempt(folder, 1)
    if fault == 'input': (folder/'initial.glb').write_bytes(b'changed')
    elif fault == 'request':
        request = read(folder/'request.json'); request['solver']['epochs'] += 1; save(folder/'request.json', request)
    elif fault == 'runtime': monkeypatch.setattr(jobs, 'runtime', lambda: {'changed':True})
    elif fault == 'methods':
        request = read(folder/'request.json'); request['methods']['surface_clip_job.py'] = '0'*64
        save(folder/'request.json', request); save(folder/'prepared.json', dict(request_sha256=sha256(folder/'request.json')))
    else:
        state = read(folder/'state.json')
        if fault == 'receipt': jobs.artifact(folder, state['accepted'][0]['path']).write_bytes(b'changed')
        elif fault == 'candidate': jobs.artifact(folder, state['current_clip']).write_bytes(b'changed')
        elif fault == 'position': state['next_start'] += 1; save(folder/'state.json', state)
        elif fault == 'escape': state['accepted'][0]['path'] = '../outside.json'; save(folder/'state.json', state)
    raw = (folder/'state.json').read_bytes()
    with pytest.raises(ValueError): attempt(folder)
    assert (folder/'state.json').read_bytes() == raw


def test_preparation_copies_and_refuses_reuse(tmp_path):
    folder, source, _, _ = prepared(tmp_path)
    digest = sha256(folder/'source.glb'); source.write_bytes(b'external edit')
    assert jobs.request_for(folder)['inputs']['source.glb'] == digest
    with pytest.raises(FileExistsError): jobs.prepare(folder, folder/'source.glb', folder/'initial.glb', **config())


@pytest.mark.parametrize('value', [True, 0, -1, 10001])
def test_invalid_attempt_budget_refused(tmp_path, value):
    folder, _, _, _ = prepared(tmp_path)
    with pytest.raises(ValueError): attempt(folder, value)
    assert not (folder/'attempts').exists()


@pytest.mark.parametrize('status,code', [('complete',0),('deferred',2),('failed',1)])
def test_cli_propagates_guard_status(tmp_path, monkeypatch, status, code):
    import run_guarded_job, audit_guarded_job
    monkeypatch.setattr(jobs, 'request_for', lambda folder: {})
    monkeypatch.setattr(run_guarded_job, 'run', lambda *a, **k: dict(status=status))
    monkeypatch.setattr(audit_guarded_job, 'audit', lambda folder: dict(status=status))
    monkeypatch.setattr(sys, 'argv', ['surface_clip_job.py','run','--folder',str(tmp_path/'job')])
    assert jobs.main() == code


def test_actual_cli_busy_worker_returns_deferred_exit(tmp_path):
    from contextlib import nullcontext
    import tempfile
    import action_worker_lock as locks
    # Real guards require an in-project output even when pytest's own temp root
    # is outside the checkout (as it is in ordinary CI invocations).
    cache = jobs.ROOT/'.cache'; cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache, prefix='surface-cli-') as temporary:
        location = Path(temporary).resolve()
        assert location.parent == cache.resolve()  # Bound automatic cleanup.
        folder, _, _, _ = prepared(location)
        owned = getattr(locks._owner, 'path', None) is not None
        with nullcontext() if owned else locks.worker_lock():
            process = subprocess.run([sys.executable, jobs.__file__, 'run','--folder',str(folder)],
                                     capture_output=True, text=True, timeout=60)
        assert process.returncode == 2, process.stderr
        report = json.loads(process.stdout)
        assert report['status'] == 'deferred' and report['reason'] == 'owned_worker_busy'
        assert not (folder/'state.json').exists()
