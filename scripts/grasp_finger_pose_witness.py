"""Freeze a reachable body pose and test bounded finger-only clearance."""
import argparse
import shutil
import time
from pathlib import Path
import numpy as np
import torch
from scipy.optimize import least_squares
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from grasp_pose_witness import PoseProblem,BODY
from grasp_pose_witness_bounded import inverse_rotation_bound,physical_parameters


def run(study,seed_report,output):
    torch.set_num_threads(2);study=Path(study).resolve();seed_report=Path(seed_report).resolve();output=Path(output).resolve()
    fit=study/'fit';summary=read(fit/'summary.json');seed_record=read(seed_report/'result.json');seed_protocol=read(seed_report/'protocol.json');frame=seed_protocol['frame']
    if summary['solver_version']!=13 or seed_protocol['fit_summary_sha256']!=sha256(fit/'summary.json'):raise ValueError('Seed study mismatch')
    if sha256(seed_report/'pose.npz')!=seed_record['pose_sha256'] or sha256(ASSET)!=summary['mesh_sha256']:raise ValueError('Seed/mesh changed')
    for name,digest in seed_protocol['inputs'].items():
        if sha256(ROOT/name)!=digest:raise ValueError('Seed input changed')
    folder=fit/'assets'/summary['trials'][0]['id']/'A';p=PoseProblem(folder,dict(np.load(ASSET,allow_pickle=False)),frame)
    physical_seed=np.array(seed_record['parameters']);seed_audit,_=p.independent(physical_seed)
    if not seed_audit['rotation_norm_bounds_passed']:raise ValueError('Seed violates original budgets')
    initial=np.r_[inverse_rotation_bound(physical_seed[:-1].reshape(-1,3),p.limits).ravel(),physical_seed[-1]]
    free=np.arange(3*len(BODY),p.dim-1);indices=torch.tensor(free,dtype=torch.long);constant=p.t(initial)
    def expand(values):return constant.index_copy(0,indices,values)
    output.mkdir(parents=True,exist_ok=False);snap=output/'implementation';snap.mkdir()
    methods=['grasp_finger_pose_witness.py','grasp_pose_witness.py','grasp_pose_witness_bounded.py','support_contact_v8.py','support_contact_v5.py','floor_contact.py','scene_solver_context.py','object_geometry.py']
    protocol=dict(at=now(),study=study.relative_to(ROOT).as_posix(),frame=frame,seed_result_sha256=sha256(seed_report/'result.json'),seed_protocol_sha256=sha256(seed_report/'protocol.json'),inputs=seed_protocol['inputs'],fit_summary_sha256=sha256(fit/'summary.json'),implementation={n:sha256(ROOT/'scripts'/n) for n in methods},smooth_max_m=.0001,evaluation_limit=300,time_limit_seconds=240,free_joint_names=[p.names[j] for j in p.editable[len(BODY):]],fixed='All body rotations and root lift at point-reachable seed; 38 finger rotation norm budgets remain relative to the original preprocessed pose.',scope='More restrictive pose-only diagnostic. No full-clip, anatomy, self-collision or dynamics proof. Every original point/normal/full-skin/floor gate independently checked; no relaxed target accepted.',quality_approved=False)
    save(output/'protocol.json',protocol)
    for n in methods:shutil.copyfile(ROOT/'scripts'/n,snap/n)
    start=time.monotonic();history=[];cache=None;best=initial[free].copy();best_key=(float('inf'),float('inf'))
    def pair(x):
        nonlocal cache,best,best_key
        if cache is not None and np.array_equal(cache[0],x):return cache[1:]
        variable=p.t(x).requires_grad_();mapped=physical_parameters(expand(variable),p.limits);slack=p.geometry_slack(mapped,.0001);residual=torch.relu(-slack)
        jac=np.array([torch.autograd.grad(value,variable,retain_graph=True)[0].detach().numpy() if float(value.detach())>0 else np.zeros(len(x)) for value in residual]);values=residual.detach().numpy();key=(float(values.max()),float(values@values))
        if key<best_key:best=x.copy();best_key=key
        history.append(dict(evaluation=len(history)+1,seconds=time.monotonic()-start,maximum_normalized_violation=key[0],squared_violation=key[1],slack=dict(zip(p.labels,slack.detach().numpy().tolist()))));cache=(x.copy(),values,jac)
        if len(history)%25==0:save(output/'progress.json',dict(status='running',history=history,best_key=best_key));print(dict(evaluations=len(history),worst=key[0],best=best_key[0]),flush=True)
        if time.monotonic()-start>240:raise TimeoutError('Diagnostic time guard')
        return values,jac
    try:
        result=least_squares(lambda x:pair(x)[0],initial[free],jac=lambda x:pair(x)[1],method='trf',tr_solver='lsmr',max_nfev=300,ftol=1e-12,xtol=1e-12,gtol=1e-10)
        solver=dict(success=bool(result.success),message=str(result.message),evaluations=int(result.nfev));status='complete';last=result.x
    except TimeoutError as e:solver=dict(success=False,message=str(e));status='interrupted_resource_guard';last=cache[0]
    parameters=physical_parameters(expand(p.t(best)),p.limits).detach().numpy();audit,motion=p.independent(parameters)
    np.testing.assert_allclose(parameters[:3*len(BODY)],physical_seed[:3*len(BODY)],atol=1e-12,rtol=1e-12)
    assert parameters[-1]==physical_seed[-1]
    with torch.no_grad():_,_,_,v=p.fk(p.t(parameters))
    nv=p.surface.vertices(motion['global_rot_mats'][0],motion['posed_joints'][0]);error=float(np.max(np.abs(v.numpy()-nv)))
    if error>2e-6:raise ValueError('Independent full skin mismatch')
    last_parameters=physical_parameters(expand(p.t(last)),p.limits).detach().numpy();last_audit,_=p.independent(last_parameters)
    for name,digest in protocol['inputs'].items():
        if sha256(ROOT/name)!=digest:raise ValueError('Input changed')
    for name,digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Implementation changed')
    np.savez(output/'pose.npz',**motion)
    save(output/'result.json',dict(at=now(),status=status,solver=solver,seconds=time.monotonic()-start,seed=seed_audit,candidate=audit,final_solver_candidate=last_audit,parameters=parameters.tolist(),history=history,body_and_root_unchanged=True,independent_skin_max_error_m=error,pose_sha256=sha256(output/'pose.npz'),protocol_sha256=sha256(output/'protocol.json'),quality_approved=False))
    save(output/'pipeline.json',dict(status=status,pose_witness_passed=audit['pose_witness_passed'],quality_approved=False));print(dict(status=status,solver=solver,audit=audit),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('seed_report',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    with threadpool_limits(limits=2):run(args.study,args.seed_report,args.output)
