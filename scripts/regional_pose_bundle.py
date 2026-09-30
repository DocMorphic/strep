"""Bounded regional restoration with active rows and full nonlinear safeguards.

The linear model sees a bounded set of rows, including near-tied extrema.
Acceptance sees EVERY skin/patch clearance row and every contact constraint,
both before and after pose serialization. Rejected probes never replace a pose.
"""
import argparse
from pathlib import Path
import shutil
import time
import numpy as np
import psutil
import torch
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from regional_pose_witness import RegionalPoseProblem
from regional_pose_bounded import coordinates
from grasp_pose_witness_bounded import physical_parameters
from region_contact_objective import violations
from support_contact_v8 import torch_primitive_clearance_violation
from constraint_restoration import minimax_step, assess_trial


def active_rows(values, groups, singles, extra=(), margin=.1, cap=128):
    values=np.asarray(values)
    if values.ndim!=1 or not np.isfinite(values).all() or type(cap) is not int or cap<1 or not np.isfinite(margin) or margin<0:
        raise ValueError('Finite residuals and bounded active-row policy required')
    required=set(singles)|set(extra);near=set()
    for group in groups:
        ids=np.asarray(group,dtype=int)
        if not len(ids) or np.any(ids<0) or np.any(ids>=len(values)):raise ValueError('Invalid maximum group')
        worst=int(ids[np.argmax(values[ids])]);required.add(worst)
        near.update(int(i) for i in ids[values[ids]>=values[worst]-margin])
    if any(type(i) not in [int,np.int64,np.int32] or not 0<=i<len(values) for i in required):raise ValueError('Invalid required row')
    if len(required)>cap:raise ValueError('Active-row resource cap exhausted')
    remaining=sorted(near-required,key=lambda i:(-values[i],i))[:cap-len(required)]
    return np.array(sorted(required|set(remaining)),dtype=int)


class BundleProblem:
    def __init__(self, problem):
        self.p=problem;_,self.scale=coordinates(problem)
        count=len(problem.skin['bind_vertices']);cursor=0;self.groups=[];self.singles=[]
        for _ in range(1+len(problem.objects)):
            self.groups.append(np.arange(cursor,cursor+count));cursor+=count
        for r in problem.regions:
            self.groups.append(np.arange(cursor,cursor+len(r['ids'])));cursor+=len(r['ids'])
            self.singles.extend(range(cursor,cursor+13));cursor+=13
        self.count=cursor

    def physical(self,z):return physical_parameters(z*self.p.t(self.scale),self.p.limits)

    def from_vertices(self,v):
        p=self.p;rows=[(p.config['clearance_m']-v[:,1])/.001]
        for g,_,position,rotation in p.objects:
            rows.append(torch_primitive_clearance_violation(v[None],position,rotation,g,p.config['object_clearance_m']).reshape(-1)/.001)
        for r in p.regions:
            rows.append(violations(v[r['ids']],r['local_faces'],r['triple'],r['local_anchor'],p.t(r['target']),p.t(r['normal']),
                r['geometry'],p.t(r['position']),p.t(r['rotation']),r['limits'],r['anchor_tolerance']))
        return torch.cat(rows)

    def residual(self,z):
        _,_,_,v=self.p.fk(self.physical(z));return self.from_vertices(v)

    def collapsed(self,values):
        # Match the original ordering: floor, objects, patch max + 13 rows per hand.
        leading=1+len(self.p.objects)
        result=[values[g].max() for g in self.groups[:leading]]
        for i,g in enumerate(self.groups[leading:]):
            result.append(values[g].max());result.extend(values[self.singles[i*13:(i+1)*13]])
        return np.array(result)

    def serialized(self,z):
        physical=self.physical(self.p.t(z)).detach().numpy();audit,motion=self.p.independent(physical)
        v=self.p.surface.vertices(motion['global_rot_mats'][0],motion['posed_joints'][0])
        with torch.no_grad():g=self.from_vertices(self.p.t(v)).numpy()
        return g,audit,motion,physical

    def pair(self,z,ids,guard=None):
        variable=self.p.t(z).requires_grad_();g=self.residual(variable)
        rows=[]
        for k,i in enumerate(ids):
            if guard is not None and k%16==0:guard()
            rows.append(torch.autograd.grad(g[int(i)],variable,retain_graph=True)[0].numpy())
        jac=np.array(rows)
        return g.detach().numpy(),jac


