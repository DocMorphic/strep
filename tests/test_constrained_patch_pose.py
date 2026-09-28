import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from constrained_patch_pose import constraint_pair


def test_floor_and_euclidean_contact_derivatives():
    rng=np.random.default_rng(2)
    points=rng.normal(0,.02,(8,3));jac=rng.normal(0,.1,(8,3,4))
    patches={'knee':dict(vertices=[0,1,2]),'foot':dict(vertices=[5,6,7])}
    contacts=[dict(patch='knee',target_position_m=[0,.0015,0]),dict(patch='foot',target_position_m=[.01,.0015,.01])]
    c,d=constraint_pair(points,jac,contacts,patches,.005,.02)
    numeric=[]
    for i in range(4):
        a=constraint_pair(points+jac[:,:,i]*1e-6,jac,contacts,patches,.005,.02)[0]
        b=constraint_pair(points-jac[:,:,i]*1e-6,jac,contacts,patches,.005,.02)[0]
        numeric.append((a-b)/2e-6)
    np.testing.assert_allclose(d,np.array(numeric).T,atol=1e-8,rtol=1e-6)
    assert len(c)==10


def test_margin_tightens_instead_of_relaxing_screens():
    points=np.array([[0,-.005,0.]])
    c,_=constraint_pair(points,np.zeros((1,3,1)),[],{},.005,.02)
    assert c[0]<0
    with pytest.raises(ValueError):constraint_pair(points,np.zeros((1,3,1)),[],{},.005,.02,margin=.006)
