import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from edit_interval_clock import edit_interval_clock


def test_full_release_is_sampled_even_when_historical_crossings_end_at_contact():
    times,report=edit_interval_clock([.1,1.9],[np.arange(5)*.5],[.75,1.])
    np.testing.assert_allclose(times,[.1,.3,.5,.75,1.,1.25,1.5,1.7,1.9],rtol=0,atol=1e-16)
    assert times[-1]>1. and not report['continuous_collision_certified']


def test_asynchronous_clocks_and_required_times_are_retained_exactly():
    clocks=[np.array([0.,.3,.9,1.]),np.array([.1,.45,.8])]
    times,report=edit_interval_clock([.2,.95],clocks,[.199,.4500000001,1.])
    for stamp in [.2,.3,.45,.8,.9,.95,.199,.4500000001,1.]:assert stamp in times
    breaks=np.asarray(report['native_partition_s'])
    for a,b in zip(breaks[:-1],breaks[1:]):assert a+(b-a)/2 in times


@pytest.mark.parametrize('window,clocks,required',[([1,0],[[0,1]],[]),([0,1],[],[]),([0,1],[[0,0]],[]),([0,1],[[0,float('nan')]],[]),([0,1],[[0,1]],[-1])])
def test_invalid_clocks_fail(window,clocks,required):
    with pytest.raises(ValueError):edit_interval_clock(window,clocks,required)
