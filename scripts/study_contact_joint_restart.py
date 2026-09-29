"""Full-joint warm restarts of the two retained non-root-repairable cases.

This is an explicit development experiment. It retains original source budgets,
restarts optimizer/multiplier state, and never promotes a result to approved.
"""
import argparse
from pathlib import Path
import shutil
import time
import traceback

import numpy as np
import psutil
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
import torch

from strep import ROOT, read, save, sha256, now
from action_worker_lock import worker_lock
from build_soma_preview import ASSET
from verify_contact_archive import verify_archive
from held_pose_preservation import restore_locked_pose, POSE_KEYS
from support_contact_v8 import refine
from inspect_motion import skeleton_metadata
from export_point_rate_objective import ExportPointRateObjective
from evaluate_body_contact import evaluate
from run_body_contact import export_motion
from audit_checked_contact import audit
from kimodo.skeleton import SOMASkeleton77
from study_export_feedback import engine_check


def original_budget_check(source, candidate, max_lift, max_degrees):
    """Compare to the immutable original, never to the previous fitted result."""
    lift = candidate['root_positions'][:, 1].astype(float)-source['root_positions'][:, 1]
    if not np.array_equal(candidate['root_positions'][:, [0, 2]], source['root_positions'][:, [0, 2]]):
        raise ValueError('Root XZ changed')
    if not np.isfinite(lift).all() or lift.min() < 0 or lift.max() > max_lift:
        raise ValueError('Original root budget exceeded')
    relative = source['local_rot_mats'].transpose(0, 1, 3, 2) @ candidate['local_rot_mats']
    if not np.isfinite(relative).all(): raise ValueError('Nonfinite rotations')
    angles = np.rad2deg(Rotation.from_matrix(relative.reshape(-1, 3, 3)).magnitude())
    if angles.max() > max_degrees+1e-6:
        raise ValueError('Original rotation budget exceeded')
    return dict(minimum_root_lift_m=float(lift.min()), maximum_root_lift_m=float(lift.max()),
                maximum_rotation_delta_degrees=float(angles.max()))


