"""Exact held-key and fractional outside-segment preservation regressions."""
import sys
from pathlib import Path
from copy import deepcopy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation, Slerp
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from localized_spline import localized_controls
from held_pose_preservation import restore_locked_pose, POSE_KEYS


def motion():
    rng=np.random.default_rng(29)
    rotations=Rotation.from_rotvec(rng.normal(size=(36,3))*.15).as_matrix().reshape(12,3,3,3).astype('float32')
    return dict(root_positions=rng.normal(size=(12,3)).astype('float32'),
        posed_joints=rng.normal(size=(12,3,3)).astype('float32'),
        local_rot_mats=rotations.copy(),global_rot_mats=rotations.copy(),
        foot_contacts=np.zeros((12,4),dtype='float32'),metadata={'origin':['candidate']})


@pytest.mark.parametrize('window',[[3,8],[0,8],[3,11],[0,11]])
@pytest.mark.parametrize('warm_start',[False,True])
def test_locked_seed_keys_preserve_fractional_export_segments_and_free_edits(window,warm_start):
    source=motion();seed=deepcopy(source)
    if warm_start:
        seed['root_positions'][:,1]+=.12
        seed['posed_joints'][:,:,1]+=.12
        for key in ['local_rot_mats','global_rot_mats']:
            seed[key]=(seed[key].astype(float)@Rotation.from_euler('y',.2).as_matrix()).astype('float32')
    _,locked,_=localized_controls(np.eye(12),window)
    candidate=deepcopy(seed)
    # Simulate the unwanted reconstruction changes at every native key,
    # alongside the intended much larger edit inside the free interval.
    for key in POSE_KEYS:
        candidate[key]=np.nextafter(candidate[key],np.float32(np.inf))
        candidate[key][~locked]+=.001
    before_seed=deepcopy(seed);before_candidate=deepcopy(candidate)
    result=restore_locked_pose(seed,candidate,locked)
    for key in POSE_KEYS:
        assert result[key][locked].tobytes()==seed[key][locked].tobytes()
        assert result[key][~locked].tobytes()==candidate[key][~locked].tobytes()
        assert seed[key].tobytes()==before_seed[key].tobytes()
        assert candidate[key].tobytes()==before_candidate[key].tobytes()
        assert not np.shares_memory(result[key],seed[key]) and not np.shares_memory(result[key],candidate[key])
    times=np.arange(177)/16
    outside=times[(times<window[0])|(times>window[1])]
    for key in ['root_positions','posed_joints']:
        a=seed[key].reshape(12,-1);b=result[key].reshape(12,-1)
        for axis in range(a.shape[1]):
            np.testing.assert_array_equal(np.interp(outside,np.arange(12),a[:,axis]),np.interp(outside,np.arange(12),b[:,axis]))
    if len(outside):
        for joint in range(3):
            a=Slerp(np.arange(12),Rotation.from_matrix(seed['global_rot_mats'][:,joint]))(outside).as_matrix()
            b=Slerp(np.arange(12),Rotation.from_matrix(result['global_rot_mats'][:,joint]))(outside).as_matrix()
            np.testing.assert_array_equal(a,b)
    assert result['foot_contacts'].tobytes()==candidate['foot_contacts'].tobytes()
    result['metadata']['origin'].append('changed')
    assert candidate['metadata']['origin']==['candidate']


def test_copy_is_bit_exact_including_negative_zero_and_empty_or_full_mask():
    seed=motion();candidate=deepcopy(seed);seed['root_positions'][0,0]=-0.;candidate['root_positions'][0,0]=0.
    for mask,expected in [(np.ones(12,bool),seed),(np.zeros(12,bool),candidate)]:
        result=restore_locked_pose(seed,candidate,mask)
        for key in POSE_KEYS:assert result[key].tobytes()==expected[key].tobytes()


@pytest.mark.parametrize('fault',['dtype','shape','nan_seed','nan_candidate','integer','missing','short_mask','integer_mask'])
def test_invalid_native_data_cannot_be_silently_cast_or_partially_restored(fault):
    seed=motion();candidate=deepcopy(seed);locked=np.ones(12,bool)
    if fault=='dtype':candidate['posed_joints']=candidate['posed_joints'].astype('float64')
    elif fault=='shape':candidate['global_rot_mats']=candidate['global_rot_mats'][:,:2]
    elif fault=='nan_seed':seed['root_positions'][0,0]=np.nan
    elif fault=='nan_candidate':candidate['root_positions'][0,0]=np.nan
    elif fault=='integer':candidate['root_positions']=candidate['root_positions'].astype(int)
    elif fault=='missing':del seed['local_rot_mats']
    elif fault=='short_mask':locked=locked[:-1]
    elif fault=='integer_mask':locked=locked.astype(int)
    with pytest.raises(ValueError):restore_locked_pose(seed,candidate,locked)
