import sys
from pathlib import Path
import numpy as np
import pytest
import torch
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read
from build_soma_preview import ASSET
from scene_solver_context import compile_context,box_signed_distance
from support_contact_v6 import torch_box_depth


def test_box_penalty_matches_geometry_and_has_outward_gradient():
    rotation=Rotation.from_euler('y',31,degrees=True).as_matrix();origin=np.array([2.,1.,-3.]);size=np.array([.4,.8,1.])
    local=np.array([[.1,0,0],[.3,0,0],[0,.39,0]]);world=local@rotation.T+origin
    points=torch.tensor(world[None],requires_grad=True,dtype=torch.float64)
    depths=torch_box_depth(points,torch.tensor(origin[None]),torch.tensor(rotation[None]),torch.tensor(size))
    np.testing.assert_allclose(depths.detach()[0],np.maximum(0,-box_signed_distance(world,origin,rotation,size)),atol=1e-12)
    depths.square().sum().backward();local_gradient=points.grad.numpy()[0]@rotation
    assert local_gradient[0,0]<0 # descent pushes the point toward +X / outside
    np.testing.assert_allclose(local_gradient[1],0,atol=1e-12)
    assert torch.isfinite(points.grad).all()


def test_oriented_box_context_uses_actor_native_normal_and_geometry():
    scene=read(ROOT/'reports/scene-fit-fixtures-v2/box-seed-11.json');skin=dict(np.load(ASSET))
    rotation=Rotation.from_euler('y',90,degrees=True)
    scene['actors']['A']['transform']=dict(translation_m=[2,0,-1],rotation_xyzw=rotation.as_quat().tolist())
    context=compile_context(scene,'A',['left-grip','right-grip'],skin)
    np.testing.assert_allclose(context['normals'][0]['directions'][60],[0,0,-1],atol=1e-12)
    np.testing.assert_allclose(rotation.apply(context['boxes'][0]['positions_m'][60])+[2,0,-1],[0,.2,.55],atol=1e-12)
    assert len(context['normals'])==2


def test_explicit_high_five_normal_has_correct_local_direction():
    scene=read(ROOT/'reports/scene-fit-fixtures-v1/high-five.json');skin=dict(np.load(ASSET))
    c=scene['contacts'][1];c['normal_target']=dict(space='world',direction=[0,0,-1])
    context=compile_context(scene,'B',['B-meeting'],skin)
    np.testing.assert_allclose(context['normals'][0]['directions'][60],[0,0,1],atol=1e-12)
    c['normal_target']['direction']=[0,0,-2]
    with pytest.raises(ValueError):compile_context(scene,'B',['B-meeting'],skin)


@pytest.mark.parametrize('shape',['box','sphere','cylinder'])
def test_contact_buffer_tracks_keep_physical_penetration_and_other_vertex_buffers(shape):
    from object_geometry import Geometry
    from support_contact_v8 import torch_primitive_clearance_violation
    geometry=Geometry(shape,{'box':(.1,.1,.1),'sphere':(.05,),'cylinder':(.05,.1)}[shape])
    rotations=np.tile(Rotation.from_euler('y',31,degrees=True).as_matrix(),(4,1,1))
    positions=np.column_stack([np.arange(4)*.01,np.ones(4),np.zeros(4)])
    local=np.tile(np.array([[.05,0,0],[.049,0,0],[.05,0,0],[.055,0,0]]),(4,1,1))
    world=np.einsum('fvi,fji->fvj',local,rotations)+positions[:,None,:]
    points=torch.tensor(world,dtype=torch.float64,requires_grad=True)
    margins=torch.tensor(np.tile([0,0,.002,0],(4,1)),dtype=torch.float64)
    violation=torch_primitive_clearance_violation(points,torch.tensor(positions),torch.tensor(rotations),geometry,margins)
    np.testing.assert_allclose(violation.detach(),np.tile([0,.001,.002,-.005],(4,1)),atol=1e-12,rtol=0)
    torch.relu(violation).square().sum().backward();assert torch.isfinite(points.grad).all()
    # Penetrating contact vertices still get an outward descent direction.
    gradient=np.einsum('fvi,fij->fvj',points.grad.numpy(),rotations)
    assert (gradient[:,1,0]<0).all()


