from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_inverse_rigid_frame import inverse_rigid_frame_points as pull


def skew(w):return np.array([[0.,-w[2],w[1]],[w[2],0.,-w[0]],[-w[1],w[0],0.]])


def fixture(columns=7):
    rng=np.random.default_rng(17);p=rng.normal(size=(5,3));t=rng.normal(size=3);R=Rotation.from_rotvec([.3,-.7,.2]).as_matrix();jp=rng.normal(size=(5,3,columns));jt=rng.normal(size=(3,columns));omega=rng.normal(size=(3,columns));jr=np.stack([R@skew(omega[:,c]) for c in range(columns)],axis=-1)
    return p,t,R,jp,jt,jr,omega


def test_values_match_independent_homogeneous_inverse_and_roundtrip():
    p,t,R,*_=fixture();local,jac,report=pull(p,t,R);T=np.eye(4);T[:3,:3]=R;T[:3,3]=t;expected=(np.linalg.inv(T)@np.c_[p,np.ones(len(p))].T).T[:,:3]
    np.testing.assert_allclose(local,expected,atol=1e-14);np.testing.assert_allclose(local@R.T+t,p,atol=1e-14);assert jac is None and not report['frame_repaired']


def test_every_column_matches_independent_finite_rigid_pose_perturbations():
    p,t,R,jp,jt,jr,omega=fixture();local,jac,report=pull(p,t,R,points_jacobian=jp,position_jacobian=jt,rotation_jacobian=jr)
    for c in range(jp.shape[-1]):
        h=1e-6;plus=pull(p+h*jp[...,c],t+h*jt[:,c],R@Rotation.from_rotvec(h*omega[:,c]).as_matrix())[0];minus=pull(p-h*jp[...,c],t-h*jt[:,c],R@Rotation.from_rotvec(-h*omega[:,c]).as_matrix())[0]
        np.testing.assert_allclose((plus-minus)/(2*h),jac[...,c],atol=2e-9,rtol=2e-8)
    assert report['columns']==7 and report['point_translation_rotation_derivatives_included'] and not report['collision_certified']


def test_common_rigid_point_and_frame_motion_cancels():
    p,t,R,jp,jt,jr,_=fixture();local=pull(p,t,R)[0];jp=np.einsum('ijc,vj->vic',jr,local)+jt[None,:,:];_,jac,_=pull(p,t,R,points_jacobian=jp,position_jacobian=jt,rotation_jacobian=jr)
    np.testing.assert_allclose(jac,0.,atol=3e-15)


def test_final_supported_column_is_not_dropped():
    p,t,R,*_=fixture();jp=np.zeros((5,3,768));jt=np.zeros((3,768));jr=np.zeros((3,3,768));jp[:,:,-1]=[1.,2.,3.];_,jac,report=pull(p,t,R,points_jacobian=jp,position_jacobian=jt,rotation_jacobian=jr)
    assert report['columns']==768 and np.count_nonzero(jac[...,:-1])==0;np.testing.assert_allclose(jac[...,-1],np.tile([1.,2.,3.]@R,(5,1)))


def test_global_rigid_reexpression_preserves_local_values_and_jacobians():
    p,t,R,jp,jt,jr,_=fixture();q=Rotation.from_rotvec([-.1,.2,.4]).as_matrix();a=np.array([2.,3.,4.]);expected=pull(p,t,R,points_jacobian=jp,position_jacobian=jt,rotation_jacobian=jr)
    actual=pull(p@q.T+a,q@t+a,q@R,points_jacobian=np.einsum('ij,vjc->vic',q,jp),position_jacobian=q@jt,rotation_jacobian=np.einsum('ij,jkc->ikc',q,jr))
    for x,y in zip(actual[:2],expected[:2]):np.testing.assert_allclose(x,y,atol=8e-15)


def test_fixed_frame_uses_complete_point_derivatives_with_explicit_zero_frame_sides():
    p,t,R,jp,jt,jr,_=fixture();_,jac,_=pull(p,t,R,points_jacobian=jp,position_jacobian=np.zeros_like(jt),rotation_jacobian=np.zeros_like(jr));np.testing.assert_allclose(jac,np.einsum('vkc,kj->vjc',jp,R))


