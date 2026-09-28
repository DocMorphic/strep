import json
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import inspect_motion as motion
import strep


def fixture():
    frames, joints = 4, 30
    positions = np.zeros((frames, joints, 3), dtype=np.float32)
    positions[..., 1] = 1
    rotations = np.broadcast_to(np.eye(3), (frames, joints, 3, 3)).copy()
    return {'posed_joints': positions, 'local_rot_mats': rotations,
            'global_rot_mats': rotations.copy(), 'root_positions': positions[:, 0].copy(),
            'foot_contacts': np.zeros((frames, 4))}


def test_rejects_nonfinite_and_mismatched_motion():
    data = fixture(); data['posed_joints'][0, 0, 0] = np.nan
    with pytest.raises(ValueError, match='Non-finite'):
        motion.validate_motion(data, 30)
    data = fixture(); data['root_positions'] = np.zeros((3, 3))
    with pytest.raises(ValueError, match='frame/shape'):
        motion.validate_motion(data, 30)


def test_rejects_reflection_rotation():
    data = fixture(); data['local_rot_mats'][0, 0, 0, 0] = -1
    with pytest.raises(ValueError, match='Improper rotations'):
        motion.validate_motion(data, 30)


def test_no_contact_is_missing_score_not_perfect_score():
    data = fixture()
    names, _, feet = motion.validate_motion(data, 30)
    result = motion.metrics(data, names, feet, 30)
    assert result['foot_horizontal_speed_predicted_contact_m_s'] is None
    assert result['foot_horizontal_speed_height_proxy_m_s'] is None


def test_one_metre_per_second_slide():
    data = fixture()
    names, _, feet = motion.validate_motion(data, 30)
    for name in feet:
        data['posed_joints'][:, names.index(name), 1] = 0
        data['posed_joints'][:, names.index(name), 0] = np.arange(4) / 30
    data['foot_contacts'][:] = 1
    result = motion.metrics(data, names, feet, 30)
    assert result['foot_horizontal_speed_height_proxy_m_s']['mean'] == pytest.approx(1)
    assert result['foot_horizontal_speed_predicted_contact_m_s']['mean'] == pytest.approx(1)


def test_soma77_contact_order_and_end_of_clip_event():
    _, _, feet = motion.skeleton_metadata(77)
    assert feet == ['LeftFoot', 'LeftToeBase', 'LeftToeEnd', 'RightFoot', 'RightToeBase', 'RightToeEnd']
    contacts = np.array([[0], [1], [1], [1]])
    events = motion.contact_events(contacts, ['LeftFoot'], 30)
    assert events[0]['start_frame'] == 1
    assert events[0]['end_frame_exclusive'] == 4


def test_inspection_preserves_source_and_labels_provenance(tmp_path):
    source = tmp_path / 'motion.npz'
    np.savez(source, **fixture())
    digest = strep.sha256(source)
    report = motion.inspect_motion(source, tmp_path / 'derived', 30, 'synthetic_test')
    assert strep.sha256(source) == digest
    assert report['provenance'] == 'synthetic_test'
    assert (tmp_path / 'derived/preview.html').exists()
    assert '__MOTION_DATA__' not in (tmp_path / 'derived/preview.html').read_text()


def test_blocked_attempt_is_preserved_and_retry_is_new_directory(tmp_path, monkeypatch):
    template = strep.read(strep.ROOT / 'benchmarks/run-record.template.json')
    strep.save(tmp_path / 'benchmarks/run-record.template.json', template)
    strep.save(tmp_path / 'benchmarks/v0.json', {})
    monkeypatch.setattr(strep, 'ROOT', tmp_path)
    monkeypatch.setattr(strep, 'source_check', lambda: 'pinned')
    monkeypatch.setattr(strep, 'doctor', lambda: {'blockers': ['missing gated model']})
    job = dict(id='run/seed-11/unprocessed/actor-A', case_id='run', actor='A', condition='unprocessed',
               seed=11, prompt='Run.', durations_s=[4], model_revision='revision', rig_sha256='hash')
    first = strep.run_job(job); second = strep.run_job(job)
    assert first != second
    assert strep.read(first)['status'] == 'blocked'
    assert strep.read(first)['elapsed_wall_seconds_including_startup'] >= 0
    assert strep.read(second)['command_argv'] is None


def test_run_id_cannot_escape_output_root(monkeypatch):
    monkeypatch.setattr(strep, 'source_check', lambda: 'pinned')
    with pytest.raises(ValueError, match='escapes'):
        strep.run_job({'id': '../../outside'})


def test_embedding_cache_rejects_unknown_prompts_and_returns_copy(tmp_path, monkeypatch):
    import torch
    from safetensors.torch import save_file
    import embedding_cache as cache
    monkeypatch.setattr(cache, 'source_check', lambda: 'pinned')
    monkeypatch.setattr(cache, 'required_texts', lambda: ['A person runs.'])
    tensor = torch.arange(4096, dtype=torch.float32).reshape(1, 1, 4096)
    path = tmp_path / 'embeddings.safetensors'
    save_file({'features': tensor}, str(path))
    manifest = {'kimodo_git_commit': 'pinned', 'benchmark_sha256': strep.sha256(strep.ROOT / 'benchmarks/v0.json'),
                'encoder_revisions': {m['repo_id']: m['revision'] for m in strep.read(strep.LOCK)['models'] if not m['repo_id'].startswith('nvidia/')},
                'tensor_sha256': strep.sha256(path), 'texts': ['A person runs.']}
    strep.save(tmp_path / 'manifest.json', manifest)
    encoder = cache.CachedEncoder(tmp_path / 'manifest.json')
    first, lengths = encoder(['A person runs.'])
    assert torch.equal(first, tensor) and lengths == [1]
    first.zero_()
    second, _ = encoder(['A person runs.'])
    assert torch.equal(second, tensor)
    with pytest.raises(ValueError, match='Uncached prompt'):
        encoder(['A person dances.'])
    manifest['tensor_sha256'] = 'incorrect_digest'
    strep.save(tmp_path / 'manifest.json', manifest)
    with pytest.raises(ValueError, match='checksum'):
        cache.CachedEncoder(tmp_path / 'manifest.json')


def test_legacy_fixture_derivations_are_explicit(tmp_path):
    data = fixture()
    del data['local_rot_mats']; del data['root_positions']
    source = tmp_path / 'legacy.npz'; np.savez(source, **data)
    with pytest.raises(ValueError, match='Missing motion array'):
        motion.inspect_motion(source, tmp_path / 'strict', 30, 'generated_baseline')
    report = motion.inspect_motion(source, tmp_path / 'legacy', 30, 'upstream_example_not_generated_here')
    assert len(report['derivations']) == 2
