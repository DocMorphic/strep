"""Exploratory bounded least squares over every regional clearance residual.

Matrix-free Jacobian products avoid a dense skin-by-parameter derivative table.
Intermediate tradeoffs are allowed; original serialized pose acceptance is not
relaxed. Best-peak, best-cost and terminal outputs are retained independently.
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
from strep import ROOT,read,save,sha256,now
from regional_pose_witness import RegionalPoseProblem
from regional_pose_bundle import BundleProblem
from torch_jacobian_operator import TorchJacobianOperator


def family_weights(count,groups,singles):
    weights=np.ones(count,dtype=float);covered=[]
    for group in groups:
        ids=np.asarray(group,dtype=int)
        if not len(ids) or np.any(ids<0) or np.any(ids>=count):raise ValueError('Invalid clearance family')
        weights[ids]=1/np.sqrt(len(ids));covered.extend(ids.tolist())
    if len(singles)%13:raise ValueError('Regional scalar layout mismatch')
    covered.extend(singles)
    if sorted(covered)!=list(range(count)):raise ValueError('Residual families must partition every row exactly once')
    for start in range(0,len(singles),13):
        for offset in [0,3,6]:weights[np.array(singles[start+offset:start+offset+3])]=1/np.sqrt(3)
    return weights


def read_warm_start(path,variant,study,prior):
    path=Path(path).resolve();study=Path(study).resolve()
    if variant not in ['best_peak','best_cost','terminal']:raise ValueError('Unknown warm-start variant')
    protocol=read(path/'protocol.json');result=read(path/'result.json')
    if result['status'] not in ['complete','interrupted_resource_guard'] or result['protocol_sha256']!=sha256(path/'protocol.json'):
        raise ValueError('Completed or resource-stopped full-residual result required')
    if protocol['study']!=study.relative_to(ROOT).as_posix():raise ValueError('Warm start belongs to a different source study')
    for key in ['selections','rotation_limits_degrees','max_root_lift_m']:
        if protocol[key]!=prior[key]:raise ValueError('Warm-start controls changed: '+key)
    for file,digest in protocol['inputs'].items():
        if sha256(file)!=digest:raise ValueError('Warm-start input changed')
    for name,digest in protocol['methods'].items():
        if sha256(path/'implementation'/name)!=digest:raise ValueError('Warm-start archived method changed')
    selected=result['variants'][variant]
    if not selected['audit']['bounds_passed'] or sha256(path/selected['pose'])!=selected['pose_sha256']:
        raise ValueError('Warm-start pose changed or failed bounds')
    inputs={**protocol['inputs'],**{str(path/n):sha256(path/n) for n in ['protocol.json','result.json',selected['pose']]}}
    return selected,inputs,dict(study=path.relative_to(ROOT).as_posix(),variant=variant,result_sha256=sha256(path/'result.json'))


def run(study,output,evaluations=150,seconds=180.,lsmr_iterations=30,warm_start=None,variant='best_cost',linear_solver='lsmr'):
    if type(evaluations) is not int or not 1<=evaluations<=500 or type(seconds) not in [int,float] or not np.isfinite(seconds) or not 0<seconds<=1200:
        raise ValueError('Bounded solve budgets required')
    if type(lsmr_iterations) is not int or not 1<=lsmr_iterations<=500:raise ValueError('Bounded positive LSMR iteration cap required')
    if linear_solver not in ['lsmr','exact']:raise ValueError('Unknown trust-region linear solver')
    torch.set_num_threads(2);study=Path(study).resolve();output=Path(output).resolve()
    previous=read(study/'result.json');prior=read(study/'protocol.json')
    if previous['status']!='complete' or not previous['candidate']['bounds_passed']:raise ValueError('Completed bounded study required')
    if sha256(study/'protocol.json')!=previous['protocol_sha256'] or sha256(study/'pose.npz')!=previous['pose_sha256']:raise ValueError('Seed artifacts changed')
    for path,digest in prior['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Input changed')
    for name,digest in prior['methods'].items():
        if sha256(study/'implementation'/name)!=digest:raise ValueError('Archived seed method changed')
    p=RegionalPoseProblem(ROOT/prior['fit'],prior['frame']);b=BundleProblem(p)
    selected=previous;expected_seed=previous['candidate'];warm_inputs={};warm_descriptor=None
    if warm_start is not None:
        selected,warm_inputs,warm_descriptor=read_warm_start(warm_start,variant,study,prior)
        expected_seed=selected['audit']
    initial=np.array(selected['bounded_preimage']);np.testing.assert_array_equal(b.physical(p.t(initial)).numpy(),selected['parameters'])
    weights=family_weights(b.count,b.groups,b.singles);tw=p.t(weights)
    output.mkdir(parents=True,exist_ok=False);snap=output/'implementation';snap.mkdir()
    for pattern in ['*.py','*.gd']:
        for path in (ROOT/'scripts').glob(pattern):shutil.copyfile(path,snap/path.name)
    inputs={**prior['inputs'],**warm_inputs,**{str(study/n):sha256(study/n) for n in ['protocol.json','result.json','pose.npz']}}
    protocol=dict(at=now(),study=study.relative_to(ROOT).as_posix(),inputs=inputs,methods={q.name:sha256(q) for q in snap.iterdir()},
        selections=prior['selections'],rotation_limits_degrees=prior['rotation_limits_degrees'],max_root_lift_m=prior['max_root_lift_m'],
        evaluations=evaluations,seconds_budget=seconds,linear_solver=linear_solver,
        lsmr_maxiter=lsmr_iterations if linear_solver=='lsmr' else None,dense_allocation_limit_bytes=128*1024**2,
        warm_start=warm_descriptor,full_residual_count=b.count,
        weighting='Squared residual means per full-skin/patch clearance family; means per gap/radius/spacing triple; unit weight for area/centroid/normal/anchor. Every row has positive weight; zero residual requires all original modeled inequalities.',
        selection='Retain lexicographically smallest (maximum unweighted violation, weighted squared residual), smallest weighted squared residual, and terminal point separately; include seed. No variant is promoted automatically.',
        scope='Exploratory single-pose feasibility; intermediate regression allowed. Original independent serialized contact/geometry/edit thresholds unchanged. No temporal, anatomy, balance, support, engine or human-review approval.',quality_approved=False)
    save(output/'protocol.json',protocol)
    seed_serial,seed_audit,_,_=b.serialized(initial);assert seed_audit==expected_seed
    def residual(z):return torch.relu(b.residual(z))*tw
    op=TorchJacobianOperator(residual,initial)
    direction=np.random.default_rng(929).normal(size=len(initial));direction/=np.linalg.norm(direction)
    cot=np.random.default_rng(930).normal(size=b.count);cot/=np.linalg.norm(cot);h=1e-7
    with torch.no_grad():fd=((residual(p.t(initial+h*direction))-residual(p.t(initial-h*direction)))/(2*h)).numpy()
    jv=op@direction;np.testing.assert_allclose(jv,fd,atol=2e-4,rtol=2e-4)
    adjoint_error=float(abs(cot@jv-direction@(op.T@cot)))
    if adjoint_error>1e-8:raise ValueError('Jacobian transpose identity failed')
    save(output/'preflight.json',dict(seed=seed_audit,directional_error=float(abs(jv-fd).max()),adjoint_error=adjoint_error,
        operator_shape=op.shape,weight_range=[float(weights.min()),float(weights.max())]))
    del op
    with torch.no_grad():seed_raw=b.residual(p.t(initial)).numpy()
    seed_weighted=np.maximum(seed_raw,0)*weights
    best_peak=initial.copy();best_cost=initial.copy();last=initial.copy()
    peak_key=(float(max(0.,seed_raw.max())),float(seed_weighted@seed_weighted));cost_key=peak_key[1]
    start=time.monotonic();history=[];peak_rss=0;operators=0;products=dict(forward=0,transpose=0)
    active_operator=None
    def guard():
        nonlocal peak_rss
        rss=psutil.Process().memory_info().rss;peak_rss=max(peak_rss,rss)
        if time.monotonic()-start>seconds or rss>2*1024**3 or psutil.virtual_memory().available<1.25*1024**3:raise TimeoutError('Full residual resource guard')
    def fun(z):
        nonlocal best_peak,best_cost,last,peak_key,cost_key
        guard()
        with torch.no_grad():raw=b.residual(p.t(z)).numpy();physical=b.physical(p.t(z)).numpy()
        fraction=float((np.linalg.norm(physical[:-1].reshape(-1,3),axis=1)/p.limits).max())
        if fraction>1+1e-12 or not 0<=physical[-1]<=p.config['max_root_lift_m']:raise ValueError('Bounded parameter invariant failed')
        weighted=np.maximum(raw,0)*weights;cost=float(weighted@weighted);key=(float(max(0.,raw.max())),cost)
        if key<peak_key:peak_key=key;best_peak=z.copy()
        if cost<cost_key:cost_key=cost;best_cost=z.copy()
        last=z.copy()
        history.append(dict(evaluation=len(history)+1,seconds=time.monotonic()-start,maximum_violation=key[0],squared_weighted_residual=cost,rotation_budget_fraction=fraction))
        save(output/'progress.json',dict(status='running',pid=psutil.Process().pid,created_at=psutil.Process().create_time(),history=history,best_peak=peak_key,best_cost=cost_key))
        if len(history)%10==0:print(history[-1],flush=True)
        return weighted
    def jac(z):
        nonlocal active_operator,operators
        if active_operator is not None:
            for key in products:products[key]+=active_operator.products[key]
        active_operator=None
        active_operator=TorchJacobianOperator(residual,z,guard);operators+=1
        return active_operator if linear_solver=='lsmr' else active_operator.to_dense(protocol['dense_allocation_limit_bytes'])
    lower=np.r_[np.full(len(initial)-1,-np.inf),0.];upper=np.r_[np.full(len(initial)-1,np.inf),1.]
    try:
        fit=least_squares(fun,initial,jac=jac,bounds=(lower,upper),method='trf',tr_solver=linear_solver,
            tr_options=dict(maxiter=protocol['lsmr_maxiter']) if linear_solver=='lsmr' else {},
            max_nfev=evaluations,ftol=1e-12,xtol=1e-12,gtol=1e-10)
        last=fit.x;solver=dict(success=bool(fit.success),message=str(fit.message),evaluations=int(fit.nfev));status='complete'
    except TimeoutError as exc:solver=dict(success=False,message=str(exc));status='interrupted_resource_guard'
    if active_operator is not None:
        for key in products:products[key]+=active_operator.products[key]
    variants={}
    for name,z in [('best_peak',best_peak),('best_cost',best_cost),('terminal',last)]:
        serial,audit,motion,physical=b.serialized(z)
        if not audit['bounds_passed']:raise ValueError('Serialized edit bounds failed')
        with torch.no_grad():raw=b.residual(p.t(z)).numpy()
        filename=name+'.npz';np.savez(output/filename,**motion)
        variants[name]=dict(audit=audit,parameters=physical.tolist(),bounded_preimage=z.tolist(),
            maximum_violation=float(max(0.,raw.max())),squared_weighted_residual=float(np.square(np.maximum(raw,0)*weights).sum()),
            serialized_maximum_violation=float(max(0.,serial.max())),pose=filename,pose_sha256=sha256(output/filename))
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Input changed')
    for name,digest in protocol['methods'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Method changed')
    save(output/'result.json',dict(at=now(),status=status,solver=solver,seconds=time.monotonic()-start,peak_rss_bytes=peak_rss,operators=operators,products=products,
        seed=seed_audit,seed_maximum_violation=float(seed_raw.max()),seed_weighted_cost=float(seed_weighted@seed_weighted),
        variants=variants,history=history,protocol_sha256=sha256(output/'protocol.json'),quality_approved=False))
    save(output/'pipeline.json',dict(status=status,pose_witness_passed=any(v['audit']['pose_witness_passed'] for v in variants.values()),quality_approved=False))
    print(dict(status=status,solver=solver,variants={k:v['audit'] for k,v in variants.items()}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--evaluations',type=int,default=150);parser.add_argument('--seconds',type=float,default=180.)
    parser.add_argument('--lsmr-iterations',type=int,default=30);parser.add_argument('--warm-start',type=Path)
    parser.add_argument('--variant',choices=['best_peak','best_cost','terminal'],default='best_cost')
    parser.add_argument('--linear-solver',choices=['lsmr','exact'],default='lsmr')
    a=parser.parse_args()
    with threadpool_limits(limits=2):run(a.study,a.output,a.evaluations,a.seconds,a.lsmr_iterations,a.warm_start,a.variant,a.linear_solver)
