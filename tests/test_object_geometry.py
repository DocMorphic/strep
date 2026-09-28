import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from object_geometry import Geometry
from scene_constraints import box_vertex_depth
from scene_solver_context import box_signed_distance
from object_dynamics import uniform_box_inertia,diagnose


def test_rotated_box_preserves_existing_depth_distance_and_inertia():
    rng=np.random.default_rng(24);points=rng.normal(size=(300,3));center=np.array([.1,.2,-.3])
    r=Rotation.from_euler('xyz',[.4,-.7,.2]).as_matrix();size=[.7,.9,1.3];shape=Geometry('box',tuple(size))
    np.testing.assert_allclose(shape.penetration_depth(points,center,r),box_vertex_depth(points,center,r,size),atol=1e-15)
    np.testing.assert_array_equal(shape.distance_gradient(points,center,r)[0],box_signed_distance(points,center,r,size))
    np.testing.assert_array_equal(shape.uniform_inertia(2.),uniform_box_inertia(2.,size))


def test_sphere_distance_is_rotation_invariant_and_has_exact_depth():
    sphere=Geometry('sphere',(.25,));p=np.array([[0,0,0],[.1,0,0],[.25,0,0],[.4,0,0]])
    d,g,defined=sphere.distance_gradient(p,[0,0,0],np.eye(3))
    np.testing.assert_allclose(d,[-.25,-.15,0,.15],atol=1e-15)
    assert not defined[0] and np.all(defined[1:])
    r=Rotation.from_rotvec([.4,.1,.9]).as_matrix()
    np.testing.assert_allclose(sphere.distance_gradient(p,[0,0,0],r)[0],d,atol=1e-15)
    np.testing.assert_allclose(sphere.world_half_extents(r),[.25]*3)


@pytest.mark.parametrize('shape',[Geometry('box',(.7,.9,1.3)),Geometry('sphere',(.4,))])
def test_world_gradients_match_central_differences(shape):
    p=np.array([[.2,.1,.1],[1.,.8,.7],[-.8,.2,.6]])
    r=Rotation.from_euler('xyz',[.2,.3,-.4]).as_matrix();center=np.array([.1,-.2,.05])
    _,gradient,defined=shape.distance_gradient(p,center,r);assert np.all(defined)
    columns=[]
    for axis in range(3):
        delta=np.zeros(3);delta[axis]=1e-6
        columns.append((shape.distance_gradient(p+delta,center,r)[0]-shape.distance_gradient(p-delta,center,r)[0])/2e-6)
    np.testing.assert_allclose(gradient,np.stack(columns,axis=1),atol=1e-8,rtol=1e-7)


def test_grip_normal_rejects_box_edges_and_sphere_interior():
    box=Geometry('box',(2.,2.,2.));sphere=Geometry('sphere',(1.,))
    np.testing.assert_array_equal(box.local_surface_normal([1,0,0]),[1,0,0])
    with pytest.raises(ValueError):box.local_surface_normal([1,1,0])
    with pytest.raises(ValueError):sphere.local_surface_normal([0,0,0])
    np.testing.assert_allclose(sphere.local_surface_normal([0,1,0]),[0,1,0])


def test_sphere_constant_spin_free_flight_has_zero_required_wrench():
    t=np.arange(9)/30;gravity=np.array([0.,-9.81,0.]);p=np.array([0.,1.,0.])+t[:,None]*[1.,2.,0.]+.5*t[:,None]**2*gravity
    q=Rotation.from_rotvec(t[:,None]*[.4,.7,-.2]).as_quat();sphere=Geometry('sphere',(.2,))
    result=diagnose(p,q,fps=30,mass_kg=3.,inertia_body_kg_m2=sphere.uniform_inertia(3.),gravity_m_s2=gravity,
        phases=[dict(id='flight',start_frame=0,end_frame_exclusive=9,support_assumption='free_flight')])
    np.testing.assert_allclose(result['required_non_gravity_force_world_N'],0,atol=1e-10)
    np.testing.assert_allclose(result['required_torque_about_com_world_Nm'],0,atol=1e-10)


@pytest.mark.parametrize('value',[
    {'schema':'strep-object-geometry-v1','shape':'sphere','radius_m':True},
    {'schema':'strep-object-geometry-v1','shape':'sphere','radius_m':-1},
    {'schema':'strep-object-geometry-v1','shape':'box','size_m':[1,2,float('nan')]},
    {'schema':'strep-object-geometry-v1','shape':'sphere','radius_m':1,'size_m':[2,2,2]},
])
def test_ambiguous_or_invalid_geometry_is_rejected(value):
    with pytest.raises(ValueError):Geometry.parse(value)
