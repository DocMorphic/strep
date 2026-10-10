"""Recheck saved poses from a RAM-stopped fit as a separate geometry recovery.

Never synthesizes a completed optimizer report or advances its coverage schedule.
Original references, bounds, trust steps and complete interval retention still apply.
"""
import argparse
from pathlib import Path
import re
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now
from audit_contact_interval import pose_tracks, overlay_pose_tracks, evaluate_interval
from contact_interval_coverage import select_window, partition_frames
from contact_interval_resume import original_limits, same_motion, seed_window
from protected_inequality_step import retain
from pose_restoration_policy import row_diagnostics

SCHEMA = 'strep-saved-contact-candidate-recovery-v1'
FILES = {'baseline-motion.npz', 'retained-motion.npz', 'baseline.json',
         'proposed.json', 'row-diagnostics.json', 'candidate-replays.json'}
SCOPE = ('Fresh native geometry replay of saved partial candidates, exact starting history, '
         'unchanged local bounds/trust and complete interval retention. No optimizer '
         'trajectory/tangent/start completion, scheduling promotion, interpolation, '
         'dynamics, metadata, export, engine or human approval.')


def unapproved(*records):
    if any(r.get(k) is not False for r in records for k in ['quality_approved', 'release_approved']):
        raise ValueError('Explicitly unapproved diagnostic records required')


def binder(checked):
    def bind(path, digest):
        path = Path(path).resolve()
        if (not path.is_relative_to(ROOT.resolve()) or not isinstance(digest, str)
                or not re.fullmatch('[0-9a-f]{64}', digest) or sha256(path) != digest):
            raise ValueError('In-project immutable recovery binding changed')
        if str(path) in checked and checked[str(path)] != digest:
            raise ValueError('Conflicting recovery binding')
        checked[str(path)] = digest
    return bind


def stopped_source(partial, guard, study, frames, width, original_bindings,
                   methods, definitions, prior, bind):
    """Recheck terminal resource history, never rely on a partial retained flag."""
    from audit_guarded_job import audit
    partial = Path(partial).resolve(); guard = Path(guard).resolve()
    if not partial.is_relative_to(guard.parent) or partial.is_relative_to(guard):
        raise ValueError('Partial stage and supervisor must share an attempt directory')
    receipt = audit(guard)
    if (receipt['status'] != 'failed' or receipt['reason'] != 'available_ram_guard'
            or receipt['worker_started'] is not True):
        raise ValueError('A reaped RAM-stopped worker is required')
    for path in guard.rglob('*'):
        if path.is_file(): bind(path, sha256(path))
    if any((partial/name).exists() for name in ['result.json', 'retained-motion.npz', 'proposed-motion.npz']):
        raise ValueError('Recovery must not replace a completed stage')
    protocol = read(partial/'protocol.json'); pipeline = read(partial/'pipeline.json')
    progress = read(partial/'fit-progress.json')
    unapproved(protocol, pipeline)
    if (pipeline.get('status') != 'processing' or progress.get('status') != 'processing'
            or protocol.get('source_study') != study.relative_to(ROOT).as_posix()
            or protocol.get('frames') != frames or protocol.get('width') != width
            or protocol.get('fps') != 30 or protocol.get('metadata_approved') is not False
            or protocol.get('interval_resume') is None or prior is None
            or protocol['interval_resume']['directory'] != prior['directory']
            or protocol['interval_resume']['result_sha256'] != prior['result_sha256']):
        raise ValueError('Incomplete stage with the exact verified source/clock/history required')
    inputs = protocol.get('inputs_sha256', {})
    if any(inputs.get(p) != h for p, h in original_bindings.items()):
        raise ValueError('Original inputs differ')
    for path, digest in inputs.items(): bind(path, digest)
    archived = protocol.get('methods_sha256', {})
    optional = {'contact_candidate_recovery.py', 'contact_interval_resume.py'}
    if protocol.get('proposal_geometry_solver', 'supporting-planes') == 'supporting-planes':
        optional.add('geometry_conic_start.py')
    if not set(methods)-optional <= set(archived) <= set(methods):
        raise ValueError('Complete original implementation required')
    for name, digest in archived.items(): bind(partial/'implementation'/name, digest)
    if protocol.get('native_metadata_sha256') != sha256(definitions):
        raise ValueError('Original native metadata differs')
    bind(partial/'implementation/kimodo-skeleton-definitions.py', protocol['native_metadata_sha256'])
    # Bind every partial observation/archive, even though rejected optimizer trials
    # are not interpreted as evidence for recovered poses.
    for path in partial.rglob('*'):
        if path.is_file(): bind(path, sha256(path))
    trials = progress.get('trials')
    if (not isinstance(trials, list) or not 1 <= len(trials) <= 10000
            or len({r.get('label') for r in trials}) != len(trials)
            or any(not isinstance(r.get('label'), str)
                   or not re.fullmatch('[a-zA-Z0-9_-]{1,100}', r['label'])
                   or type(r.get('retained')) is not bool for r in trials)):
        raise ValueError('Complete uniquely named partial observations required')
    return protocol, trials


