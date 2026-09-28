"""Bounded least-squares pose feasibility diagnostic; no animation approval."""
import argparse
import shutil
import time
from pathlib import Path
import numpy as np
import psutil
import torch
from scipy.optimize import least_squares
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from grasp_pose_witness import PoseProblem
from support_contact_v8 import bounded_rotation


def inverse_rotation_bound(theta,limits):
    theta=np.asarray(theta);limits=np.asarray(limits)
    fraction=np.sum(theta**2,axis=-1)/limits**2
    if np.any(fraction>=1):raise ValueError('Seed must lie strictly inside rotation norm budgets')
    return theta/np.sqrt(1-fraction)[:,None]


def physical_parameters(parameters,limits):
    limits=torch.as_tensor(limits,dtype=parameters.dtype)[:,None]
    angles=bounded_rotation(parameters[:-1].reshape(-1,3)/limits,limits)
    return torch.cat([angles.reshape(-1),parameters[-1:]])


class WitnessFound(Exception):pass


def run(study,output,frame=60,smooth_max_m=0.,jacobian_scale=False,constraint_groups='full'):
    torch.set_num_threads(2);study=Path(study).resolve();output=Path(output).resolve();fit=study/'fit';summary=read(fit/'summary.json')
    if summary['solver_version']!=13 or read(study/'pipeline.json')['status']!='complete':raise ValueError('Completed V13 required')
    if sha256(ASSET)!=summary['mesh_sha256']:raise ValueError('Mesh changed')
    folder=fit/'assets'/summary['trials'][0]['id']/'A';skin=dict(np.load(ASSET,allow_pickle=False));p=PoseProblem(folder,skin,frame)
    if constraint_groups not in ['full','points','points_geometry']:raise ValueError('Unknown diagnostic constraint relaxation')
    keep=np.array([constraint_groups=='full' or label.startswith('point:') or (constraint_groups=='points_geometry' and not label.startswith('normal:')) for label in p.labels])
    output.mkdir(parents=True,exist_ok=False)
    implementation=['grasp_pose_witness_bounded.py','grasp_pose_witness.py','support_contact_v8.py','support_contact_v5.py','floor_contact.py','scene_solver_context.py','object_geometry.py','inspect_motion.py']
    inputs=[folder/n for n in ['limb-motion.npz','previous-motion.npz','motion.npz','recipe.json']]+[ASSET]
    limits=dict(evaluations=300,seconds=240,maximum_rss_bytes=2*1024**3,minimum_available_bytes=int(1.25*1024**3))
    protocol=dict(at=now(),frame=frame,constraint_groups=constraint_groups,optimized_constraints=[label for label,active in zip(p.labels,keep) if active],omitted_constraints=[label for label,active in zip(p.labels,keep) if not active],relaxation_warning='Diagnostic only. Independent final pose audit always enforces ALL original targets; relaxed optimization success is not a full witness.',smooth_max_m=smooth_max_m,x_scale='jac' if jacobian_scale else 1.,smoothing_scope='Optional unnormalized log-sum-exp upper bound on geometric max violations. Conservative optimization surrogate; independent exact geometry gates unchanged.',study=study.relative_to(ROOT).as_posix(),fit_summary_sha256=sha256(fit/'summary.json'),limits=limits,inputs={path.relative_to(ROOT).as_posix():sha256(path) for path in inputs},implementation={n:sha256(ROOT/'scripts'/n) for n in implementation},rotation_limits_degrees=dict(zip([p.names[j] for j in p.editable],np.rad2deg(p.limits))),max_root_lift_m=p.config['max_root_lift_m'],point_tolerance_m=p.config['point_tolerance_m'],normal_tolerance_degrees=p.config['normal_tolerance_degrees'],full_skin_clearance_m=p.config['object_clearance_m'],selection='Smallest maximum normalized violation, then squared violation sum, among visited bounded parameter vectors.',change='SLSQP with nonlinear norm inequalities replaced by hard bounded rotation coordinates and trust-region least squares of violation residuals. Removes seed-distance objective. Same geometry targets, physical edit limits and seed pose; not a one-factor ablation.',scope='Single pose necessary-condition relaxation. No temporal basis, velocity, acceleration, inferred support tracking, balance, self-collision or anatomy. Full skin replaces the clip solver collision sample. Success is only a pose witness; failure is not infeasibility proof.',quality_approved=False)
    save(output/'protocol.json',protocol);snap=output/'implementation';snap.mkdir()
    for n in implementation:shutil.copyfile(ROOT/'scripts'/n,snap/n)
    initial=np.r_[inverse_rotation_bound(p.seed[:-1].reshape(-1,3),p.limits).ravel(),p.seed[-1]]
    mapped=physical_parameters(p.t(initial),p.limits).numpy();np.testing.assert_allclose(mapped,p.seed,atol=1e-12,rtol=1e-12)
    with torch.no_grad():r,positions,_,_=p.fk(p.t(mapped))
    error=max(float(np.abs(r.numpy()-p.candidate['global_rot_mats'][frame]).max()),float(np.abs(positions.numpy()-p.candidate['posed_joints'][frame]).max()))
    if error>2e-6:raise ValueError('Mapped seed differs from V13')
    directional_error=None
    if smooth_max_m>0:
        variable=p.t(initial).requires_grad_();slack=p.geometry_slack(physical_parameters(variable,p.limits),smooth_max_m)
        jacobian=np.array([torch.autograd.grad(value,variable,retain_graph=True)[0].detach().numpy() for value in slack])
        direction=np.random.default_rng(716).normal(size=p.dim);direction/=np.linalg.norm(direction);h=1e-6
        with torch.no_grad():
            plus=p.geometry_slack(physical_parameters(p.t(initial+h*direction),p.limits),smooth_max_m)
            minus=p.geometry_slack(physical_parameters(p.t(initial-h*direction),p.limits),smooth_max_m)
            fd=((plus-minus)/(2*h)).numpy()
        np.testing.assert_allclose(jacobian@direction,fd,atol=2e-5,rtol=2e-4)
        directional_error=float(np.abs(jacobian@direction-fd).max())
    save(output/'preflight.json',dict(seed_fk_error=error,all_smooth_geometry_directional_error=directional_error))
    start=time.monotonic();history=[];best=initial.copy();best_key=(float('inf'),float('inf'));cache=None;peak=0
    def pair(x):
        nonlocal cache,best,best_key,peak
        if cache is not None and np.array_equal(cache[0],x):return cache[1:]
        variable=p.t(x).requires_grad_();physical=physical_parameters(variable,p.limits);slack=p.geometry_slack(physical,smooth_max_m);residual=torch.relu(-slack[keep])
        jac=np.array([torch.autograd.grad(value,variable,retain_graph=True)[0].detach().numpy() if float(value.detach())>0 else np.zeros(p.dim) for value in residual])
        values=residual.detach().numpy();key=(float(values.max()),float(values@values))
        if key<best_key:best=x.copy();best_key=key
        fraction=float((torch.linalg.vector_norm(physical[:-1].reshape(-1,3),dim=-1)/p.t(p.limits)).max().detach())
        if fraction>1+1e-12 or not 0<=x[-1]<=p.config['max_root_lift_m']:raise ValueError('Hard parameter bound violation')
        rss=psutil.Process().memory_info().rss;peak=max(peak,rss)
        history.append(dict(evaluation=len(history)+1,seconds=time.monotonic()-start,maximum_normalized_violation=key[0],squared_violation=key[1],rotation_budget_fraction=fraction,slack=dict(zip(p.labels,slack.detach().numpy().tolist()))))
        cache=(x.copy(),values,jac)
        if len(history)%10==0:
            save(output/'progress.json',dict(status='running',pid=psutil.Process().pid,created=psutil.Process().create_time(),history=history,best_key=best_key,sampled_peak_rss_bytes=peak))
            print(dict(evaluations=len(history),worst=key[0],best=best_key[0],seconds=time.monotonic()-start),flush=True)
        if key[0]<1e-8:raise WitnessFound()
        if time.monotonic()-start>limits['seconds'] or rss>limits['maximum_rss_bytes'] or psutil.virtual_memory().available<limits['minimum_available_bytes']:raise TimeoutError('Diagnostic resource guard')
        return values,jac
    lower=np.r_[np.full(p.dim-1,-np.inf),0.];upper=np.r_[np.full(p.dim-1,np.inf),p.config['max_root_lift_m']]
    try:
        result=least_squares(lambda x:pair(x)[0],initial,jac=lambda x:pair(x)[1],bounds=(lower,upper),method='trf',tr_solver='lsmr',x_scale='jac' if jacobian_scale else 1.,max_nfev=limits['evaluations'],ftol=1e-12,xtol=1e-12,gtol=1e-10)
        solver=dict(success=bool(result.success),message=str(result.message),evaluations=int(result.nfev));status='complete';last=result.x
    except WitnessFound:solver=dict(success=None,message='Stopped at selected normalized violations below 1e-8; independent pose validation decides success');status='complete';last=best
    except TimeoutError as e:solver=dict(success=False,message=str(e));status='interrupted_resource_guard';last=cache[0]
    parameters=physical_parameters(p.t(best),p.limits).detach().numpy();audit,motion=p.independent(parameters);seed_audit,_=p.independent(p.seed)
    final_parameters=physical_parameters(p.t(last),p.limits).detach().numpy();final_audit,_=p.independent(final_parameters)
    with torch.no_grad():_,_,_,vertices=p.fk(p.t(parameters))
    independent=p.surface.vertices(motion['global_rot_mats'][0],motion['posed_joints'][0]);skin_error=float(np.max(np.abs(vertices.numpy()-independent)))
    if skin_error>2e-6:raise ValueError('Independent skin mismatch')
    for name,digest in protocol['inputs'].items():
        if sha256(ROOT/name)!=digest:raise ValueError('Input changed')
    for n,digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/n)!=digest:raise ValueError('Implementation changed')
    np.savez(output/'pose.npz',**motion)
    save(output/'result.json',dict(at=now(),status=status,solver=solver,seconds=time.monotonic()-start,sampled_peak_rss_bytes=peak,seed=seed_audit,candidate=audit,final_solver_candidate=final_audit,parameters=parameters.tolist(),bounded_preimage=best.tolist(),history=history,seed_fk_error=error,independent_skin_max_error_m=skin_error,full_skin_vertices=len(skin['bind_vertices']),pose_sha256=sha256(output/'pose.npz'),protocol_sha256=sha256(output/'protocol.json'),quality_approved=False))
    save(output/'pipeline.json',dict(status=status,pose_witness_passed=audit['pose_witness_passed'],quality_approved=False));print(dict(status=status,solver=solver,audit=audit),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--frame',type=int,default=60);parser.add_argument('--smooth-max-m',type=float,default=0.);parser.add_argument('--jacobian-scale',action='store_true');parser.add_argument('--constraint-groups',choices=['full','points','points_geometry'],default='full');args=parser.parse_args()
    with threadpool_limits(limits=2):run(args.study,args.output,args.frame,args.smooth_max_m,args.jacobian_scale,args.constraint_groups)
