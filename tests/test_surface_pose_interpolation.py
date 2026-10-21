from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from surface_pose_model import SurfacePoseModel
from surface_pose_interpolation import InterpolatedPoseMap,SampledPoseWindow,rotation_parameters
from surface_pose_working_floor import WorkingFloorConstraints
from surface_pose_window import CoupledPoseWindow
from native_support_clock import NativeSupportSampler
from test_surface_pose_model import fixture


def world_from_local(local,parents):
    world=local.copy()
    for i,parent in enumerate(parents):
        if parent>=0:world[i]=world[parent]@local[i]
    return world


def native_local(a,b,fraction):
    result=a.copy()
    for node in range(len(a)):
        q=NativeSupportSampler.value('rotation',np.array([0.,1.]),Rotation.from_matrix(np.array([a[node,:3,:3],b[node,:3,:3]])).as_quat(),'LINEAR',float(fraction))
        result[node,:3,:3]=Rotation.from_quat(q).as_matrix()
        result[node,:3,3]=(1-fraction)*a[node,:3,3]+fraction*b[node,:3,3]
    return result


def models(fraction=.37):
    rig,world=fixture();world[2,:3,:3]=np.eye(3)
    left=SurfacePoseModel(rig,world,1,[1,2]);local=left.local.copy()
    local[1,:3,3]+=[.1,.03,-.02]
    local[1,:3,:3]=local[1,:3,:3]@Rotation.from_rotvec([.2,-.1,.15]).as_matrix()
    local[2,:3,:3]=local[2,:3,:3]@Rotation.from_rotvec([-.1,.15,.3]).as_matrix()
    right=SurfacePoseModel(rig,world_from_local(local,rig.parents),1,[1,2])
    sampled=SurfacePoseModel(rig,world_from_local(native_local(left.local,right.local,fraction),rig.parents),1,[1,2])
    return left,right,sampled


def independent_points(left,right,edits,fraction):
    a=left.evaluate(edits[:left.size],derivatives=False)[1]
    b=right.evaluate(edits[left.size:],derivatives=False)[1]
    return left.rig.vertices(world_from_local(native_local(a,b,fraction),left.parents))


@pytest.mark.parametrize('fraction',[0.,.125,.5,.91,1.])
def test_complete_skin_matches_native_slerp_and_endpoint_derivatives(fraction):
    left,right,sampled=models(fraction);mapping=InterpolatedPoseMap(left,right,sampled,fraction)
    edits=np.linspace(-.12,.17,2*left.size);value,chain=mapping.parameters(edits)
    _,_,points,jac=sampled.evaluate(value)
    np.testing.assert_allclose(points,independent_points(left,right,edits,fraction),atol=1e-12,rtol=0)
    composed=jac@chain
    for i in range(len(edits)):
        delta=np.zeros_like(edits);delta[i]=1e-6
        numerical=(independent_points(left,right,edits+delta,fraction)-independent_points(left,right,edits-delta,fraction))/2e-6
        np.testing.assert_allclose(composed[:,:,i],numerical,atol=3e-9,rtol=1e-7)


@pytest.mark.parametrize('angle',[0.,1e-8,1e-5,.4])
def test_small_angle_branch_and_identical_endpoints(angle):
    a=np.eye(3);b=Rotation.from_rotvec([0.,angle,0.]).as_matrix();t=.31
    q=NativeSupportSampler.value('rotation',np.array([0.,1.]),Rotation.from_matrix(np.array([a,b])).as_quat(),'LINEAR',t)
    baseline=Rotation.from_quat(q).as_matrix();x=np.zeros(6)
    value,jac=rotation_parameters(a,b,baseline,x[:3],x[3:],t)
    np.testing.assert_allclose(value,0,atol=1e-15)
    for i in range(6):
        h=np.zeros(6);h[i]=1e-7
        plus=rotation_parameters(a,b,baseline,h[:3],h[3:],t,derivatives=False)[0]
        minus=rotation_parameters(a,b,baseline,-h[:3],-h[3:],t,derivatives=False)[0]
        np.testing.assert_allclose(jac[:,i],(plus-minus)/2e-7,atol=1e-8,rtol=1e-7)


