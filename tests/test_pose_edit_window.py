import sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pose_edit_window import blend
from rig_transition import compose,localize


def test_center_target_and_original_outside_survive_rotated_parent():
    parents=[-1,0,1];local=np.tile(np.eye(4),(41,3,1,1))
    local[:,0,:3,:3]=Rotation.from_euler('y',40,degrees=True).as_matrix()
    local[:,1,:3,3]=[0,1,0];local[:,2,:3,3]=[.4,0,0]
    local[:,0,0,3]=np.arange(41)/100
    world=compose(local,parents)
    goal=local[20].copy();goal[2,:3,:3]=Rotation.from_euler('x',20,degrees=True).as_matrix()
    target=compose(goal[None],parents)[0];target[1:,:3,3]+=[.03,.04,.02]
    after,weights=blend(world,parents,1,[2],20,target)
    np.testing.assert_allclose(after[20],target,atol=1e-12)
    np.testing.assert_array_equal(after[weights==0],world[weights==0])
    restored=localize(after,parents)
    np.testing.assert_allclose(restored[:,2,:3,3],local[:,2,:3,3],atol=1e-12)
    assert weights[20]==1 and weights[6]==0 and weights[34]==0
