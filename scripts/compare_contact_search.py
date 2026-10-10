"""Matched search-step experiments with unchanged saved-pose acceptance limits.

Separate branches share only their already verified starting history. No branch
is automatically promoted and no optimizer success certifies motion quality.
"""
import argparse
from pathlib import Path
import shutil
import time
import numpy as np
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from action_worker_lock import worker_lock
from contact_interval_coverage import partition_frames
from contact_interval_resume import FILES
from contact_candidate_recovery import RESOURCE_METHODS
import batch_contact_interval as batch

SCHEMA = 'strep-contact-search-comparison-v1'
SAME_FIELDS = ['source_study', 'frames', 'width', 'fps', 'selected_frames',
               'selection_exclusions', 'original_limits', 'pose_dim',
               'inequality_labels', 'representation_labels', 'tradeoff_mask',
               'proposal_feasible_mask', 'proposal_headroom_normalized',
               'iterations', 'seconds', 'proposal_solve_iterations',
               'proposal', 'proposal_start', 'proposal_priority',
               'proposal_geometry_solver', 'proposal_margin_fallback',
               'proposal_trial_correction', 'proposal_tangent_guard',
               'representation_guard', 'methods_sha256', 'native_metadata_sha256',
               'source_motion_sha256', 'inputs_sha256']


def matched_branches(first, second):
    """Check actual stored origins, controls, every original limit and row."""
    a, b = read(first/'protocol.json'), read(second/'protocol.json')
    if any(k not in a or k not in b or a[k] != b[k] for k in SAME_FIELDS):
        raise ValueError('Matched source, selected window, references, limits, rows and fit budgets required')
    if (a['interval_resume']['directory'] != b['interval_resume']['directory']
            or a['interval_resume']['result_sha256'] != b['interval_resume']['result_sha256']):
        raise ValueError('Identical verified starting history required')
    if read(first/'baseline.json') != read(second/'baseline.json'):
        raise ValueError('Complete measured starting summaries differ')
    with np.load(first/'baseline-motion.npz', allow_pickle=False) as x, np.load(second/'baseline-motion.npz', allow_pickle=False) as y:
        if set(x.files) != set(y.files): raise ValueError('Starting pose population differs')
        for key in x.files:
            if x[key].shape != y[key].shape or x[key].dtype != y[key].dtype:
                raise ValueError('Starting pose precision or shape differs')
            np.testing.assert_array_equal(x[key], y[key])
    x, y = read(first/'row-diagnostics.json')['rows'], read(second/'row-diagnostics.json')['rows']
    if [r['label'] for r in x] != [r['label'] for r in y]: raise ValueError('Complete original row population differs')
    np.testing.assert_array_equal([r['initial_slack'] for r in x], [r['initial_slack'] for r in y])


