"""Fit a retained contact request with the existing native body screens in the objective.

Development experiment only. Keep source, warm seed and all failed outputs;
do not automatically replace Studio results or change acceptance thresholds.
"""
import argparse
from pathlib import Path
import shutil
import time
import traceback
import numpy as np
import psutil
import torch
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from action_worker_lock import worker_lock
from build_soma_preview import ASSET
from contact_timing_job import verify_source
from held_pose_preservation import restore_locked_pose, POSE_KEYS
from support_contact_v8 import refine
from inspect_motion import skeleton_metadata, validate_motion
from export_point_rate_objective import ExportPointRateObjective
from evaluate_body_contact import evaluate
from run_body_contact import export_motion
from audit_checked_contact import audit
from kimodo.skeleton import SOMASkeleton77
from study_contact_joint_restart import original_budget_check
from study_export_feedback import engine_check


def run(source_path, seed_path, check_path, output, *, body_screen=True, support_screen=False, outer_stages=6, iterations=120, root_optimizer_scale_m=1.):
    if not output.is_relative_to(ROOT/'reports'):
        raise ValueError('Keep experiment outputs under reports')
    if output.exists():raise ValueError('Use a new output directory')
    paths = {**{name: source_path/name for name in ['motion.npz','soma.glb','raw/motion.npz','limb/motion.npz']},
             'seed/motion.npz': seed_path/'motion.npz', 'seed/recipe.json': seed_path/'recipe.json',
             **{name: check_path/name for name in ['bound-contact-spec.json','rate-reference.json','timing-result.json']},
             'skin.npz': ASSET}
    inputs = {name: dict(path=str(path), sha256=sha256(path)) for name,path in paths.items()}
    output.mkdir()
    process = psutil.Process();save(output/'worker.json',dict(pid=process.pid,created=process.create_time()))
    for name,path in paths.items():
        target=output/'inputs'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    (output/'implementation').mkdir()
    methods={}
    for path in (ROOT/'scripts').iterdir():
        if path.suffix not in ['.py','.gd']:continue
        shutil.copyfile(path,output/'implementation'/path.name);methods[path.name]=sha256(path)
    save(output/'freeze.json',dict(inputs=inputs,implementation=methods))
    def verify():
        for name,row in inputs.items():
            if sha256(Path(row['path']))!=row['sha256'] or sha256(output/'inputs'/name)!=row['sha256']:
                raise ValueError('Experiment input changed: '+name)
        for name,digest in methods.items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:
                raise ValueError('Experiment method changed: '+name)
    def phase(status,**extra):
        save(output/'pipeline.json',dict(status=status,at=now(),quality_approved=False,**extra))
        print(status,extra,flush=True)
    try:
        with worker_lock(),threadpool_limits(limits=1):
            torch.set_num_threads(2);verify();phase('preparing')
            root=output/'inputs'
            source=dict(np.load(root/'motion.npz'));seed=dict(np.load(root/'seed/motion.npz'))
            raw=dict(np.load(root/'raw/motion.npz'));limb=dict(np.load(root/'limb/motion.npz'));skin=dict(np.load(root/'skin.npz'))
            for motion in [source,seed,raw,limb]:
                validate_motion(motion,30)
                if motion['posed_joints'].shape!=source['posed_joints'].shape:raise ValueError('Experiment motion clocks differ')
            save(output/'source-validation.json',verify_source(root/'soma.glb',source,skin))
            spec=read(root/'bound-contact-spec.json');reference=read(root/'rate-reference.json')
            window=read(root/'timing-result.json')['requested_window']
            held=np.ones(len(source['root_positions']),bool);held[window[0]+1:window[1]]=False
            seed=restore_locked_pose(source,seed,held)
            config=read(root/'seed/recipe.json')['config']
            if config['max_root_lift_m']!=.22 or config['max_rotation_degrees']!=40:raise ValueError('Unexpected original budgets')
            original_budget_check(source,seed,.22,40)
            _,parents,_=skeleton_metadata(77)
            guard=ExportPointRateObjective(torch.tensor(source['global_rot_mats'],dtype=torch.float64),
                torch.tensor(source['posed_joints'],dtype=torch.float64),parents,skin,spec,window)
            if guard.record()!=reference:raise ValueError('Original point-rate limits changed')
            save(output/'protocol.json',dict(outer_stages=outer_stages,iterations_per_stage=iterations,window=window,
                native_body_references=['raw','limb'] if body_screen else [],native_support_screen=support_screen,root_optimizer_scale_m=root_optimizer_scale_m,native_limits=dict(joint_change_m=.22,added_joint_speed_m_s=1.5),
                new_constraint='Optional native body and fixed-patch support inequalities relative to both immutable references; enabled modes recorded separately',
                retained='Original controls, initialization, root/rotation budgets, pin target, export point/global rates and floor guards',
                quality_approved=False))
            start=time.perf_counter();phase('fitting')
            candidate,recipe=refine(source,source,skin,progress=lambda row:phase('fitting',progress=row),raw=source,
                contact_spec=spec,warm_start=seed,edit_window=window,export_rate_guard=True,export_point_rate_guard=True,
                skin_backend='sparse',root_coordinate_mode='physical_box',outer_stage_count=outer_stages,iteration_count=iterations,root_optimizer_scale_m=root_optimizer_scale_m,
                authored_point_scaling='tolerance',export_floor_guard=True,export_point_position_guard=True,
                native_body_references=dict(raw=raw,limb=limb) if body_screen else None,
                native_support_references=dict(raw=raw,limb=limb) if support_screen else None)
            elapsed=time.perf_counter()-start
            if recipe['export_rates']['ceilings']!=read(root/'seed/recipe.json')['export_rates']['ceilings']:
                raise ValueError('Original global rate limits changed')
            budgets=original_budget_check(source,candidate,.22,40)
            for key in POSE_KEYS:
                if candidate[key][held].tobytes()!=source[key][held].tobytes():raise ValueError('Held source changed')
            phase('exporting');take=output/'candidate';take.mkdir()
            np.savez(take/'motion.npz',**candidate);save(take/'recipe.json',recipe)
            evaluation,body=evaluate(raw,limb,candidate,skin,recipe)
            validation=export_motion(take,candidate,skin,SOMASkeleton77(),evaluation['after']['per_frame_max_depth_m'])
            final=audit(root/'soma.glb',take/'soma.glb',spec,window,reference)
            save(take/'checked-export-audit.json',final);save(take/'body-evaluation.json',dict(evaluation=evaluation,body=body))
            # Independently recompute from serialized NPZ, not the last optimizer evaluation.
            stored=dict(np.load(take/'motion.npz'));body_peaks={}
            for name,motion in [('raw',raw),('limb',limb)]:
                delta=stored['posed_joints'].astype(float)-motion['posed_joints'].astype(float)
                body_peaks[name]=[float(np.linalg.norm(delta,axis=-1).max()),float(np.linalg.norm(np.diff(delta,axis=0)*30,axis=-1).max())]
            phase('engine_check');engine_passed,checks=engine_check(output,'candidate',take,contact_spec=spec)
            peaks=[max(r[k] for r in final['variants']['candidate']['joints']) for k in ['peak_speed_m_s','peak_acceleration_m_s2']]
            caps=recipe['export_rates']['ceilings'];excess=[max(0.,a-b) for a,b in zip(peaks,caps)]
            contact_pass=bool(final['all_requested_pin_samples_within_5mm'] and final['outside_preservation_passed']
                and final['floor_nonregression']['maximum_added_depth_m']==0
                and all(max(r['candidate_excess_over_checked'])==0 for r in final['phase_rates']))
            verify()
            save(output/'completion.json',dict(fit_seconds=elapsed,evaluations=recipe['evaluations'],contact_screen=contact_pass,
                flags=evaluation['flags'],native_body_peaks=body_peaks,global_peaks=peaks,global_caps=caps,global_excess=excess,
                engine_passed=engine_passed,engine_checks=checks,validation=validation,budgets=budgets,quality_approved=False,
                files={p.relative_to(output).as_posix():sha256(p) for p in output.rglob('*') if p.is_file() and p.name not in ['pipeline.json','worker.json','supervisor.log']}))
            phase('complete',contact_screen=contact_pass,flags=evaluation['flags'],engine_passed=engine_passed)
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['source','seed','checked-plan','output']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--body-screen',action=argparse.BooleanOptionalAction,default=True)
    parser.add_argument('--support-screen',action='store_true')
    parser.add_argument('--outer-stages',type=int,default=6)
    parser.add_argument('--iterations',type=int,default=120)
    parser.add_argument('--root-optimizer-scale-m',type=float,default=1.)
    args=parser.parse_args()
    run(args.source.resolve(),args.seed.resolve(),args.checked_plan.resolve(),args.output.resolve(),body_screen=args.body_screen,support_screen=args.support_screen,outer_stages=args.outer_stages,iterations=args.iterations,root_optimizer_scale_m=args.root_optimizer_scale_m)
