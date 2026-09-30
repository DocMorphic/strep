import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from coupled_surface_norms import separation_rows,penetrating_rows


def test_both_actors_contribute_in_canonical_order_and_common_translation_cancels():
    point=np.array([[.2,.3,-.02]])
    triangle=np.array([[[0.,0,0],[1,0,0],[0,1,0]]]);bary=np.array([[.5,.2,.3]])
    source=np.eye(3)[None];target=np.tile(np.eye(3),(1,3,1,1))
    for actor in [0,1]:
        vector,jacobian=separation_rows(point,triangle,bary,source,target,actor)
        np.testing.assert_allclose(vector,[[0,0,-.02]],atol=1e-15)
        np.testing.assert_allclose(jacobian@np.tile([.1,.2,.3],2),0,atol=1e-15)
        expected=np.concatenate([np.eye(3),-np.eye(3)] if actor==0 else [-np.eye(3),np.eye(3)],axis=1)
        np.testing.assert_allclose(jacobian[0],expected)


def test_only_initially_penetrating_rows_get_the_distance_cap():
    vectors=np.array([[0,0,-.01],[0,0,.002],[0,0,0.]])
    rows=penetrating_rows(vectors,np.zeros((3,3,6)),np.array([-.01,.002,0]),np.array([.02,.02,.02]))
    np.testing.assert_array_equal(rows['witness_indices'],[0])
    np.testing.assert_array_equal(rows['radii'],[.02])
    np.testing.assert_array_equal(rows['vectors'],vectors[:1])


def test_fixed_barycentric_distance_bounds_closest_face_distance():
    point=np.array([[.201,.3,-.02]])
    triangle=np.array([[[0.,0,0],[1,0,0],[0,1,0]]]);bary=np.array([[.5,.2,.3]])
    vector,_=separation_rows(point,triangle,bary,np.zeros((1,3,3)),np.zeros((1,3,3,3)),0)
    nearest_face_distance=.02
    assert np.linalg.norm(vector[0])>nearest_face_distance
    assert np.linalg.norm(vector[0])==pytest.approx(np.hypot(.02,.001))


def test_invalid_barycentric_binding_cannot_claim_a_surface_distance_bound():
    with pytest.raises(ValueError,match='Barycentric'):
        separation_rows(np.zeros((1,3)),np.zeros((1,3,3)),[[-.1,.5,.6]],np.zeros((1,3,3)),np.zeros((1,3,3,3)),0)
    with pytest.raises(ValueError,match='nonnegative'):
        penetrating_rows(np.zeros((1,3)),np.zeros((1,3,3)),[-.1],[-.1])


def test_roundoff_at_triangle_edge_is_projected_to_convex_weights():
    triangle=np.array([[[0.,0,0],[1.,0,0],[0,1.,0]]])
    vector,_=separation_rows(np.zeros((1,3)),triangle,[[-1e-12,.5,.5+1e-12]],np.zeros((1,3,2)),np.zeros((1,3,3,4)),1)
    point=-vector[0]
    assert point[0]>=0 and point[1]>=0 and point[2]==0
    assert point.sum()==pytest.approx(1.)
    assert vector.shape==(1,3)
