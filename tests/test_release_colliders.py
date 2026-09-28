import copy
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from release_colliders import validate_colliders,compile_colliders,box_separation,audit_collisions
from object_release import release_request,simulate,validate,audit_simulation,ENGINE


def platform():
    return dict(id='table',size_m=[4,.2,3],position_m=[0,.9,0],rotation_xyzw=Rotation.from_euler('y',37,degrees=True).as_quat().tolist(),friction=.6,restitution=0.)


@pytest.mark.parametrize('field,value',[('id','floor'),('id','../bad'),('size_m',[0,1,1]),('position_m',[0,float('nan'),0]),('rotation_xyzw',[0,0,0,2]),('friction',True),('restitution',2)])
def test_invalid_static_geometry_or_material_rejected(field,value):
    item=platform();item[field]=value
    with pytest.raises(ValueError):validate_colliders([item])


def test_sat_touch_overlap_separation_and_coordinate_invariance():
    eye=np.eye(3);p=np.array([0.,0,0]);size=[2,2,2]
    for x,expected in [(2,0),(2.2,.2),(1.8,-.2),(0,-2)]:
        q=np.array([x,0.,0.]);assert box_separation(p,eye,size,q,eye,size)==pytest.approx(expected)
        r=Rotation.from_euler('xyz',[37,19,61],degrees=True).as_matrix();t=np.array([3.,2,-1])
        assert box_separation(r@p+t,r,size,r@q+t,r,size)==pytest.approx(expected,abs=1e-12)
    assert box_separation(p,eye,[2,2,2],p,eye,[8,8,8])==pytest.approx(-5)


def test_moving_scene_geometry_is_not_silently_frozen():
    obj=dict(shape='box',size_m=[1,1,1],keyframes=[dict(frame=0,translation_m=[0,0,0],rotation_xyzw=[0,0,0,1]),dict(frame=5,translation_m=[1,0,0],rotation_xyzw=[0,0,0,1])])
    scene=dict(frame_count=6,objects=dict(released=copy.deepcopy(obj),table=obj))
    with pytest.raises(ValueError,match='moves after release'):compile_colliders(scene,'released',2,friction=.6,restitution=0)
    scene['objects']['table']['keyframes']=[obj['keyframes'][-1]|{'frame':0}]
    result=compile_colliders(scene,'released',2,friction=.6,restitution=0)
    assert len(result)==1 and result[0]['id']=='object:table' and result[0]['position_m']==[1,0,0]


@pytest.mark.skipif(not ENGINE.exists(),reason='Pinned Godot unavailable')
def test_actual_static_table_contact_is_not_floor_and_audit_detects_tampering(tmp_path):
    track=dict(fps=30,size_m=[.2,.2,.2],positions_m=[[0,2,0]]*91,rotations_xyzw=[[0,0,0,1]]*91)
    request=release_request(track,2,mass_kg=2,friction=.6,restitution=0)
    request['static_colliders']=[platform()]
    result=simulate(request,tmp_path/'table');obs=result['observations'];audit=audit_collisions(request,obs,2)
    assert 'table' in audit['final_contact_colliders'] and 'floor' not in audit['final_contact_colliders']
    # The 240Hz hard impact exceeds the 10mm depth screen. Keep that failure;
    # settling on the intended surface does not erase an impact defect.
    assert not audit['collision_and_settling_screens_passed']
    assert audit['colliders'][0]['max_penetration_m']>.01
    assert obs[-1]['position_m'][1]==pytest.approx(1.1,abs=.003)
    before=[o for o in obs if o['tick']/240<.3]
    for o in before:
        t=o['tick']/240;assert o['position_m'][1]==pytest.approx(2-9.81*(t*t+t/240)/2,abs=2e-5)
        assert o['contact_colliders']==[]
    broken=copy.deepcopy(result);broken['static_colliders'][0]['position_m'][0]+=1
    with pytest.raises(AssertionError):audit_simulation(validate(request),broken)
    broken=copy.deepcopy(result);broken['observations'][-1]['contact_colliders'][0]='unknown'
    with pytest.raises(ValueError,match='contact records'):audit_simulation(validate(request),broken)
    # Geometric proximity cannot invent a contact observation.
    missing=copy.deepcopy(obs)
    for o in missing:o['contact_colliders']=[];o['contact_count']=0
    assert not audit_collisions(request,missing,2)['collision_and_settling_screens_passed']
    refined=copy.deepcopy(request);refined['physics_fps']=480;refined['steps']*=2
    finer=simulate(refined,tmp_path/'table-480hz');finer_audit=audit_collisions(refined,finer['observations'],2)
    assert finer_audit['colliders'][0]['max_penetration_m']<audit['colliders'][0]['max_penetration_m']
    assert finer_audit['collision_and_settling_screens_passed']
