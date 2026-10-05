"""Independent geometric/solver checks for closed, local-Y cylinders."""
import copy
import sys
from pathlib import Path
import numpy as np
import pytest
import torch
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from object_geometry import Geometry,scene_geometry
from object_geometry_mesh import triangle_mesh
from region_contact_objective import signed_distance
from support_contact_v8 import torch_primitive_depth,torch_primitive_clearance_violation
from release_geometry import floor_gaps
from object_floor_placement import floor_lower_bound,place_above_floor

CYLINDER=Geometry('cylinder',(.3,1.2))


def test_cylinder_schema_full_height_and_no_ambiguous_legacy_dimensions():
    record=dict(schema='strep-object-geometry-v1',shape='cylinder',radius_m=.3,height_m=1.2)
    assert CYLINDER.record()==record and Geometry.parse(record)==CYLINDER
    np.testing.assert_array_equal(CYLINDER.local_size(),[.6,1.2,.6])
    for mutation in [dict(radius_m=True),dict(height_m=0),dict(height_m=float('inf')),dict(height_m=[1.]),dict(size_m=[1,2,3])]:
        with pytest.raises(ValueError):Geometry.parse({**record,**mutation})
    with pytest.raises(ValueError):Geometry.parse({k:v for k,v in record.items() if k!='height_m'})
    with pytest.raises(ValueError):scene_geometry(dict(geometry=record,height_m=1.))
    with pytest.raises(ValueError):scene_geometry(dict(shape='box',size_m=[1,1,1],height_m=1.))


def test_cylinder_exact_side_cap_corner_and_ambiguous_normals():
    points=np.array([[0,0,0],[.1,0,0],[0,.5,0],[.3,.2,0],[0,.6,0],[.6,1.,0],[.3,.6,0],[0,.9,0]])
    distance,normal,defined=CYLINDER.distance_gradient(points,[0,0,0],np.eye(3))
    np.testing.assert_allclose(distance,[-.3,-.2,-.1,0,0,.5,0,.3],atol=1e-15)
    np.testing.assert_array_equal(defined,[False,True,True,True,True,True,False,True])
    np.testing.assert_allclose(normal[5],[.6,.8,0],atol=1e-15)
    np.testing.assert_array_equal(CYLINDER.local_surface_normal([0,.6,0]),[0,1,0])
    np.testing.assert_array_equal(CYLINDER.local_surface_normal([-.3,.2,0]),[-1,0,0])
    with pytest.raises(ValueError,match='unique'):CYLINDER.local_surface_normal([.3,.6,0])
    with pytest.raises(ValueError,match='unique'):CYLINDER.local_surface_normal([.2,0,0])


def test_transformed_numpy_and_tensor_gradients_agree_with_finite_differences():
    rng=np.random.default_rng(703);local=rng.uniform(-.9,.9,(100,3))
    r=Rotation.from_euler('xyz',[.45,-.23,1.1]).as_matrix();p=np.array([1.3,-.2,.7]);points=local@r.T+p
    distance,gradient,defined=CYLINDER.distance_gradient(points,p,r)
    assert defined.all()
    x=torch.tensor(points,dtype=torch.float64,requires_grad=True)
    values=signed_distance(x,torch.tensor(p),torch.tensor(r),CYLINDER)
    np.testing.assert_allclose(values.detach(),distance,atol=1e-15)
    np.testing.assert_allclose(torch.autograd.grad(values.sum(),x)[0],gradient,atol=1e-14)
    for i in range(3):
        e=np.eye(3)[i]*1e-6
        fd=(CYLINDER.distance_gradient(points+e,p,r)[0]-CYLINDER.distance_gradient(points-e,p,r)[0])/2e-6
        np.testing.assert_allclose(fd,gradient[:,i],atol=2e-9)
    # Different poses in the same batch catch accidental world-axis queries.
    rotations=np.stack([np.eye(3),r]);positions=np.array([[0,0,0],p])
    batched=np.einsum('vj,fij->fvi',local,rotations)+positions[:,None]
    x=torch.tensor(batched,dtype=torch.float64,requires_grad=True)
    violation=torch_primitive_clearance_violation(x,torch.tensor(positions),torch.tensor(rotations),CYLINDER,.002)
    np.testing.assert_allclose(violation.detach(),np.tile(.002-distance,(2,1)),atol=1e-15)
    np.testing.assert_allclose(torch_primitive_depth(x,torch.tensor(positions),torch.tensor(rotations),CYLINDER,.002).detach(),np.maximum(violation.detach().numpy(),0),atol=1e-15)
    assert torch.isfinite(torch.autograd.grad(violation.sum(),x)[0]).all()


