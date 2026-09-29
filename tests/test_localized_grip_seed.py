import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from object_grip_seed import localized_controls,fit_frames
from support_contact_v5 import correction_basis
from floor_contact import reconstruct


def test_cubic_local_basis_cannot_change_unselected_native_keys():
    basis,_=correction_basis(180,6)
    transform,outside,record=localized_controls(basis,[48,133])
    rng=np.random.default_rng(91)
    delta=basis@transform@rng.normal(size=(transform.shape[1],12))
    assert np.max(abs(delta[outside]))<1e-11
    assert np.max(abs(delta[60:122]))>.1
    assert 0<record['free_controls']<basis.shape[1]


@pytest.mark.parametrize('window',[[-1,8],[0,20],[8,3],[True,8],[0.,8],[0],None])
def test_invalid_windows_rejected(window):
    with pytest.raises(ValueError):localized_controls(np.eye(12),window)


def test_local_fit_changes_grasp_but_preserves_nonzero_seed_outside():
    n=18;parents=[-1,0,1]
    source=dict(root_positions=np.zeros((n,3)),local_rot_mats=np.tile(np.eye(3),(n,3,1,1)),global_rot_mats=np.tile(np.eye(3),(n,3,1,1)),posed_joints=np.tile([[0.,0.,0.],[1.,0.,0.],[2.,0.,0.]],(n,1,1)))
    local=source['local_rot_mats'].copy();local[:,1]=Rotation.from_euler('z',np.full(n,.1)).as_matrix()
    seed=reconstruct(source,local,parents)
    local=seed['local_rot_mats'].copy();local[6:12,1]=Rotation.from_euler('z',np.full(6,.18)).as_matrix()
    target=reconstruct(source,local,parents);weight=np.zeros(n);weight[6:12]=1
    basis,_=correction_basis(n,2)
    result,record=fit_frames(source,seed,parents,[1],[.4],1,basis,[2],target['posed_joints'][:,[2]],target['global_rot_mats'][:,[2]],weight,80,edit_window=[3,14])
    outside=np.r_[0:3,15:18]
    np.testing.assert_allclose(result['local_rot_mats'][outside],seed['local_rot_mats'][outside],atol=1e-10)
    assert np.max(abs(result['posed_joints'][6:12]-seed['posed_joints'][6:12]))>.02
    assert np.max(Rotation.from_matrix(result['local_rot_mats'][:,1]).magnitude())<.4
    assert record['reconstruction']['original_edit_budgets_preserved']
    assert record['localization']['maximum_outside_seed_rotation_error_rad']<1e-10
    np.testing.assert_allclose(result['local_rot_mats'][[3,14]],seed['local_rot_mats'][[3,14]],atol=1e-10)
    assert not record['quality_approved']


def test_window_without_any_local_spline_direction_is_rejected():
    with pytest.raises(ValueError,match='no free spline controls'):
        localized_controls(np.ones((12,1)),[4,7])


@pytest.mark.parametrize('window,boundaries',[
    ([3,8],[3,8]),([0,8],[8]),([3,11],[3]),([0,11],[]),
])
def test_local_controls_preserve_fractional_export_outside_window(window,boundaries):
    from scipy.spatial.transform import Slerp
    # Independent per-key controls expose the endpoint leakage that cubic
    # support can happen to hide in a rotation-only check.
    n=12
    transform,locked,record=localized_controls(np.eye(n),window)
    rng=np.random.default_rng(23)
    change=transform@rng.normal(size=(transform.shape[1],3))*.07
    original_root=rng.normal(size=(n,3))*.02
    edited_root=original_root+np.where(locked[:,None],0,change)
    original=Rotation.from_rotvec(rng.normal(size=(n,3))*.1)
    edited=original*Rotation.from_rotvec(change)
    times=np.arange((n-1)*16+1)/16
    outside=(times<window[0])|(times>window[1])
    points=times[outside]
    for axis in range(3):
        np.testing.assert_allclose(np.interp(points,np.arange(n),edited_root[:,axis]),
                                   np.interp(points,np.arange(n),original_root[:,axis]),atol=1e-12)
    if len(points):
        error=(Slerp(np.arange(n),original)(points).inv()*Slerp(np.arange(n),edited)(points)).magnitude()
        assert np.max(error)<1e-12
    assert record['locked_boundary_keys']==boundaries
    assert record['outside_keys']==window[0]+n-1-window[1]
    assert record['locked_keys']==record['outside_keys']+len(boundaries)
    assert np.max(abs(change))>.01


def test_window_endpoints_cannot_be_the_only_free_controls():
    with pytest.raises(ValueError,match='no free spline controls'):
        localized_controls(np.eye(12),[4,5])


def test_export_counterexample_changing_selected_endpoint_leaks_outside():
    # Both native keys strictly outside [3,8] remain untouched, yet the
    # adjoining half-frame changes. This is why the selected endpoint is held.
    original=np.zeros(12);candidate=original.copy();candidate[3]=.004
    assert np.array_equal(original[:3],candidate[:3])
    assert np.interp(2.5,np.arange(12),candidate)==.002
