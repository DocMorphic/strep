import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
from bounded_pose_ik import solve,hierarchy_order,world_matrices


def target(angle):
    m=np.eye(4);m[:3,:3]=Rotation.from_euler('z',angle,degrees=True).as_matrix();m[:3,3]=[0,1,0]
    return dict(node=0,world_matrix=m,position_tolerance_m=.0005,rotation_tolerance_degrees=.05)


def test_non_topological_rig_reaches_target_and_preserves_unedited_values():
    local=np.tile(np.eye(4),(2,1,1));local[0,1,3]=1;parents=np.array([1,-1])
    fitted,report=solve(local,parents,[target(12)],{0:30})
    assert report['targets_matched'];np.testing.assert_array_equal(fitted[1],local[1]);np.testing.assert_array_equal(fitted[:,:3,3],local[:,:3,3])
    assert report['max_edit_degrees'][0]<30


def test_unreachable_target_retains_residual_without_breaking_bounds():
    local=np.tile(np.eye(4),(2,1,1));local[0,1,3]=1
    fitted,report=solve(local,np.array([1,-1]),[target(80)],{0:10})
    assert not report['targets_matched'];assert report['max_edit_degrees'][0]<=10+1e-8
    assert report['targets'][0]['rotation_error_degrees']>60
    with pytest.raises(ValueError,match='Cyclic'):hierarchy_order(np.array([1,0]))
