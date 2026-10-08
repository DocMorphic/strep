import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from point_numerical_headroom import working_limits,validate_margin


def test_absolute_and_relative_caps_keep_stricter_positive_active_limits_without_mutation():
    limits=np.array([[.001,.005,1e-7],[.001,.005,1e-7]])
    active=np.array([[True,True,True],[False,False,False]])
    before=limits.copy();mask=active.copy()
    result,reserved=working_limits(limits,active,.00001)
    np.testing.assert_allclose(reserved[0],[1e-5,1e-5,1e-9],atol=0,rtol=1e-15)
    np.testing.assert_array_equal(result[1],limits[1])
    assert (result[0]<limits[0]).all() and (result>0).all()
    np.testing.assert_array_equal(result+reserved,limits)
    np.testing.assert_array_equal(limits,before);np.testing.assert_array_equal(active,mask)
    assert not np.shares_memory(result,limits)


def test_disabled_headroom_is_exactly_compatible_and_never_changes_acceptance_data():
    limits=np.array([[.005,.001],[.003,.002]])
    for active in [np.ones((2,2),bool),np.zeros((2,2),bool)]:
        result,reserved=working_limits(limits,active,0.)
        np.testing.assert_array_equal(result,limits);np.testing.assert_array_equal(reserved,0.)


@pytest.mark.parametrize('margin',[True,False,-1e-6,.00101,float('nan'),float('inf'),'0.00001',None])
def test_invalid_numerical_margins_reject(margin):
    with pytest.raises(ValueError):validate_margin(margin)


@pytest.mark.parametrize('limits,active',[
    ([[0.]],[[True]]),([[-.001]],[[True]]),([[float('nan')]],[[True]]),
    ([[float('inf')]],[[True]]),([.001],[True]),([[]],[[]]),
    ([[.001]],[[1]]),([[.001]],[[False,True]])])
def test_invalid_or_incomplete_populations_reject(limits,active):
    with pytest.raises(ValueError):working_limits(limits,np.asarray(active),.00001)


def test_complete_long_clock_reserves_only_requested_keys_in_every_column():
    limits=np.full((1800,4),.005);limits[203:901,1]=.001
    active=np.zeros_like(limits,dtype=bool);active[203:901,1]=True;active[1300:,3]=True
    result,reserved=working_limits(limits,active,.00001)
    assert result.shape==(1800,4) and np.count_nonzero(reserved)==1198
    np.testing.assert_array_equal(result[~active],limits[~active])
    assert (result[active]<limits[active]).all()