def test_moving_projection_value_and_derivative_are_invariant_under_common_rotation():
    from native_triangle_pair_projection import projection_rows
    a=np.array([[[0.,0,0],[0.,1,0],[0.,0,1]]]);b=a+[1.,0,0];R=Rotation.from_rotvec([.1,.3,-.2]).as_matrix();t=np.array([2.,3.,4.]);local_points=np.vstack([a.reshape(-1,3),b.reshape(-1,3)]);world=local_points@R.T+t;jr=(R@skew([.3,.5,.7]))[...,None];jt=np.array([[.1],[.2],[.3]]);jp=np.einsum('ijc,vj->vic',jr,local_points)+jt[None,:,:]
    value,jac,_=pull(world,t,R,points_jacobian=jp,position_jacobian=jt,rotation_jacobian=jr);rows=projection_rows(value[:3][None],value[3:][None],np.array([[1.,0,0]]),left_jacobian=jac[:3][None],right_jacobian=jac[3:][None])
    np.testing.assert_allclose(rows['jacobian'],0.,atol=1e-13);np.testing.assert_allclose(rows['margins'],100.,atol=1e-12)


@pytest.mark.parametrize('missing',[0,1,2])
def test_incomplete_derivative_sides_rejected(missing):
    p,t,R,jp,jt,jr,_=fixture();kw=dict(points_jacobian=jp,position_jacobian=jt,rotation_jacobian=jr);kw[list(kw)[missing]]=None
    with pytest.raises(ValueError,match='All point'):pull(p,t,R,**kw)


@pytest.mark.parametrize('bad',[np.diag([-1.,1.,1.]),np.diag([1.,1.,1.1]),np.zeros((3,3))])
def test_nonrigid_or_reflected_frame_is_rejected_without_repair(bad):
    p,t,*_=fixture()
    with pytest.raises(ValueError,match='Proper rigid'):pull(p,t,bad)


def test_inconsistent_rotation_derivative_is_rejected():
    p,t,R,jp,jt,jr,_=fixture();jr[:,:,0]=R
    with pytest.raises(ValueError,match='tangent'):pull(p,t,R,points_jacobian=jp,position_jacobian=jt,rotation_jacobian=jr)


@pytest.mark.parametrize('which',[0,1,2,3,4,5])
def test_nonfinite_complete_inputs_rejected(which):
    arrays=list(fixture()[:6]);arrays[which].flat[-1]=np.nan;p,t,R,jp,jt,jr=arrays
    with pytest.raises(ValueError,match='finite'):pull(p,t,R,points_jacobian=jp,position_jacobian=jt,rotation_jacobian=jr)


@pytest.mark.parametrize('budget',[dict(maximum_jacobian_bytes=1),dict(maximum_working_bytes=1),dict(maximum_working_bytes=True),dict(maximum_jacobian_bytes=64*1024**2+1)])
def test_complete_budget_rejection_never_truncates_points_or_columns(budget):
    p,t,R,jp,jt,jr,_=fixture()
    with pytest.raises(ValueError):pull(p,t,R,points_jacobian=jp,position_jacobian=jt,rotation_jacobian=jr,**budget)


@pytest.mark.parametrize('bad',['empty','columns','frame_columns','boolean','complex','too_far'])
def test_invalid_shapes_or_nonreal_values_rejected(bad):
    p,t,R,jp,jt,jr,_=fixture()
    if bad=='empty':p=p[:0]
    elif bad=='columns':jp=np.zeros((5,3,769))
    elif bad=='frame_columns':jt=jt[:,:-1]
    elif bad=='boolean':p=p.astype(bool)
    elif bad=='complex':jr=jr.astype(complex)
    else:p[0,0]=1e7
    with pytest.raises(ValueError):pull(p,t,R,points_jacobian=jp,position_jacobian=jt,rotation_jacobian=jr)


def test_strided_inputs_remain_unchanged():
    p,t,R,jp,jt,jr,_=fixture();p=p[::-1];jp=jp[::-1];original=[a.copy() for a in [p,t,R,jp,jt,jr]];pull(p,t,R,points_jacobian=jp,position_jacobian=jt,rotation_jacobian=jr)
    for a,b in zip(original,[p,t,R,jp,jt,jr]):np.testing.assert_array_equal(a,b)
