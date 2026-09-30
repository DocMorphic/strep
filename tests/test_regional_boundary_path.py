import sys
from pathlib import Path
import numpy as np
import pytest
import torch
from scipy.spatial.transform import Rotation,Slerp
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from regional_boundary_path import interpolate_rotations,cylinder_distance,kinematics
from object_geometry import Geometry
from regional_boundary_path import BoundaryPath,assemble


def test_rotations_match_scipy_and_derivatives_include_both_endpoints():
    from support_contact_v5 import rodrigues
    raw=torch.tensor([[.2,-.1,.3],[-.1,.4,.2]],dtype=torch.float64,requires_grad=True)
    def f(v):return interpolate_rotations(rodrigues(v[0]),rodrigues(v[1]),torch.tensor(.37)).ravel()
    expected=Slerp([0,1],Rotation.from_rotvec(raw.detach().numpy()))([.37]).as_matrix()[0]
    np.testing.assert_allclose(f(raw).detach().reshape(3,3),expected,atol=1e-8)
    assert torch.autograd.gradcheck(f,(raw,),eps=1e-6,atol=1e-5)


def test_stationary_interpolation_has_finite_gradient():
    from support_contact_v5 import rodrigues
    raw=torch.zeros((2,3),dtype=torch.float64,requires_grad=True)
    result=interpolate_rotations(rodrigues(raw[0]),rodrigues(raw[1]),torch.tensor(.25))
    assert torch.isfinite(torch.autograd.grad(result.sum(),raw)[0]).all()


def test_cylinder_distance_matches_independent_geometry():
    points=np.random.default_rng(730).normal(size=(2,100,3))
    rotations=Rotation.from_rotvec([[.2,.4,-.1],[-.3,.2,.8]]).as_matrix();centers=np.array([[.3,-.1,.2],[.5,.2,.1]])
    actual=cylinder_distance(torch.tensor(points),torch.tensor(centers),torch.tensor(rotations),(.5,1.2)).numpy()
    for i in range(2):np.testing.assert_allclose(actual[i],Geometry('cylinder',(.5,1.2)).distance_gradient(points[i],centers[i],rotations[i])[0],atol=1e-14)


def test_kinematics_applies_parent_rotation_and_root_translation():
    local=torch.eye(3,dtype=torch.float64).repeat(1,3,1,1)
    local[0,0]=torch.tensor(Rotation.from_euler('z',90,degrees=True).as_matrix())
    offsets=torch.tensor([[[2.,3.,4.],[1.,0.,0.],[1.,0.,0.]]],dtype=torch.float64)
    _,p=kinematics(local,offsets,[-1,0,1])
    np.testing.assert_allclose(p[0],[[2,3,4],[2,4,4],[2,5,4]],atol=1e-14)


def test_path_protects_neighbor_poses_and_bounds_all_native_edits():
    from types import SimpleNamespace
    names=['Root']+[s+p for s in ['Left','Right'] for p in ['Shoulder','Arm','ForeArm','Hand']]
    local=np.broadcast_to(np.eye(3),(12,9,3,3)).copy();positions=np.zeros((12,9,3));positions[:,:,1]=2
    positions[:,1:,0]=np.arange(1,9)*.1
    motion=dict(local_rot_mats=local,global_rot_mats=local.copy(),posed_joints=positions,root_positions=positions[:,0])
    t=lambda v:torch.as_tensor(np.asarray(v),dtype=torch.float64)
    p=SimpleNamespace(names=names,parents=[-1]+[0]*8,base=motion,lookup={j:j-1 for j in range(1,9)},limits=np.full(8,.5),t=t,
        indices=np.array([[1],[5]]),bind=t(np.zeros((2,1,3))),weights=t(np.ones((2,1))),config=dict(clearance_m=.002,object_clearance_m=.002))
    track=(Geometry('cylinder',(.2,.4)),np.broadcast_to([10.,0.,0.],(12,3)),np.broadcast_to(np.eye(3),(12,3,3)))
    settings=dict(rotation_curvature_scale=.02,position_curvature_scale_m=.002,position_reference_scale_m=.05,geometry_scale_m=.00005,clearance_reserve_m=.0001)
    path=BoundaryPath(p,motion,[4,5,6],track,settings)
    raw=np.full(len(path.initial),100.);actual=path.locals(t(raw)).numpy()
    np.testing.assert_array_equal(actual[[0,1,5,6]],local[[2,3,7,8]])
    np.testing.assert_array_equal(actual[:,0],local[path.support,0])
    angles=Rotation.from_matrix(actual[2:5,1:].reshape(-1,3,3)).magnitude()
    assert angles.max()<.5 and angles.min()>.49
    np.testing.assert_array_equal(path.times,np.arange(3,7.001,.25))
    value,grad,terms=path.pair(raw)
    assert value>0 and np.isfinite(grad).all() and terms['rotation_curvature']>0
    # Both entry and exit joins have nonzero curvature although free keys agree.
    arm=actual[:,1:];curvature=arm[2:]-2*arm[1:-1]+arm[:-2]
    assert np.linalg.norm(curvature[0])>0 and np.linalg.norm(curvature[-1])>0


def test_assembly_does_not_normalize_frozen_float32_rotations():
    local=np.broadcast_to(np.eye(3,dtype=np.float32),(5,2,3,3)).copy()
    local[:,0,0,0]=np.float32(1+1e-7)
    positions=np.zeros((5,2,3),dtype=np.float32);positions[:,1,0]=1
    source=dict(local_rot_mats=local,global_rot_mats=local.copy(),posed_joints=positions,root_positions=positions[:,0].copy(),foot_contacts=np.ones((5,2)))
    desired=local.astype(float);desired[2,1]=Rotation.from_rotvec([0,0,.2]).as_matrix()
    candidate=assemble(source,desired,[2],[-1,0])
    np.testing.assert_array_equal(candidate['local_rot_mats'][:,0],source['local_rot_mats'][:,0])
    for key in source:np.testing.assert_array_equal(candidate[key][[0,1,3,4]],source[key][[0,1,3,4]])
    np.testing.assert_array_equal(candidate['root_positions'],source['root_positions'])
    assert not np.array_equal(candidate['local_rot_mats'][2,1],local[2,1])
