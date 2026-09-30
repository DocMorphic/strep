import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from paired_surface_witness import moving_gap,moving_gap_jacobian


def data():
    triangles=np.array([[[0,0,0],[1,0,0],[0,1,0]]],float)
    return np.array([[.2,.3,-.02]]),triangles,np.array([[.5,.2,.3]]),np.array([[0,0,1.]])


def test_pair_gap_is_invariant_to_common_translation_but_tracks_partner():
    points,triangles,bary,normals=data();shift=np.array([3.,-2.,4.])
    assert moving_gap(points,triangles,bary,normals)[0]==pytest.approx(-.02)
    np.testing.assert_allclose(moving_gap(points+shift,triangles+shift,bary,normals),moving_gap(points,triangles,bary,normals),atol=1e-15)
    np.testing.assert_allclose(moving_gap(points,triangles+[0,0,.01],bary,normals),[-.03])


def test_both_actor_jacobians_match_independent_central_differences():
    points,triangles,bary,normals=data()
    source=np.array([[[.2,-.1],[.1,.3],[.5,-.2]]])
    target=np.arange(27,dtype=float).reshape(1,3,3,3)/100
    jac=moving_gap_jacobian(source,target,bary,normals)
    def value(x):
        return moving_gap(points+np.einsum('nid,d->ni',source,x[:2]),triangles+np.einsum('njid,d->nji',target,x[2:]),bary,normals)
    actual=np.empty_like(jac);step=1e-6
    for col in range(5):
        delta=np.zeros(5);delta[col]=step;actual[:,col]=(value(delta)-value(-delta))/(2*step)
    np.testing.assert_allclose(jac,actual,atol=1e-10,rtol=0)
    assert np.any(jac[:,:2]) and np.any(jac[:,2:])


def test_common_actor_translation_has_zero_relative_derivative():
    _,_,bary,normals=data();source=np.eye(3)[None];target=np.tile(np.eye(3),(1,3,1,1))
    jac=moving_gap_jacobian(source,target,bary,normals)
    np.testing.assert_allclose(jac@np.r_[1.,2.,3.,1.,2.,3.],0,atol=1e-15)


def test_rejects_off_triangle_binding_and_unnormalized_plane():
    points,triangles,bary,normals=data()
    with pytest.raises(ValueError,match='Barycentric'):moving_gap(points,triangles,np.array([[-.2,.2,1.]]),normals)
    with pytest.raises(ValueError,match='Unit'):moving_gap(points,triangles,bary,normals*2)
