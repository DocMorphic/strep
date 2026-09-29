import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_scene_region_fit import edit_bounds,native_fk_error
from inspect_motion import skeleton_metadata


@pytest.mark.parametrize('failure',['body','finger','noneditable','root_x','root_y','labels'])
def test_independent_bound_audit_rejects_policy_violations(failure):
    names,_,_=skeleton_metadata(77)
    source=dict(root_positions=np.zeros((3,3)),local_rot_mats=np.tile(np.eye(3),(3,77,1,1)),foot_contacts=np.zeros((3,4)))
    candidate={k:v.copy() for k,v in source.items()};config=dict(max_rotation_degrees=40,max_root_lift_m=.22)
    assert edit_bounds(source,candidate,names,config)[0]
    if failure=='body':candidate['local_rot_mats'][1,names.index('Chest')]=Rotation.from_euler('x',41,degrees=True).as_matrix()
    if failure=='finger':candidate['local_rot_mats'][1,names.index('LeftHandIndex2')]=Rotation.from_euler('x',13,degrees=True).as_matrix()
    if failure=='noneditable':candidate['local_rot_mats'][1,0]=Rotation.from_euler('x',.1,degrees=True).as_matrix()
    if failure=='root_x':candidate['root_positions'][1,0]=.001
    if failure=='root_y':candidate['root_positions'][1,1]=.221
    if failure=='labels':candidate['foot_contacts'][1,0]=1
    assert not edit_bounds(source,candidate,names,config)[0]


def test_native_audit_catches_changed_bone_offsets_even_with_zero_rotation_edits():
    source=dict(root_positions=np.zeros((3,3)),posed_joints=np.tile([[0,0,0],[0,1,0]],(3,1,1)).astype(float),
                local_rot_mats=np.tile(np.eye(3),(3,2,1,1)),global_rot_mats=np.tile(np.eye(3),(3,2,1,1)))
    candidate={k:v.copy() for k,v in source.items()}
    assert native_fk_error(source,candidate,[-1,0])==0
    candidate['posed_joints'][1,1,1]+=.01
    assert native_fk_error(source,candidate,[-1,0])==pytest.approx(.01)
