import copy
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read
from build_soma_preview import ASSET
from floor_contact import Surface
from palm_contacts import calibrate,surface_track
from scene_constraints import effector_track,target_track,transform_motion
from compile_scene_contacts import compile_contacts


@pytest.fixture(scope='module')
def skin():return dict(np.load(ASSET))


def test_calibrated_points_are_on_mirrored_palm_regions_and_bind_surface(skin):
    candidates=calibrate(skin);surface=Surface(skin);bind=skin['bind_rig_transform']
    actor=dict(rotations=bind[None,:,:3,:3],positions=bind[None,:,:3,3])
    for name,c in candidates.items():
        vertex=c['surface_vertex'];assert vertex in surface.regions[name]
        np.testing.assert_allclose(surface_track(actor,skin,vertex)[0],skin['bind_vertices'][vertex],atol=1e-6)
        j=surface.names.index(name)
        np.testing.assert_allclose(bind[j,:3,:3]@c['offset_m']+bind[j,:3,3],skin['bind_vertices'][vertex],atol=1e-6)
        assert np.linalg.norm(c['palm_normal_local'])==pytest.approx(1)
        assert c['status']=='anatomical_review_pending'
    np.testing.assert_allclose(np.abs(candidates['LeftHand']['offset_m']),np.abs(candidates['RightHand']['offset_m']),atol=.001)


def test_partner_target_uses_actual_surface_not_wrist_offset(skin):
    scene=read(ROOT/'reports/scene-preview-v1/high-five-seed-11/palm.json')['scene']
    entry=scene['actors']['B'];motion=dict(np.load(ROOT/entry['motion']))
    actor=transform_motion(motion,entry['transform']);candidate=calibrate(skin)['RightHand']
    target=dict(space='actor',actor='B',**candidate)
    actual=target_track(target,{'B':actor},{},120,skin)
    expected=effector_track(actor,candidate,skin)
    np.testing.assert_array_equal(actual,expected)
    wrist=effector_track(actor,dict(joint='RightHand',offset_m=[0,0,0]),skin)
    assert np.linalg.norm(actual-wrist,axis=1).min()>.03


def test_compiler_inverse_actor_transform_and_rotating_moving_box(skin):
    scene=read(ROOT/'reports/scene-preview-v1/lift-box-seed-11/palm.json')['scene']
    scene['actors']['A']['transform']=dict(translation_m=[2,0,-1],rotation_xyzw=Rotation.from_euler('y',90,degrees=True).as_quat().tolist())
    scene['objects']['box']['keyframes']=[dict(frame=0,translation_m=[2,1,0],rotation_xyzw=[0,0,0,1]),dict(frame=179,translation_m=[2,2,0],rotation_xyzw=Rotation.from_euler('y',90,degrees=True).as_quat().tolist())]
    scene['contacts'][0].update(start_frame=0,end_frame=179)
    spec,provenance=compile_contacts(scene,'A',['left-grip'],skin)
    track=np.array(spec['regions']['LeftHand']['segments'][0]['positions_m'])
    # First grip world [1.8,1.1,0]; last [2,2.1,.2]. Undo actor yaw and origin.
    np.testing.assert_allclose(track[0],[-1,1.1,-.2],atol=1e-12)
    np.testing.assert_allclose(track[-1],[-1.2,2.1,0],atol=1e-12)
    assert spec['schema_version']==2
    assert provenance['sources']['A']['sha256']==scene['actors']['A']['source_sha256']


def test_two_actors_get_same_shared_world_goal_in_different_native_spaces(skin):
    scene=read(ROOT/'reports/scene-preview-v1/high-five-seed-11/palm.json')['scene']
    for name in ['A','B']:
        spec,_=compile_contacts(scene,name,[name+'-meeting'],skin)
        native=np.array(spec['regions']['RightHand']['segments'][0]['positions_m'][0])
        pose=scene['actors'][name]['transform']
        world=Rotation.from_quat(pose['rotation_xyzw']).apply(native)+pose['translation_m']
        np.testing.assert_allclose(world,[0,1.5,0],atol=1e-12)


@pytest.mark.parametrize('change', ['tilt','height','overlap','proxy','wrong_actor','unknown_id','hash'])
def test_compiler_rejects_unsupported_or_ambiguous_constraints(skin,change):
    scene=copy.deepcopy(read(ROOT/'reports/scene-preview-v1/high-five-seed-11/palm.json')['scene']);ids=['A-meeting']
    if change=='tilt':scene['actors']['A']['transform']['rotation_xyzw']=Rotation.from_euler('x',10,degrees=True).as_quat().tolist()
    if change=='height':scene['actors']['A']['transform']['translation_m'][1]=.1
    if change=='overlap':ids.append('hand-to-hand')
    if change=='proxy':del scene['contacts'][0]['effector']['surface_vertex']
    if change=='wrong_actor':ids=['B-meeting']
    if change=='unknown_id':ids=['missing']
    if change=='hash':scene['actors']['A']['source_sha256']='bad'
    with pytest.raises(ValueError):compile_contacts(scene,'A',ids,skin)


def test_compiler_keeps_authored_tolerance_in_native_track_and_provenance(skin):
    scene=copy.deepcopy(read(ROOT/'reports/scene-preview-v1/lift-box-seed-11/palm.json')['scene'])
    scene['contacts'][0]['tolerance_m']=.001
    snapshot=copy.deepcopy(scene)
    spec,provenance=compile_contacts(scene,'A',['left-grip'],skin)
    assert scene==snapshot
    assert spec['regions']['LeftHand']['segments'][0]['tolerance_m']==.001
    assert provenance['contacts'][0]['tolerance_m']==.001
    del scene['contacts'][0]['tolerance_m']
    spec,provenance=compile_contacts(scene,'A',['left-grip'],skin)
    assert spec['regions']['LeftHand']['segments'][0]['tolerance_m']==.03
