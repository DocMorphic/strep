import copy
import itertools
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from convex_colliders import ConvexBoxTest,direction_hull,validate_points,volume_centroid
from actor_collision_proxies import DIRECTIONS
from release_colliders import box_separation,audit_collisions
from object_release import simulate,validate,ENGINE,audit_simulation


def cube(size=(2,.2,2)):
    return (np.array(list(itertools.product([-1.,1.],repeat=3)))*np.array(size)/2).tolist()


def test_polytope_outer_fit_and_box_equivalence():
    points=np.array(cube());hull=direction_hull(DIRECTIONS,(points@DIRECTIONS.T).max(axis=0)+.001)
    assert len(hull)<=48
    fit=ConvexBoxTest(cube());rng=np.random.default_rng(311)
    for _ in range(30):
        p=rng.normal(size=3);r=Rotation.random(random_state=rng).as_matrix();p2=rng.normal(size=3);r2=Rotation.random(random_state=rng).as_matrix()
        assert fit.gap(p,r,[.4,.3,.2],p2,r2)==pytest.approx(box_separation(p,r,[.4,.3,.2],p2,r2,[2,.2,2]),abs=1e-10)
    assert fit.gap([0,0,0],np.eye(3),[.1,.1,.1],[0,0,0],np.eye(3))==pytest.approx(-.15)


@pytest.mark.parametrize('points',[[[0,0,0]]*4,[[0,0,0],[1,0,0],[0,1,0],[1,1,0]],cube()+[[0,0,0]],cube()+[cube()[0]]])
def test_invalid_convex_geometry(points):
    with pytest.raises(ValueError):validate_points(points)


def test_asymmetric_uniform_tetrahedron_centroid():
    vertices=np.array([[0,0,0],[.4,0,0],[0,.2,0],[0,0,.3]])
    np.testing.assert_allclose(volume_centroid(vertices),vertices.mean(axis=0),atol=1e-14)
    r=Rotation.from_euler('xyz',[.2,-.5,.7]).as_matrix();translation=[2,3,4]
    np.testing.assert_allclose(volume_centroid(vertices@r.T+translation),vertices.mean(axis=0)@r.T+translation,atol=1e-12)


@pytest.mark.skipif(not ENGINE.exists(),reason='Pinned engine unavailable')
@pytest.mark.parametrize('asymmetric',[False,True,'irregular'])
def test_actual_moving_convex_contact_and_geometry_audit(tmp_path,asymmetric):
    steps=480;t=np.arange(-1,steps+1)/240
    r=dict(position_m=[0,1.2,0],rotation_xyzw=[0,0,0,1],linear_velocity_m_s=[0,0,0],angular_velocity_rad_s=[0,0,0],size_m=[.2,.2,.2],mass_kg=2.,physics_fps=240,steps=steps,friction=.6,restitution=0.,floor_enabled=True,floor_height_m=0.,contact_max_allowed_penetration_m=.001,backend='Jolt Physics',moving_colliders=[dict(id='actor:A:fixture',shape='convex',points_m=cube(),friction=.6,restitution=0.,positions_m=(np.array([0,.9,0])+t[:,None]*[.2,.15,0]).tolist(),rotations_xyzw=Rotation.from_rotvec(t[:,None]*[0,.2,0]).as_quat().tolist())])
    if asymmetric:
        r['moving_colliders'][0]['points_m']=[[0,0,0],[.4,0,0],[0,.2,0],[0,0,.3]]
    if asymmetric=='irregular':
        cloud=np.random.default_rng(241).normal(size=(100,3))*[.15,.07,.12]+[.03,-.04,.01]
        r['moving_colliders'][0]['points_m']=direction_hull(DIRECTIONS,(cloud@DIRECTIONS.T).max(axis=0)).tolist()
    report=simulate(r,tmp_path/'convex');audit=audit_collisions(r,report['observations'],2)
    assert audit['actor_collisions_simulated'] and not audit['actor_motion_responds']
    if not asymmetric:assert audit['collision_and_settling_screens_passed']
    broken=copy.deepcopy(report);broken['moving_colliders'][0]['points_m'][0][0]+=.01
    with pytest.raises(AssertionError):audit_simulation(validate(r),broken)
