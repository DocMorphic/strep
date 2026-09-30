import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read
from regional_pose_witness import RegionalPoseProblem
from regional_wrist_track import frame_problem,fixed_finger_parameters,project
from region_grasp_track import arm_columns


@pytest.fixture(scope='module')
def fixture():
    prior=read(ROOT/'reports/cylinder-pose-bounded-v1/protocol.json');fit=ROOT/prior['fit']
    p=RegionalPoseProblem(fit,prior['frame']);scene=read(fit/'authored-scene.json')
    anchors={r['id']:r['anchor'] for r in p.regions}
    return p,scene,anchors,fit


@pytest.mark.parametrize('frame',[60,96,120])
def test_frame_local_problem_matches_fresh_native_constructor(fixture,frame):
    p,scene,anchors,fit=fixture;actual=frame_problem(p,frame,scene,anchors);expected=RegionalPoseProblem(fit,frame)
    for field in ['initial','offsets','root']:np.testing.assert_array_equal(getattr(actual,field),getattr(expected,field))
    for a,b in zip(actual.regions,expected.regions):
        for field in ['position','rotation','target','normal']:np.testing.assert_allclose(a[field],b[field],atol=1e-14,rtol=0)
    aa,am=actual.independent(expected.seed);ba,bm=expected.independent(expected.seed)
    assert aa==ba
    for key in am:np.testing.assert_array_equal(am[key],bm[key])
    assert p.frame==96


def test_fixed_shape_retains_original_norm_budgets(fixture):
    p,scene,anchors,_=fixture;reference=np.array(read(ROOT/'reports/cylinder-guide-projection-v1/result.json')['parameters'])
    motion=dict(np.load(ROOT/'reports/cylinder-guide-projection-v1/pose.npz'))
    joints=[j for j in p.editable if 'Hand' in p.names[j] and p.names[j] not in ['LeftHand','RightHand']]
    locked=[j for j,n in enumerate(p.names) if 'Hand' in n and j not in p.editable]
    assert not np.any(np.isin(p.indices,locked)&(p.skin['lbs_weights']>0))
    for frame in [60,96,120,121]:
        local=frame_problem(p,frame,scene,anchors);fixed=fixed_finger_parameters(local,reference,motion['local_rot_mats'][0])
        audit,changed=local.independent(fixed);assert audit['bounds_passed']
        np.testing.assert_allclose(changed['local_rot_mats'][0,joints],motion['local_rot_mats'][0,joints],atol=1e-7,rtol=0)
        np.testing.assert_allclose(changed['local_rot_mats'][0,locked],p.base['local_rot_mats'][frame,locked],atol=1e-7,rtol=0)


def test_projection_stops_at_reached_wrist_without_claiming_pose_acceptance(fixture):
    p,scene,anchors,_=fixture;reference=np.array(read(ROOT/'reports/cylinder-guide-projection-v1/result.json')['parameters'])
    _,motion=p.independent(reference);targets={hand:dict(position=motion['posed_joints'][0,p.names.index(hand)],rotation=motion['global_rot_mats'][0,p.names.index(hand)]) for hand in ['LeftHand','RightHand']}
    columns,_=arm_columns(p);parameters,result=project(p,reference,reference[columns],targets,lambda:None)
    assert result['solver']['termination']=='numerical_wrist_targets_reached'
    assert result['solver']['success'] is None
    np.testing.assert_allclose(parameters,reference,atol=1e-15,rtol=0)
    assert not p.independent(parameters)[0]['pose_witness_passed'] # Original guides still fail.
