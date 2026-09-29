"""Frozen root-only feasibility experiment on a retained checked-fit candidate."""
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
from checked_contact_job import prepare, verify
from action_worker_lock import worker_lock
from build_soma_preview import ASSET
from inspect_motion import skeleton_metadata, validate_motion
from root_height_feasibility import RootHeightProblem, solve


def run(control, output):
    control, output = Path(control).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Preserve previous experiment')
    verify(control)
    if read(control/'pipeline.json')['status']!='complete': raise ValueError('Completed control required')
    summary = read(control/'result/summary.json')
    if len(summary['trials'])!=1: raise ValueError('Single retained candidate required')
    trial = summary['trials'][0]; seed = control/'result/takes'/trial['id']
    for name, digest in trial['hashes'].items():
        if sha256(seed/name)!=digest: raise ValueError('Retained candidate changed: '+name)
    request = read(control/'edit-request.json')
    prepare(dict(checked_plan=request['check_id'], revision=request['check_revision']), output)
    for name in ['source-take/motion.npz', 'source-take/soma.glb', 'checked-plan/bound-contact-spec.json',
                 'checked-plan/rate-reference.json', 'checked-plan/edit-request.json']:
        if sha256(output/name)!=sha256(control/name): raise ValueError('Original source or checked policy differs')
    (output/'seed').mkdir()
    for name in ['motion.npz', 'soma.glb', 'recipe.json', 'evidence.json', 'checked-export-audit.json']:
        shutil.copyfile(seed/name, output/'seed'/name)
    protocol = dict(created_at=now(), control=str(control), attempts=6, trust_m=1e-5, normalized_margin=1e-4,
        original_max_root_lift_m=read(seed/'recipe.json')['config']['max_root_lift_m'],
        method='Root Y only, seed rotations/XZ/heading fixed; original source rate/floor/edit budgets. '
               'Linearized LP proposals recheck every nonlinear sampled inequality; no failed row waiver. '
               'Interior margin strengthens solver proposals, never changes acceptance. Float32 and GLB audited separately.',
        quality_approved=False)
    save(output/'protocol.json', protocol)
    frozen = read(output/'checked-freeze.json')
    for p in (output/'seed').iterdir(): frozen['inputs'][p.relative_to(output).as_posix()]=sha256(p)
    frozen['inputs']['protocol.json']=sha256(output/'protocol.json')
    save(output/'checked-freeze.json', frozen)
    process=psutil.Process(); save(output/'worker.json', dict(pid=process.pid, created=process.create_time()))
    def phase(status, **kw):
        save(output/'pipeline.json', dict(status=status, **kw, quality_approved=False))
        print(status, kw, flush=True)
    try:
        verify(output)
        with worker_lock(), threadpool_limits(limits=1):
            torch.set_num_threads(2); started=time.perf_counter()
            source=dict(np.load(output/'source-take/motion.npz')); seed_motion=dict(np.load(output/'seed/motion.npz'))
            skin=dict(np.load(ASSET)); spec=read(output/'checked-plan/bound-contact-spec.json')
            options=read(output/'checked-plan/edit-request.json')['options']
            _, parents, _=skeleton_metadata(77)
            phase('building_constraints')
            problem=RootHeightProblem(source, seed_motion, parents, skin, spec, options['edit_window'], protocol['original_max_root_lift_m'])
            c, j, groups=problem.evaluate(problem.start)
            rng=np.random.default_rng(2809); direction=rng.normal(size=len(problem.start)); direction/=np.linalg.norm(direction)
            eps=1e-7
            numerical=(problem.evaluate(problem.start+eps*direction, False)[0]-problem.evaluate(problem.start-eps*direction, False)[0])/(2*eps)
            analytic=j@direction
            difference=np.abs(analytic-numerical)
            # Mixed absolute/relative derivative test, including all rows.
            derivative_pass=bool(np.all(difference<=2e-4+2e-5*np.abs(numerical)))
            cache_checks=[]
            for offset in [np.zeros_like(direction), direction*1e-5]:
                x=problem.start+offset
                fast=problem.evaluate(x, False)[0]; full=problem.reference_residuals(problem.motion(x))
                error=float(np.abs(fast-full).max()); cache_checks.append(error)
                if error>1e-7: raise ValueError('Cached constraints differ from full export proxy')
            preflight=dict(rows=len(c), coordinates=len(problem.start), groups=groups,
                cache_maximum_normalized_errors=cache_checks, derivative_pass=derivative_pass,
                directional_derivative_maximum_absolute_error=float(difference.max()),
                jacobian_bytes=j.nbytes, cached_floor_bytes=problem.heights.nbytes,
                setup_and_verification_s=time.perf_counter()-started)
            save(output/'preflight.json', preflight)
            if not derivative_pass: raise ValueError('Root correction derivative check failed')
            phase('correcting', rows=len(c), coordinates=len(problem.start))
            candidate, solver=solve(problem, attempts=protocol['attempts'], trust=protocol['trust_m'], margin=protocol['normalized_margin'],
                progress=lambda row: print('step', row['iteration'], 'accepted', row['accepted'], row.get('message'), flush=True))
            save(output/'solver.json', solver)
            # Keep native dtype. Any serialization shift is measured, never
            # silently grandfathered into the solver acceptance tolerance.
            candidate={name:value.astype(seed_motion[name].dtype) for name,value in candidate.items()}
            serialized=problem.reference_residuals(candidate)
            save(output/'serialized-proxy.json', dict(minimum_slack=float(serialized.min()),
                violations=int((serialized<0).sum()), sampled_feasible=bool(serialized.min()>=0), quality_approved=False))
            validate_motion(candidate, 30)
            for name in ['local_rot_mats', 'global_rot_mats']:
                if not np.array_equal(candidate[name],seed_motion[name]): raise ValueError('Rotation changed')
            if not np.array_equal(candidate['root_positions'][:, [0,2]],seed_motion['root_positions'][:, [0,2]]): raise ValueError('Root XZ changed')
            locked=np.ones(len(candidate['root_positions']),dtype=bool); locked[problem.free]=False
            if not np.array_equal(candidate['posed_joints'][locked],seed_motion['posed_joints'][locked]): raise ValueError('Held pose changed')
            lift=candidate['root_positions'][:,1].astype(float)-source['root_positions'][:,1]
            if lift.min() < -2e-7 or lift.max()>problem.max_lift+2e-7: raise ValueError('Original root bound exceeded')
            phase('exporting_and_auditing')
            from evaluate_body_contact import evaluate
            from run_body_contact import export_motion
            from kimodo.skeleton import SOMASkeleton77
            from audit_checked_contact import audit
            raw=dict(np.load(output/'source-take/raw/motion.npz')); limb=dict(np.load(output/'source-take/limb/motion.npz'))
            evaluation, body=evaluate(raw,limb,candidate,skin,dict(applied=True))
            take=output/'candidate'
            validation=export_motion(take,candidate,skin,SOMASkeleton77(),evaluation['after']['per_frame_max_depth_m'])
            reference=read(output/'checked-plan/rate-reference.json')
            audit_result=audit(output/'source-take/soma.glb',take/'soma.glb',spec,options['edit_window'],reference)
            save(take/'checked-export-audit.json', audit_result)
            save(take/'body-evaluation.json', dict(evaluation=evaluation,body=body))
            # Every stationary-pin/rate/floor requirement is retained. This
            # screen is narrower than all motion quality and never approves it.
            checked_pass=bool(audit_result['all_requested_pin_samples_within_5mm'] and
                audit_result['outside_preservation_passed'] and audit_result['floor_nonregression']['maximum_added_depth_m']==0 and
                all(max(row['candidate_excess_over_checked'])==0 for row in audit_result['phase_rates']))
            verify(output); verify(control)
            result=dict(elapsed_s=time.perf_counter()-started, solver_sampled_feasible=solver['sampled_feasible'],
                serialized_proxy_feasible=bool(serialized.min()>=0), checked_contact_export_screen_passed=checked_pass,
                validation=validation, root_change_m=solver['maximum_root_change_m'], flags=evaluation['flags'], quality_approved=False,
                files={p.relative_to(output).as_posix():sha256(p) for p in [output/'protocol.json',output/'preflight.json',output/'solver.json',
                    output/'serialized-proxy.json',take/'motion.npz',take/'soma.glb',take/'checked-export-audit.json',take/'body-evaluation.json']})
            save(output/'completion.json', result); phase('complete', checked_contact_export_screen_passed=checked_pass)
    except BaseException as exc:
        phase('failed', error=str(exc), traceback=traceback.format_exc()); raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('control',type=Path); parser.add_argument('output',type=Path)
    args=parser.parse_args(); run(args.control,args.output)
