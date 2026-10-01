import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from scan_serialized_witness_ray import scan


def sample(x):
    good=x[0]==0 or .18<=x[1]<=.20
    return dict(vectors=np.zeros((1,3)),caps=np.ones(1),scales=np.ones(1),margins=np.array([.01 if good else -.1,.5]),depths=np.array([.02-.01*x[0]]))


def test_grid_finds_feasible_interval_between_halving_trials():
    point,report=scan(sample,[0.,0.],[.5,0.],[0.,1.],witness_start=0,witness_count=1,divisions=32)
    np.testing.assert_array_equal(point,[.5,.1875])
    assert report['numerically_feasible'] and len(report['trials'])==32
    assert report['mesh_validation_required'] and not report['accepted_for_publication']


def test_surface_success_cannot_compensate_for_motion_failure():
    def actual(x):
        value=sample(x)
        if x[0]>.4 and .18<=x[1]<=.20:value['vectors'][0,0]=1.01
        return value
    point,report=scan(actual,[0.,0.],[.5,0.],[0.,1.],witness_start=0,witness_count=1,divisions=32)
    assert point is None and not report['numerically_feasible']
    row=report['trials'][5];assert row['failed_witnesses']==0 and not row['eligible']


def test_control_bounds_are_not_clipped_or_ignored():
    point,report=scan(sample,[0.,0.],[.5,0.],[0.,8.],witness_start=0,witness_count=1,divisions=32)
    assert point is None
    assert all(r['reason']=='control bounds' for r in report['trials'][4:])


def test_caps_remain_fixed_during_replay():
    def actual(x):
        value=sample(x)
        if x[1]>.1:value['caps'][0]=2.
        return value
    with pytest.raises(ValueError,match='remain fixed'):
        scan(actual,[0.,0.],[.5,0.],[0.,1.],witness_start=0,witness_count=1,divisions=32)


@pytest.mark.parametrize('divisions',[0,1025,8.5])
def test_invalid_grid_size(divisions):
    with pytest.raises(ValueError):scan(sample,[0.,0.],[.5,0.],[0.,1.],witness_start=0,witness_count=1,divisions=divisions)
