from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_cycle_blend_audit import blend_worlds


def test_child_before_parent_keeps_link_and_follows_aligned_root():
    a=np.repeat(np.eye(4)[None],2,axis=0);b=a.copy()
    a[0,:3,3]=[2,1,0];a[1,:3,3]=[2,0,0]
    b[0,:3,3]=[8,1,0];b[1,:3,3]=[8,0,0]
    alignment=np.eye(4);alignment[0,3]=-4
    result=blend_worlds([1,-1],[a,b],1,alignment,.5)
    np.testing.assert_allclose(result[:, :3,3],[[3,1,0],[3,0,0]])


def test_node_renumbering_does_not_change_blended_pose():
    a=np.repeat(np.eye(4)[None],3,axis=0);b=a.copy()
    a[:,:3,3]=[[0,2,0],[0,1,0],[0,0,0]]
    b[:,:3,3]=[[4,2,0],[4,1,0],[4,0,0]]
    reverse=blend_worlds([1,2,-1],[a,b],2,np.eye(4),.25)
    forward=blend_worlds([-1,0,1],[a[::-1],b[::-1]],0,np.eye(4),.25)
    np.testing.assert_allclose(reverse,forward[::-1])
