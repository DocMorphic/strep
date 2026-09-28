from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read
from authored_root_correction import POLICY,export
from joint_root_correction import JointProblem
from verify_joint_root_correction import inspect


@pytest.fixture(scope='module')
def problem():
    study=ROOT/'reports/joint-root-correction-v1'
    case=read(study/'protocol.json')['cases'][0]
    return JointProblem(study/case['id'],case,POLICY)


def test_world_goal_regression_cannot_be_hidden_by_unchanged_rotations(problem,tmp_path):
    goal=problem.targets['goals'][0];f,n=goal['frame'],goal['node']
    vector=problem.world[2*f,n,:3,3]-goal['position_m']
    direction=vector/np.linalg.norm(vector) if np.linalg.norm(vector)>0 else np.array([1.,0,0])
    parent=problem.rig.parents[problem.root]
    rotation=np.eye(3) if parent<0 else problem.world[2*f,parent,:3,:3]
    offsets=np.zeros((problem.frames,3));offsets[f]=np.linalg.solve(rotation,.001*direction)
    path=tmp_path/'moved-goal.glb';export(problem.rig,problem.root,offsets,path)
    audit=inspect(problem.folder,path,POLICY)
    assert not audit['checks']['world_goals']
    assert audit['checks']['goal_orientations']
    assert audit['goals'][0]['position_cap_excess_m']>.0009


def test_fixed_context_is_checked_separately(problem,tmp_path):
    offsets=np.zeros((problem.frames,3));offsets[5,0]=.001
    path=tmp_path/'context.glb';export(problem.rig,problem.root,offsets,path)
    audit=inspect(problem.folder,path,POLICY)
    assert not audit['checks']['fixed_context']
    assert not audit['candidate_original_hard_checks']['fixed_context']


def test_envelope_budget_is_not_replaced_by_full_window_budget(problem,tmp_path):
    f=int(np.flatnonzero((problem.envelope>0)&(problem.envelope<.1))[0])
    offsets=np.zeros((problem.frames,3));offsets[f,0]=.01
    path=tmp_path/'envelope.glb';export(problem.rig,problem.root,offsets,path)
    audit=inspect(problem.folder,path,POLICY)
    assert not audit['candidate_original_hard_checks']['horizontal_root']


def test_unchanged_motion_has_no_goal_or_context_regression(problem):
    audit=inspect(problem.folder,problem.source,POLICY)
    assert all(v for k,v in audit['checks'].items() if k!='base')
    assert not audit['root']['checks']['objective']
    assert audit['source_flags']==audit['candidate_flags']


def test_studio_relative_floor_rejects_negligible_chain_improvement():
    from verify_joint_root_correction import inspect
    folder=ROOT/'reports/rig-jobs/20260928-105220-0d84b0dc'
    policy=read(folder/'request.json')['policy'].copy()
    policy['minimum_relative_energy_improvement']=.001
    audit=inspect(folder/'solver',folder/'transfer/character.glb',policy,
        source=folder/'input/character.glb',original=folder/'baseline/character.glb')
    assert not audit['root']['checks']['objective']
    assert all(v for k,v in audit['checks'].items() if k!='base')