def describe(directory, seconds):
    result = read(directory/'result.json')
    if (result.get('status') != 'complete' or result.get('quality_approved') is not False
            or result.get('release_approved') is not False or len(result['records']) != 1):
        raise ValueError('One complete unapproved attempt per comparison branch required')
    stage = ROOT/result['records'][0]['directory']; record = read(stage/'result.json')
    if stage.resolve() != (directory/'stage-1').resolve():
        raise ValueError('Owned ordered comparison stage required')
    if sha256(stage/'result.json') != result['records'][0]['result_sha256']:
        raise ValueError('Bound comparison stage changed')
    protocol = read(stage/'protocol.json'); pipeline = read(stage/'pipeline.json')
    if (record.get('status') != 'complete' or pipeline.get('status') != 'complete'
            or protocol.get('metadata_approved') is not False
            or set(record.get('files_sha256', {})) != FILES
            or any(r.get(k) is not False for r in [protocol, record, pipeline] for k in ['quality_approved', 'release_approved'])
            or sha256(stage/'protocol.json') != record['protocol_sha256']
            or any(sha256(stage/n) != h for n, h in record['files_sha256'].items())):
        raise ValueError('Complete immutable unapproved branch artifacts required')
    kept = record['decision']['update_retained']
    if type(kept) is not bool or (kept and record['decision']['source_rows_preserved'] is not True):
        raise ValueError('Preserving complete native retention required')
    measured = read(stage/('proposed.json' if kept else 'baseline.json'))
    rows = read(stage/'row-diagnostics.json')['rows']
    values = np.array([r['final_slack' if kept else 'initial_slack'] for r in rows])
    violation = np.maximum(-values, 0)
    return dict(directory=directory.relative_to(ROOT).as_posix(), result_sha256=sha256(directory/'result.json'),
        stage_directory=stage.relative_to(ROOT).as_posix(), stage_result_sha256=sha256(stage/'result.json'),
        selected_frames=record['selected_frames'], update_retained=kept, local_stop=record['local_stop'],
        fit_seconds=record['fit']['seconds'], branch_seconds=seconds, row_count=len(rows),
        retained_physical_contact_keys_passed=sum(p['pose_checks_passed'] for p in measured['per_frame_physical']),
        retained_all_physical_contact_keys_passed=measured['physical_contact_keys_passed'],
        retained_keyed_contact_keys_passed=sum(r['keyed_rows_passed'] for r in measured['frames'] if r['frame'] in protocol['frames']),
        retained_complete_keyed_rows_passed=measured['complete_keyed_rows_passed'],
        retained_worst_violation=float(violation.max()), retained_squared_violation=float(violation@violation),
        quality_approved=False, release_approved=False)


