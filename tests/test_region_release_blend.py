import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from region_release_blend import release_weight


@pytest.mark.parametrize('profile',['quintic','early-return'])
def test_release_weights_preserve_endpoints_and_original_norm_balls(profile):
    frames=np.linspace(121,145,97);weights=np.array([release_weight(f,121,145,profile) for f in frames])
    assert weights[0]==1 and weights[-1]==0 and (np.diff(weights)<=0).all()
    assert release_weight(120,121,145)==1 and release_weight(146,121,145)==0
    a=np.array([.3,.2,.1]);b=np.array([-.2,.1,.3]);mixed=(1-weights[:,None])*a+weights[:,None]*b
    assert (np.linalg.norm(mixed,axis=1)<=max(np.linalg.norm(a),np.linalg.norm(b))+1e-12).all()


@pytest.mark.parametrize('frame,start,end',[(121,121,121),(122,121,120),(np.nan,121,145)])
def test_invalid_release_intervals_rejected(frame,start,end):
    with pytest.raises(ValueError):release_weight(frame,start,end)


def test_early_return_has_flat_endpoints_and_moves_weight_before_speed_peak():
    h=1e-4
    assert (1-release_weight(h,0,1,'early-return'))/h**2<.02
    assert release_weight(1-h,0,1,'early-return')/h**2<.02
    assert release_weight(130.75,121,145,'early-return')<release_weight(130.75,121,145)
    with pytest.raises(ValueError):release_weight(125,121,145,'unknown')
