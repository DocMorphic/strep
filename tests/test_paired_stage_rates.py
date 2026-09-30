import sys
from pathlib import Path
import pytest
import numpy as np
import copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_paired_stage_rates import validate_population,phase_windows
from audit_scene_joint_rates import compare_rates
from verify_paired_stage_rates import verify_rates


def fixture():
    request=dict(seeds=[11,22],methods=['raw','body_fit','body_fit_posture'])
    manifest=dict(scenes=[dict(id=f'{m}-seed-{s}') for s in request['seeds'] for m in request['methods']])
    engine=[dict(scene_id=row['id'],actor=a,frames=150) for row in manifest['scenes'] for a in ['A','B']]
    return manifest,request,engine


def test_complete_population_and_duplicate_scene_rejection():
    manifest,request,engine=fixture();assert len(validate_population(manifest,request,engine))==6
    manifest['scenes'][-1]=manifest['scenes'][0]
    with pytest.raises(ValueError,match='stage/seed'):validate_population(manifest,request,engine)


def test_missing_partner_engine_evidence_cannot_be_replaced_by_duplicate():
    manifest,request,engine=fixture();engine[-1]=engine[0]
    with pytest.raises(ValueError,match='actor evidence'):validate_population(manifest,request,engine)


def test_reject_changed_frame_or_seed_population():
    manifest,request,engine=fixture();engine[0]['frames']=149
    with pytest.raises(ValueError,match='frame count'):validate_population(manifest,request,engine)
    request['seeds']=[11,11]
    with pytest.raises(ValueError,match='Distinct seeds'):validate_population(manifest,request,engine)


def test_windows_bind_event_and_both_posture_joins():
    windows=phase_windows(150,75,[60,75,75,90])
    assert windows['entry_join']==[58,62] and windows['exit_join']==[88,92] and windows['event']==[73,77]
    with pytest.raises(ValueError):phase_windows(150,76,[60,75,75,90])


def test_independent_peak_replay_checks_locations_not_just_values():
    source=np.zeros((17,2,3));candidate=source.copy();candidate[8,1,0]=.01
    rates=compare_rates(source,candidate,['Arm','Finger'],{'event':[1,3]})
    count,error=verify_rates(source,candidate,rates,['Arm','Finger'])
    assert count==8 and error<1e-10
    changed=copy.deepcopy(rates);changed['acceleration']['windows'][0]['joints'][1]['candidate_peak_frame']+=.25
    with pytest.raises(ValueError,match='clock'):verify_rates(source,candidate,changed,['Arm','Finger'])


def test_independent_replay_rejects_aggregate_hiding_finger_increase():
    source=np.zeros((17,2,3));candidate=source.copy();source[8,0,0]=.02;candidate[8,0,0]=.01;candidate[8,1,0]=.005
    rates=compare_rates(source,candidate,['Arm','Finger'],{'event':[1,3]})
    rates['acceleration']['windows'][0]['increased_joints_over_1e_5']=0
    with pytest.raises(ValueError,match='increase count'):verify_rates(source,candidate,rates,['Arm','Finger'])
