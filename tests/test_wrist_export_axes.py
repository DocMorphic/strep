import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from export_bounded_wrist_motion import joint_channels


def test_joint_selection_preserves_clock_with_reordered_subset():
    world=np.tile(np.eye(4),(4,5,1,1))
    for frame in range(4):
        for joint in range(5):world[frame,joint,:3,3]=[frame,joint,frame*10+joint]
    rotations,positions=joint_channels(world,[3,1,4])
    assert rotations.shape==(4,3,3,3);assert positions.shape==(4,3,3)
    np.testing.assert_array_equal(positions[:,0],[[0,3,3],[1,3,13],[2,3,23],[3,3,33]])
    np.testing.assert_array_equal(positions[2,1],[2,1,21])
