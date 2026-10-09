"""Missing/altered atomic receipts cannot certify gameplay state or timing."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from study_scene_prop_ownership import fixture
from scene_commit_receipts import audit


def sample():
    _,plan=fixture();group=plan['groups'][0];actions=[]
    for transition in group['transitions']:
        actions.append(dict(object=transition['object'],before=transition['before'],after=transition['after'],
            event_ids=list(dict.fromkeys(c['event_id'] for c in transition['changes'])),source_time_s=.2,
            physics_application_time_s=.2,application_delay_s=0.,tick=12,session=0,last_grip_released=False,
            pose=np.eye(4).tolist(),velocity=[0,0,0],spin=[0,0,0]))
    modes={'A':'embedded','B':'extracted'};roots={a:np.eye(4).tolist() for a in modes}
    states={p:dict(pose=np.eye(4).tolist(),velocity=[0,0,0],spin=[0,0,0],contacts=[],collision_layer=0,collision_mask=0,
        step_s=1/60,gravity=[0,-9.81,0],inverse_mass=.5,inverse_inertia=[1,1,1],direct_state_class='JoltPhysicsDirectBodyState3D') for p in ['P','Q']}
    record=dict(tick=12,session=0,source_time_s=.2,group_cursor=1,members={'P':['AL','AR'],'Q':['BR']},
        modes={'P':'held','Q':'held'},tracking={p:dict(pose=np.eye(4).tolist(),time_s=.2) for p in states},props=states,
        physics_root_deltas=copy.deepcopy(roots),transport='live',failure='',command='')
    receipt=dict(schema='strep-scene-prop-commit-v1',commit_id='123:0:12',owner_instance_id='123',
        source_semantic_sha256=plan['source_semantic_sha256'],source_clock=plan['clock'],
        source_events=[dict(e,time_s=.2) for e in plan['source_events'][:2]],actions=actions,record=copy.deepcopy(record),
        actor_root_motion=roots,root_modes=modes,scene_pose_time_s=.2,scene_playback_time_s=.2,quality_approved=False,release_approved=False,
        physics_rate_hz=60,action_clock=dict(schema='strep-scene-prop-action-clock-f64le-v1',count=len(actions),bytes_hex=np.array([[.2,.2,0.]]*len(actions),dtype='<f8').tobytes().hex()))
    receipt['props_state_phase']='assigned_before_force_integration'
    record['scene']={'actors':{a:{'root_motion':np.eye(4)[:3].T.tolist()} for a in modes}}
    observed=dict(commit_receipts=[receipt],commit_callbacks=[dict(commit_id=receipt['commit_id'],all_containers_read_only=True,all_bodies_seen=True,owner_state_matches=True)],
        detached_copies=1,records=[record],actions=copy.deepcopy(actions))
    return plan,modes,observed


def test_complete_atomic_boundary_and_no_quality_inference():
    plan,modes,observed=sample();result=audit(plan,modes,observed,physics_fps=60)
    assert result['receipts']==1 and result['actions']==2
    assert result['all_recorded_commit_boundaries_checked'] and not result['quality_approved'] and not result['release_approved']


@pytest.mark.parametrize('fault',['missing_receipt','missing_all_notifications','duplicate','missing_body','missing_actor',
    'source_binding','clock','event','event_time','late_actor','mode','changed_members','changed_action','hidden_delay',
    'writable','incomplete_callback','faulted','approval','extra_boundary','different_owner','empty_state','incomplete_tracking','nonfinite_state','missing_delta',
    'clock_bytes','clock_count','physics_rate','unplanned_owner','unplanned_mode','phase'])
def test_resealed_incomplete_or_changed_receipts_fail(fault):
    plan,modes,observed=sample();receipt=observed['commit_receipts'][0]
    if fault=='missing_receipt':observed['commit_receipts']=[];observed['commit_callbacks']=[];observed['detached_copies']=0
    elif fault=='missing_all_notifications':observed['commit_receipts']=[];observed['commit_callbacks']=[];observed['detached_copies']=0;observed['actions']=[]
    elif fault=='duplicate':observed['commit_receipts']*=2;observed['commit_callbacks']*=2;observed['detached_copies']=2;observed['records']*=2
    elif fault=='missing_body':del receipt['record']['props']['Q']
    elif fault=='missing_actor':del receipt['actor_root_motion']['B']
    elif fault=='source_binding':receipt['source_semantic_sha256']='0'*64
    elif fault=='clock':receipt['source_clock']=copy.deepcopy(receipt['source_clock']);receipt['source_clock']['bytes_hex']='00'*48
    elif fault=='event':receipt['source_events'][0]=dict(receipt['source_events'][0],timing_confirmed=False)
    elif fault=='event_time':receipt['source_events'][0]['time_s']+=.001
    elif fault=='late_actor':receipt['scene_pose_time_s']+=.001
    elif fault=='mode':receipt['root_modes']=dict(modes,A='extracted')
    elif fault=='changed_members':receipt['record']['members']['P']=['AL']
    elif fault=='changed_action':receipt['actions'][0]['after']=['AL'];observed['actions'][0]['after']=['AL']
    elif fault=='hidden_delay':receipt['actions'][0]['physics_application_time_s']=.21;observed['actions'][0]['physics_application_time_s']=.21
    elif fault=='writable':observed['commit_callbacks'][0]['all_containers_read_only']=False
    elif fault=='incomplete_callback':observed['commit_callbacks'][0]['all_bodies_seen']=False
    elif fault=='faulted':receipt['record']['failure']='Missing body callback'
    elif fault=='approval':receipt['quality_approved']=True
    elif fault=='extra_boundary':receipt['record']['tick']=13;receipt['commit_id']='123:0:13';observed['commit_callbacks'][0]['commit_id']=receipt['commit_id']
    elif fault=='different_owner':receipt['owner_instance_id']='456'
    elif fault=='empty_state':receipt['record']['props']['Q']={}
    elif fault=='incomplete_tracking':receipt['record']['tracking']={}
    elif fault=='nonfinite_state':receipt['record']['props']['Q']['velocity'][0]=float('nan')
    elif fault=='missing_delta':del receipt['record']['physics_root_deltas']['B']
    elif fault=='clock_bytes':receipt['action_clock']['bytes_hex']='00'*48
    elif fault=='clock_count':receipt['action_clock']['count']=1
    elif fault=='physics_rate':receipt['physics_rate_hz']=120
    elif fault=='unplanned_owner':
        receipt['record']['members']['Q']=[];observed['records'][0]['members']['Q']=[]
    elif fault=='unplanned_mode':
        receipt['record']['modes']['Q']='released';observed['records'][0]['modes']['Q']='released'
    elif fault=='phase':receipt['props_state_phase']='collision_resolved'
    with pytest.raises((ValueError,AssertionError)):audit(plan,modes,observed,physics_fps=60)


def test_pause_preview_resume_do_not_redispatch_or_reset_forward_cursor():
    plan,modes,observed=sample();record=observed['records'][0]
    observed['records'].extend([dict(record,transport='paused',command='pause'),dict(record,transport='preview',group_cursor=0,command='preview'),dict(record,command='resume')])
    assert audit(plan,modes,observed,physics_fps=60)['receipts']==1


def test_changed_actor_root_fails_even_when_all_callback_flags_are_true():
    plan,modes,observed=sample();observed['commit_receipts'][0]['actor_root_motion']['B'][0][3]=.01
    with pytest.raises(AssertionError):audit(plan,modes,observed,physics_fps=60)


def test_signed_refcounted_identity_is_preserved_without_float_conversion():
    plan,modes,observed=sample();receipt=observed['commit_receipts'][0]
    receipt['owner_instance_id']='-9223372006269909511';receipt['commit_id']=receipt['owner_instance_id']+':0:12'
    observed['commit_callbacks'][0]['commit_id']=receipt['commit_id']
    assert audit(plan,modes,observed,physics_fps=60)['receipts']==1
