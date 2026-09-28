import sys
from pathlib import Path
import numpy as np
import pytest
from threadpoolctl import threadpool_limits
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from analytic_patch_contact import AnalyticPatchFitter
from cached_patch_contact import CachedPatchFitter
from reference_temporal_patch_frame import evaluate
from target_rig_contact import baseline
from rig_asset import RigAsset
from strep import ROOT,read


@pytest.fixture
def fitters():
    spec=read(ROOT/'reports/target-rig-contact-v1/specs/wave.json')
    rig=RigAsset.load(ROOT/'reports/rig-axis-calibration-v1/wave/character.glb')
    _,local=baseline(rig,spec['frames'])
    return AnalyticPatchFitter(rig,spec,local),CachedPatchFitter(rig,spec,local)


def test_frame_parameters_and_priors_match_uncached_exactly(fitters):
    original,cached=fitters;x=original.bounds*np.linspace(-.2,.2,len(original.bounds))
    with threadpool_limits(limits=1):
        for frame,delta,prior in [(25,0,.4),(25,0,.7),(26,0,.7),(26,.001,.7),(25,.001,.2)]:
            values=x.copy();values[0]+=delta
            args=(frame,values,[x*.8,x*.9],x*prior,[x*.3,x*.4])
            a=evaluate(original,*args);b=evaluate(cached,*args)
            for left,right in zip(a,b):np.testing.assert_array_equal(left,right)
    assert cached.surface_hits>0 and cached.surface_misses>1


def test_callers_cannot_corrupt_cached_surface_or_parameter_key(fitters):
    original,cached=fitters;x=np.zeros(len(original.bounds))
    with threadpool_limits(limits=1):
        points,jac=cached.surface_jacobian(25,x)
        with pytest.raises(ValueError):points[0,0]=123
        with pytest.raises(ValueError):jac[0,0,0]=123
        x[0]=.001
        changed=cached.surface_jacobian(25,x)
        expected=original.surface_jacobian(25,x)
    for a,b in zip(changed,expected):np.testing.assert_array_equal(a,b)
