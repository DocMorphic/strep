from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from root_release_block import root_pair,RootBlockProblem
from block_release_fit import solve
from serialized_pose import SerializedPose
from test_guarded_release_fit import ToyFitter


class TranslatingFitter(ToyFitter):
    spec={**ToyFitter.spec,'root_node':0}
    def pose(self,frame,values):
        world=np.tile(np.eye(4),(2,1,1));world[:,1,3]=.001;world[:,:3,3]+=values[:3]
        return world,world
    def surface_jacobian(self,frame,values):
        jac=np.zeros((2,3,9));jac[:,:,:3]=np.eye(3)
        return self.rig.vertices(self.pose(frame,values)[0]),jac


def make_problem():
    fitter=TranslatingFitter();initial=np.zeros((7,9));initial[3,0]=.1
    oracle=SerializedPose(fitter.rig,{0,1},0,7)
    centers=np.array([fitter.rig.vertices(oracle.pose(fitter.pose(f,x)[0])) for f,x in enumerate(initial)])
    caps=np.maximum(.001,np.linalg.norm(np.diff(centers,n=2,axis=0),axis=2))
    envelope=dict(active_frames=np.zeros((7,2),bool),support_steps=np.zeros((6,2),bool),support_speed_caps_m_s=np.zeros((6,2)),
        hover_caps_m=np.ones((7,2)),rotation_cap_radians=0.,safety_caps_m_s2=caps,root_safety_caps_m_s2=caps[:,0])
    return RootBlockProblem(fitter,initial,oracle,[2,3,4],[0,1,2],envelope,dict(centers=[2,3,4],limit_m_s2=.001))


def test_root_derivative_includes_neighbor_acceleration_and_ignores_leg_columns():
    world=np.tile(np.eye(4),(6,2,1,1));positions,jac=root_pair(world,[2,3],[0,2,6],0,6)
    assert jac[2,0,0]==1 and jac[3,2,4]==1 and not np.any(jac[:,:,2]) and not np.any(jac[:,:,5])
    assert np.any(np.diff(jac,n=2,axis=0)[0]) and np.any(np.diff(jac,n=2,axis=0)[3])


def test_complete_root_objective_and_constraint_derivative_and_cache():
    p=make_problem();x=p.initial[np.ix_(p.frames,p.free)].ravel();d=np.random.default_rng(20).normal(size=len(x));d/=np.linalg.norm(d)
    row=p.evaluate(x,False);minus,plus=[p.evaluate(x+s*1e-6*d,False) for s in [-1,1]]
    np.testing.assert_allclose((plus[0]-minus[0])/2e-6,row[1]@d,atol=1e-7)
    np.testing.assert_allclose((plus[2]-minus[2])/2e-6,row[3]@d,atol=1e-6)
    a=p.evaluate(x);b=p.evaluate(x);assert len(a[2])==len(b[2]);np.testing.assert_array_equal(a[2],b[2])


def test_solver_reduces_root_spike_with_fixed_legs_and_outside_frames():
    p=make_problem();values,proof=solve(p,80)
    assert proof['accepted_fraction'] is not None and proof['objective_after']<proof['objective_before']
    np.testing.assert_array_equal(values[:,3:],p.initial[:,3:]);np.testing.assert_array_equal(values[[0,1,5,6]],p.initial[[0,1,5,6]])
    assert p.evaluate(values[np.ix_(p.frames,p.free)].ravel())[2].min()>=-1e-8


def test_root_envelope_rejects_a_spike_even_with_loose_foot_envelopes():
    p=make_problem();p.acceleration_caps[:]=100.;p.envelope['root_safety_caps_m_s2']=np.full(5,.01)
    x=p.initial[np.ix_(p.frames,p.free)].ravel();result=p.evaluate(x)
    assert result[2].min()<-.03


def test_edited_ancestor_is_rejected_instead_of_using_wrong_root_derivative():
    p=make_problem();p.fitter.spec={**p.fitter.spec,'root_node':1}
    rig=type('ParentRig',(TranslatingFitter.Rig,),{'parents':[-1,0]})()
    p.fitter.rig=rig;oracle=SerializedPose(rig,{0,1},1,7)
    with pytest.raises(ValueError,match='Edited ancestor'):
        RootBlockProblem(p.fitter,p.initial,oracle,p.frames,p.free,p.envelope,p.root_target)