def replay_candidates(partial, protocol, trials, factory, source, parameters,
                      frames, width, origin_type, bind):
    baseline, labels, before = evaluate_interval(factory, frames, source, parameters, width=width)
    block = select_window(frames, baseline, width, protocol.get('selection_exclusions', []))
    if block is None or protocol.get('selected_frames') != block:
        raise ValueError('Original failure-first selection differs')
    current = {r['frame']: np.asarray(r['controls']) for r in baseline['parameters']}
    window = seed_window(factory, block, source, current); origin = origin_type(window, source)
    trust = protocol.get('trust_normalized')
    if (type(trust) not in [int, float] or not np.isfinite(trust) or not 1e-5 <= trust <= .3
            or protocol.get('pose_dim') != window.pose_dim
            or protocol.get('original_limits') != original_limits(window)
            or protocol.get('inequality_labels') != window.labels
            or protocol.get('representation_labels') != window.representation_labels
            or protocol.get('tradeoff_mask') != [False]*len(window.labels)):
        raise ValueError('Original rows, limits and zero-tradeoff trust policy required')
    lower = np.tile(np.r_[np.full(window.pose_dim-1, -1.), 0.], len(block))
    upper = np.ones(window.dim)
    previous = origin.seed.copy()
    local_before = window.geometry_slack(window.problems[0].t(previous)).detach().numpy()
    saved_before = origin.rows(previous)
    state = pose_tracks(source); summary = baseline; slacks = before.copy(); records = []
    for trial in trials:
        path = partial/'trials'/trial['label']; bind(path/'audit.json', trial['audit_sha256'])
        record = read(path/'audit.json'); unapproved(record)
        if record.get('label') != trial['label'] or record.get('retained') is not trial['retained']:
            raise ValueError('Partial observation differs')
        bind(path/'window.npz', record['motion_sha256'])
        if not trial['retained']: continue
        controls = window.controls(record['parameters'])
        normalized = controls/window.scale
        if (np.any(normalized < lower) or np.any(normalized > upper)
                or np.any(np.abs((controls-previous)/window.scale) > trust+1e-12)):
            raise ValueError('Saved candidate exceeds original bounds/trust step')
        motion = dict(np.load(path/'window.npz', allow_pickle=False))
        same_motion(motion, origin.motion(controls), exact=False)
        local = window.geometry_slack(window.problems[0].t(controls)).detach().numpy()
        saved = window.saved_representation(controls, motion=motion)
        np.testing.assert_allclose(local, record['solver_slacks'], rtol=0, atol=1e-10)
        np.testing.assert_array_equal(saved, record['represented_slacks'])
        if (record.get('candidate') != origin.audit(controls, motion)
                or not retain(local_before, local, failure_policy='merit', tradeoff_mask=np.zeros(len(local), bool))
                or not retain(saved_before, saved, failure_policy='merit', tradeoff_mask=np.zeros(len(saved), bool))):
            raise ValueError('Saved candidate fails local geometry preservation')
        previous = controls.copy(); local_before = local; saved_before = saved
        # Each recorded candidate is relative to the original window, not a new
        # reference motion. All outside poses stay exactly equal to that source.
        proposed = overlay_pose_tracks(source, block, motion)
        proposed_parameters = {k: v.copy() for k, v in current.items()}
        for i, f in enumerate(block): proposed_parameters[f] = controls[i*window.pose_dim:(i+1)*window.pose_dim]
        candidate, candidate_labels, after = evaluate_interval(factory, frames, proposed, proposed_parameters, width=width)
        if candidate_labels != labels: raise ValueError('Complete original interval rows differ')
        diagnostics = row_diagnostics(labels, slacks, after, np.zeros(len(labels), bool))
        kept = (not diagnostics['source_passing_lost'] and not diagnostics['protected_source_regressed']
                and retain(slacks, after, failure_policy='merit', tradeoff_mask=np.zeros(len(labels), bool)))
        records.append(dict(label=trial['label'], globally_retained=bool(kept),
                            row_count=len(labels), diagnostics=diagnostics))
        if kept: state = proposed; current = proposed_parameters; summary = candidate; slacks = after
        print(dict(stage='saved_candidate_replayed', label=trial['label'], globally_retained=bool(kept)), flush=True)
    diagnostics = row_diagnostics(labels, before, slacks, np.zeros(len(labels), bool))
    decision = dict(update_retained=any(r['globally_retained'] for r in records),
                    source_rows_preserved=not diagnostics['source_passing_lost'] and not diagnostics['protected_source_regressed'],
                    quality_approved=False, release_approved=False)
    return state, current, baseline, summary, diagnostics, records, decision


