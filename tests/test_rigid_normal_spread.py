"""Analytic synthetic direction sets; never human motion-quality evidence."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from rigid_normal_spread import bound


def fixture():
    source=np.array([[[-np.sqrt(.5),np.sqrt(.5),0],[np.sqrt(.5),np.sqrt(.5),0]]])
    target=np.array([[0.,-1,0],[0.,-1,0]])
    return source,target


def test_angular_pair_conflict_has_attainable_45_degree_lower_bound():
    source,target=fixture();report,arrays=bound(source,target,20.)
    assert report['rejected_frames']==1 and report['maximum_necessary_error_degrees']==pytest.approx(45.)
    np.testing.assert_allclose(arrays['source_pair_degrees'],[90.]);np.testing.assert_array_equal(arrays['target_pair_degrees'],[0.])
    # Identity target pose attains 45-degree opposition at both points.
    error=np.rad2deg(np.arccos(-(source[0]*target).sum(axis=1)))
    np.testing.assert_allclose(error,45.)
    assert not report['quality_approved'] and not report['rigid_rotation_feasibility_proven']


def test_independent_common_rotations_preserve_spread_bound():
    source,target=fixture();expected,_=bound(source,target,15.)
    transformed=Rotation.from_euler('xyz',[20,30,40],degrees=True).apply(source.reshape(-1,3)).reshape(source.shape)
    target=Rotation.from_euler('xyz',[-40,10,80],degrees=True).apply(target)
    actual,_=bound(transformed,target,15.)
    assert actual['maximum_necessary_error_degrees']==pytest.approx(expected['maximum_necessary_error_degrees'])
    assert actual['rejected_frames']==1


def test_every_frame_is_retained_including_a_rejected_frame():
    source,target=fixture();source=np.concatenate([-target[None],source,-target[None]])
    result,arrays=bound(source,target,15.)
    assert result['frames']==3 and result['rejected_frames']==1
    np.testing.assert_array_equal(arrays['rejected'],[False,True,False])


def test_matching_pair_spreads_do_not_prove_proper_rotation_feasibility():
    source=np.eye(3)[None];target=-np.eye(3);target[0]*=-1
    report,_=bound(source,target,0.)
    assert report['all_frames_not_rejected'] and not report['rigid_rotation_feasibility_proven']
    # Mapping these full bases requires an improper reflection, not SO(3).
    assert np.linalg.det(-target.T)<0


def test_single_normal_has_no_pairwise_obstruction():
    report,arrays=bound(np.array([[[0.,1,0]]]),np.array([[0.,1,0]]),0.)
    assert report['all_frames_not_rejected'] and report['maximum_necessary_error_degrees']==0
    np.testing.assert_array_equal(arrays['witness_pairs'],[[-1,-1]])


@pytest.mark.parametrize('fault',['nan','nonunit_source','nonunit_target','missing_frame','shape','missing_point','boolean_limit','negative_limit','nan_limit'])
def test_invalid_populations_and_limits_reject(fault):
    source,target=fixture();limit=15.
    if fault=='nan':source[0,0,0]=np.nan
    if fault=='nonunit_source':source*=2
    if fault=='nonunit_target':target*=2
    if fault=='missing_frame':source=source[:0]
    if fault=='shape':target=target[:1]
    if fault=='missing_point':source=source[:,:0];target=target[:0]
    if fault=='boolean_limit':limit=True
    if fault=='negative_limit':limit=-1
    if fault=='nan_limit':limit=float('nan')
    with pytest.raises(ValueError):bound(source,target,limit)
