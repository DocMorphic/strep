import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_decoded_motion_edges import rig_fixture
from native_waypoint_clock import guide_clock
from continuous_waypoint_motion import ContinuousWaypointMotion
from wrist_waypoint_motion import bake
from waypoint_lattice import LinearGuide
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler


@pytest.mark.parametrize('actor',[0,1])
@pytest.mark.parametrize('extended',[False,True])
def test_batch_continuous_replay_matches_export_between_keys_and_zero_pose(actor,extended,tmp_path):
    rig,clock=rig_fixture();rig.document['skins']=[dict(joints=rig.joints)]
    window=[.15,.5,1.85 if extended else .85];native=guide_clock([clock]*6,window,[]);times=np.arange(241)/120
    if extended:assert len(native)>12
    axis=np.array([0.,0.,1.]);model=ContinuousWaypointMotion(rig,[1,2,3],native,times,[],np.eye(3),axis,actor)
    controls=np.zeros((len(native),3));weights=np.sin(np.linspace(0,np.pi,len(native)))**2
    controls[1:-1]=weights[1:-1,None]*np.array([.0073,4.1,-3.2]);guide=LinearGuide(native,controls,[.8,300,300])
    curve=lambda t:np.r_[axis*guide(t)[0]*(1 if actor==0 else -1),guide(t)[actor+1]]
    path=tmp_path/'candidate.glb';bake(rig,[1,2,3],[0,0,0],np.eye(3),0,window,[],path,control_curve=curve)
    doc,binary=read_glb(path);reader=AnimationSampler(doc,binary,0)
    expected=np.array([reader.sample(t) for t in times]);actual,maximum=model.evaluate(controls)
    np.testing.assert_allclose(actual,expected,atol=2e-12,rtol=0);assert maximum>0
    zero,_=model.evaluate(np.zeros_like(controls));np.testing.assert_array_equal(zero,model.model.source_world)
    with pytest.raises(ValueError):model.evaluate(np.ones_like(controls))