def replay_recovery(directory, study, factory, source, frames, width, original_bindings,
                    methods, definitions, origin_type, *, ancestors=(), replay_session=None):
    """Resume only after fresh source-history and saved-candidate geometry replay."""
    from contact_interval_resume import resume_interval
    checked = {}; bind = binder(checked)
    protocol = read(directory/'protocol.json'); result = read(directory/'result.json'); pipeline = read(directory/'pipeline.json')
    unapproved(protocol, result, pipeline)
    if (protocol.get('schema') != SCHEMA or protocol.get('source_study') != study.relative_to(ROOT).as_posix()
            or protocol.get('frames') != frames or protocol.get('width') != width or protocol.get('fps') != 30
            or protocol.get('metadata_approved') is not False or result.get('status') != 'complete'
            or pipeline.get('status') != 'complete' or result.get('interrupted_stage_complete') is not False
            or result.get('decision', {}).get('update_retained') is not True
            or result['decision'].get('source_rows_preserved') is not True
            or set(result.get('files_sha256', {})) != FILES):
        raise ValueError('Complete preserving geometry recovery with unchanged clock required')
    for path, digest in protocol['inputs_sha256'].items(): bind(path, digest)
    if any(protocol['inputs_sha256'].get(p) != h for p, h in original_bindings.items()):
        raise ValueError('Original recovery inputs differ')
    if set(protocol['methods_sha256']) != set(methods): raise ValueError('Complete recovery implementation required')
    for name, digest in protocol['methods_sha256'].items(): bind(directory/'implementation'/name, digest)
    if protocol['native_metadata_sha256'] != sha256(definitions): raise ValueError('Native metadata differs')
    bind(directory/'implementation/kimodo-skeleton-definitions.py', protocol['native_metadata_sha256'])
    bind(directory/'protocol.json', result['protocol_sha256'])
    for name, digest in result['files_sha256'].items(): bind(directory/name, digest)
    for name in ['result.json', 'pipeline.json']: bind(directory/name, sha256(directory/name))
    prior = protocol['interval_resume']
    state, parameters, receipt, extra = resume_interval(ROOT/prior['directory'], study, factory, source,
        frames, width, original_bindings, methods, definitions, origin_type,
        ancestors=ancestors+(directory,), replay_session=replay_session)
    if receipt['result_sha256'] != prior['result_sha256']: raise ValueError('Recovery starting history differs')
    checked.update(extra)
    partial = ROOT/protocol['interrupted_stage']; guard = ROOT/protocol['interrupted_guard']
    old, trials = stopped_source(partial, guard, study, frames, width, original_bindings,
                                methods, definitions, receipt, bind)
    proposed, current, baseline, summary, diagnostics, records, decision = replay_candidates(
        partial, old, trials, factory, state, parameters, frames, width, origin_type, bind)
    same_motion(dict(np.load(directory/'baseline-motion.npz', allow_pickle=False)), state)
    same_motion(dict(np.load(directory/'retained-motion.npz', allow_pickle=False)), proposed)
    for name, value in [('baseline.json', baseline), ('proposed.json', summary),
                        ('row-diagnostics.json', diagnostics), ('candidate-replays.json', records)]:
        if read(directory/name) != value: raise ValueError('Recovered geometry/decision differs')
    if result['decision'] != decision: raise ValueError('Recovered retention differs')
    for path, digest in checked.items(): bind(path, digest)
    receipt = dict(directory=directory.relative_to(ROOT).as_posix(), result_sha256=sha256(directory/'result.json'),
                   replayed_local_observations=len(records), original_references_preserved=True,
                   interrupted_stage_complete=False, quality_approved=False, release_approved=False, scope=SCOPE)
    payload = proposed, current, receipt, checked
    if replay_session is not None: replay_session._save_verified(directory, payload)
    return payload


