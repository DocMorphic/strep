import copy
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
from hand_posture import validate,author,weight
from verify_rig_clearance import localize


def fixture():
    rig=SimpleNamespace(parents=[-1,0,1,0],joints=[0,1,2,3])
    local=np.tile(np.eye(4),(61,4,1,1));local[:,0,0,3]=np.linspace(0,2,61);local[:,1,1,3]=1;local[:,2,0,3]=.1
    recipe=dict(schema='strep-hand-posture-v1',source_glb_sha256='a'*64,frames=61,fps=30,hand_roots=[1],
        poses=[dict(id='first',hand_root=1,targets=[dict(node=2,rotation_xyzw=Rotation.from_euler('z',30,degrees=True).as_quat().tolist())],start_frame=0,full_start_frame=10,full_end_frame=20,end_frame=30,strength=1.)],
        limits=dict(rotation_degrees=60,correction_step_degrees=5),provenance='Explicit test target')
    return rig,local,recipe


def test_timing_slerp_and_disjoint_postures_preserve_each_other_and_body():
    rig,local,recipe=fixture();second=copy.deepcopy(recipe['poses'][0]);second.update(id='second',start_frame=30,full_start_frame=40,full_end_frame=50,end_frame=60)
    second['targets'][0]['rotation_xyzw']=Rotation.from_euler('z',-30,degrees=True).as_quat().tolist();recipe['poses'].append(second)
    assert validate(recipe,rig,'a'*64)==[2]
    world,weights,checks=author(local,rig.parents,recipe);actual=localize(world,rig.parents)
    for frame,degrees in [(0,0),(5,15),(10,30),(20,30),(25,15),(30,0),(35,-15),(40,-30),(50,-30),(55,-15),(60,0)]:
        np.testing.assert_allclose(actual[frame,2,:3,:3],Rotation.from_euler('z',degrees,degrees=True).as_matrix(),atol=1e-12)
    np.testing.assert_allclose(actual[:,[0,1,3]],local[:,[0,1,3]],atol=1e-12)
    np.testing.assert_allclose(actual[:,:,:3,3],local[:,:,:3,3],atol=1e-12)
    assert checks[0]['max_correction_step_degrees']<=5


def test_binding_hand_hierarchy_overlap_and_rotation_validation():
    rig,_,recipe=fixture()
    with pytest.raises(ValueError,match='Source'):validate(recipe,rig,'b'*64)
    for node in [0,1,3]:
        r=copy.deepcopy(recipe);r['poses'][0]['targets'][0]['node']=node
        with pytest.raises(ValueError):validate(r,rig,'a'*64)
    r=copy.deepcopy(recipe);r['poses'].append(copy.deepcopy(r['poses'][0]));r['poses'][1]['id']='overlap'
    with pytest.raises(ValueError,match='Overlapping'):validate(r,rig,'a'*64)
    r=copy.deepcopy(recipe);r['poses'][0]['targets'][0]['rotation_xyzw']=[0,0,0,0]
    with pytest.raises(ValueError,match='unit quaternion'):validate(r,rig,'a'*64)


def test_large_or_abrupt_changes_are_rejected_and_zero_strength_is_unchanged():
    rig,local,recipe=fixture();recipe['limits']['rotation_degrees']=20
    with pytest.raises(ValueError,match='budget'):author(local,rig.parents,recipe)
    recipe['limits']['rotation_degrees']=60;recipe['poses'][0]['full_start_frame']=1
    with pytest.raises(ValueError,match='budget'):author(local,rig.parents,recipe)
    recipe['poses'][0]['strength']=0
    world,_,_=author(local,rig.parents,recipe)
    np.testing.assert_allclose(localize(world,rig.parents),local,atol=1e-12)


def test_absolute_target_blends_from_a_varying_rough_finger_track():
    rig,local,recipe=fixture()
    local[:,2,:3,:3]=Rotation.from_euler('z',np.arange(61)/6,degrees=True).as_matrix()
    world,_,_=author(local,rig.parents,recipe);actual=localize(world,rig.parents)
    for frame in [5,10,20,25,35]:
        w=float(weight(61,recipe['poses'][0])[frame]);angle=(1-w)*frame/6+w*30
        np.testing.assert_allclose(actual[frame,2,:3,:3],Rotation.from_euler('z',angle,degrees=True).as_matrix(),atol=1e-12)


def test_simultaneous_two_hand_tracks_are_independent():
    rig,local,recipe=fixture();rig.parents.append(3);rig.joints.append(4)
    local=np.concatenate([local,np.tile(np.eye(4),(61,1,1,1))],axis=1);local[:,4,2,3]=.1
    recipe['hand_roots']=[1,3];second=copy.deepcopy(recipe['poses'][0]);second.update(id='right',hand_root=3)
    second['targets']=[dict(node=4,rotation_xyzw=Rotation.from_euler('y',20,degrees=True).as_quat().tolist())];recipe['poses'].append(second)
    assert validate(recipe,rig,'a'*64)==[2,4]
    world,_,_=author(local,rig.parents,recipe);actual=localize(world,rig.parents)
    np.testing.assert_allclose(actual[15,2,:3,:3],Rotation.from_euler('z',30,degrees=True).as_matrix(),atol=1e-12)
    np.testing.assert_allclose(actual[15,4,:3,:3],Rotation.from_euler('y',20,degrees=True).as_matrix(),atol=1e-12)
    np.testing.assert_allclose(actual[:,[0,1,3]],local[:,[0,1,3]],atol=1e-12)
