import copy
import numpy as np
import pytest
from threadpoolctl import threadpool_limits
from test_rig_trajectory import fixture
from rig_pose_trajectory import PoseTrajectoryFitter

def make(change=None):
 rig,w,local,spec,targets,s=fixture(5);node=list(spec['edit_joints'].values())[-1]['node']
 goal=dict(frame=2,node=node,position_m=(w[2,node,:3,3]+[0,.008,0]).tolist(),rotation_matrix=w[2,node,:3,:3].tolist(),position_weight=60.,rotation_weight=.5,provenance='Synthetic test')
 if change:goal.update(change)
 return rig,w,local,spec,targets,s,goal

def test_joint_and_goal_jacobians_match_independent_fk():
 rig,w,local,spec,targets,s,goal=make();f=PoseTrajectoryFitter(rig,spec,local,targets,np.ones(5),[s],[goal]);x=np.random.default_rng(17).normal(size=len(f.bounds))*.01
 p,r,jp,jr=f.joint_pair(2,x,goal['node']);res,j=f.goal_pair(2,x)
 for k in range(len(x)):
  d=np.eye(len(x))[k]*1e-7;plus=f.pose(2,x+d)[0][goal['node']];minus=f.pose(2,x-d)[0][goal['node']]
  np.testing.assert_allclose(jp[:,k],(plus[:3,3]-minus[:3,3])/2e-7,atol=2e-8,rtol=1e-5)
  np.testing.assert_allclose(jr[:,:,k],(plus[:3,:3]-minus[:3,:3])/2e-7,atol=2e-8,rtol=1e-5)
  np.testing.assert_allclose(j[:,k],(f.goal_pair(2,x+d)[0]-f.goal_pair(2,x-d)[0])/2e-7,atol=2e-6,rtol=1e-5)
 assert f.goal_pair(0,x)[0].size==0

def test_fit_improves_goal_and_keeps_fixed_context_and_temporal_bounds(tmp_path):
 rig,w,local,spec,targets,s,goal=make();spec['max_nfev']=20
 # Isolate sparse positional response while preserving the inherited surface objective.
 f=PoseTrajectoryFitter(rig,spec,local,targets,np.array([0,.7,1,.7,0]),[],[goal]);before=np.linalg.norm(f.world[2,goal['node'],:3,3]-goal['position_m'])
 with threadpool_limits(limits=1):values,records,_=f.solve(tmp_path,max_sweeps=2)
 assert np.linalg.norm(f.world[2,goal['node'],:3,3]-goal['position_m'])<before
 assert np.array_equal(values[[0,-1]],np.zeros_like(values[[0,-1]]))
 assert np.all(np.abs(values)<=f.bounds*f.envelope[:,None]+1e-9)
 for i,x in enumerate(values):assert f.constraints(i,x)[0].min()>-1e-7
 assert all(r['cost_after']<=r['cost_before'] for r in records)

@pytest.mark.parametrize('change',[{'frame':0},{'node':-1},{'position_m':[0,float('nan'),0]},{'rotation_matrix':[[1,0,0],[0,1,0],[0,0,-1]]},{'position_weight':0},{'rotation_weight':True},{'provenance':''}])
def test_invalid_or_fixed_targets_rejected(change):
 rig,w,local,spec,targets,s,goal=make(change)
 with pytest.raises(ValueError):PoseTrajectoryFitter(rig,spec,local,targets,np.array([0,.7,1,.7,0]),[s],[goal])

def test_duplicate_target_rejected():
 rig,w,local,spec,targets,s,goal=make()
 with pytest.raises(ValueError):PoseTrajectoryFitter(rig,spec,local,targets,np.ones(5),[s],[goal,copy.deepcopy(goal)])