def test_extents_match_dense_surface_and_inertia_matches_volume_integration():
    rng=np.random.default_rng(18);rotations=Rotation.random(15,random_state=rng).as_matrix()
    angle=np.linspace(0,2*np.pi,20001)
    ring=np.stack([.3*np.cos(angle),np.full(len(angle),.6),.3*np.sin(angle)],axis=1)
    points=np.concatenate([ring,ring*[1,-1,1]])
    for r in rotations:
        np.testing.assert_allclose(abs(points@r.T).max(0),CYLINDER.world_half_extents(r),atol=5e-9,rtol=0)
    p=np.tile([0,2,0],(len(rotations),1))
    np.testing.assert_allclose(floor_gaps(CYLINDER,p,rotations),[2-CYLINDER.world_half_extents(r)[1] for r in rotations],atol=1e-14)
    # Midpoint volume quadrature uniform in r^2, angle and height.
    radial=.3*np.sqrt((np.arange(100)+.5)/100);theta=(np.arange(64)+.5)*2*np.pi/64;y=(np.arange(400)+.5)*1.2/400-.6
    x,z=radial[:,None]*np.cos(theta),radial[:,None]*np.sin(theta)
    diagonal=2*np.array([(z*z).mean()+(y*y).mean(),(x*x+z*z).mean(),(x*x).mean()+(y*y).mean()])
    np.testing.assert_allclose(np.diag(CYLINDER.uniform_inertia(2.)),diagonal,atol=2e-6)
    assert CYLINDER.bounding_radius()==pytest.approx(np.hypot(.3,.6))


def test_rotating_cylinder_placement_covers_interior_sweep():
    obj=dict(geometry=CYLINDER.record(),keyframes=[dict(frame=f,translation_m=[0,.35,0],rotation_xyzw=Rotation.from_euler('z',a,degrees=True).as_quat().tolist()) for f,a in [(0,-85),(2,85)]])
    bound=floor_lower_bound(obj,3)
    assert bound['lower_bound_m']<-.25
    candidate,recipe=place_above_floor(obj,3,max_shift_m=1.)
    dense=copy.deepcopy(candidate);dense['keyframes'][-1]['frame']=2000
    from scene_constraints import sample_object
    p,r=sample_object(dense,2001)
    assert floor_gaps(CYLINDER,p,r).min()>=.002
    assert recipe['after']['lower_bound_m']==pytest.approx(.002)
    np.testing.assert_array_equal(candidate['keyframes'][0]['rotation_xyzw'],obj['keyframes'][0]['rotation_xyzw'])


def test_cylinder_mesh_resource_limit_is_explicit():
    with pytest.raises(ValueError,match='resource limit'):triangle_mesh(CYLINDER,1e-9)


