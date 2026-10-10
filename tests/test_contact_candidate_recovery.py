"""Interrupted observations cannot substitute for a completed geometry replay."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import contact_candidate_recovery as recovery
import contact_interval_resume as resume
import audit_guarded_job
from repair_contact_interval import ExactSavedOrigin
from test_contact_interval_resume import fixture, evaluate, Window, motion, write


def partial_fixture(tmp_path, monkeypatch):
    make, args = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(recovery, 'ROOT', tmp_path)
    monkeypatch.setattr(recovery, 'evaluate_interval', evaluate)
    first, state, parameters = make('prior')
    prior = dict(directory='prior', result_sha256=resume.sha256(first/'result.json'))
    partial, _, _ = make('attempt/stage', state=state, parameters=parameters, prior=prior)
    # Preserve all toy observation files. Only the report/outputs distinguishing a
    # finished optimizer are absent, as they are in a genuinely interrupted fit.
    for name in ['result.json', 'retained-motion.npz', 'proposed-motion.npz']:
        (partial/name).unlink()
    write(partial/'pipeline.json', dict(status='processing', quality_approved=False, release_approved=False))
    trials = []
    for label in ['seed', 'kept']:
        trials.append(dict(label=label, retained=label == 'kept', audit_sha256=resume.sha256(partial/'trials'/label/'audit.json')))
    write(partial/'fit-progress.json', dict(status='processing', trials=trials))
    guard = tmp_path/'attempt/guard'; guard.mkdir(); (guard/'trace').write_text('terminal toy trace')
    monkeypatch.setattr(audit_guarded_job, 'audit', lambda p: dict(status='failed', reason='available_ram_guard', worker_started=True))
    checked = {}; bind = recovery.binder(checked)
    protocol, trials = recovery.stopped_source(partial, guard, args[0], args[3], args[4], args[5], args[6], args[7], prior, bind)
    return partial, guard, first, state, parameters, args, protocol, trials, checked, bind


def core(f):
    partial, _, _, state, parameters, args, protocol, trials, _, bind = f
    return recovery.replay_candidates(partial, protocol, trials, Window, state, parameters, args[3], args[4], ExactSavedOrigin, bind)


def test_fresh_geometry_recovers_pose_without_completing_original_stage(tmp_path, monkeypatch):
    f = partial_fixture(tmp_path, monkeypatch); actual, _, _, _, diagnostics, records, decision = core(f)
    assert decision['update_retained'] and decision['source_rows_preserved']
    assert records[0]['globally_retained'] and not diagnostics['source_passing_lost']
    for key in actual: np.testing.assert_array_equal(actual[key][[0, 3]], f[3][key][[0, 3]])
    assert not (f[0]/'result.json').exists()


@pytest.mark.parametrize('field,value', [('trust_normalized', .01), ('tradeoff_mask', [True, False]),
                                      ('selected_frames', [0, 1]), ('fps', 60)])
def test_changed_original_contract_cannot_recover(tmp_path, monkeypatch, field, value):
    f = partial_fixture(tmp_path, monkeypatch)
    f[6][field] = value
    if field == 'fps':
        write(f[0]/'protocol.json', f[6])
        with pytest.raises(ValueError): recovery.stopped_source(f[0], f[1], f[5][0], f[5][3], f[5][4], f[5][5], f[5][6], f[5][7], f[6]['interval_resume'], f[9])
    else:
        with pytest.raises(ValueError): core(f)


def test_retained_flag_cannot_hide_changed_saved_pose(tmp_path, monkeypatch):
    f = partial_fixture(tmp_path, monkeypatch)
    path = f[0]/'trials/kept/window.npz'; m = dict(np.load(path)); m['posed_joints'][0, 4, 1] = 100
    np.savez_compressed(path, **m)
    with pytest.raises(ValueError, match='binding changed'): core(f)


def test_reconstruction_mismatch_fails_even_with_resealed_observation(tmp_path, monkeypatch):
    f = partial_fixture(tmp_path, monkeypatch); path = f[0]/'trials/kept/window.npz'
    m = dict(np.load(path)); m['posed_joints'][0, 4, 1] = 100; np.savez_compressed(path, **m)
    audit = resume.read(path.parent/'audit.json'); audit['motion_sha256'] = resume.sha256(path); write(path.parent/'audit.json', audit)
    f[7][1]['audit_sha256'] = resume.sha256(path.parent/'audit.json')
    f[8].pop(str(path)); f[8].pop(str(path.parent/'audit.json'))
    with pytest.raises(AssertionError): core(f)


def test_full_interval_rejects_locally_good_candidate_that_breaks_an_exterior_row(tmp_path, monkeypatch):
    f = partial_fixture(tmp_path, monkeypatch)
    def exterior(factory, frames, m, parameters=None, **options):
        summary, labels, slacks = evaluate(factory, frames, m, parameters, **options)
        # An original passing edge becomes failing only after the local edit.
        edge = .075-float(m['posed_joints'][frames[0], 0, 0])
        return summary, labels+['body:exterior'], np.r_[slacks, edge]
    monkeypatch.setattr(recovery, 'evaluate_interval', exterior)
    actual, _, _, _, diagnostics, records, decision = core(f)
    assert not decision['update_retained'] and not records[0]['globally_retained']
    assert records[0]['diagnostics']['source_passing_lost'] == ['body:exterior']
    for key in actual: np.testing.assert_array_equal(actual[key], f[3][key])


@pytest.mark.parametrize('status,reason', [('complete', None), ('deferred', 'admission_timeout'), ('failed', 'other')])
def test_only_reaped_ram_stops_are_eligible(tmp_path, monkeypatch, status, reason):
    f = partial_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(audit_guarded_job, 'audit', lambda p: dict(status=status, reason=reason, worker_started=True))
    with pytest.raises(ValueError, match='reaped RAM-stopped'):
        recovery.stopped_source(f[0], f[1], f[5][0], f[5][3], f[5][4], f[5][5], f[5][6], f[5][7], f[6]['interval_resume'], f[9])


def test_completed_optimizer_cannot_be_overwritten_by_recovery(tmp_path, monkeypatch):
    f = partial_fixture(tmp_path, monkeypatch); write(f[0]/'result.json', {})
    with pytest.raises(ValueError, match='completed stage'):
        recovery.stopped_source(f[0], f[1], f[5][0], f[5][3], f[5][4], f[5][5], f[5][6], f[5][7], f[6]['interval_resume'], f[9])


def test_original_trust_box_is_coordinatewise_not_a_new_euclidean_limit(tmp_path, monkeypatch):
    f = partial_fixture(tmp_path, monkeypatch); path = f[0]/'trials/kept/audit.json'
    audit = resume.read(path); controls = np.asarray(audit['parameters'])
    controls[[1, 2, 5, 6]] = .09; audit['parameters'] = controls.tolist()
    write(path, audit); f[7][1]['audit_sha256'] = resume.sha256(path); f[8].pop(str(path))
    assert core(f)[-1]['update_retained']


def recovery_fixture(tmp_path, monkeypatch):
    f = partial_fixture(tmp_path, monkeypatch)
    proposed, _, baseline, summary, diagnostics, records, decision = core(f)
    directory = tmp_path/'recovery'; archive = directory/'implementation'; archive.mkdir(parents=True)
    methods = f[5][6]
    for name in methods: (archive/name).write_text('frozen recovery method')
    for name in recovery.RESOURCE_METHODS: (archive/name).write_text('frozen resource replay method')
    (archive/'kimodo-skeleton-definitions.py').write_bytes(f[5][7].read_bytes())
    protocol = dict(schema=recovery.SCHEMA, source_study='source', frames=f[5][3], width=3, fps=30,
        interval_resume=f[6]['interval_resume'], interrupted_stage='attempt/stage', interrupted_guard='attempt/guard',
        inputs_sha256=f[8], methods_sha256={n: resume.sha256(archive/n) for n in methods},
        resource_methods_sha256={n: resume.sha256(archive/n) for n in recovery.RESOURCE_METHODS},
        native_metadata_sha256=resume.sha256(f[5][7]), metadata_approved=False, quality_approved=False, release_approved=False)
    write(directory/'protocol.json', protocol)
    for name, m in [('baseline-motion.npz', f[3]), ('retained-motion.npz', proposed)]: np.savez_compressed(directory/name, **m)
    for name, value in [('baseline.json', baseline), ('proposed.json', summary), ('row-diagnostics.json', diagnostics), ('candidate-replays.json', records)]: write(directory/name, value)
    write(directory/'result.json', dict(status='complete', decision=decision, interrupted_stage_complete=False,
        protocol_sha256=resume.sha256(directory/'protocol.json'), files_sha256={n: resume.sha256(directory/n) for n in recovery.FILES}, quality_approved=False, release_approved=False))
    write(directory/'pipeline.json', dict(status='complete', quality_approved=False, release_approved=False))
    return directory, proposed, f


def test_recovery_resume_rechecks_ancestor_and_candidate_geometry(tmp_path, monkeypatch):
    directory, expected, f = recovery_fixture(tmp_path, monkeypatch)
    actual, _, receipt, bindings = resume.resume_interval(directory, *f[5])
    for key in actual: np.testing.assert_array_equal(actual[key], expected[key])
    assert receipt['interrupted_stage_complete'] is False and receipt['quality_approved'] is False
    assert str(f[2]/'result.json') in bindings


def test_resealed_recovery_result_cannot_hide_changed_diagnostics(tmp_path, monkeypatch):
    directory, _, f = recovery_fixture(tmp_path, monkeypatch)
    write(directory/'candidate-replays.json', [])
    result = resume.read(directory/'result.json'); result['files_sha256']['candidate-replays.json'] = resume.sha256(directory/'candidate-replays.json'); write(directory/'result.json', result)
    with pytest.raises(ValueError, match='geometry/decision differs'): resume.resume_interval(directory, *f[5])


def test_recovery_cannot_claim_old_optimizer_completed(tmp_path, monkeypatch):
    directory, _, f = recovery_fixture(tmp_path, monkeypatch)
    result = resume.read(directory/'result.json'); result['interrupted_stage_complete'] = True; write(directory/'result.json', result)
    with pytest.raises(ValueError, match='geometry recovery'): resume.resume_interval(directory, *f[5])


@pytest.mark.parametrize('change',['missing','altered'])
def test_recovery_resource_auditor_is_bound(tmp_path, monkeypatch, change):
    directory, _, f = recovery_fixture(tmp_path, monkeypatch)
    if change == 'altered':
        (directory/'implementation/audit_guarded_job.py').write_text('changed resource interpretation')
    else:
        protocol = resume.read(directory/'protocol.json'); protocol['resource_methods_sha256'].pop('audit_guarded_job.py')
        write(directory/'protocol.json', protocol)
        result = resume.read(directory/'result.json'); result['protocol_sha256'] = resume.sha256(directory/'protocol.json'); write(directory/'result.json', result)
    with pytest.raises(ValueError): resume.resume_interval(directory, *f[5])


def test_recovery_cycle_is_rejected(tmp_path, monkeypatch):
    directory, _, f = recovery_fixture(tmp_path, monkeypatch)
    protocol = resume.read(directory/'protocol.json'); protocol['interval_resume']['directory'] = 'recovery'; write(directory/'protocol.json', protocol)
    result = resume.read(directory/'result.json'); result['protocol_sha256'] = resume.sha256(directory/'protocol.json'); write(directory/'result.json', result)
    with pytest.raises(ValueError, match='acyclic'): resume.resume_interval(directory, *f[5])


def test_same_worker_reuse_is_bound_and_returns_independent_arrays(tmp_path, monkeypatch):
    directory, expected, f = recovery_fixture(tmp_path, monkeypatch)
    session = resume.IntervalReplaySession(); args = f[5]
    method = directory/'implementation/toy.py'
    factory = session.prepare(*args, implementation_bindings={str(method): resume.sha256(method)})
    assert factory is args[1]
    first = resume.resume_interval(directory, *args, replay_session=session)
    first[0]['posed_joints'][:] = 100
    second = resume.resume_interval(directory, *args, replay_session=session)
    np.testing.assert_array_equal(second[0]['posed_joints'], expected['posed_joints'])
    assert second[2]['geometry_replayed_this_call'] is False
    assert session.statistics()['reused_histories'] == 1
    # A partial input remains part of the recovered lineage, including on a hit.
    (f[1]/'trace').write_text('changed source resource history')
    with pytest.raises(ValueError, match='binding changed'):
        resume.resume_interval(directory, *args, replay_session=session)


def test_original_limit_relaxation_is_rejected(tmp_path, monkeypatch):
    f = partial_fixture(tmp_path, monkeypatch)
    f[6]['original_limits'][0]['added_speed_m_s'] = 999
    with pytest.raises(ValueError, match='Original rows, limits'): core(f)


def test_live_source_is_rejected_by_resource_replay(tmp_path, monkeypatch):
    f = partial_fixture(tmp_path, monkeypatch)
    def live(p): raise ValueError('Recorded owned worker remains live')
    monkeypatch.setattr(audit_guarded_job, 'audit', live)
    with pytest.raises(ValueError, match='remains live'):
        recovery.stopped_source(f[0], f[1], f[5][0], f[5][3], f[5][4], f[5][5], f[5][6], f[5][7], f[6]['interval_resume'], f[9])


@pytest.mark.parametrize('change',['live','archive'])
def test_worker_start_hashes_protect_source_and_archive_without_persistent_live_paths(tmp_path, monkeypatch, change):
    monkeypatch.setattr(recovery, 'ROOT', tmp_path)
    live = tmp_path/'source.py'; live.write_text('original worker code')
    archive = tmp_path/'archive'; archive.mkdir(); saved = archive/live.name; saved.write_bytes(live.read_bytes())
    bindings = {str(live): resume.sha256(live)}
    recovery.verify_implementation(bindings, archive)
    (live if change == 'live' else saved).write_text('different worker code')
    with pytest.raises(ValueError, match='binding changed'): recovery.verify_implementation(bindings, archive)
