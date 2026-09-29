import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from run_object_grip_seed import validate_guide_reference
from object_grip_seed import transport_frames


@pytest.mark.parametrize('reference', [0, 1, 2])
def test_guide_at_any_contact_frame_reproduces_its_world_pose(reference):
    validate_guide_reference(reference, 0, 2, 3)
    positions=np.array([[1.,2.,3.], [2.,4.,1.], [-1.,2.,0.]])
    rotations=Rotation.from_euler('xyz', [[10,20,30],[40,-20,10],[0,60,-40]],degrees=True).as_matrix()
    local_points=np.array([[.1,.2,.3],[-.2,.1,.5]])
    local_frames=Rotation.from_euler('xyz',[[10,50,30],[-30,10,60]],degrees=True).as_matrix()
    guide_points=positions[reference]+local_points@rotations[reference].T
    guide_frames=rotations[reference]@local_frames
    points,frames=transport_frames(positions,rotations,reference,guide_points,guide_frames)
    np.testing.assert_allclose(points[reference],guide_points,atol=1e-14)
    np.testing.assert_allclose(frames[reference],guide_frames,atol=1e-14)
    for i in range(3):
        np.testing.assert_allclose((points[i]-positions[i])@rotations[i],local_points,atol=1e-14)
        np.testing.assert_allclose(rotations[i].T@frames[i],local_frames,atol=1e-14)


@pytest.mark.parametrize('args',[(0,1,2,3),(3,1,2,4),(2,1,3,3),(1,2,1,3),(-1,-1,1,3),(True,0,2,3),(1.,0,2,3)])
def test_invalid_or_outside_contact_reference_rejected(args):
    with pytest.raises(ValueError):validate_guide_reference(*args)