def test_intentional_buffer_requires_explicit_mode_and_compiled_inequalities():
    from support_contact_v8 import refine
    with pytest.raises(ValueError,match='requires compiled'):
        refine({}, {}, {},intentional_object_contacts=True)
    with pytest.raises(ValueError,match='explicit correction mode'):
        refine({}, {}, {},scene_context={'intentional_object_clearance':{}})


@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
def test_object_interpolation_matches_local_slerp_hierarchy_with_finite_gradients(dtype):
    from scipy.spatial.transform import Slerp
    from object_subframe_constraints import clock,poses
    root=Rotation.from_euler('z',[-170,170,-170],degrees=True).as_matrix()
    child=Rotation.from_euler('x',[0,25,-15],degrees=True).as_matrix()
    local=torch.tensor(np.stack([root,child],1),dtype=dtype,requires_grad=True)
    offsets=torch.tensor(np.tile([[0,0,0],[1,0,0]],(3,1,1)),dtype=dtype)
    roots=torch.tensor([[0,0,0],[.3,0,0],[.6,0,0]],dtype=dtype)
    left,fraction=clock(3,4);r,p=poses(local,offsets,roots,[-1,0],left,fraction)
    times=left.numpy()+fraction.numpy()
    root_r=Slerp([0,1,2],Rotation.from_matrix(root))(times).as_matrix()
    child_r=Slerp([0,1,2],Rotation.from_matrix(child))(times).as_matrix()
    expected_r=np.stack([root_r,root_r@child_r],1)
    expected_root=np.column_stack([times*.3,np.zeros((len(times),2))])
    expected_p=np.stack([expected_root,expected_root+root_r[:,:,0]],1)
    np.testing.assert_allclose(r.detach(),expected_r,atol=2e-6,rtol=0)
    np.testing.assert_allclose(p.detach(),expected_p,atol=2e-6,rtol=0)
    (p.square().sum()+r.square().sum()).backward();assert torch.isfinite(local.grad).all()
    # Identical keys must also remain finite in float32, including backward.
    identical=torch.eye(3,dtype=dtype).expand(3,2,3,3).clone().requires_grad_()
    r,p=poses(identical,offsets,roots,[-1,0],left,fraction)
    r.sum().backward();assert torch.isfinite(identical.grad).all()


def test_playback_constraints_keep_all_intermediate_keys_and_do_not_lerp_global_poses():
    from object_subframe_constraints import clock,poses
    left,fraction=clock(3,4)
    assert left.tolist()==[0,0,0,1,1,1] and fraction.tolist()==[.25,.5,.75,.25,.5,.75]
    local=np.tile(np.eye(3),(2,2,1,1));local[1,0]=Rotation.from_euler('z',90,degrees=True).as_matrix()
    offsets=torch.tensor(np.tile([[0,0,0],[1,0,0]],(2,1,1)),dtype=torch.float64)
    left,fraction=clock(2,2);_,p=poses(torch.tensor(local),offsets,torch.zeros((2,3)),[-1,0],left,fraction)
    np.testing.assert_allclose(p[0,1],[2**-.5,2**-.5,0],atol=1e-12)
    assert np.linalg.norm(p[0,1].numpy()-[.5,.5,0])>.2
    with pytest.raises(ValueError):clock(3,True)
    with pytest.raises(ValueError):clock(3,9)


@pytest.mark.parametrize('extra',[dict(object_subframe_divisions=0),dict(object_subframe_divisions=True),
    dict(object_subframe_divisions=4),dict(object_sample_margin_m=-.001),dict(object_sample_margin_m=float('nan'))])
def test_invalid_or_unenabled_object_playback_modes_fail_before_solving(extra):
    from support_contact_v8 import refine
    with pytest.raises(ValueError):refine({}, {}, {},**extra)


@pytest.mark.parametrize('margin',[True,-.00001,.002,float('nan'),.00001])
def test_invalid_or_unbound_point_headroom_rejects_before_solving(margin):
    from support_contact_v8 import refine
    with pytest.raises(ValueError):refine({}, {}, {},point_numerical_margin_m=margin)


def test_point_headroom_never_replaces_a_distributed_region_fitter():
    from support_contact_v8 import refine
    with pytest.raises(ValueError,match='no distributed'):
        refine({}, {}, {},contact_spec={},region_fitting=object(),point_numerical_margin_m=.00001)