def run(study,output,steps=5,seconds=180.,model='bundle'):
    if model not in ['bundle','all_failed_inward']:raise ValueError('Unknown linear model')
    if type(steps) is not int or not 1<=steps<=20 or type(seconds) not in [int,float] or not np.isfinite(seconds) or not 0<seconds<=1200:
        raise ValueError('Bounded solve budgets required')
    torch.set_num_threads(2);study=Path(study).resolve();output=Path(output).resolve()
    previous=read(study/'result.json');prior=read(study/'protocol.json')
    if previous['status']!='complete' or not previous['candidate']['bounds_passed']:raise ValueError('Completed bounded seed required')
    if sha256(study/'protocol.json')!=previous['protocol_sha256'] or sha256(study/'pose.npz')!=previous['pose_sha256']:raise ValueError('Seed artifacts changed')
    for path,digest in prior['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Seed input changed')
    for name,digest in prior['methods'].items():
        if sha256(study/'implementation'/name)!=digest:raise ValueError('Seed method snapshot changed')
    p=RegionalPoseProblem(ROOT/prior['fit'],prior['frame']);b=BundleProblem(p)
    initial=np.array(previous['bounded_preimage']);accepted=initial.copy()
    np.testing.assert_array_equal(b.physical(p.t(initial)).numpy(),previous['parameters'])
    source_g,source_audit,source_motion,_=b.serialized(initial)
    assert source_audit==previous['candidate']
    output.mkdir(parents=True,exist_ok=False);snap=output/'implementation';snap.mkdir()
    for pattern in ['*.py','*.gd']:
        for path in (ROOT/'scripts').glob(pattern):shutil.copyfile(path,snap/path.name)
    inputs={**prior['inputs'],**{str(study/n):sha256(study/n) for n in ['protocol.json','result.json','pose.npz']}}
    policy=dict(model=model,steps=steps,seconds_budget=seconds,cut_rounds=4,backtracks=10,active_row_cap=128 if model=='bundle' else 4096,near_maximum_margin=.1,normalized_trust=.01,
        nonlinear_acceptance='No new or increased positive residual at any full-skin/patch/contact row, in both continuous and serialized poses; lower maximum violation required.')
    protocol=dict(at=now(),study=study.relative_to(ROOT).as_posix(),inputs=inputs,methods={q.name:sha256(q) for q in snap.iterdir()},policy=policy,
        full_residual_count=b.count,selections=prior['selections'],rotation_limits_degrees=prior['rotation_limits_degrees'],max_root_lift_m=prior['max_root_lift_m'],
        scope='One native pose. Same original targets/patches/edit bounds; no temporal, anatomy, self-collision, balance or physical support qualification. Failure is not an infeasibility proof.',quality_approved=False)
    save(output/'protocol.json',protocol)
    with torch.no_grad():continuous=b.residual(p.t(initial)).numpy()
    np.testing.assert_allclose(b.collapsed(continuous),-p.geometry_slack(p.t(previous['parameters'])).detach().numpy(),atol=1e-10,rtol=1e-10)
    ids=active_rows(continuous,b.groups,b.singles);values,jac=b.pair(initial,ids)
    direction=np.random.default_rng(923).normal(size=len(initial));direction/=np.linalg.norm(direction);h=1e-7
    with torch.no_grad():fd=((b.residual(p.t(initial+h*direction))-b.residual(p.t(initial-h*direction)))/(2*h)).numpy()[ids]
    np.testing.assert_allclose(jac@direction,fd,atol=2e-4,rtol=2e-4)
    save(output/'preflight.json',dict(active_rows=ids.tolist(),directional_error=float(abs(jac@direction-fd).max()),seed=source_audit))
    start=time.monotonic();peak=0;history=[];status='complete';stop='step_budget';accepted_count=0
    def guard():
        nonlocal peak
        rss=psutil.Process().memory_info().rss;peak=max(peak,rss)
        if time.monotonic()-start>seconds or rss>2*1024**3 or psutil.virtual_memory().available<1.25*1024**3:raise TimeoutError('Bundle resource guard')
    lower=np.r_[np.full(len(initial)-1,-np.inf),0.];upper=np.r_[np.full(len(initial)-1,np.inf),1.]
    try:
        for iteration in range(steps):
            guard()
            with torch.no_grad():before=b.residual(p.t(accepted)).numpy()
            before_serial,_,_,_=b.serialized(accepted)
            if before.max()<=0 and before_serial.max()<=0:stop='feasible';break
            extra=set();selected=False
            for cut in range(policy['cut_rounds']):
                guard()
                if model=='all_failed_inward':extra.update(int(i) for i in np.flatnonzero(before>=-.1))
                try:ids=active_rows(before,b.groups,b.singles,extra,cap=policy['active_row_cap'])
                except ValueError:stop='active_row_cap';break
                _,jac=b.pair(accepted,ids,guard)
                stepper=minimax_step
                if model=='all_failed_inward':
                    from inward_feasibility_step import inward_step
                    stepper=inward_step
                step,lp=stepper(accepted,before[ids],jac,lower,upper,np.full(len(initial),policy['normalized_trust']))
                record=dict(iteration=iteration+1,cut=cut+1,active_rows=ids.tolist(),lp=lp,trials=[]);history.append(record)
                regressing=set()
                if step is not None:
                    for attempt in range(policy['backtracks']):
                        guard();fraction=.5**attempt;trial=np.clip(accepted+fraction*step,lower,upper)
                        with torch.no_grad():after=b.residual(p.t(trial)).numpy()
                        continuous_check=assess_trial(before,after)
                        serialized_check=None;bounds=None
                        if continuous_check['accepted']:
                            trial_serial,audit,_,_=b.serialized(trial);bounds=audit['bounds_passed'];serialized_check=assess_trial(before_serial,trial_serial)
                        passed=continuous_check['accepted'] and serialized_check is not None and serialized_check['accepted'] and bounds
                        record['trials'].append(dict(fraction=fraction,continuous=continuous_check,serialized=serialized_check,bounds_passed=bounds,accepted=bool(passed),coordinates=trial.tolist()))
                        if passed:accepted=trial.copy();selected=True;accepted_count+=1;break
                        delta=np.maximum(after,0)-np.maximum(before,0)
                        candidates=np.flatnonzero(delta>0)
                        regressing.update(int(i) for i in candidates[np.argsort(-delta[candidates],kind='stable')[:16]])
                save(output/'progress.json',dict(status='running',pid=psutil.Process().pid,created_at=psutil.Process().create_time(),history=history,accepted_steps=accepted_count))
                print(dict(iteration=iteration+1,cut=cut+1,active=len(ids),accepted=selected,seconds=time.monotonic()-start),flush=True)
                if selected:break
                new=regressing-set(ids)
                if not new:stop='no_accepted_step';break
                extra.update(new)
            if not selected:
                if stop=='step_budget':stop='cut_budget'
                break
    except TimeoutError as exc:status='interrupted_resource_guard';stop=str(exc)
    final_serial,audit,motion,parameters=b.serialized(accepted)
    with torch.no_grad():final=b.residual(p.t(accepted)).numpy()
    unchanged=np.array_equal(initial,accepted)
    if unchanged:shutil.copyfile(study/'pose.npz',output/'pose.npz')
    else:np.savez(output/'pose.npz',**motion)
    if not audit['bounds_passed']:raise ValueError('Final edit bounds failed')
    if not unchanged:
        assert assess_trial(continuous,final)['accepted'] and assess_trial(source_g,final_serial)['accepted']
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Input changed')
    for name,digest in protocol['methods'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Method changed')
    save(output/'result.json',dict(at=now(),status=status,stop_reason=stop,seconds=time.monotonic()-start,peak_rss_bytes=peak,accepted_steps=accepted_count,
        unchanged=unchanged,source=source_audit,candidate=audit,parameters=parameters.tolist(),bounded_preimage=accepted.tolist(),history=history,
        initial_maximum_violation=float(continuous.max()),final_maximum_violation=float(final.max()),
        continuous_assessment=assess_trial(continuous,final),serialized_assessment=assess_trial(source_g,final_serial),
        pose_sha256=sha256(output/'pose.npz'),protocol_sha256=sha256(output/'protocol.json'),quality_approved=False))
    save(output/'pipeline.json',dict(status=status,pose_witness_passed=audit['pose_witness_passed'],quality_approved=False))
    print(dict(status=status,stop=stop,accepted=accepted_count,candidate=audit),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--steps',type=int,default=5);parser.add_argument('--seconds',type=float,default=180.)
    parser.add_argument('--model',choices=['bundle','all_failed_inward'],default='bundle')
    a=parser.parse_args()
    with threadpool_limits(limits=2):run(a.study,a.output,a.steps,a.seconds,a.model)
