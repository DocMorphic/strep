import sys
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT, read
from target_rig_contact import RigAsset,Fitter,baseline
from analytic_patch_contact import AnalyticPatchFitter


def fixture():
    spec=read(ROOT/'reports/target-rig-contact-v1/specs/wave.json')
    rig=RigAsset.load(ROOT/'reports/rig-axis-calibration-v1/wave/character.glb')
    _,local=baseline(rig,spec['frames'])
    return rig,spec,local


def test_same_residual_as_existing_authored_contact_objective():
    rig,spec,local=fixture()
    new=AnalyticPatchFitter(rig,spec,local);old=Fitter(rig,spec,local)
    x=new.bounds*np.linspace(-.4,.4,len(new.bounds))
    with threadpool_limits(limits=1):
        for frame in [0,25,119]:
            np.testing.assert_allclose(new.residual_pair(frame,x,x*.5)[0],old.residual(frame,x,x*.5),atol=1e-11,rtol=1e-10)


def test_analytic_derivative_matches_independent_finite_differences():
    rig,spec,local=fixture();fit=AnalyticPatchFitter(rig,spec,local)
    x=fit.bounds*np.linspace(-.3,.3,len(fit.bounds));previous=x*.3
    with threadpool_limits(limits=1):
        _,jac=fit.residual_pair(25,x,previous)
        numeric=[]
        # Independent legacy residual, not the new residual implementation.
        old=Fitter(rig,spec,local)
        for i in range(len(x)):
            step=np.zeros(len(x));step[i]=1e-6
            numeric.append((old.residual(25,x+step,previous)-old.residual(25,x-step,previous))/2e-6)
    np.testing.assert_allclose(jac,np.array(numeric).T,atol=2e-6,rtol=3e-5)
