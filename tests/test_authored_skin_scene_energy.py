from pathlib import Path
import sys
import copy
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from authored_skin_scene_energy import AuthoredSkinSceneEnergy
from linear_skin_operator import LinearSkinOperator


def setup():
    ids=torch.zeros((3,1),dtype=torch.long);w=torch.ones((3,1),dtype=torch.float64)
    bind=torch.tensor([[[0.,0.,0.]],[[0.,0.,.1]],[[.1,0.,0.]]],dtype=w.dtype);skin=LinearSkinOperator(ids,w,bind,1)
    def decode(x):return dict(global_rot_mats=torch.eye(3,dtype=x.dtype).expand(1,x.shape[1],1,3,3),posed_joints=x[...,:3,None].transpose(-1,-2))
    identity=np.tile(np.eye(3),(5,1,1)).tolist()
    plan=dict(schema='strep-authored-scene-guidance-v1',vertices=3,joint_names=['root'],frames=5,floor_normal=[0.,1.,0.],floor_offset_m=0.,primitives=[],contacts=[dict(id='point',vertex=0,start_frame=1,end_frame=3,targets_m=[[0.,.1,0.]]*3,normal_directions=[[0.,1.,0.]]*3,normal_faces=[[0,1,2]])])
    return skin,decode,plan,identity


@pytest.mark.parametrize('chunk',[1,2,4,16])
def test_complete_interval_and_motion_metrics_ignore_activation_chunk_boundaries(chunk):
    skin,decode,plan,_=setup();x=torch.tensor([[[0.,-.2,0.],[.1,-.1,0.],[.15,-.2,0.],[.4,-.1,0.],[.6,-.2,0.]]],dtype=torch.float64,requires_grad=True)
    reference=AuthoredSkinSceneEnergy(decode,skin,plan,frame_chunk=5);actual=AuthoredSkinSceneEnergy(decode,skin,plan,frame_chunk=chunk)
    torch.testing.assert_close(actual(x),reference(x));ga=torch.autograd.grad(actual(x),x)[0];gb=torch.autograd.grad(reference(x),x)[0];torch.testing.assert_close(ga,gb)
    a,b=actual.metrics(x),reference.metrics(x)
    assert set(a)==set(b) and a['contact_position'].shape==(3,) and a['skin_speed_m_s'].shape==(4,) and a['skin_acceleration_m_s2'].shape==(3,)
    for name in a:np.testing.assert_allclose(a[name],b[name],atol=1e-12,rtol=1e-12)
    assert np.count_nonzero(ga[0,4])>0 and np.count_nonzero(ga[0,3])>0


@pytest.mark.parametrize('shape,geometry',[('box',dict(size_m=[1.,1.,1.])),('sphere',dict(radius_m=.5)),('cylinder',dict(radius_m=.5,height_m=1.))])
def test_full_primitive_depth_matches_independent_numpy_geometry(shape,geometry):
    from object_geometry import Geometry
    skin,decode,plan,identity=setup();g=dict(schema='strep-object-geometry-v1',shape=shape,**geometry)
    plan['primitives']=[dict(geometry=g,positions_m=[[0.,0.,0.]]*5,rotations=identity)]
    energy=AuthoredSkinSceneEnergy(decode,skin,plan);x=torch.tensor([[[.2,.1,.2]]*5],dtype=torch.float64,requires_grad=True)
    metric=energy.metrics(x)['objects'];v=skin(*[decode(x)[k][0] for k in ['global_rot_mats','posed_joints']]).detach().numpy()
    expected=Geometry.parse(g).penetration_depth(v[0],np.zeros(3),np.eye(3))
    assert metric.shape==(1,3,5);np.testing.assert_allclose(metric[0,0],expected.max());np.testing.assert_allclose(metric[0,1],np.count_nonzero(expected>0));np.testing.assert_allclose(metric[0,2],expected@expected)
    assert torch.isfinite(torch.autograd.grad(energy(x),x)[0]).all()


def test_orientation_and_tangent_rows_are_not_dropped():
    skin,decode,plan,_=setup();plan['contacts'][0].update(tangent_directions=[[1.,0.,0.]]*3,hand_joint=0,knuckle_joints=[0,0,0,0])
    x=torch.zeros((1,5,3),dtype=torch.float64);m=AuthoredSkinSceneEnergy(decode,skin,plan).metrics(x)
    assert len(m['contact_normal'])==len(m['contact_tangent'])==len(m['contact_tangent_degenerate'])==3
    assert np.all(m['contact_tangent_degenerate']==1) and np.all(m['contact_normal']==0)


def test_invalid_target_clock_and_vertex_reject():
    skin,decode,plan,_=setup()
    for fault in ['clock','vertex']:
        bad=copy.deepcopy(plan)
        if fault=='clock':bad['contacts'][0]['targets_m']=[]
        else:bad['contacts'][0]['vertex']=99
        with pytest.raises(ValueError):AuthoredSkinSceneEnergy(decode,skin,bad)
