import copy
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from moving_release_colliders import compile_moving
from object_release import simulate,validate,audit_simulation,ENGINE
from release_colliders import audit_collisions


def request(axis=(0,.2,0),velocity=(.2,.15,0),fps=240):
    t=np.arange(-1,fps*2+1)/fps
    collider=dict(id='table',size_m=[2,.2,2],friction=.6,restitution=0.,
        positions_m=(np.array([0,.9,0])+t[:,None]*velocity).tolist(),
        rotations_xyzw=Rotation.from_rotvec(t[:,None]*axis).as_quat().tolist())
    return dict(position_m=[0,1.2,0],rotation_xyzw=[0,0,0,1],linear_velocity_m_s=[0,0,0],angular_velocity_rad_s=[0,0,0],
        size_m=[.2,.2,.2],mass_kg=2.,physics_fps=fps,steps=fps*2,friction=.6,restitution=0.,floor_enabled=True,
        floor_height_m=0.,contact_max_allowed_penetration_m=.001,backend='Jolt Physics',moving_colliders=[collider])


@pytest.mark.parametrize('change',['length','nan','quaternion','duplicate','backend','id','shape','material'])
def test_bad_moving_requests_rejected(change):
    r=request();c=r['moving_colliders'][0]
    if change=='length':c['positions_m'].pop()
    if change=='nan':c['positions_m'][3][0]=float('nan')
    if change=='quaternion':c['rotations_xyzw'][3]=[0,0,0,2]
    if change=='duplicate':r['moving_colliders'].append(copy.deepcopy(c))
    if change=='backend':r.pop('backend')
    if change=='id':c['id']='floor'
    if change=='shape':c['size_m']=[0,1,1]
    if change=='material':c['friction']=True
    with pytest.raises(ValueError):validate(r)


def test_compiler_preserves_fractional_clock_and_incoming_sample():
    obj=dict(shape='box',size_m=[2,.2,2],keyframes=[
        dict(frame=0,translation_m=[0,.9,0],rotation_xyzw=[0,0,0,1]),
        dict(frame=60,translation_m=[.4,1.2,0],rotation_xyzw=Rotation.from_rotvec([0,.4,0]).as_quat().tolist())])
    scene=dict(frame_count=61,objects=dict(released=copy.deepcopy(obj),table=obj))
    c=compile_moving(scene,'released',2,physics_fps=240,friction=.6,restitution=0)[0]
    t=2/30+np.arange(-1,465)/240
    np.testing.assert_allclose(c['positions_m'],np.array([0,.9,0])+t[:,None]*[.2,.15,0],atol=1e-12)
    np.testing.assert_allclose(Rotation.from_quat(c['rotations_xyzw']).as_rotvec(),t[:,None]*[0,.2,0],atol=1e-12)


@pytest.mark.skipif(not ENGINE.exists(),reason='Pinned Godot unavailable')
@pytest.mark.parametrize('axis,velocity,fps',[
    ((0,.2,0),(.2,.15,0),240),((.11,-.17,.23),(.05,0,-.1),240),
    ((0,0,0),(0,0,0),240),((0,.2,0),(.2,.15,0),480)])
def test_actual_kinematic_pose_velocity_and_backend(axis,velocity,fps,tmp_path):
    r=request(axis,velocity,fps);result=simulate(r,tmp_path/'simulation')
    assert result['direct_state_class']=='JoltPhysicsDirectBodyState3D'
    assert result['collision_margin_fraction']==0
    # simulate already audits every pose, linear and angular velocity, clock,
    # shape, material, mass/inertia and dynamic initial state against request.
    if axis==(0,.2,0):
        audit=audit_collisions(r,result['observations'],2)
        assert audit['collision_and_settling_screens_passed']
        assert audit['final_speed_m_s']>.2
        assert audit['final_relative_support_motion'][0]['linear_speed_m_s']<.001
    for field in ['position_m','linear_velocity_m_s','angular_velocity_rad_s']:
        broken=copy.deepcopy(result);broken['observations'][10]['moving_colliders'][0][field][0]+=.01
        with pytest.raises(AssertionError):audit_simulation(validate(r),broken)
    broken=copy.deepcopy(result);broken['direct_state_class']='GodotPhysicsDirectBodyState3D'
    with pytest.raises(ValueError,match='actually active'):audit_simulation(validate(r),broken)
    broken=copy.deepcopy(result);broken['observations'][5]['moving_colliders']=[]
    with pytest.raises(ValueError,match='observations'):audit_simulation(validate(r),broken)


@pytest.mark.skipif(not ENGINE.exists(),reason='Pinned Godot unavailable')
def test_jolt_analytic_freefall_and_static_impact(tmp_path):
    r=request();r['moving_colliders']=[];r['position_m']=[0,2,0];r['floor_enabled']=False
    result=simulate(r,tmp_path/'freefall')
    for o in result['observations']:
        t=o['tick']/r['physics_fps']
        np.testing.assert_allclose(o['position_m'],[0,2-9.81*(t*t+t/r['physics_fps'])/2,0],atol=1e-4,rtol=0)
        np.testing.assert_allclose(o['linear_velocity_m_s'],[0,-9.81*t,0],atol=1e-4,rtol=0)
    r['floor_enabled']=True
    result=simulate(r,tmp_path/'impact')
    assert audit_collisions(r,result['observations'],2)['collision_and_settling_screens_passed']
