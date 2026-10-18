"""Authored clock/frame/source wiring with inert metadata fixtures, no vendor."""
from pathlib import Path
import copy
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import compile_scene_guidance as module
from strep import sha256


@pytest.fixture
def fixture(tmp_path,monkeypatch):
    names=['Hips','RightHand',*['RightHand'+f+'2' for f in ['Index','Middle','Ring','Pinky']]]+[f'joint{i}' for i in range(71)]
    assert len(names)==77
    skin=dict(rig_joint_names=np.array(names),bind_vertices=np.array([[0.,0.,0.],[0.,0.,.1],[.1,0.,0.]]),faces=np.array([[0,1,2]]),
        lbs_indices=np.zeros((3,8),dtype=int),lbs_weights=np.tile([1.,0,0,0,0,0,0,0],(3,1)),bind_rig_transform=np.tile(np.eye(4),(77,1,1)))
    count=5;motion=dict(posed_joints=np.zeros((count,77,3)),root_positions=np.zeros((count,3)),global_rot_mats=np.tile(np.eye(3),(count,77,1,1)),local_rot_mats=np.tile(np.eye(3),(count,77,1,1)),foot_contacts=np.zeros((count,6)))
    for name in ['A','B']:np.savez(tmp_path/(name+'.npz'),**motion)
    identity=dict(translation_m=[0.,0.,0.],rotation_xyzw=[0.,0.,0.,1.])
    scene=dict(schema_version=1,id='source-scene',fps=30,frame_count=count,actors={name:dict(motion=name+'.npz',source_sha256=sha256(tmp_path/(name+'.npz')),transform=copy.deepcopy(identity)) for name in ['A','B']},
        objects={'parcel':dict(shape='box',size_m=[.2,.4,.6],keyframes=[dict(frame=0,**identity),dict(frame=4,translation_m=[1.,0.,0.],rotation_xyzw=[0.,0.,0.,1.])])},
        contacts=[dict(id='grip',actor='A',effector=dict(surface_vertex=0,joint='RightHand'),target=dict(space='object',object='parcel',point_m=[.1,0.,0.]),start_frame=1,end_frame=3,tolerance_m=.005,normal_target=dict(space='world',direction=[0.,1.,0.]),tangent_target=dict(space='world',direction=[1.,0.,0.]))])
    monkeypatch.setattr(module,'validate_motion',lambda motion,fps:(names,None,None))
    return scene,skin,tmp_path


def test_every_object_frame_contact_interval_and_orientation_is_preserved(fixture):
    scene,skin,root=fixture;old=copy.deepcopy(scene);result=module.compile_scene_guidance(scene,'A',skin,project_root=root)
    assert scene==old and result['all_original_contact_ids']==['grip'] and len(result['primitives'][0]['positions_m'])==5
    c=result['contacts'][0];assert c['start_frame']==1 and c['end_frame']==3 and len(c['targets_m'])==len(c['normal_directions'])==len(c['tangent_directions'])==3
    np.testing.assert_allclose(c['targets_m'],[[.35,0,0],[.6,0,0],[.85,0,0]])
    assert c['tolerance_m']==.005 and c['normal_faces']==[[0,1,2]] and not result['partner_collision_evaluated']


def test_arbitrary_rigid_actor_placement_and_explicit_origin_reproduce_world_values(fixture):
    scene,skin,root=fixture;r=Rotation.from_euler('xyz',[20.,40.,-15.],degrees=True);p=np.array([1.,2.,3.]);scene['actors']['A']['transform']=dict(translation_m=p.tolist(),rotation_xyzw=r.as_quat().tolist())
    result=module.compile_scene_guidance(scene,'A',skin,project_root=root,origin_xz_m=(.3,-.2));effective=p+r.apply([.3,0,-.2])
    np.testing.assert_allclose(result['actor_placement_m'],effective)
    native=np.array(result['contacts'][0]['targets_m']);np.testing.assert_allclose(native@r.as_matrix().T+effective,[[.35,0,0],[.6,0,0],[.85,0,0]],atol=1e-14)
    world=np.array([.2,.7,-.5]);local=(world-effective)@r.as_matrix()
    assert local@np.array(result['floor_normal'])-result['floor_offset_m']==pytest.approx(world[1])


def test_box_sphere_and_cylinder_tracks_are_kept_without_proxy_substitution(fixture):
    scene,skin,root=fixture
    for shape in ['sphere','cylinder']:
        scene['objects'][shape]=dict(geometry=dict(schema='strep-object-geometry-v1',shape=shape,radius_m=.2,**({'height_m':.6} if shape=='cylinder' else {})),keyframes=[dict(frame=0,translation_m=[1.,0.,0.],rotation_xyzw=[0.,0.,0.,1.])])
    result=module.compile_scene_guidance(scene,'A',skin,project_root=root)
    assert [p['geometry']['shape'] for p in result['primitives']]==['box','sphere','cylinder'] and all(len(p['positions_m'])==5 for p in result['primitives'])


def test_incoming_partner_point_uses_fixed_source_and_keeps_original_identity(fixture):
    scene,skin,root=fixture;scene['contacts']=[dict(id='meeting',actor='B',effector=dict(surface_vertex=0),target=dict(space='actor',actor='A',surface_vertex=1),start_frame=2,end_frame=2,tolerance_m=.03)]
    result=module.compile_scene_guidance(scene,'A',skin,project_root=root);c=result['contacts'][0]
    assert c['id']=='meeting' and c['vertex']==1 and c['reciprocal_point'] and c['target_provenance']=='fixed reference partner track' and 'normal_directions' not in c


@pytest.mark.parametrize('fault',['hash','interval','actor','object','self_contact','region','unit','tangent','origin'])
def test_invalid_or_unmodeled_requirements_reject_before_inference(fixture,fault):
    scene,skin,root=fixture;kwargs={}
    if fault=='hash':scene['actors']['A']['source_sha256']='0'*64
    elif fault=='interval':scene['contacts'][0]['end_frame']=5
    elif fault=='actor':scene['contacts'][0]['actor']='missing'
    elif fault=='object':scene['contacts'][0]['target']['object']='missing'
    elif fault=='self_contact':scene['contacts'][0]['target']=dict(space='actor',actor='A',surface_vertex=1)
    elif fault=='region':scene['contacts'][0]['region_contact']={}
    elif fault=='unit':scene['contacts'][0]['normal_target']['direction']=[0,2,0]
    elif fault=='tangent':scene['contacts'][0]['tangent_target']['direction']=[0,1,0]
    else:kwargs['origin_xz_m']=(float('nan'),0.)
    with pytest.raises(ValueError):module.compile_scene_guidance(scene,'A',skin,project_root=root,**kwargs)


def test_reference_read_race_does_not_bind_different_bytes(fixture,monkeypatch):
    scene,skin,root=fixture;old=module.validate_motion;changed=[False]
    def racing(motion,fps):
        if not changed[0]:
            with (root/'A.npz').open('ab') as f:f.write(b'changed during read')
            changed[0]=True
        return old(motion,fps)
    monkeypatch.setattr(module,'validate_motion',racing)
    with pytest.raises(ValueError,match='changed'):module.compile_scene_guidance(scene,'A',skin,project_root=root)
