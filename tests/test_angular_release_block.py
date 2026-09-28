from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from angular_release_block import AngularBlockProblem,chord_cap,rotation_steps
from angular_conic_descent import affine_constraints,direction
from block_release_fit import BlockProblem
from serialized_pose import SerializedPose


def problem():
    class Rig:
        parents=[-1,-1,-1];document=dict(nodes=[{},{},{}])
        def vertices(self,world):return world[:2,:3,3]
    class Fitter:
        nodes=[0,1];rig=Rig();bounds=np.ones(9)
        spec=dict(root_node=2,fps=1.,patches=dict(Left=dict(vertices=[0]),Right=dict(vertices=[1])),limits=dict(root_step_m=1.,joint_step_degrees=90.))
        local=np.tile(np.eye(4),(7,3,1,1));local[:,:,1,3]=.001
        def pose(self,frame,values):
            local=self.local[frame].copy();local[:2,:3,:3]=local[:2,:3,:3]@Rotation.from_rotvec(values[3:].reshape(2,3)).as_matrix();return local,local
        def surface_jacobian(self,frame,values):return self.rig.vertices(self.pose(frame,values)[0]),np.zeros((2,3,9))
    f=Fitter();initial=np.zeros((7,9));initial[3,6]=.2;initial[5,3]=.5
    oracle=SerializedPose(f.rig,{0,1,2},2,7)
    envelope=dict(active_frames=np.zeros((7,2),bool),support_steps=np.zeros((6,2),bool),support_speed_caps_m_s=np.zeros((6,2)),hover_caps_m=np.ones((7,2)),rotation_cap_radians=1.,root_safety_caps_m_s2=np.ones(5))
    base=BlockProblem(f,initial,oracle,[2,3,4],list(range(3,9)),envelope,np.ones((5,2)),dict(centers=[3],side_index=0,limit_m_s2=1.))
    matrices=np.array([oracle.pose(f.pose(i,v)[0])[:2,:3,:3] for i,v in enumerate(initial)])
    caps=np.maximum(rotation_steps(matrices),.05)
    return AngularBlockProblem(base,dict(safety_caps_radians=caps,target=dict(end_frame=3,joint_index=1,limit_radians=.15)))


def test_chord_angle_equivalence_through_pi_and_noncommuting_axes():
    rng=np.random.default_rng(19);r=Rotation.random(40,random_state=rng).as_matrix().reshape(20,2,3,3)
    angles=Rotation.from_matrix(r[:,0].transpose(0,2,1)@r[:,1]).magnitude()
    np.testing.assert_allclose(np.linalg.norm((r[:,1]-r[:,0]).reshape(20,9),axis=1)/np.sqrt(2),chord_cap(angles),atol=1e-14)
    np.testing.assert_allclose(chord_cap([0,np.pi]),[0,2])
    with pytest.raises(ValueError):chord_cap([np.pi+.01])


def test_angular_objective_derivative_and_cone_identity():
    p=problem();x=p.initial[np.ix_(p.frames,p.free)].ravel();d=np.random.default_rng(9).normal(size=len(x));d/=np.linalg.norm(d)
    base=p.evaluate(x,False);minus=p.evaluate(x-1e-6*d,False);plus=p.evaluate(x+1e-6*d,False)
    np.testing.assert_allclose((plus[0]-minus[0])/2e-6,base[1]@d,atol=1e-6)
    np.testing.assert_allclose((plus[2]-minus[2])/2e-6,base[3]@d,atol=1e-7)
    c,_,cones=affine_constraints(p,x);margins=np.r_[c,[(v['cap']**2-v['vector']@v['vector'])/v['scale']**2 for v in cones]]
    np.testing.assert_allclose(margins,p.evaluate(x)[2],atol=1e-12)
    assert p.evaluate(x)[0]>0 # Target spike is hidden by other joint's larger global peak.


def test_proposal_reduces_selected_joint_without_global_max_loophole():
    p=problem();x=p.initial[np.ix_(p.frames,p.free)].ravel();delta,record=direction(p,x,.01,{})
    assert delta is not None and record['predicted_objective_change']<0
    result=p.evaluate(x+delta)
    assert result[0]<p.evaluate(x)[0] and result[2].min()>=-1e-8
    np.testing.assert_array_equal(p.values(x+delta)[:,0:3],p.initial[:,0:3])
