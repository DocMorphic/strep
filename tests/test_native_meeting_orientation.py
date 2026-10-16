"""Shared contact orientation retains frame geometry and bounded edit reference."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_meeting_orientation import MeetingOrientation


@pytest.mark.parametrize('value',[[0.,0.,0.],[.2,-.3,.1],[1.,0.,0.],[.3,.7,-.5]])
def test_frame_and_derivatives(value):
    model=MeetingOrientation([0,0,1],[0,1,0],10.)
    x=np.array(value);r=model.evaluate(x)
    assert np.linalg.norm(r['normal_world'])==pytest.approx(1.)
    assert np.linalg.norm(r['tangent_world'])==pytest.approx(1.)
    assert r['normal_world']@r['tangent_world']==pytest.approx(0.,abs=1e-15)
    for column in range(3):
        step=np.eye(3)[column]*1e-6;p=model.evaluate(x+step);m=model.evaluate(x-step)
        for key,jkey in [('normal_world','normal_jacobian'),('tangent_world','tangent_jacobian')]:
            np.testing.assert_allclose(r[jkey][:,column],(p[key]-m[key])/2e-6,atol=2e-10,rtol=2e-7)
        assert r['edit_margin_jacobian'][column]==pytest.approx((p['edit_margin']-m['edit_margin'])/2e-6,abs=2e-10)
    assert r['edit_margin']==pytest.approx(1-x@x)


def test_source_epoch_cap_and_unaccepted_trial_are_distinct():
    normal=np.array([0.,0.,1.]);tangent=np.array([0.,1.,0.]);model=MeetingOrientation(normal,tangent,10.)
    normal[:]=0;tangent[:]=0
    np.testing.assert_array_equal(model.evaluate([0,0,0])['normal_world'],[0,0,1])
    assert model.evaluate([1,0,0])['normal_world']@[0,0,1]==pytest.approx(np.cos(np.radians(10)))
    assert model.evaluate([1.1,0,0])['edit_margin']<0
    np.testing.assert_array_equal(model.evaluate([0,0,0])['tangent_world'],[0,1,0])


@pytest.mark.parametrize('normal,tangent,cap',[
    ([0,0,0],[0,1,0],10),([0,0,2],[0,1,0],10),([0,0,1],[0,0,1],10),
    ([0,0,float('nan')],[0,1,0],10),([0,0,1],[0,1,0],True),
    ([0,0,1],[0,1,0],0),([0,0,1],[0,1,0],31),([0,0,1],[0,1,0],float('inf'))])
def test_bad_reference_or_cap_rejects(normal,tangent,cap):
    with pytest.raises(ValueError):MeetingOrientation(normal,tangent,cap)


@pytest.mark.parametrize('value',[[0,0],[0,0,0,0],[0,float('nan'),0],[0,0,float('inf')]])
def test_bad_controls_reject(value):
    with pytest.raises(ValueError):MeetingOrientation([0,0,1],[0,1,0],10).evaluate(value)
