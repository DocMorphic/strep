import sys
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read
from rig_asset import RigAsset
from target_rig_contact import baseline
from analytic_patch_contact import AnalyticPatchFitter
from temporal_patch_frame import evaluate,pose_budget_pair
from types import SimpleNamespace


def test_temporal_objective_and_inequality_gradients():
    spec=read(ROOT/'reports/target-rig-contact-v1/specs/wave.json')
    rig=RigAsset.load(ROOT/'reports/rig-axis-calibration-v1/wave/character.glb')
    _,local=baseline(rig,spec['frames']);fit=AnalyticPatchFitter(rig,spec,local)
    x=fit.bounds*np.linspace(-.2,.2,len(fit.bounds));neighbors=[x*.8,x*.9]
    with threadpool_limits(limits=1):
        _,grad,_,jac=evaluate(fit,25,x,neighbors)
        ng=[];nj=[]
        for i in range(len(x)):
            step=np.zeros(len(x));step[i]=1e-6
            a=evaluate(fit,25,x+step,neighbors);b=evaluate(fit,25,x-step,neighbors)
            ng.append((a[0]-b[0])/2e-6);nj.append((a[2]-b[2])/2e-6)
    np.testing.assert_allclose(grad,ng,atol=1e-6,rtol=1e-5)
    np.testing.assert_allclose(jac,np.array(nj).T,atol=1e-5,rtol=5e-5)


def test_true_rotation_budget_accepts_single_axis_and_rejects_diagonal_overrun():
    fit=SimpleNamespace(spec={'limits':{'root_horizontal_m':.04,'root_vertical_m':.12}},angles=np.array([.6]))
    x=np.zeros(6);x[3]=.5
    assert pose_budget_pair(fit,x)[0].min()>=0 # Valid even beyond old .6/sqrt3 box.
    x[4]=.5
    assert pose_budget_pair(fit,x)[0][-1]<0 # Two large components exceed the same norm budget.
