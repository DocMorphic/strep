"""Achievable two-key bounds, incompatible author limits and complete populations."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from temporal_rotation_bounds import assess


def poses(angles):
    return Rotation.from_euler('z',angles,degrees=True).as_matrix()[:,None]


def test_two_key_bound_is_achievable_on_the_same_geodesic():
    original=poses([0,150]);raw=original.tobytes()
    bound,report=assess(original,[0,.1],[[20],[30]],speed_limits_degrees_per_second=[900])
    actual=float((Rotation.from_euler('z',20,degrees=True).inv()*Rotation.from_euler('z',120,degrees=True)).magnitude())*180/np.pi/.1
    assert bound[0,0]==pytest.approx(actual,abs=2e-6) and report['speed_limits_proven_incompatible']
    assert report['witnesses'][0]['edit_caps_degrees']==[20,30] and original.tobytes()==raw
    assert not report['quality_approved'] and not report['source_changed']


def test_limits_are_optional_and_not_a_calibrated_project_gate():
    lower,report=assess(poses([0,179.9]),[0,1/120],[25])
    assert lower[0,0]==pytest.approx(15588,abs=2e-5)
    assert not report['author_speed_limits_provided'] and not report['speed_limits_proven_incompatible']
    assert not report['anatomical_speed_threshold_calibrated'] and not report['continuous_time_verified']


def test_zero_neighbor_bounds_do_not_prove_one_globally_constant_pose_exists():
    lower,report=assess(poses([0,100,200]),[0,1,2],[50],speed_limits_degrees_per_second=[0])
    np.testing.assert_array_equal(lower,[[0],[0]])
    assert not report['speed_limits_proven_incompatible'] and 'not global trajectory feasibility' in report['scope']
    # First/last references are 160 degrees apart; their 50-degree balls cannot
    # share the constant pose demanded by zero speed across the whole interval.
    assert Rotation.from_euler('z',200,degrees=True).magnitude()*180/np.pi>100


def test_every_neighbor_and_joint_is_retained_including_protected_endpoints():
    r=np.stack([poses([0,40,80])[:,0],poses([0,20,60])[:,0]],axis=1)
    bounds,report=assess(r,[0,.1,.3],[[0,0],[5,10],[0,0]],speed_limits_degrees_per_second=[100,100])
    np.testing.assert_allclose(bounds,[[350,100],[175,150]],atol=2e-6)
    assert report['neighbor_comparisons']==4 and report['excluded_neighbor_comparisons']==3
    assert {w['joint'] for w in report['witnesses']}=={0,1}


def test_constant_coordinate_basis_changes_do_not_change_the_bound():
    r=poses([0,35,170,179.9999]);left=Rotation.from_euler('xyz',[13,27,-18],degrees=True).as_matrix()
    right=Rotation.from_euler('xyz',[-37,8,71],degrees=True).as_matrix()
    a,_=assess(r,[0,.1,.2,.3],[5]);b,_=assess(left@r@right,[0,.1,.2,.3],[5])
    np.testing.assert_allclose(a,b,atol=1e-9)


@pytest.mark.parametrize('angle',[0,1e-8,179.99999,180])
def test_identity_tiny_and_half_turn_angles_remain_finite(angle):
    lower,_=assess(poses([0,angle]),[0,1],[0])
    assert lower[0,0]==pytest.approx(max(0,angle-1e-7),abs=1e-10)


def test_small_reference_drift_is_explicitly_projected_without_mutation():
    r=poses([0,90]);r[0,0,0,0]+=1e-12;raw=r.tobytes()
    lower,report=assess(r,[0,1],[0])
    assert lower[0,0]==pytest.approx(90,abs=2e-7)
    assert report['reference_rotation_projection_max_element_change']>0 and r.tobytes()==raw


@pytest.mark.parametrize('fault',['bool-cap','mixed-bool-cap','negative-cap','large-cap','cap-shape','time-repeat','time-negative',
    'time-shape','nan','reflection','scale','bool-matrix','bool-speed','negative-speed','speed-shape','one-frame'])
def test_invalid_or_ambiguous_inputs_reject(fault):
    r=poses([0,90]);times=[0,1];caps=[25];speed=[100]
    if fault=='bool-cap':caps=[True]
    elif fault=='mixed-bool-cap':caps=[[25],[False]]
    elif fault=='negative-cap':caps=[-1]
    elif fault=='large-cap':caps=[181]
    elif fault=='cap-shape':caps=[25,25]
    elif fault=='time-repeat':times=[0,0]
    elif fault=='time-negative':times=[-1,0]
    elif fault=='time-shape':times=[0]
    elif fault=='nan':r[0,0,0,0]=np.nan
    elif fault=='reflection':r[0,0,0,0]=-1
    elif fault=='scale':r[0,0,0,0]=1.1
    elif fault=='bool-matrix':r=np.tile(np.eye(3,dtype=bool),(2,1,1,1))
    elif fault=='bool-speed':speed=[True]
    elif fault=='negative-speed':speed=[-1]
    elif fault=='speed-shape':speed=[100,100]
    else:r=r[:1];times=[0]
    with pytest.raises(ValueError):assess(r,times,caps,speed_limits_degrees_per_second=speed)
