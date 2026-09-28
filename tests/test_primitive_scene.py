import copy
import sys
from pathlib import Path
import numpy as np
import pytest
import torch
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from object_geometry import Geometry,scene_geometry
from scene_constraints import sample_object,target_track
from scene_solver_context import compile_context,context_primitives
from support_contact_v8 import torch_primitive_depth,torch_box_depth
from scene_object_export import export_objects
from gltf_tools import read_glb,accessor
from rig_clip_import import AnimationSampler
from strep import ROOT


def sphere():
    return dict(geometry=Geometry('sphere',(.3,)).record(),keyframes=[
        dict(frame=0,translation_m=[0.,1.,0.],rotation_xyzw=[0,0,0,1]),
        dict(frame=4,translation_m=[1.,1.5,0.],rotation_xyzw=Rotation.from_euler('z',90,degrees=True).as_quat().tolist())])


def test_sphere_grip_follows_surface_under_translation_and_rotation():
    obj=sphere();p,r=sample_object(obj,5)
    grip=target_track(dict(space='object',object='ball',point_m=[.3,0,0]),{},dict(ball=(p,r)),5)
    np.testing.assert_allclose(grip[0],[.3,1,0],atol=1e-12)
    np.testing.assert_allclose(grip[-1],[1,1.8,0],atol=1e-12)
    np.testing.assert_allclose(np.linalg.norm(grip-p,axis=1),.3,atol=1e-12)


@pytest.mark.parametrize('mutation',[dict(shape='sphere'),dict(radius_m=.3),dict(size_m=[.6]*3)])
def test_mixed_geometry_cannot_choose_conflicting_dimensions(mutation):
    obj=sphere();obj.update(mutation)
    with pytest.raises(ValueError,match='mix'):sample_object(obj,5)


def test_solver_context_rotates_sphere_normals_to_actor_space():
    yaw=Rotation.from_euler('y',90,degrees=True)
    scene=dict(frame_count=5,actors={'A':dict(transform=dict(translation_m=[2,0,-1],rotation_xyzw=yaw.as_quat().tolist()))},
        objects={'ball':sphere()},contacts=[dict(id='grip',actor='A',effector=dict(surface_vertex=0),target=dict(space='object',object='ball',point_m=[.3,0,0]),start_frame=0,end_frame=4)])
    context=compile_context(scene,'A',['grip'],dict(bind_vertices=np.zeros((1,3))))
    geometry,item=context_primitives(context)[0]
    assert geometry.shape=='sphere' and context['boxes']==[]
    world=yaw.apply(context['normals'][0]['directions'])
    np.testing.assert_allclose(world[0],[-1,0,0],atol=1e-12)
    np.testing.assert_allclose(world[-1],[0,-1,0],atol=1e-12)
    np.testing.assert_allclose(yaw.apply(item['positions_m'])+[2,0,-1],sample_object(sphere(),5)[0],atol=1e-12)


@pytest.mark.parametrize('shape',[Geometry('sphere',(.3,)),Geometry('box',(.6,.8,1.))])
def test_tensor_clearance_has_correct_geometry_and_gradient(shape):
    origin=np.array([[1.,.5,-2.]])
    rotation=Rotation.from_euler('xyz',[.4,.3,.2]).as_matrix()[None]
    local=np.array([[[.12,.04,.03],[.5,.7,.8]]]);world=np.einsum('fvi,fji->fvj',local,rotation)+origin[:,None,:]
    points=torch.tensor(world,dtype=torch.float64,requires_grad=True)
    depth=torch_primitive_depth(points,torch.tensor(origin),torch.tensor(rotation),shape)
    np.testing.assert_allclose(depth.detach()[0],shape.penetration_depth(world[0],origin[0],rotation[0]),atol=1e-12)
    assert torch.autograd.gradcheck(lambda x:torch_primitive_depth(x,torch.tensor(origin),torch.tensor(rotation),shape),(points,),eps=1e-6,atol=1e-5)
    if shape.shape=='box':
        np.testing.assert_array_equal(torch_primitive_depth(points,torch.tensor(origin),torch.tensor(rotation),shape,.002).detach(),
            torch_box_depth(points,torch.tensor(origin),torch.tensor(rotation),torch.tensor(shape.dimensions,dtype=points.dtype),.002).detach())


def test_exported_mesh_and_clock_match_sphere_geometry(tmp_path):
    obj=sphere();path=tmp_path/'sphere.glb';export_objects(dict(frame_count=5,fps=30,objects={'ball':obj}),path)
    doc,data=read_glb(path);geometry=doc['nodes'][0]['extras']['strep_geometry']
    assert geometry==obj['geometry']
    points=accessor(doc,data,doc['meshes'][0]['primitives'][0]['attributes']['POSITION'])
    np.testing.assert_allclose(np.linalg.norm(points,axis=1),.3,atol=1e-7)
    sampler=AnimationSampler(doc,data,0);p,r=sample_object(obj,5)
    for f in range(5):
        actual=sampler.sample(f/30)[0]
        np.testing.assert_allclose(actual[:3,3],p[f],atol=1e-6)
        np.testing.assert_allclose(actual[:3,:3],r[f],atol=1e-6)


def test_legacy_box_and_versioned_box_have_identical_preview_geometry(tmp_path):
    legacy=dict(shape='box',size_m=[.3,.4,.5],keyframes=[sphere()['keyframes'][0]])
    canonical=dict(geometry=scene_geometry(legacy).record(),keyframes=copy.deepcopy(legacy['keyframes']))
    output=[]
    for name,obj in [('legacy',legacy),('canonical',canonical)]:
        path=tmp_path/(name+'.glb');export_objects(dict(frame_count=5,fps=30,objects={'box':obj}),path);output.append(path.read_bytes())
    assert output[0]==output[1]


def test_sphere_scene_collision_audit_uses_actual_actor_skin(tmp_path):
    from build_soma_preview import ASSET
    from floor_contact import Surface
    from scene_constraints import evaluate
    source=ROOT/'reports/action-jobs/breadth-v2-round-01-a/takes/ground_and_recovery-kneel-rise-a-seed-1301/motion.npz'
    with np.load(source,allow_pickle=False) as z:
        motion={key:z[key][:3] for key in ['posed_joints','local_rot_mats','global_rot_mats','root_positions','foot_contacts']}
    np.savez(tmp_path/'actor.npz',**motion)
    skin=dict(np.load(ASSET));surface=Surface(skin)
    points=[surface.vertices(r,p) for r,p in zip(motion['global_rot_mats'],motion['posed_joints'])]
    center=points[0][1000];radius=.03
    scene=dict(schema_version=1,id='sphere-depth-control',fps=30,frame_count=3,contacts=[],
        actors={'A':dict(motion='actor.npz',transform=dict(translation_m=[0,0,0],rotation_xyzw=[0,0,0,1]))},
        objects={'ball':dict(geometry=Geometry('sphere',(radius,)).record(),keyframes=[dict(frame=0,translation_m=center.tolist(),rotation_xyzw=[0,0,0,1])])})
    measured=evaluate(scene,skin,project_root=tmp_path)['object_collisions'][0]
    expected=[float(np.maximum(0,radius-np.linalg.norm(p-center,axis=1)).max()) for p in points]
    np.testing.assert_allclose(measured['per_frame_max_depth_m'],expected,atol=1e-12)
    assert expected[0]==pytest.approx(radius)


def test_scene_primitive_preview_module_is_on_the_explicit_server_allowlist():
    from action_studio_server import allowed_file
    assert allowed_file('/scene-object-geometry.js')==ROOT/'scripts/scene-object-geometry.js'
