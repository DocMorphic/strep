import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from shared_palm_meeting import target,measure


C=np.array([[0.,0.,-.01],[.01,0.,.01]])
N=np.array([[0.,0.,1.],[0.,0.,-1.]])


def test_target_has_shared_midpoint_and_facing_normals():
    spec=target(C,N);centers=np.array(spec['centers_m']);normals=np.array(spec['normals'])
    np.testing.assert_allclose(centers.mean(axis=0),C.mean(axis=0))
    assert np.linalg.norm(centers[0]-centers[1])==pytest.approx(.001)
    assert (centers[1]-centers[0])@normals[0]>0
    row=measure(centers,normals,spec)
    assert row['contact_target_pass'] and row['collision_validation_required'] and not row['quality_approved']
    assert not measure(C,N,spec)['contact_target_pass']


def test_actor_swap_preserves_physical_target():
    first=target(C,N);second=target(C[::-1],N[::-1])
    np.testing.assert_allclose(first['centers_m'],np.array(second['centers_m'])[::-1])
    np.testing.assert_allclose(first['normals'],np.array(second['normals'])[::-1])


def test_rigid_placement_preserves_target_geometry():
    rotation=Rotation.from_rotvec([.2,.4,-.1]).as_matrix();shift=np.array([1.,2.,3.])
    first=target(C,N);second=target(C@rotation.T+shift,N@rotation.T)
    np.testing.assert_allclose(second['centers_m'],np.array(first['centers_m'])@rotation.T+shift)


def test_bad_surface_normals_fail_closed():
    with pytest.raises(ValueError,match='unit'):target(C,np.zeros((2,3)))
    with pytest.raises(ValueError,match='ambiguous'):target(C,np.tile(N[0],(2,1)))


def test_anchor_distance_alone_cannot_pass_orientation():
    spec=target(C,N)
    assert not measure(spec['centers_m'],-np.array(spec['normals']),spec)['contact_target_pass']
