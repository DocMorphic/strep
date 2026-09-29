import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from rotation_return import tangent_return, bounded_path_edits


@pytest.mark.parametrize('delta',[[0.,0.,0.],[1e-7,-2e-7,1e-7],[.5,-.9,.3],[3.13,0.,0.]])
def test_noncommuting_endpoint_body_rates_and_rotations(delta):
    a=Rotation.from_rotvec([[.1,.2,-.3]]);b=a*Rotation.from_rotvec([delta])
    rate0=np.array([[.012,-.023,.031]]);rate1=np.array([[-.021,.007,.019]])
    before=a*Rotation.from_rotvec(-rate0);after=b*Rotation.from_rotvec(rate1);duration=24
    def at(t): return Rotation.from_matrix(tangent_return(a.as_matrix(),b.as_matrix(),before.as_matrix(),after.as_matrix(),t,duration))
    np.testing.assert_allclose(at(0).as_matrix(),a.as_matrix(),atol=1e-14)
    np.testing.assert_allclose(at(1).as_matrix(),b.as_matrix(),atol=1e-14)
    h=1e-7
    np.testing.assert_allclose((a.inv()*at(h)).as_rotvec()/(h*duration),rate0,atol=5e-8)
    np.testing.assert_allclose((at(1-h).inv()*b).as_rotvec()/(h*duration),rate1,atol=5e-8)


@pytest.mark.parametrize('fraction,duration',[(-1,24),(1.1,24),(np.nan,24),(.5,0),(.5,np.inf)])
def test_invalid_path_inputs(fraction,duration):
    with pytest.raises(ValueError): tangent_return(*([np.eye(3)[None]]*4),fraction,duration)


def test_norm_projection_preserves_safe_vectors_and_direction():
    vectors=np.array([[0.,0.,0.],[.1,.2,.3],[.4,.8,1.2]])
    out=bounded_path_edits(vectors,np.full(3,.7))
    np.testing.assert_array_equal(out[:2],vectors[:2])
    assert np.linalg.norm(out[2])==pytest.approx(.699)
    np.testing.assert_allclose(out[2]/np.linalg.norm(out[2]),vectors[2]/np.linalg.norm(vectors[2]))
    with pytest.raises(ValueError): bounded_path_edits(vectors,np.full(3,.0001))
