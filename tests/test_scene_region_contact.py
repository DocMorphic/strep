import copy
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_region_contact import SCHEMA, mesh_fingerprint, validate_binding, measure_frame
from compile_scene_regions import compile_regions
from compile_scene_contacts import compile_contacts
from scene_solver_context import compile_context
from scene_constraints import evaluate
from object_geometry import Geometry
from inspect_motion import skeleton_metadata

LIMITS = dict(clearance_m=.002, contact_gap_m=.003, spacing_m=.006,
              area_m2=.000025, centroid_error_m=.005, local_radius_m=.03, normal_degrees=10.)
POINTS = np.array([[-.01,.502,-.01],[.01,.502,-.01],[0,.502,.02]])
FACES = np.array([[0,1,2]])


def measurement(points=POINTS, faces=FACES, rotation=np.eye(3), origin=np.zeros(3)):
    return measure_frame(points@rotation.T+origin, np.arange(3), faces,
                         rotation@[0,.5,0]+origin, rotation@[0,-1,0],
                         Geometry('box',(1,1,1)),origin,rotation,LIMITS)


def test_distributed_contact_is_invariant_under_rigid_placement():
    first=measurement()
    transformed=measurement(rotation=Rotation.from_euler('xyz',[.3,.5,.7]).as_matrix(),origin=np.array([4,2,-3]))
    assert first['passed'] and transformed['passed']
    assert transformed['contact_triangle']['area_m2']==pytest.approx(first['contact_triangle']['area_m2'])


@pytest.mark.parametrize('failure',['single_point','penetration','collinear','normal'])
def test_point_touch_does_not_hide_region_failures(failure):
    points=POINTS.copy();faces=FACES.copy()
    if failure=='single_point':points[1:,1]+=.1
    if failure=='penetration':points[:,1]-=.003
    if failure=='collinear':points[:,2]=0
    if failure=='normal':faces=faces[:,::-1]
    assert not measurement(points,faces)['passed']


@pytest.fixture
def fixture(tmp_path):
    names,_,_=skeleton_metadata(77)
    bind=np.tile(np.eye(4),(77,1,1));rot=np.tile(np.eye(3),(3,77,1,1))
    skin=dict(bind_vertices=POINTS.copy(),faces=FACES.copy(),rig_joint_names=np.array(names),
              bind_rig_transform=bind,lbs_indices=np.full((3,1),names.index('LeftHand')),lbs_weights=np.ones((3,1)))
    motion=dict(root_positions=np.zeros((3,3)),posed_joints=np.zeros((3,77,3)),
                local_rot_mats=rot,global_rot_mats=rot.copy(),foot_contacts=np.zeros((3,4)))
    np.savez(tmp_path/'motion.npz',**motion)
    binding=dict(schema=SCHEMA,mesh_sha256=mesh_fingerprint(skin),hand='LeftHand',face_ids=[0],limits=LIMITS.copy())
    contact=dict(id='grip',actor='A',effector=dict(joint='LeftHand',surface_vertex=0),
                 target=dict(space='object',object='box',point_m=[0,.5,0]),
                 start_frame=0,end_frame=2,tolerance_m=.02,region_contact=binding)
    scene=dict(schema_version=1,id='region-test',fps=30,frame_count=3,
               actors={'A':dict(motion='motion.npz',transform=dict(translation_m=[0,0,0],rotation_xyzw=[0,0,0,1]))},
               contacts=[contact],objects={'box':dict(geometry=Geometry('box',(1,1,1)).record(),
                 keyframes=[dict(frame=0,translation_m=[0,0,0],rotation_xyzw=[0,0,0,1])])})
    return skin,scene,tmp_path


@pytest.mark.parametrize('failure',['mesh','duplicate','bool','outside','anchor','limits','hand'])
def test_binding_rejects_stale_or_ambiguous_mesh_selections(fixture,failure):
    skin,scene,_=fixture;c=scene['contacts'][0];b=c['region_contact']
    if failure=='mesh':skin['bind_vertices'][0,0]+=.001
    if failure=='duplicate':b['face_ids']=[0,0]
    if failure=='bool':b['face_ids']=[False]
    if failure=='outside':b['face_ids']=[1]
    if failure=='anchor':c['effector']['surface_vertex']=4
    if failure=='limits':b['limits']['spacing_m']=float('nan')
    if failure=='hand':b['hand']='RightHand'
    with pytest.raises(ValueError):validate_binding(b,c['effector'],skin)


def test_compilation_preserves_native_region_and_rejects_legacy_reduction(fixture):
    skin,scene,root=fixture;original=copy.deepcopy(scene)
    result=compile_regions(scene,'A',['grip'],skin,root)
    assert scene==original and result['regions'][0]['binding']==scene['contacts'][0]['region_contact']
    assert result['solver_supported'] and result['solver_version']==14
    with pytest.raises(ValueError,match='cannot be reduced'):compile_contacts(scene,'A',['grip'],skin,root)
    with pytest.raises(ValueError,match='does not support'):compile_context(scene,'A',['grip'],skin)
    yaw=Rotation.from_euler('y',60,degrees=True)
    scene['actors']['A']['transform']=dict(translation_m=[2,0,3],rotation_xyzw=yaw.as_quat().tolist())
    result=compile_regions(scene,'A',['grip'],skin,root)['regions'][0]
    np.testing.assert_allclose(yaw.apply(result['object_positions_m'])+[2,0,3],np.zeros((3,3)),atol=1e-12)
    np.testing.assert_allclose(yaw.apply(result['desired_normals']),np.tile([0,-1,0],(3,1)),atol=1e-12)


def test_scene_acceptance_cannot_ignore_failed_region_when_anchor_passes(fixture):
    skin,scene,root=fixture
    first=evaluate(scene,skin,root)['contacts'][0]
    assert first['all_requested_frames_within_tolerance']
    skin['bind_vertices'][1:,1]+=.1
    scene['contacts'][0]['region_contact']['mesh_sha256']=mesh_fingerprint(skin)
    failed=evaluate(scene,skin,root)['contacts'][0]
    assert failed['anchor_all_requested_frames_within_tolerance']
    assert not failed['all_requested_frames_within_tolerance']
    assert failed['region_contact']['passed_frames']==0


def test_region_cannot_be_silently_used_for_partner_or_world(fixture):
    skin,scene,root=fixture;scene['contacts'][0]['target']=dict(space='world',point_m=[0,.5,0])
    with pytest.raises(ValueError,match='rigid primitive'):compile_regions(scene,'A',['grip'],skin,root)


@pytest.mark.parametrize('value',[0,-.01,True,float('nan'),float('inf')])
def test_region_compilation_rejects_invalid_anchor_tolerances(fixture,value):
    skin,scene,root=fixture;scene['contacts'][0]['tolerance_m']=value
    with pytest.raises(ValueError,match='Anchor tolerance'):compile_regions(scene,'A',['grip'],skin,root)