def test_antipodal_quaternion_sign_uses_short_arc():
    a,b=Rotation.from_euler('z',[170.,-170.],degrees=True).as_matrix();baseline=Rotation.from_euler('z',180.,degrees=True).as_matrix()
    value,jac=rotation_parameters(a,b,baseline,np.zeros(3),np.zeros(3),.5)
    np.testing.assert_allclose(value,0,atol=1e-14)
    for i in range(6):
        h=np.zeros(6);h[i]=1e-6
        plus=rotation_parameters(a,b,baseline,h[:3],h[3:],.5,derivatives=False)[0]
        minus=rotation_parameters(a,b,baseline,-h[:3],-h[3:],.5,derivatives=False)[0]
        np.testing.assert_allclose(jac[:,i],(plus-minus)/2e-6,atol=1e-8,rtol=1e-7)


def problem(model):
    return WorkingFloorConstraints(model,angles_degrees=[45.,60.],root_horizontal_m=.2,root_vertical_m=.5,
        floor_depth_m=.005,contact_error_m=.02,floor_reserve_m=.001,contact_reserve_m=.001,
        contacts=[dict(vertex=0,target_m=[.2,.5,.1])])


def test_sampled_window_constraint_jacobian_matches_all_parameter_perturbations():
    a,b,m=models();mapping=InterpolatedPoseMap(a,b,m,.37);keys=CoupledPoseWindow([problem(a),problem(b)],root_step_m=.025,rotation_step_degrees=5.)
    window=SampledPoseWindow(keys,[(0,mapping,problem(m))]);x=np.linspace(-.03,.04,window.size);window.grow(x,batch_size=1)
    gaps,jac=window.pair(x);np.testing.assert_allclose(window.values(x),gaps,atol=1e-12,rtol=0)
    for i in range(len(x)):
        h=np.zeros_like(x);h[i]=1e-6
        np.testing.assert_allclose(jac[:,i],(window.values(x+h)-window.values(x-h))/2e-6,atol=3e-6,rtol=1e-7)
    assert len(window.values(x,full=True))>len(gaps)


@pytest.mark.parametrize('fault',['fraction','drift','root_basis','source_rotation','source_translation'])
def test_unsupported_interpolation_rejected_explicitly(fault):
    a,b,m=models();fraction=.37
    if fault=='fraction':fraction=float('nan')
    if fault=='drift':m.local[1,0,0]+=1e-6
    if fault=='root_basis':m.root_translation_map[0,0]+=.01
    if fault=='source_rotation':m.local[1,:3,:3]=m.local[1,:3,:3]@Rotation.from_rotvec([.01,0,0]).as_matrix()
    if fault=='source_translation':m.local[1,1,3]+=.01
    with pytest.raises(ValueError):InterpolatedPoseMap(a,b,m,fraction)


def test_ambiguous_half_turn_rejected():
    with pytest.raises(ValueError,match='half-turn'):
        rotation_parameters(np.eye(3),Rotation.from_rotvec([np.pi,0,0]).as_matrix(),np.eye(3),np.zeros(3),np.zeros(3),.5)


def test_duplicate_samples_and_invalid_parameter_population_rejected():
    a,b,m=models();mapping=InterpolatedPoseMap(a,b,m,.37);p=problem(m);keys=CoupledPoseWindow([problem(a),problem(b)],root_step_m=.025,rotation_step_degrees=5.)
    with pytest.raises(ValueError):SampledPoseWindow(keys,[(0,mapping,p),(0,mapping,p)])
    with pytest.raises(ValueError):mapping.parameters(np.zeros(3))
    with pytest.raises(ValueError):mapping.parameters(np.full(18,np.nan))
