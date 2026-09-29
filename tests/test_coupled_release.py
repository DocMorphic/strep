import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from coupled_release import second_difference_matrix,speed_excess_pair


def test_temporal_operator_preserves_affine_paths_and_detects_boundary_spike():
    matrix=second_difference_matrix(7)
    np.testing.assert_array_equal(matrix@(2+3*np.arange(7)),np.zeros(5))
    spike=np.zeros(7);spike[1]=1
    np.testing.assert_array_equal(matrix@spike,[-2,1,0,0,0])
    # A selected interior key affects the adjacent locked-boundary stencil.
    assert matrix[0,1]!=0


@pytest.mark.parametrize('count',[2,-1,3.0,True])
def test_temporal_operator_rejects_invalid_key_count(count):
    with pytest.raises(ValueError):second_difference_matrix(count)


def test_speed_cap_gradient_and_inactive_stationary_case():
    a=np.array([.1,.2,.3]);b=a+np.array([.004,-.002,.006]);cap=.1;scale=.0005
    value,da,db=speed_excess_pair(a,b,cap,scale)
    assert value>0
    direction=np.array([.2,-.3,.1]);h=1e-7
    fd=(speed_excess_pair(a+h*direction,b,cap,scale)[0]-speed_excess_pair(a-h*direction,b,cap,scale)[0])/(2*h)
    assert fd==pytest.approx(da@direction,rel=1e-6)
    np.testing.assert_array_equal(da,-db)
    value,da,db=speed_excess_pair(a,a,0.,scale)
    assert value==0 and not da.any() and not db.any()
    with pytest.raises(ValueError):speed_excess_pair(a,b,cap,0.)
