import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from scipy.spatial.transform import Rotation
from bounded_pose_ball_ik import solve


def test_norm_search_reaches_rotation_excluded_by_inscribed_box():
    local=np.eye(4)[None];desired=np.eye(4);desired[:3,:3]=Rotation.from_euler('z',15,degrees=True).as_matrix()
    target=dict(node=0,world_matrix=desired,position_tolerance_m=.0005,rotation_tolerance_degrees=.05)
    fitted,report=solve(local,np.array([-1]),[target],{0:20})
    assert not report['box_initializer']['targets_matched']
    assert report['targets_matched'];assert report['norm_refinement']['accepted']
    assert report['max_edit_degrees'][0]<=20+1e-6
    np.testing.assert_array_equal(fitted[:,:3,3],local[:,:3,3])


def test_unreachable_rotation_stays_within_actual_norm_cap():
    local=np.eye(4)[None];desired=np.eye(4);desired[:3,:3]=Rotation.from_euler('y',70,degrees=True).as_matrix()
    fitted,report=solve(local,np.array([-1]),[dict(node=0,world_matrix=desired,position_tolerance_m=.0005,rotation_tolerance_degrees=.05)],{0:20})
    assert not report['targets_matched'];assert report['max_edit_degrees'][0]<=20+1e-6
    assert report['targets'][0]['rotation_error_degrees']>49