def test_cylinder_export_preserves_geometry_and_all_animated_transforms(tmp_path):
    from scene_constraints import sample_object,target_track
    from scene_object_export import export_objects
    from gltf_tools import read_glb,accessor
    from rig_clip_import import AnimationSampler
    obj=dict(geometry=CYLINDER.record(),keyframes=[
        dict(frame=0,translation_m=[-.4,.7,.3],rotation_xyzw=Rotation.from_euler('xyz',[.2,.6,-.3]).as_quat().tolist()),
        dict(frame=30,translation_m=[.8,1.1,-.4],rotation_xyzw=Rotation.from_euler('xyz',[1.3,-.5,.8]).as_quat().tolist())])
    path=tmp_path/'cylinder.glb';export_objects(dict(frame_count=31,fps=30,objects=dict(can=obj)),path)
    doc,binary=read_glb(path);node=doc['nodes'][0]
    assert node['extras']['strep_geometry']==CYLINDER.record()
    vertices=accessor(doc,binary,doc['meshes'][0]['primitives'][0]['attributes']['POSITION'])
    np.testing.assert_allclose(CYLINDER.distance_gradient(vertices,[0,0,0],np.eye(3))[0],0,atol=1e-7)
    p,r=sample_object(obj,31);sampler=AnimationSampler(doc,binary,0)
    for f in range(31):
        actual=sampler.sample(f/30)[0]
        np.testing.assert_allclose(actual[:3,3],p[f],atol=1e-6)
        np.testing.assert_allclose(actual[:3,:3],r[f],atol=1e-6)
    for point in [[.3,0,0],[0,.6,0]]:
        track=target_track(dict(space='object',object='can',point_m=point),{},dict(can=(p,r)),31)
        for f in range(31):
            actual=sampler.sample(f/30)[0]@np.array([*point,1.])
            np.testing.assert_allclose(actual[:3],track[f],atol=1e-6)


def test_cylinder_region_measurement_and_residual_detect_intruding_patch():
    from scene_region_contact import measure_frame
    from region_contact_objective import violations
    points=np.array([[-.01,.602,-.01],[.01,.602,-.01],[0,.602,.02]])
    faces=np.array([[0,1,2]]);ids=np.arange(3);target=np.array([0,.6,0]);normal=np.array([0,-1,0])
    limits=dict(clearance_m=.002,contact_gap_m=.003,spacing_m=.006,area_m2=.000025,centroid_error_m=.005,local_radius_m=.03,normal_degrees=10.)
    for shift,passed in [(0,True),(-.003,False)]:
        patch=points+[0,shift,0]
        row=measure_frame(patch,ids,faces,target,normal,CYLINDER,np.zeros(3),np.eye(3),limits)
        assert row['passed']==passed
        def t(v):return torch.tensor(v,dtype=torch.float64)
        residual=violations(t(patch),faces,ids,0,t(target),t(normal),CYLINDER,t(np.zeros(3)),t(np.eye(3)),limits,.02)
        assert (float(residual.max())<1e-10)==passed


def test_skin_scene_audit_detects_cylinder_interior_with_independent_depth(tmp_path):
    from strep import ROOT
    from build_soma_preview import ASSET
    from floor_contact import Surface
    from scene_constraints import evaluate
    source=ROOT/'reports/action-jobs/breadth-v2-round-01-a/takes/ground_and_recovery-kneel-rise-a-seed-1301/motion.npz'
    with np.load(source,allow_pickle=False) as z:
        motion={k:z[k][:3] for k in ['posed_joints','local_rot_mats','global_rot_mats','root_positions','foot_contacts']}
    np.savez(tmp_path/'actor.npz',**motion)
    with np.load(ASSET,allow_pickle=False) as z:skin=dict(z)
    surface=Surface(skin);points=[surface.vertices(r,p) for r,p in zip(motion['global_rot_mats'],motion['posed_joints'])]
    center=points[0][1000];r=Rotation.from_euler('xyz',[.5,-.7,.9]).as_matrix()
    scene=dict(schema_version=1,id='cylinder-depth-control',fps=30,frame_count=3,contacts=[],
        actors=dict(A=dict(motion='actor.npz',transform=dict(translation_m=[0,0,0],rotation_xyzw=[0,0,0,1]))),
        objects=dict(can=dict(geometry=Geometry('cylinder',(.03,.09)).record(),keyframes=[dict(frame=0,translation_m=center.tolist(),rotation_xyzw=Rotation.from_matrix(r).as_quat().tolist())])))
    actual=evaluate(scene,skin,project_root=tmp_path)['object_collisions'][0]
    expected=[]
    for p in points:
        local=(p-center)@r
        # Distance to nearest side/cap for inside points; zero for outside.
        depth=np.maximum(0,np.minimum(.03-np.hypot(local[:,0],local[:,2]),.045-abs(local[:,1])))
        expected.append(float(depth.max()))
    np.testing.assert_allclose(actual['per_frame_max_depth_m'],expected,atol=1e-14)
    assert expected[0]==pytest.approx(.03)
