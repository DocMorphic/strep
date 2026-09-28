import copy
import itertools
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from object_geometry import Geometry
from release_geometry import primitive_gap,body_geometry
from convex_colliders import ConvexSphereTest
from object_release import release_request,validate,simulate,bake,audit_simulation,ENGINE
from release_colliders import audit_collisions


def track():
    return dict(fps=30,geometry=Geometry('sphere',(.2,)).record(),positions_m=[[0,1.5,0] for _ in range(61)],rotations_xyzw=[[0,0,0,1] for _ in range(61)])


def test_primitive_pair_gaps_and_convex_distance_include_edges_and_corners():
    box=Geometry('box',(2.,2.,2.));sphere=Geometry('sphere',(.2,));r=Rotation.from_rotvec([.2,.3,.1]).as_matrix();origin=np.array([.7,-.2,.1])
    convex=ConvexSphereTest(list(map(list,itertools.product([-1.,1.],repeat=3))))
    for point in [[0,0,0],[.9,0,0],[1.1,0,0],[1.1,1.1,0],[1.3,1.4,1.5]]:
        center=np.array(point)@r.T+origin
        expected=float(box.distance_gradient(np.array([point]),np.zeros(3),np.eye(3))[0][0]-.2)
        assert primitive_gap(sphere,center,np.eye(3),box,origin,r)==pytest.approx(expected)
        assert primitive_gap(box,origin,r,sphere,center,np.eye(3))==pytest.approx(expected)
        assert convex.gap(center,.2,origin,r)==pytest.approx(expected)
    assert primitive_gap(sphere,[0,0,0],r,sphere,[.5,0,0],r)==pytest.approx(.1)


def test_sphere_request_uses_solid_inertia_and_rejects_mixed_dimensions():
    request=release_request(track(),2,mass_kg=3.)
    result=validate(request)
    assert 'size_m' not in request
    np.testing.assert_allclose(result['inertia_diagonal_kg_m2'],[.4*3*.2**2]*3)
    request['size_m']=[.4]*3
    with pytest.raises(ValueError):validate(request)


@pytest.mark.skipif(not ENGINE.exists(),reason='Pinned Godot unavailable')
def test_actual_sphere_freeflight_spin_geometry_and_prefix(tmp_path):
    source=track();source['positions_m']=[[0,10,0] for _ in range(61)]
    times=np.arange(61)/30;source['rotations_xyzw']=Rotation.from_rotvec(times[:,None]*[.2,.7,-.1]).as_quat().tolist()
    request=release_request(source,30);request['floor_enabled']=False
    report=simulate(request,tmp_path/'flight');observations=report['observations'];t=np.arange(len(observations))/240
    expected=np.array(request['position_m'])+.5*(t*t+t/240)[:,None]*[0,-9.81,0]
    np.testing.assert_allclose([o['position_m'] for o in observations],expected,atol=3e-5,rtol=0)
    rotation=Rotation.from_rotvec(t[:,None]*request['angular_velocity_rad_s'])*Rotation.from_quat(request['rotation_xyzw'])
    np.testing.assert_allclose(Rotation.from_quat([o['rotation_xyzw'] for o in observations]).as_matrix(),rotation.as_matrix(),atol=1e-5,rtol=0)
    assert report['released_geometry']['shape']=='sphere'
    candidate=bake(source,30,request,report)
    assert candidate['positions_m'][:31]==source['positions_m'][:31]
    assert candidate['rotations_xyzw'][:31]==source['rotations_xyzw'][:31]
    wrong=copy.deepcopy(report);wrong['released_geometry']['radius_m']=.3
    with pytest.raises(AssertionError):audit_simulation(validate(request),wrong)


@pytest.mark.parametrize('support',['floor','box','sphere'])
@pytest.mark.skipif(not ENGINE.exists(),reason='Pinned Godot unavailable')
def test_actual_sphere_contact_uses_installed_support_geometry(tmp_path,support):
    request=release_request(track(),2)
    if support!='floor':
        geometry=Geometry('box',(2.,.5,2.)) if support=='box' else Geometry('sphere',(.5,))
        request['static_colliders']=[dict(id='support',geometry=geometry.record(),position_m=[0,.25 if support=='box' else .5,0],rotation_xyzw=[0,0,0,1],friction=.6,restitution=0.)]
    report=simulate(request,tmp_path/support);obs=report['observations'];expected_id='floor' if support=='floor' else 'support'
    assert any(expected_id in o['contact_colliders'] for o in obs)
    audit=audit_collisions(validate(request),obs,2)
    assert all(row['max_penetration_m']<.01 for row in audit['colliders'])
    if support!='sphere':assert audit['collision_and_settling_screens_passed']
    if support=='floor':assert abs(obs[-1]['position_m'][1]-.2)<.01


@pytest.mark.skipif(not ENGINE.exists(),reason='Pinned Godot unavailable')
def test_actual_moving_sphere_pushes_released_sphere_on_jolt(tmp_path):
    source=track();source['positions_m']=[[0,.2,0] for _ in range(61)]
    request=release_request(source,2);request['backend']='Jolt Physics'
    steps=request['steps'];t=np.arange(-1,steps+1)/request['physics_fps']
    request['moving_colliders']=[dict(id='mover',geometry=Geometry('sphere',(.2,)).record(),positions_m=np.c_[-1+t,np.full(len(t),.2),np.zeros(len(t))].tolist(),rotations_xyzw=[[0,0,0,1] for _ in t],friction=.6,restitution=0.)]
    report=simulate(request,tmp_path/'moving');obs=report['observations']
    assert any('mover' in o['contact_colliders'] for o in obs)
    assert obs[-1]['position_m'][0]>.5
    assert report['moving_colliders'][0]['geometry']['shape']=='sphere'
    audit=audit_collisions(validate(request),obs,2)
    assert audit['colliders'][0]['max_penetration_m']<.01


@pytest.mark.skipif(not ENGINE.exists(),reason='Pinned Godot unavailable')
def test_actual_box_can_collide_with_a_static_sphere(tmp_path):
    source=track();source.pop('geometry');source['size_m']=[.4]*3
    request=release_request(source,2);request['backend']='Jolt Physics'
    request['static_colliders']=[dict(id='sphere-support',geometry=Geometry('sphere',(.5,)).record(),position_m=[0,.5,0],rotation_xyzw=[0,0,0,1],friction=.6,restitution=0.)]
    report=simulate(request,tmp_path/'box-on-sphere')
    assert report['released_geometry']['shape']=='box'
    assert any('sphere-support' in o['contact_colliders'] for o in report['observations'])
    audit=audit_collisions(validate(request),report['observations'],2)
    assert audit['colliders'][0]['shape']=='sphere' and audit['colliders'][0]['max_penetration_m']<.01
