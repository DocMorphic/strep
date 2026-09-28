import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from object_attachment import attach_trajectory


def fixture():
    p=np.tile([1.,2.,3.],(8,1));r=np.tile(np.eye(3),(8,1,1))
    a=np.c_[np.arange(8)*.1,np.ones(8),np.zeros(8)];q=Rotation.from_euler('y',np.arange(8)*10,degrees=True).as_matrix()
    return p,r,a,q


def test_grasp_offset_stays_rigid_and_does_not_snap_or_mutate_inputs():
    p,r,a,q=fixture();copies=[x.copy() for x in [p,r,a,q]]
    actual,rot,recipe=attach_trajectory(p,r,a,q,2,6)
    np.testing.assert_array_equal(actual[:2],p[:2]);np.testing.assert_array_equal(rot[:2],r[:2])
    np.testing.assert_allclose(actual[2],p[2],atol=1e-12);np.testing.assert_allclose(rot[2],r[2],atol=1e-12)
    for f in range(2,6):
        np.testing.assert_allclose(q[f].T@(actual[f]-a[f]),recipe['anchor_local_translation_m'],atol=1e-12)
        np.testing.assert_allclose(q[f].T@rot[f],recipe['anchor_local_rotation'],atol=1e-12)
    for actual,original in zip([p,r,a,q],copies):np.testing.assert_array_equal(actual,original)


def test_release_uses_predicted_boundary_pose_then_authored_relative_tail():
    p,r,a,q=fixture();p[7]=p[6]+[0,-.2,0]
    actual,rot,recipe=attach_trajectory(p,r,a,q,2,6)
    np.testing.assert_allclose(actual[6],a[6]+q[6]@recipe['anchor_local_translation_m'],atol=1e-12)
    np.testing.assert_allclose(actual[7]-actual[6],rot[6]@r[6].T@(p[7]-p[6]),atol=1e-12)
    assert recipe['release_frame']==6


def test_attachment_to_clip_end_has_no_release_event():
    p,r,a,q=fixture();_,_,recipe=attach_trajectory(p,r,a,q,0,8)
    assert recipe['release_frame'] is None


@pytest.mark.parametrize('start,end',[(-1,3),(3,3),(4,3),(0,9),(False,3)])
def test_bad_interval_is_rejected(start,end):
    with pytest.raises(ValueError):attach_trajectory(*fixture(),start,end)
