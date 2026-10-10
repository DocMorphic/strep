import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from scipy.spatial.transform import Rotation
from bounded_pose_ball_ik import solve


def test_norm_search_reaches_rotation_excluded_by_inscribed_box():
    local=np.eye(4)[None];desired=np.eye(4);desired[:3,:3]=Rotation.from_euler('z',15,degrees=True).as_matrix()
    target=dict(node=0,world_matrix=desired,position_tolerance_m=.0005,rotation_tolerance_degrees=.05)
    fitted,report=solve(local,np.array([-1]),[target],{0:20})
    assert not report['box_initializer']['targets_matched']
    assert report['targets_matched'];assert report['norm_refinement']['accepted']
    assert report['max_edit_degrees'][0]<=20+1e-6
    np.testing.assert_array_equal(fitted[:,:3,3],local[:,:3,3])


def test_unreachable_rotation_stays_within_actual_norm_cap():
    local=np.eye(4)[None];desired=np.eye(4);desired[:3,:3]=Rotation.from_euler('y',70,degrees=True).as_matrix()
    fitted,report=solve(local,np.array([-1]),[dict(node=0,world_matrix=desired,position_tolerance_m=.0005,rotation_tolerance_degrees=.05)],{0:20})
    assert not report['targets_matched'];assert report['max_edit_degrees'][0]<=20+1e-6
    assert report['targets'][0]['rotation_error_degrees']>49


# Previous-pose continuation is separate from the default independent fit.
import pytest
import bounded_pose_continuation as continuation
from types import SimpleNamespace


def continuation_target(node=0,angle=0):
    m=np.eye(4);m[:3,:3]=Rotation.from_euler('z',angle,degrees=True).as_matrix()
    return dict(node=node,world_matrix=m,position_tolerance_m=.0005,rotation_tolerance_degrees=.05)


def test_continuation_preserves_previous_choice_in_redundant_chain():
    local=np.tile(np.eye(4),(2,1,1));previous=local.copy()
    previous[0,:3,:3]=Rotation.from_euler('z',12,degrees=True).as_matrix()
    previous[1,:3,:3]=Rotation.from_euler('z',-12,degrees=True).as_matrix()
    fitted,report=continuation.solve(local,np.array([-1,0]),[continuation_target(1)],{0:20,1:20},previous)
    assert report['targets_matched'] and report['optimized_candidate_accepted']
    changes=Rotation.from_matrix(previous[:,:3,:3].transpose(0,2,1)@fitted[:,:3,:3]).magnitude()
    assert np.degrees(changes).max()<.5
    assert max(report['max_edit_degrees'])<20
    assert report['quality_approved'] is report['release_approved'] is False
    np.testing.assert_array_equal(local,np.tile(np.eye(4),(2,1,1)))


def test_continuation_projects_previous_outside_current_source_cap():
    local=np.eye(4)[None];previous=local.copy();previous[0,:3,:3]=Rotation.from_euler('z',70,degrees=True).as_matrix()
    fitted,report=continuation.solve(local,np.array([-1]),[continuation_target(angle=70)],{0:20},previous)
    assert max(report['max_edit_degrees'])<=20+1e-6
    assert np.degrees(np.linalg.norm(report['initial_rotation_vectors_rad'][0]))<20
    assert not report['targets_matched'] and report['targets'][0]['rotation_error_degrees']>49


def test_continuation_uses_current_translations_and_protected_nodes():
    local=np.tile(np.eye(4),(3,1,1));local[0,:3,3]=[.2,.3,.4];local[1,:3,3]=[.7,1,.9]
    previous=local.copy();previous[:,:3,3]+=100;previous[1,:3,:3]=Rotation.from_euler('z',8,degrees=True).as_matrix()
    target=continuation_target(1,8);target['world_matrix'][:3,3]=[.9,1.3,1.3]
    fitted,report=continuation.solve(local,np.array([2,0,-1]),[target],{1:20},previous)
    assert report['targets_matched'];np.testing.assert_array_equal(fitted[[0,2]],local[[0,2]])
    np.testing.assert_array_equal(fitted[:,:3,3],local[:,:3,3]);np.testing.assert_array_equal(previous[:,:3,3],local[:,:3,3]+100)


@pytest.mark.parametrize('bad',[float('nan'),999.])
def test_continuation_rejects_invalid_optimizer_candidate_and_reports_fallback(monkeypatch,bad):
    local=np.eye(4)[None];previous=local.copy();previous[0,:3,:3]=Rotation.from_euler('z',30,degrees=True).as_matrix()
    monkeypatch.setattr(continuation,'minimize',lambda *a,**k:SimpleNamespace(x=np.array([0.,0.,bad]),success=False,status=8,message='fixture failure',nit=1,nfev=1))
    fitted,report=continuation.solve(local,np.array([-1]),[continuation_target()],{0:10},previous)
    assert not report['optimized_candidate_accepted'] and not report['targets_matched']
    np.testing.assert_array_equal(report['rotation_vectors_rad'],report['initial_rotation_vectors_rad'])
    assert np.degrees(Rotation.from_matrix(fitted[0,:3,:3]).magnitude())<=10


@pytest.mark.parametrize('override',[
    dict(previous=np.tile(np.eye(4),(2,1,1))),dict(parents=np.array([0])),
    dict(edit_limits_degrees={1:20}),dict(edit_limits_degrees={0:-1}),dict(edit_limits_degrees={0:float('nan')}),
    dict(source_weight=-.01),dict(continuation_weight=float('inf')),dict(source_weight=True),
    dict(max_evaluations=0),dict(max_evaluations=True),dict(targets=[]),
])
def test_continuation_rejects_incomplete_or_invalid_problem(override):
    args=dict(local=np.eye(4)[None],parents=np.array([-1]),targets=[continuation_target()],edit_limits_degrees={0:20},previous=np.eye(4)[None])
    args.update(override)
    with pytest.raises(ValueError):continuation.solve(**args)


@pytest.mark.parametrize('where',['local','previous','world_matrix'])
def test_continuation_rejects_improper_rigid_inputs(where):
    local=np.eye(4)[None];previous=local.copy();target=continuation_target()
    if where=='world_matrix':target[where][0,0]=-1
    elif where=='local':local[0,0,0]=-1
    else:previous[0,0,0]=-1
    with pytest.raises(ValueError,match='Proper rigid'):continuation.solve(local,np.array([-1]),[target],{0:20},previous)
