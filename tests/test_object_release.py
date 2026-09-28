import copy
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from object_release import simulate,release_request,validate,bake,audit_simulation,ENGINE
from strep import read


def track():
    t=np.arange(61)/30
    return dict(fps=30,size_m=[.4,.4,.4],positions_m=np.c_[t,10+2*t-.1*t*t,-t].tolist(),
        rotations_xyzw=Rotation.from_rotvec(t[:,None]*[0,1,0]).as_quat().tolist())


def test_release_uses_only_incoming_motion_and_preserves_input():
    source=track();before=copy.deepcopy(source);request=release_request(source,30)
    np.testing.assert_allclose(request['linear_velocity_m_s'],[1,1.8,-1],atol=1e-12)
    np.testing.assert_allclose(request['angular_velocity_rad_s'],[0,1,0],atol=1e-12)
    source['positions_m'][31]=[1000,2000,3000]
    assert release_request(source,30)==request
    assert before['positions_m'][30]==request['position_m']


@pytest.mark.parametrize('key,value',[('mass_kg',False),('physics_fps',60),('steps',0),
    ('size_m',[-1,1,1]),('floor_enabled',1),('friction',1.01),('restitution',float('nan')),
    ('rotation_xyzw',[0,0,0,2])])
def test_invalid_simulation_request_rejected(key,value):
    request=release_request(track(),30);request[key]=value
    with pytest.raises(ValueError):validate(request)


@pytest.mark.skipif(not ENGINE.exists(),reason='Pinned local Godot unavailable')
def test_real_engine_clock_analytic_freefall_spin_and_bake(tmp_path):
    source=track();before=copy.deepcopy(source);request=release_request(source,30)
    request['floor_enabled']=False
    actual=simulate(request,tmp_path/'engine');obs=actual['observations'];t=np.arange(len(obs))/240;g=np.array([0.,-9.81,0.])
    p0=np.array(request['position_m']);v0=np.array(request['linear_velocity_m_s']);dt=1/240
    # GodotPhysics3D uses semi-implicit Euler, whose constant-gravity discrete
    # solution differs from the analytic parabola by g*t*dt/2.
    expected=p0+t[:,None]*v0+.5*(t*t+t*dt)[:,None]*g
    np.testing.assert_allclose([o['position_m'] for o in obs],expected,atol=3e-5,rtol=0)
    np.testing.assert_allclose([o['linear_velocity_m_s'] for o in obs],v0+t[:,None]*g,atol=3e-5,rtol=0)
    r0=Rotation.from_quat(request['rotation_xyzw'])
    expected_r=(Rotation.from_rotvec(t[:,None]*request['angular_velocity_rad_s'])*r0).as_matrix()
    np.testing.assert_allclose(Rotation.from_quat([o['rotation_xyzw'] for o in obs]).as_matrix(),expected_r,atol=1e-5,rtol=0)
    assert all(o['contact_count']==0 for o in obs)
    candidate=bake(source,30,request,actual)
    assert source==before and candidate['positions_m'][:31]==source['positions_m'][:31]
    assert candidate['rotations_xyzw'][:31]==source['rotations_xyzw'][:31]
    np.testing.assert_allclose(candidate['positions_m'][31:],np.array([o['position_m'] for o in obs])[8::8],atol=0,rtol=0)
    corrupted=copy.deepcopy(actual);corrupted['observations'][3]['tick']=4
    with pytest.raises(ValueError,match='ticks'):bake(source,30,request,corrupted)


@pytest.mark.skipif(not ENGINE.exists(),reason='Pinned local Godot unavailable')
def test_floor_impact_is_simulated_and_timestep_refinement_reduces_freefall_error(tmp_path):
    source=track();source['positions_m']=[[0,1,0] for _ in source['positions_m']]
    source['rotations_xyzw']=[[0,0,0,1] for _ in source['rotations_xyzw']]
    request=release_request(source,2)
    actual=simulate(request,tmp_path/'floor');obs=actual['observations'];positions=np.array([o['position_m'] for o in obs])
    assert any(o['contact_count']>0 for o in obs)
    assert .19<positions[-1,1]<.21 and positions[:,1].min()>.19
    assert np.linalg.norm(obs[-1]['linear_velocity_m_s'])<.05
    # At 0.1s, before impact, halving dt halves the integration error.
    errors=[]
    for fps in [240,480]:
        req=copy.deepcopy(request);req.update(physics_fps=fps,steps=fps//10,floor_enabled=False)
        run=simulate(req,tmp_path/str(fps));end=run['observations'][-1]
        errors.append(abs(end['position_m'][1]-(1-.5*9.81*.1**2)))
    assert .45<errors[1]/errors[0]<.55
