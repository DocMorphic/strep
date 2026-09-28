from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from conic_root_descent import tightened_cap


def test_buffer_only_tightens_movable_prediction_and_keeps_tiny_caps_positive():
    item=dict(kind='support_speed',cap=2e-5,jacobian=np.ones((2,1)))
    assert tightened_cap(item,{'support_speed':1e-5})==1e-5
    assert tightened_cap(item,{'support_speed':1.})==1e-5
    assert tightened_cap(item,{})==item['cap']
    assert item['cap']==2e-5
    assert tightened_cap({**item,'jacobian':np.zeros((2,1))},{'support_speed':1.})==item['cap']


def test_bad_buffer_cannot_loosen_caps():
    item=dict(kind='foot_acceleration',cap=1.,jacobian=np.ones((3,1)))
    for value in [-1.,np.nan,np.inf]:
        with pytest.raises(ValueError):tightened_cap(item,{'foot_acceleration':value})
