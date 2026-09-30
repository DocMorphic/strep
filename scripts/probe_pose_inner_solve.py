"""Capture the actual SciPy TRF inner system; compare only its LSMR cap.

The default solve is returned to SciPy unchanged. Extra solves see the exact
same scaled, augmented operator and right-hand side. This creates diagnostic
linear solutions, not a new accepted pose or a nonlinear convergence proof.
"""
import argparse
import inspect
from pathlib import Path
import shutil
import time
import numpy as np
import psutil
import scipy
import scipy.optimize._lsq.trf as trf
from scipy.optimize import least_squares
import torch
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from regional_pose_witness import RegionalPoseProblem
from regional_pose_bundle import BundleProblem
from regional_pose_full_residual import family_weights
from torch_jacobian_operator import TorchJacobianOperator
from lsmr_accuracy import measure


def run(study,output):
    torch.set_num_threads(2);study=Path(study).resolve();output=Path(output).resolve()
    prior=read(study/'protocol.json');result=read(study/'result.json')
    if result['status']!='complete' or result['protocol_sha256']!=sha256(study/'protocol.json'):raise ValueError('Completed full-residual study required')
    selected=result['variants']['best_cost']
    if sha256(study/selected['pose'])!=selected['pose_sha256']:raise ValueError('Selected pose changed')
    for path,digest in prior['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Input changed')
    for name,digest in prior['methods'].items():
        if sha256(study/'implementation'/name)!=digest:raise ValueError('Method snapshot changed')
    reference=read(ROOT/prior['study']/'protocol.json');p=RegionalPoseProblem(ROOT/reference['fit'],reference['frame']);b=BundleProblem(p)
    x=np.array(selected['bounded_preimage']);weights=p.t(family_weights(b.count,b.groups,b.singles))
    assert b.serialized(x)[1]==selected['audit']
    output.mkdir(parents=True,exist_ok=False);snap=output/'implementation';snap.mkdir()
    for pattern in ['*.py','*.gd']:
        for path in (ROOT/'scripts').glob(pattern):shutil.copyfile(path,snap/path.name)
    trf_path=Path(inspect.getfile(trf));shutil.copyfile(trf_path,output/'scipy-trf.py')
    inputs={**prior['inputs'],**{str(study/n):sha256(study/n) for n in ['protocol.json','result.json',selected['pose']]}}
    protocol=dict(at=now(),study=study.relative_to(ROOT).as_posix(),variant='best_cost',inputs=inputs,
        methods={q.name:sha256(q) for q in snap.iterdir()},scipy_version=scipy.__version__,torch_version=torch.__version__,
        scipy_trf_source=str(trf_path),scipy_trf_sha256=sha256(trf_path),caps=[30,175,500],seconds_budget=180,
        scope='One actual scaled and regularized TRF inner system. Baseline answer is returned unchanged. No nonlinear/pose quality approval.',quality_approved=False)
    save(output/'protocol.json',protocol)
    start=time.monotonic();peak=0;systems=[]
    def guard():
        nonlocal peak
        rss=psutil.Process().memory_info().rss;peak=max(peak,rss)
        if time.monotonic()-start>180 or rss>2*1024**3 or psutil.virtual_memory().available<1.25*1024**3:raise TimeoutError('Inner probe resource guard')
    def residual(z):return torch.relu(b.residual(z))*weights
    def fun(z):
        guard()
        with torch.no_grad():return residual(p.t(z)).numpy()
    original=trf.lsmr
    def capture(a,rhs,**options):
        if systems:raise ValueError('Unexpected second inner system')
        if options!=dict(maxiter=30):raise ValueError('Unexpected baseline inner options')
        baseline,record=measure(a,rhs,options,original)
        comparison=dict(shape=list(a.shape),rhs_norm=float(np.linalg.norm(rhs)),solves=[record]);systems.append(comparison)
        save(output/'progress.json',dict(status='running',pid=psutil.Process().pid,created_at=psutil.Process().create_time(),systems=systems))
        for cap in [175,500]:
            guard();_,other=measure(a,rhs,{**options,'maxiter':cap},original)
            comparison['solves'].append(other)
            save(output/'progress.json',dict(status='running',pid=psutil.Process().pid,created_at=psutil.Process().create_time(),systems=systems))
            print({k:v for k,v in other.items() if k!='solution'},flush=True)
            if other['stop_code']!=7:break
        return baseline
    trf.lsmr=capture
    try:
        lower=np.r_[np.full(len(x)-1,-np.inf),0.];upper=np.r_[np.full(len(x)-1,np.inf),1.]
        fit=least_squares(fun,x,jac=lambda z:TorchJacobianOperator(residual,z,guard),bounds=(lower,upper),
            method='trf',tr_solver='lsmr',tr_options=dict(maxiter=30),max_nfev=2,ftol=1e-12,xtol=1e-12,gtol=1e-10)
        status='complete';outer=dict(message=str(fit.message),evaluations=int(fit.nfev),initial_cost=selected['squared_weighted_residual'],returned_cost=float(2*fit.cost))
    except TimeoutError as exc:status='interrupted_resource_guard';outer=dict(message=str(exc))
    finally:trf.lsmr=original
    if sha256(trf_path)!=protocol['scipy_trf_sha256']:raise ValueError('SciPy source changed')
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Input changed')
    for name,digest in protocol['methods'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Method changed')
    save(output/'result.json',dict(at=now(),status=status,systems=systems,outer=outer,seconds=time.monotonic()-start,peak_rss_bytes=peak,
        scipy_function_restored=trf.lsmr is original,protocol_sha256=sha256(output/'protocol.json'),quality_approved=False))
    print(dict(status=status,outer=outer,seconds=time.monotonic()-start),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('output',type=Path);a=parser.parse_args()
    with threadpool_limits(limits=2):run(a.study,a.output)