def run(study, partial, guard, resume, output, frames, *, width=3):
    from repair_contact_interval import METHODS, ExactSavedOrigin
    from contact_interval_resume import resume_interval
    from coupled_pose_window import CoupledPoseWindow
    from guarded_pose_restoration import DEFINITIONS
    from build_soma_preview import ASSET
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    import torch
    partition_frames(frames, width)
    study, partial, guard, resume, output = [Path(p).resolve() for p in [study, partial, guard, resume, output]]
    inputs = [study, partial, guard, resume]
    if (any(not p.is_relative_to(ROOT.resolve()) for p in inputs+[output])
            or any(output.is_relative_to(p) or p.is_relative_to(output) for p in inputs)):
        raise ValueError('Separate immutable in-project recovery inputs/output required')
    if output.exists(): raise FileExistsError(output)
    with worker_lock(), threadpool_limits(limits=2):
        torch.set_num_threads(2)
        summary = read(study/'fit/summary.json')
        if summary.get('solver_version') != 17 or read(study/'pipeline.json')['status'] != 'complete' or len(summary['trials']) != 1 or sha256(ASSET) != summary['mesh_sha256']:
            raise ValueError('Completed original V17 source and unchanged native skin required')
        folder = study/'fit/assets'/summary['trials'][0]['id']/'A'
        paths = [folder/name for name in ['raw-motion.npz', 'limb-motion.npz', 'previous-motion.npz', 'motion.npz', 'recipe.json']]
        paths += [ASSET, DEFINITIONS, study/'fit/summary.json', study/'pipeline.json']
        original = {str(p): sha256(p) for p in paths}; checked = original.copy(); bind = binder(checked)
        source = pose_tracks(dict(np.load(folder/'motion.npz', allow_pickle=False)))
        skin = dict(np.load(ASSET, allow_pickle=False)); factory = lambda block: CoupledPoseWindow(folder, skin, block, row_chunk=4)
        state, parameters, receipt, extra = resume_interval(resume, study, factory, source, frames, width, original, METHODS, DEFINITIONS, ExactSavedOrigin)
        checked.update(extra)
        protocol, trials = stopped_source(partial, guard, study, frames, width, original, METHODS, DEFINITIONS, receipt, bind)
        output.mkdir(parents=True); archive = output/'implementation'; archive.mkdir()
        for name in METHODS: shutil.copyfile(ROOT/'scripts'/name, archive/name)
        shutil.copyfile(DEFINITIONS, archive/'kimodo-skeleton-definitions.py')
        recovery_protocol = dict(schema=SCHEMA, at=now(), source_study=study.relative_to(ROOT).as_posix(), frames=frames, width=width, fps=30,
            interrupted_stage=partial.relative_to(ROOT).as_posix(), interrupted_guard=guard.relative_to(ROOT).as_posix(),
            interval_resume=receipt, inputs_sha256=checked.copy(), methods_sha256={n: sha256(archive/n) for n in METHODS},
            native_metadata_sha256=sha256(DEFINITIONS), metadata_approved=False, quality_approved=False, release_approved=False, scope=SCOPE)
        save(output/'protocol.json', recovery_protocol); save(output/'pipeline.json', dict(status='processing', quality_approved=False, release_approved=False))
        try:
            proposed, current, baseline, summary, diagnostics, records, decision = replay_candidates(partial, protocol, trials, factory, state, parameters, frames, width, ExactSavedOrigin, bind)
            for name, motion in [('baseline-motion.npz', state), ('retained-motion.npz', proposed)]: np.savez_compressed(output/name, **motion)
            for name, value in [('baseline.json', baseline), ('proposed.json', summary), ('row-diagnostics.json', diagnostics), ('candidate-replays.json', records)]: save(output/name, value)
            for path, digest in checked.items(): bind(path, digest)
            if any(sha256(ROOT/'scripts'/n) != h or sha256(archive/n) != h for n, h in recovery_protocol['methods_sha256'].items()):
                raise ValueError('Recovery implementation changed')
            save(output/'result.json', dict(status='complete', at=now(), schema=SCHEMA, decision=decision, interrupted_stage_complete=False,
                selected_frames=protocol['selected_frames'], recovered_candidates=sum(r['globally_retained'] for r in records),
                row_count=len(diagnostics['rows']), physical_contact_keys_passed=summary['physical_contact_keys_passed'],
                protocol_sha256=sha256(output/'protocol.json'), files_sha256={n: sha256(output/n) for n in sorted(FILES)},
                scope=SCOPE, quality_approved=False, release_approved=False))
            save(output/'pipeline.json', dict(status='complete', quality_approved=False, release_approved=False))
        except Exception as exc:
            save(output/'pipeline.json', dict(status='failed', error_type=type(exc).__name__, error=str(exc), quality_approved=False, release_approved=False)); raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['study', 'partial', 'guard', 'resume', 'output']: p.add_argument(name)
    p.add_argument('--start', type=int, required=True); p.add_argument('--end', type=int, required=True); p.add_argument('--width', type=int, default=3)
    a = p.parse_args(); run(a.study, a.partial, a.guard, a.resume, a.output, list(range(a.start, a.end+1)), width=a.width)