def run(suite, output):
    output.mkdir(exist_ok=False)
    process = psutil.Process()
    save(output/'worker.json', dict(pid=process.pid, created=process.create_time()))
    methods = {}
    (output/'implementation').mkdir()
    for path in (ROOT/'scripts').iterdir():
        if path.suffix not in ['.py', '.gd']: continue
        shutil.copyfile(path, output/'implementation'/path.name)
        methods[path.name] = sha256(path)
    protocol = dict(cases=['crawl-11', 'kick-11'], outer_stage_count=6, iteration_count=120,
        edit_window=[10, 109], reference='Original source motion, not warm-start motion',
        optimizer_state='New optimizer and zero initial inequality multipliers; fitted poses only are reused',
        method='All original v8 body-joint controls with exact held source poses, original source root/rotation/rate/floor limits. '
               'Six outer stages, 120 iterations per stage, tolerance-scaled authored points and all prior export guards. '
               'Independent full export and engine checks; retain every failed result. No root-only post-repair in this study.',
        implementation=methods, quality_approved=False, created_at=now())
    save(output/'protocol.json', protocol)

    def phase(status, **fields):
        save(output/'pipeline.json', dict(status=status, at=now(), quality_approved=False, **fields))
        print(status, fields, flush=True)

    def verify_methods():
        for name, digest in methods.items():
            if sha256(ROOT/'scripts'/name) != digest or sha256(output/'implementation'/name) != digest:
                raise ValueError('Study method changed: '+name)

    try:
        phase('verifying_archive')
        save(output/'historical-verification.json', verify_archive(suite, suite/'batch-engine-followup-v2'))
        skin = dict(np.load(ASSET)); _, parents, _ = skeleton_metadata(77)
        results = []
        with worker_lock(), threadpool_limits(limits=1):
            torch.set_num_threads(2)
            for case in protocol['cases']:
                phase('preparing', case=case)
                folder=output/case; folder.mkdir()
                old=ROOT/'reports/contact-jobs'/('contact-breadth-v1-'+case+'-repair')
                paths=[old/'source-take'/n for n in ['motion.npz','soma.glb','raw/motion.npz','limb/motion.npz']]
                paths += [old/'seed'/n for n in ['motion.npz','soma.glb','recipe.json']]
                paths += [old/'checked-plan'/n for n in ['bound-contact-spec.json','rate-reference.json']]
                inputs={str(p):sha256(p) for p in paths+[ASSET]}; save(folder/'inputs.json', inputs)
                source=dict(np.load(old/'source-take/motion.npz')); seed=dict(np.load(old/'seed/motion.npz'))
                if len(source['root_positions']) != 120: raise ValueError('Study expects the declared 120-frame clips')
                held=np.ones(120, bool); held[11:109]=False
                seed=restore_locked_pose(source, seed, held)
                config=read(old/'seed/recipe.json')['config']
                if config['max_root_lift_m'] != .22 or config['max_rotation_degrees'] != 40:
                    raise ValueError('Original study budgets differ')
                before=original_budget_check(source, seed, .22, 40)
                spec=read(old/'checked-plan/bound-contact-spec.json'); reference=read(old/'checked-plan/rate-reference.json')
                guard=ExportPointRateObjective(torch.tensor(source['global_rot_mats'], dtype=torch.float64),
                    torch.tensor(source['posed_joints'], dtype=torch.float64), parents, skin, spec, [10,109])
                if guard.record() != reference: raise ValueError('Original rate reference changed')
                raw=dict(np.load(old/'source-take/raw/motion.npz')); limb=dict(np.load(old/'source-take/limb/motion.npz'))
                evaluation, body=evaluate(raw, limb, seed, skin, dict(applied=True))
                export_motion(folder/'warm-seed', seed, skin, SOMASkeleton77(), evaluation['after']['per_frame_max_depth_m'])
                initial=audit(old/'source-take/soma.glb',folder/'warm-seed/soma.glb',spec,[10,109],reference)
                save(folder/'warm-seed/checked-export-audit.json',initial)
                save(folder/'warm-seed/body-evaluation.json',dict(evaluation=evaluation,body=body))
                save(folder/'warm-seed/budgets.json',before)
                started=time.perf_counter()
                phase('fitting',case=case)
                candidate,recipe=refine(source,source,skin,
                    progress=lambda row: phase('fitting',case=case,progress=row),raw=source,
                    contact_spec=spec,warm_start=seed,edit_window=[10,109],
                    export_rate_guard=True,export_point_rate_guard=True,skin_backend='sparse',
                    root_coordinate_mode='physical_box',outer_stage_count=6,iteration_count=120,
                    authored_point_scaling='tolerance',export_floor_guard=True,export_point_position_guard=True)
                fit_seconds=time.perf_counter()-started
                if recipe['export_rates']['ceilings'] != read(old/'seed/recipe.json')['export_rates']['ceilings']:
                    raise ValueError('Original global rate ceilings changed')
                budgets=original_budget_check(source,candidate,.22,40)
                for key in POSE_KEYS:
                    if candidate[key][held].tobytes()!=source[key][held].tobytes():raise ValueError('Held source poses changed')
                take=folder/'candidate';take.mkdir()
                np.savez(take/'motion.npz',**candidate);save(take/'recipe.json',recipe);save(take/'budgets.json',budgets)
                phase('exporting',case=case)
                evaluation,body=evaluate(raw,limb,candidate,skin,recipe)
                validation=export_motion(take,candidate,skin,SOMASkeleton77(),evaluation['after']['per_frame_max_depth_m'])
                final=audit(old/'source-take/soma.glb',take/'soma.glb',spec,[10,109],reference)
                save(take/'checked-export-audit.json',final);save(take/'body-evaluation.json',dict(evaluation=evaluation,body=body))
                phase('engine_check',case=case)
                engine_passed,checks=engine_check(folder,case,take,contact_spec=spec)
                global_peaks=[max(r[k] for r in final['variants']['candidate']['joints']) for k in ['peak_speed_m_s','peak_acceleration_m_s2']]
                caps=recipe['export_rates']['ceilings']
                contact_pass=bool(final['all_requested_pin_samples_within_5mm'] and final['outside_preservation_passed']
                    and final['floor_nonregression']['maximum_added_depth_m']==0
                    and all(max(r['candidate_excess_over_checked'])==0 for r in final['phase_rates']))
                for path,digest in inputs.items():
                    if sha256(Path(path))!=digest:raise ValueError('Study input changed: '+path)
                verify_methods()
                record=dict(case=case,fit_seconds=fit_seconds,evaluations=recipe['evaluations'],contact_screen=contact_pass,
                    flags=evaluation['flags'],global_peaks=global_peaks,global_caps=caps,
                    global_excess=[max(0.,a-b) for a,b in zip(global_peaks,caps)],engine_passed=engine_passed,
                    engine_checks=checks,validation=validation,budgets=budgets,quality_approved=False,
                    files={p.relative_to(folder).as_posix():sha256(p) for p in folder.rglob('*') if p.is_file()})
                save(folder/'completion.json',record);results.append(record)
                phase('case_complete',case=case,contact_screen=contact_pass,engine_passed=engine_passed)
                if not engine_passed:raise ValueError('Engine verification failed')
        save(output/'completion.json',dict(cases=results,quality_approved=False))
        phase('complete')
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not args.output.resolve().is_relative_to((ROOT/'reports').resolve()):parser.error('Keep generated outputs under reports/')
    run(args.suite.resolve(),args.output.resolve())
