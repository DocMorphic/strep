import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from regional_pose_full_residual import family_weights


def test_weights_balance_families_without_omitting_any_row():
    w=family_weights(18,[np.arange(2),np.arange(2,5)],list(range(5,18)))
    g=np.r_[np.full(2,2.),np.full(3,3.),np.ones(13)]
    assert np.all(w>0)
    assert np.square(w*g).sum()==pytest.approx(20.)
    for i in range(18):
        probe=np.full(18,-1.);probe[i]=1e-6
        assert np.square(w*np.maximum(probe,0)).sum()>0
    assert not np.maximum(-np.ones(18),0).any()


@pytest.mark.parametrize('count,groups,singles',[
    (3,[[0,1],[1,2]],[]), (3,[[0,1]],[]), (2,[[0,1]],[1]), (2,[[]],[]), (2,[[0,2]],[])])
def test_incomplete_duplicate_or_invalid_layout_rejected(count,groups,singles):
    with pytest.raises(ValueError):family_weights(count,groups,singles)
