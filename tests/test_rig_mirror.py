import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from rig_mirror import mirror,correspondence,annotations,draft_correspondence
from rig_transition import compose,localize


def fixture(asymmetric=False):
    parents=[-1,0,1,2,1,4,0]
    local=np.tile(np.eye(4),(7,1,1))
    local[0,:3,3]=[2,.2,-1];local[1,:3,3]=[0,1,0]
    local[2,:3,3]=[.3,0,0];local[3,:3,3]=[.4,0,0]
    local[4,:3,3]=[-.3,0,0];local[5,:3,3]=[-.4,0,0]
    local[6,:3,3]=[0,0,3]
    if asymmetric:
        local[4,:3,3]=[-.25,.1,0];local[5,:3,3]=[-.5,0,.03]
        for n in range(7):local[n,:3,:3]=Rotation.from_euler('xyz',[n*11,n*7,n*-9],degrees=True).as_matrix()
    rig=SimpleNamespace(parents=parents,joints=[1,2,3,4,5],reference=compose(local[None],parents)[0],document={'nodes':[{'name':n} for n in ['outside','Hips','LeftArm','LeftHand','RightArm','RightHand','prop']]})
    return rig,local,{'1':1,'2':4,'3':5,'4':2,'5':3}


class MirrorTests(unittest.TestCase):
    def test_exact_reflection_of_symmetric_joint_positions(self):
        rig,local,pairs=fixture();before=np.tile(local,(3,1,1,1))
        for f in range(3):
            before[f,2,:3,:3]=Rotation.from_euler('z',20*f,degrees=True).as_matrix()
            before[f,3,:3,:3]=Rotation.from_euler('y',17*f,degrees=True).as_matrix()
            before[f,1,:3,3]+=[.1*f,.05*f,.2*f]
        world=compose(before,rig.parents);point=world[0,1,:3,3]
        after=mirror(rig,world,1,pairs,[1,0,0],point)
        F=np.diag([-1,1,1])
        for dst,src in pairs.items():
            np.testing.assert_allclose(after[:,int(dst),:3,3],point+(world[:,src,:3,3]-point)@F,atol=1e-12)
        np.testing.assert_allclose(after[:,[0,6]],world[:,[0,6]],atol=1e-12)

    def test_asymmetric_rest_axes_and_animated_parent_are_reversible(self):
        rig,local,pairs=fixture(True);before=np.tile(local,(4,1,1,1))
        for f in range(4):
            for n in range(7):
                before[f,n,:3,:3]=before[f,n,:3,:3]@Rotation.from_euler('xyz',[f*n,3*f,7*f],degrees=True).as_matrix()
                before[f,n,:3,3]+=[f*.002,n*f*.001,f*-.003]
        world=compose(before,rig.parents);normal=np.array([.6,0,.8]);point=world[0,1,:3,3]
        after=mirror(rig,world,1,pairs,normal,point)
        np.testing.assert_allclose(mirror(rig,after,1,pairs,normal,point),world,atol=2e-13)
        np.testing.assert_allclose(after[:,[0,6]],world[:,[0,6]],atol=1e-13)
        np.testing.assert_allclose(after[:,1,1,3],world[:,1,1,3],atol=1e-13)
        np.testing.assert_allclose(np.linalg.det(after[...,:3,:3]),1,atol=1e-13)

    def test_asymmetric_reference_pose_and_bone_lengths_retained(self):
        rig,local,pairs=fixture(True);world=rig.reference[None]
        after=mirror(rig,world,1,pairs,[1,0,0],world[0,1,:3,3])
        np.testing.assert_allclose(after,world,atol=1e-13)
        animated=local.copy();animated[2,:3,:3]@=Rotation.from_euler('x',.4).as_matrix()
        after=mirror(rig,compose(animated[None],rig.parents),1,pairs,[1,0,0],world[0,1,:3,3])
        np.testing.assert_allclose(localize(after,rig.parents)[0,:,:3,3],local[:,:3,3],atol=1e-13)

    def test_invalid_correspondence_plane_and_nonrigid_inputs(self):
        rig,local,pairs=fixture();world=rig.reference[None]
        for change in ({'2':2},{'2':5,'5':2,'3':4,'4':3},{'1':True}):
            with self.assertRaises(ValueError):correspondence(rig,1,{**pairs,**change})
        for normal in ([2,0,0],[0,1,0],[float('nan'),0,0]):
            with self.assertRaises(ValueError):mirror(rig,world,1,pairs,normal,[0,0,0])
        for row,col,value in [(0,0,2),(3,0,.1)]:
            bad=world.copy();bad[0,2,row,col]=value
            with self.assertRaises(ValueError):mirror(rig,bad,1,pairs,[1,0,0],[0,0,0])

    def test_role_draft(self):
        rig,_,pairs=fixture()
        self.assertEqual(draft_correspondence(rig,{'Hips':1,'LeftArm':2,'RightArm':4,'LeftHand':3,'RightHand':5}),pairs)
        rig.document['nodes'][2]['name']='arm_L__4_';rig.document['nodes'][4]['name']='arm_R'
        self.assertEqual(draft_correspondence(rig,{'Hips':1,'LeftArm':2,'RightArm':4,'LeftHand':3,'RightHand':5}),pairs)

    def test_nominal_float_scale_drift_is_bounded(self):
        from rig_mirror import rigid
        rig,_,pairs=fixture();rig.reference[...,:3,:3]*=1.0000002
        world=rig.reference[None].copy();point=world[0,1,:3,3]
        after=mirror(rig,world,1,pairs,[1,0,0],point)
        np.testing.assert_allclose(mirror(rig,after,1,pairs,[1,0,0],point),rigid(world),atol=1e-13)
        rig.reference[...,:3,:3]*=1.01
        with self.assertRaises(ValueError):mirror(rig,world,1,pairs,[1,0,0],point)

    def test_sidecar_identity_timing_and_review(self):
        contact={'mapping':{'LeftHand':3,'RightHand':5},'intervals':[{'joint':'LeftHand','start_frame':1,'end_frame_exclusive':4,'start_seconds':1/30,'end_seconds_exclusive':4/30}]}
        events={'fps':30,'events':[{'name':'left_hit','frame':2,'time_s':2/30,'kind':'authored','requires_review':False}]}
        original=copy.deepcopy((contact,events))
        new,markers=annotations(contact,events,5,{1:1,2:4,3:5,4:2,5:3},'a'*64)
        self.assertEqual((contact,events),original)
        self.assertEqual(new['mapping'],contact['mapping'])
        self.assertEqual(new['intervals'][0]['joint'],'RightHand')
        self.assertEqual(markers['events'][0]['frame'],2)
        self.assertTrue(markers['events'][0]['requires_review'])
        self.assertEqual(markers['events'][0]['name'],'left_hit')
        for bad in [{'events':[{'frame':5}]},{'events':[{'frame':2,'time_s':1}]}]:
            with self.assertRaises(ValueError):annotations(contact,bad,5,{1:1,2:4,3:5,4:2,5:3},'a'*64)
        contact['intervals'][0]['node']=3
        with self.assertRaises(ValueError):annotations(contact,events,5,{1:1,2:4,3:5,4:2,5:3},'a'*64)


if __name__=='__main__':unittest.main()
