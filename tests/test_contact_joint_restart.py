"""A warm start must not grant a fresh root or rotation edit allowance."""
from pathlib import Path
import sys
from copy import deepcopy

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from study_contact_joint_restart import original_budget_check


def motion(height=1., angle=0.):
    roots=np.array([[0.,height,0.],[0.,height,0.]])
    rotations=np.tile(Rotation.from_euler('z',angle,degrees=True).as_matrix(),(2,1,1,1))
    return dict(root_positions=roots,local_rot_mats=rotations)


def test_root_restart_may_not_reset_original_allowance():
    source,seed,candidate=motion(),motion(1.20),motion(1.23)
    original_budget_check(seed,candidate,.22,40)
    with pytest.raises(ValueError,match='Original root budget'):
        original_budget_check(source,candidate,.22,40)


def test_rotation_restart_may_not_reset_original_allowance():
    source,seed,candidate=motion(),motion(angle=35),motion(angle=45)
    original_budget_check(seed,candidate,.22,40)
    with pytest.raises(ValueError,match='Original rotation budget'):
        original_budget_check(source,candidate,.22,40)


@pytest.mark.parametrize('fault',['root_x','root_z','negative_lift','nan_root','nan_rotation'])
def test_original_fixed_coordinates_and_finite_pose_are_required(fault):
    source=motion();candidate=deepcopy(source)
    if fault=='root_x':candidate['root_positions'][0,0]=.001
    if fault=='root_z':candidate['root_positions'][0,2]=.001
    if fault=='negative_lift':candidate['root_positions'][0,1]-=.001
    if fault=='nan_root':candidate['root_positions'][0,1]=np.nan
    if fault=='nan_rotation':candidate['local_rot_mats'][0,0,0,0]=np.nan
    with pytest.raises(ValueError):original_budget_check(source,candidate,.22,40)


def test_valid_original_relative_edits_report_actual_values_without_mutation():
    source,candidate=motion(),motion(1.12,25)
    before=deepcopy(candidate)
    result=original_budget_check(source,candidate,.22,40)
    assert result['maximum_root_lift_m']==pytest.approx(.12)
    assert result['maximum_rotation_delta_degrees']==pytest.approx(25)
    for key in candidate:np.testing.assert_array_equal(candidate[key],before[key])
