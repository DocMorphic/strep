"""Full regional pose diagnostic with bounded rotations and trust-region steps.

All visited rotations obey source-relative norm budgets by construction.
Best and terminal trials are retained separately; only the independent
original pose audit can establish a witness. No clip is modified.
"""
import argparse
from pathlib import Path
import shutil
import time
import numpy as np
import psutil
import torch
from scipy.optimize import least_squares
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from build_soma_preview import ASSET
from regional_pose_witness import RegionalPoseProblem
from grasp_pose_witness_bounded import inverse_rotation_bound, physical_parameters


def coordinates(problem):
    scale = np.r_[np.repeat(problem.limits, 3), problem.config['max_root_lift_m']]
    initial = np.r_[inverse_rotation_bound(problem.seed[:-1].reshape(-1, 3), problem.limits).ravel(), problem.seed[-1]]/scale
    return initial, scale


def run(fit, output, frame=96, evaluations=150, seconds=180.):
    if type(evaluations) is not int or not 1 <= evaluations <= 500 or not np.isfinite(seconds) or not 0 < seconds <= 1200:
        raise ValueError('Bounded positive solve budget required')
    torch.set_num_threads(2)
    fit, output = Path(fit).resolve(), Path(output).resolve()
    problem = RegionalPoseProblem(fit, frame)
    initial, scale = coordinates(problem)
    output.mkdir(parents=True, exist_ok=False)
    snapshot = output/'implementation'; snapshot.mkdir()
    for pattern in ['*.py', '*.gd']:
        for path in (ROOT/'scripts').glob(pattern): shutil.copyfile(path, snapshot/path.name)
    inputs = [fit/n for n in ['protocol.json', 'result.json', 'source-motion.npz', 'motion.npz', 'authored-scene.json', 'recipe.json']]+[ASSET]
    protocol = dict(at=now(), fit=fit.relative_to(ROOT).as_posix(), frame=frame, evaluations=evaluations, seconds_budget=seconds,
        inputs={str(p):sha256(p) for p in inputs}, methods={p.name:sha256(p) for p in snapshot.iterdir()},
        selections=problem.selections, rotation_limits_degrees=dict(zip([problem.names[j] for j in problem.editable],np.rad2deg(problem.limits))),
        max_root_lift_m=problem.config['max_root_lift_m'],
        selection='Smallest maximum normalized original geometric violation, then squared violation sum, among all evaluated bounded poses including the seed.',
        method='Normalized smooth bounded rotation coordinates; trust-region reflective least squares of positive original geometric violations. No geometric condition is omitted.',
        scope='One native pose only. Temporal rates, support, self-collision, anatomy and balance are not established. Failure is not an infeasibility proof.', quality_approved=False)
    save(output/'protocol.json', protocol)
    def mapped(z): return physical_parameters(z*problem.t(scale), problem.limits)
    np.testing.assert_allclose(mapped(problem.t(initial)).numpy(), problem.seed, atol=1e-12, rtol=1e-12)
    def original_pair(z):
        variable = problem.t(z).requires_grad_()
        physical = mapped(variable)
        slack = problem.geometry_slack(physical)
        jac = np.array([torch.autograd.grad(v,variable,retain_graph=True)[0].detach().numpy() for v in slack])
        return slack.detach().numpy(), jac, physical.detach().numpy()
    seed_values, seed_jac, _ = original_pair(initial)
    direction=np.random.default_rng(910).normal(size=len(initial));direction/=np.linalg.norm(direction);h=1e-7
    with torch.no_grad():
        fd=((problem.geometry_slack(mapped(problem.t(initial+h*direction)))-problem.geometry_slack(mapped(problem.t(initial-h*direction))))/(2*h)).numpy()
    np.testing.assert_allclose(seed_jac@direction,fd,atol=2e-4,rtol=2e-4)
    seed_audit,_=problem.independent(problem.seed)
    save(output/'preflight.json',dict(seed=seed_audit,directional_error=float(abs(seed_jac@direction-fd).max()),full_skin_vertices=len(problem.skin['bind_vertices'])))
    start=time.monotonic(); history=[];best=initial.copy();last=initial.copy();cache=None;peak=0
    seed_residual=np.maximum(-seed_values,0.)
    best_key=(float(seed_residual.max()),float(seed_residual@seed_residual))
    def guard():
        nonlocal peak
        rss=psutil.Process().memory_info().rss;peak=max(peak,rss)
        if time.monotonic()-start>seconds or rss>2*1024**3 or psutil.virtual_memory().available<1.25*1024**3:
            raise TimeoutError('Bounded pose resource guard')
    def pair(z):
        nonlocal cache,best,last,best_key
        guard()
        if cache is not None and np.array_equal(z,cache[0]):return cache[1:]
        values,jac,physical=original_pair(z)
        fraction=float((np.linalg.norm(physical[:-1].reshape(-1,3),axis=1)/problem.limits).max())
        if fraction>1+1e-12 or not 0<=physical[-1]<=problem.config['max_root_lift_m']:
            raise ValueError('Bounded coordinate invariant violated')
        residual=np.maximum(-values,0.);jac=-jac*(values<0)[:,None]
        key=(float(residual.max()),float(residual@residual))
        if key<best_key:best=z.copy();best_key=key
        last=z.copy();cache=(z.copy(),residual,jac)
        history.append(dict(evaluation=len(history)+1,seconds=time.monotonic()-start,maximum_violation=key[0],squared_violation=key[1],rotation_budget_fraction=fraction))
        save(output/'progress.json',dict(status='running',pid=psutil.Process().pid,created_at=psutil.Process().create_time(),history=history,best_key=best_key))
        if len(history)%10==0:print(history[-1],flush=True)
        return residual,jac
    lower=np.r_[np.full(len(initial)-1,-np.inf),0.];upper=np.r_[np.full(len(initial)-1,np.inf),1.]
    try:
        result=least_squares(lambda z:pair(z)[0],initial,jac=lambda z:pair(z)[1],bounds=(lower,upper),
            method='trf',tr_solver='exact',max_nfev=evaluations,ftol=1e-12,xtol=1e-12,gtol=1e-10)
        last=result.x;solver=dict(success=bool(result.success),message=str(result.message),evaluations=int(result.nfev));status='complete'
    except TimeoutError as exc:solver=dict(success=False,message=str(exc));status='interrupted_resource_guard'
    parameters=mapped(problem.t(best)).numpy();terminal=mapped(problem.t(last)).numpy()
    audit,motion=problem.independent(parameters);last_audit,last_motion=problem.independent(terminal)
    if not audit['bounds_passed'] or not last_audit['bounds_passed']:raise ValueError('Serialized bounded pose exceeds original edit limits')
    np.savez(output/'pose.npz',**motion);np.savez(output/'terminal-pose.npz',**last_motion)
    with torch.no_grad():_,_,_,vertices=problem.fk(problem.t(parameters))
    skin_error=float(abs(vertices.numpy()-problem.surface.vertices(motion['global_rot_mats'][0],motion['posed_joints'][0])).max())
    if skin_error>2e-6:raise ValueError('Independent skin mismatch')
    for path,digest in protocol['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Input changed')
    for name,digest in protocol['methods'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Method changed')
    save(output/'result.json',dict(at=now(),status=status,solver=solver,seconds=time.monotonic()-start,peak_rss_bytes=peak,
        seed=seed_audit,candidate=audit,terminal=last_audit,parameters=parameters.tolist(),terminal_parameters=terminal.tolist(),
        bounded_preimage=best.tolist(),best_key=best_key,history=history,independent_skin_error_m=skin_error,
        pose_sha256=sha256(output/'pose.npz'),terminal_pose_sha256=sha256(output/'terminal-pose.npz'),protocol_sha256=sha256(output/'protocol.json'),quality_approved=False))
    save(output/'pipeline.json',dict(status=status,pose_witness_passed=audit['pose_witness_passed'],quality_approved=False))
    print(dict(status=status,solver=solver,best_key=best_key,candidate=audit),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('fit',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--frame',type=int,default=96);parser.add_argument('--evaluations',type=int,default=150);parser.add_argument('--seconds',type=float,default=180.)
    a=parser.parse_args()
    with threadpool_limits(limits=2):run(a.fit,a.output,a.frame,a.evaluations,a.seconds)
