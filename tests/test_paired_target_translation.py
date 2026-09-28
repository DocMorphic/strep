import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import pytest
from plan_paired_contact_target import translations


def test_relative_target_and_minimal_common_lift():
    a=np.array([[.02,1.,0.],[0.,-.007,0.]])
    b=np.array([[-.02,1.003,.01],[0.,-.009,0.]])
    normal=np.array([0.,0.,1.]);delta=translations([a,b],0,normal,.002)
    np.testing.assert_allclose(b[0]+delta[1]-a[0]-delta[0],normal*.002,atol=1e-12)
    floors=[(p+d)[:,1].min() for p,d in zip([a,b],delta)]
    assert min(floors)==pytest.approx(.001)
    assert np.max(np.abs(delta[:,[0,2]]))<=.04


def test_unreachable_root_budget_is_rejected():
    with pytest.raises(ValueError,match='limits'):
        translations([np.array([[1.,1,0]]),np.array([[0.,1,0]])],0,np.array([0.,0,1]),.002)


def test_tangent_shift_and_protected_frames():
    from verify_paired_target_plan import protected
    points=[np.array([[.01,1.,0.],[0.,.0,0.]]),np.array([[-.01,1.,0.],[0.,.0,0.]])]
    offset=np.array([.016,0.,0.])
    delta=translations(points,0,np.array([0.,0.,1.]),.004,tangent_offset=offset)
    np.testing.assert_allclose(points[1][0]+delta[1]-points[0][0]-delta[0],offset+[0,0,.004],atol=1e-12)
    source={'root_positions':np.zeros((3,3)), 'local_rot_mats':np.tile(np.eye(3),(3,2,1,1))}
    candidate={k:v.copy() for k,v in source.items()};candidate['root_positions'][1]+=delta[0]
    protected(source,candidate,{1:delta[0]},np.eye(3))
    candidate['root_positions'][2,0]=.001
    with pytest.raises(ValueError,match='root_positions'):protected(source,candidate,{1:delta[0]},np.eye(3))