def run(study, output, frames, resume, resume_batch, *, trusts=(.03, .10), width=3,
        seconds=300, iterations=8, solve_iterations=10, max_seconds=1800):
    partition_frames(frames, width)
    if (not isinstance(trusts, (list, tuple)) or not 2 <= len(trusts) <= 4
            or any(type(t) not in [int, float] or not np.isfinite(t) or not 1e-5 <= t <= .3 for t in trusts)
            or len(set(trusts)) != len(trusts) or type(iterations) is not int or not 1 <= iterations <= 100
            or type(solve_iterations) is not int or not 1 <= solve_iterations <= 300
            or type(seconds) not in [int, float] or not np.isfinite(seconds) or not 1 <= seconds <= 1800
            or type(max_seconds) not in [int, float] or not np.isfinite(max_seconds) or not seconds+300 <= max_seconds <= 3600):
        raise ValueError('Distinct bounded search steps and matched fit budgets required')
    if any(not isinstance(p, (str, Path)) or not str(p) for p in [study, output, resume, resume_batch]):
        raise ValueError('Explicit original study, verified motion, completed schedule and fresh output required')
    study, output, resume, resume_batch = [Path(p).resolve() for p in [study, output, resume, resume_batch]]
    inputs = [study, resume, resume_batch]
    if (any(not p.is_relative_to(ROOT.resolve()) for p in inputs+[output])
            or any(output.is_relative_to(p) or p.is_relative_to(output) for p in inputs)):
        raise ValueError('Separate immutable in-project comparison inputs/output required')
    if output.exists(): raise FileExistsError(output)
    with worker_lock(), threadpool_limits(limits=2):
        # Metadata scheduling is not a native proof; every first state still
        # receives complete pose/history replay in the owned session below.
        exclusions, scheduling = batch.batch_attempted_history(resume_batch, study, frames, width, resume)
        bindings = {**scheduling, str(resume/'result.json'): sha256(resume/'result.json')}
        methods = batch.repair.METHODS+RESOURCE_METHODS+['batch_contact_interval.py', 'compare_contact_search.py']
        live = {n: sha256(ROOT/'scripts'/n) for n in methods}
        output.mkdir(); archive = output/'implementation'; archive.mkdir()
        for name in methods: shutil.copyfile(ROOT/'scripts'/name, archive/name)
        if any(sha256(archive/n) != h for n, h in live.items()): raise ValueError('Comparison source changed')
        protocol = dict(schema=SCHEMA, at=now(), source_study=study.relative_to(ROOT).as_posix(), frames=frames,
            width=width, trusts=list(trusts), resume=resume.relative_to(ROOT).as_posix(),
            resume_batch=resume_batch.relative_to(ROOT).as_posix(), initial_exclusions=exclusions,
            inputs_sha256=bindings, methods_sha256=live, seconds=seconds, iterations=iterations,
            solve_iterations=solve_iterations, per_branch_admission_budget_seconds=max_seconds,
            scope='Only normalized proposal search trust varies. Original pose/contact/object/floor/reference and full-interval acceptance limits stay fixed. Fit budgets match; first-branch startup includes full ancestry replay, so overall branch wall times are not matched.',
            quality_approved=False, release_approved=False)
        save(output/'protocol.json', protocol); save(output/'pipeline.json', dict(status='processing', quality_approved=False, release_approved=False))
        session = batch.repair.IntervalReplaySession(); records = []; first = None
        try:
            for index, trust in enumerate(trusts):
                directory = output/('branch-'+str(index+1)); started = time.monotonic()
                batch._run(study, directory, frames, width, resume, 1, seconds, iterations, trust, solve_iterations,
                    max_seconds, proposal_geometry_solver='conic', resume_batch=resume_batch, replay_session=session)
                record = describe(directory, time.monotonic()-started); record['trust_normalized'] = trust
                stage = ROOT/record['stage_directory']
                if first is None: first = stage
                else: matched_branches(first, stage)
                records.append(record)
                save(output/'progress.json', dict(status='processing', records=records, history_reuse=session.statistics(), quality_approved=False, release_approved=False))
            if (any(sha256(Path(p)) != h for p, h in bindings.items())
                    or any(sha256(ROOT/'scripts'/n) != h or sha256(archive/n) != h for n, h in live.items())
                    or any(sha256(ROOT/r['directory']/'result.json') != r['result_sha256'] or sha256(ROOT/r['stage_directory']/'result.json') != r['stage_result_sha256'] for r in records)):
                raise ValueError('Comparison inputs, methods or completed branches changed')
            result = dict(schema=SCHEMA, status='complete', at=now(), records=records, protocol_sha256=sha256(output/'protocol.json'),
                matched_start_and_original_limits=True, history_reuse=session.statistics(), selected_branch=None,
                quality_approved=False, release_approved=False,
                scope='Matched source and per-fit budgets, retained saved-interval diagnostics only. Separate complete schedules remain branch-specific; no automatic promotion, optimizer/quality, metadata, interpolation, dynamics, engine or human certificate.')
            save(output/'result.json', result); save(output/'pipeline.json', dict(status='complete', quality_approved=False, release_approved=False))
            return result
        except Exception as exc:
            save(output/'pipeline.json', dict(status='failed', error_type=type(exc).__name__, error=str(exc), quality_approved=False, release_approved=False)); raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['study', 'output', 'resume', 'resume_batch']: p.add_argument(name)
    p.add_argument('--start', type=int, required=True); p.add_argument('--end', type=int, required=True)
    p.add_argument('--trusts', type=float, nargs='+', default=[.03, .10]); p.add_argument('--width', type=int, default=3)
    p.add_argument('--seconds', type=float, default=300); p.add_argument('--iterations', type=int, default=8)
    p.add_argument('--solve-iterations', type=int, default=10); p.add_argument('--max-seconds', type=float, default=1800)
    a = p.parse_args(); run(a.study, a.output, list(range(a.start, a.end+1)), a.resume, a.resume_batch, trusts=a.trusts,
        width=a.width, seconds=a.seconds, iterations=a.iterations, solve_iterations=a.solve_iterations, max_seconds=a.max_seconds)
