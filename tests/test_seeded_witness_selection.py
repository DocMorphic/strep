from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from seeded_witness_selection import select


def records():
    return [dict(source=1,target=0,points=[[4],[3]]),dict(source=0,target=1,points=[[9],[5]])]


def test_includes_boundary_both_directions_and_preserves_depth_identity():
    r=select(records(),[.019,.018,.017999,.02],.02,.002)
    assert r['keys']==[(0,1,5),(1,0,3),(1,0,4)]
    np.testing.assert_allclose(r['original_depths_m'],[.02,.018,.019])


def test_retains_empty_population_and_no_cap_relaxation():
    r=select(records(),[-.001,0,.002,.003],.005,.001)
    assert r['keys']==[] and r['cap_m']==.005
    with pytest.raises(ValueError,match='exceeds'):select(records(),[.020001,0,0,0],.02,.002)


@pytest.mark.parametrize('depths,cap,band', [([0,0,0],.02,.002),([0,0,0,np.nan],.02,.002),([0]*4,-1,.002),([0]*4,.02,0),([0]*4,.02,np.inf)])
def test_rejects_malformed_depths_or_thresholds(depths,cap,band):
    with pytest.raises(ValueError):select(records(),depths,cap,band)


def test_duplicate_or_invalid_vertices_are_not_silently_removed():
    r=records();r[0]['points'][1]=[4]
    with pytest.raises(ValueError):select(r,[0]*4,.02,.002)
    r=records();r[0]['points'][0]=[True]
    with pytest.raises(ValueError):select(r,[0]*4,.02,.002)
