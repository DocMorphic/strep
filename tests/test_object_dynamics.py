import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from object_dynamics import diagnose,uniform_box_inertia


def setup(frames=31):
    return dict(positions_m=np.zeros((frames,3)),rotations_xyzw=np.tile([0.,0.,0.,1.],(frames,1)),
        fps=30,mass_kg=5.,inertia_body_kg_m2=uniform_box_inertia(5.,[.4,.6,.8]),
        gravity_m_s2=[0.,-9.81,0.],phases=[dict(id='whole',start_frame=0,end_frame_exclusive=frames,support_assumption='unknown')])


def test_stationary_object_requires_weight_support_not_zero_force():
    result=diagnose(**setup())
    np.testing.assert_allclose(result['required_non_gravity_force_world_N'],np.tile([0,49.05,0],(29,1)))
    np.testing.assert_allclose(result['required_torque_about_com_world_Nm'],0)
    assert result['physical_approval'] is None
    assert not result['phases'][0]['free_flight_residual_applicable']


def test_ballistic_com_has_zero_non_gravity_force():
    args=setup();t=np.arange(31)/30
    args['positions_m']=np.c_[2*t,1+3*t-4.905*t**2,-t]
    args['phases'][0]['support_assumption']='free_flight'
    result=diagnose(**args)
    np.testing.assert_allclose(result['required_non_gravity_force_world_N'],0,atol=5e-11)
    assert result['phases'][0]['free_flight_residual_applicable']


def test_constant_rotation_about_nonprincipal_axis_requires_gyroscopic_torque():
    args=setup();axis=np.array([1.,2.,3.]);axis/=np.linalg.norm(axis);omega=2*axis
    args['rotations_xyzw']=Rotation.from_rotvec(np.arange(31)[:,None]/30*omega).as_quat()
    result=diagnose(**args);r=Rotation.from_quat(args['rotations_xyzw'][1:-1]).as_matrix()
    expected=np.einsum('fij,j->fi',r,np.cross(omega,args['inertia_body_kg_m2']@omega))
    np.testing.assert_allclose(result['required_torque_about_com_world_Nm'],expected,atol=1e-11)


def test_coordinate_change_and_quaternion_signs_do_not_change_physics():
    args=setup();t=np.arange(31)/30;args['positions_m']=np.c_[t**2,t**3,t]
    args['rotations_xyzw']=Rotation.from_rotvec(t[:,None]*[.5,1.,0.]).as_quat()
    base=diagnose(**args);rot=Rotation.from_euler('xyz',[.3,.5,.7]);r=rot.as_matrix()
    args['positions_m']=args['positions_m']@r.T+[4,5,6]
    args['rotations_xyzw']=(rot*Rotation.from_quat(args['rotations_xyzw'])).as_quat()
    args['rotations_xyzw'][::2]*=-1
    args['gravity_m_s2']=r@args['gravity_m_s2'];actual=diagnose(**args)
    for field in ['required_non_gravity_force_world_N','required_torque_about_com_world_Nm']:
        np.testing.assert_allclose(actual[field],np.array(base[field])@r.T,atol=1e-10)


def test_phase_boundary_impulse_is_retained_but_not_averaged_into_interior():
    args=setup(9);args['positions_m'][4:,0]=1
    args['phases']=[dict(id='a',start_frame=0,end_frame_exclusive=4,support_assumption='supported'),
        dict(id='b',start_frame=4,end_frame_exclusive=9,support_assumption='unknown')]
    result=diagnose(**args)
    assert result['excluded_boundary_frames']==[3,4]
    assert abs(result['required_non_gravity_force_world_N'][2][0])==4500
    assert [p['interior_samples'] for p in result['phases']]==[2,3]
    assert result['phases'][1]['required_non_gravity_force_N']['max']==pytest.approx(49.05,abs=1e-12)


@pytest.mark.parametrize('field,value',[('mass_kg',True),('mass_kg',0),('fps',float('nan')),
    ('inertia_body_kg_m2',np.diag([1.,1.,3.])),('gravity_m_s2',[0,float('inf'),0]),
    ('rotations_xyzw',np.tile([0.,0.,0.,2.],(31,1))),('phases',[])])
def test_invalid_assumptions_are_rejected(field,value):
    args=setup();args[field]=value
    with pytest.raises(ValueError):diagnose(**args)


def test_missing_phase_coverage_is_not_assumed_free_flight():
    args=setup();args['phases'][0]['start_frame']=1
    with pytest.raises(ValueError,match='cover'):diagnose(**args)


def test_pi_rotation_step_rejected():
    args=setup();args['rotations_xyzw'][1]=[1,0,0,0]
    with pytest.raises(ValueError,match='near-pi'):diagnose(**args)


def test_per_sample_gravity_matches_constant_vector_and_preserves_legacy_output():
    args=setup();legacy=diagnose(**args);args['gravity_m_s2']=np.tile(args['gravity_m_s2'],(31,1));actual=diagnose(**args)
    for name in legacy:
        if name!='gravity_m_s2':assert actual[name]==legacy[name]


def test_variable_native_gravity_uses_the_central_sample_without_smoothing():
    args=setup();gravity=np.zeros((31,3));gravity[:,0]=np.arange(31);gravity[:,1]=-9.81
    args['gravity_m_s2']=gravity;actual=diagnose(**args)
    np.testing.assert_array_equal(actual['required_non_gravity_force_world_N'],-5*gravity[1:-1])
    assert actual['gravity_m_s2']==gravity.tolist()


@pytest.mark.parametrize('gravity',[np.zeros((30,3)),np.zeros((31,1)),np.full((31,3),np.nan)])
def test_incomplete_or_nonfinite_gravity_tracks_are_rejected(gravity):
    args=setup();args['gravity_m_s2']=gravity
    with pytest.raises(ValueError,match='gravity'):diagnose(**args)
