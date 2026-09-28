import sys
from pathlib import Path
import numpy as np
import pytest
from threadpoolctl import threadpool_limits
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read
from rig_asset import RigAsset
from target_rig_contact import baseline
from analytic_patch_contact import AnalyticPatchFitter
from temporal_patch_frame import evaluate as original
from reference_temporal_patch_frame import evaluate


@pytest.fixture(scope='module')
def fixture():
    spec=read(ROOT/'reports/target-rig-contact-v1/specs/wave.json')
    rig=RigAsset.load(ROOT/'reports/rig-axis-calibration-v1/wave/character.glb')
    _,local=baseline(rig,spec['frames']);fit=AnalyticPatchFitter(rig,spec,local)
    x=fit.bounds*np.linspace(-.2,.2,len(fit.bounds));return fit,x,[x*.8,x*.9]


def test_zero_reference_reproduces_previous_objective_and_constraints(fixture):
    fit,x,neighbors=fixture
    with threadpool_limits(limits=1):
        a=original(fit,25,x,neighbors);b=evaluate(fit,25,x,neighbors,np.zeros_like(x),[np.zeros_like(x)]*2)
    for av,bv in zip(a,b):np.testing.assert_allclose(av,bv,atol=1e-12,rtol=1e-12)


def test_reference_changes_priors_without_changing_hard_constraints(fixture):
    fit,x,neighbors=fixture;reference=x*.5;refs=[x*.3,x*.4]
    with threadpool_limits(limits=1):
        old=original(fit,25,x,neighbors);new=evaluate(fit,25,x,neighbors,reference,refs)
        np.testing.assert_array_equal(old[2],new[2]);np.testing.assert_array_equal(old[3],new[3])
        numeric=[]
        for i in range(len(x)):
            step=np.zeros_like(x);step[i]=1e-6
            a=evaluate(fit,25,x+step,neighbors,reference,refs)[0]
            b=evaluate(fit,25,x-step,neighbors,reference,refs)[0]
            numeric.append((a-b)/2e-6)
    np.testing.assert_allclose(new[1],numeric,atol=1e-6,rtol=1e-5)


def test_missing_neighbor_reference_is_rejected(fixture):
    fit,x,neighbors=fixture
    with pytest.raises(ValueError):evaluate(fit,25,x,neighbors,x,[x])
