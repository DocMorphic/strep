from pathlib import Path
import copy
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_motion_envelope import MotionEnvelope,source_peak_policy,TRACKS

C='1'*64;R='2'*64


def fixture():
    values={name:np.arange(1,6-order,dtype=float) for name,(_,order) in TRACKS.items()}
    values.update(floor=np.array([[0.,.01,0.,0.,0.],[0,1,0,0,0],[0,.0001,0,0,0]]),contact_position=np.array([.3,.2]))
    return values,source_peak_policy(values,5,C,R)


def test_global_budget_allows_faster_at_one_time_without_increasing_overall_peak():
    before,policy=fixture();after={k:v.copy() for k,v in before.items()};after['skin_speed_m_s'][0]=3.5;after['contact_position']-=.01
    env=MotionEnvelope(policy,before,context_sha256=C,reference_metrics_sha256=R);r=env.compare(before,after)
    assert not r['strict_source_comparison']['all_metrics_nonregressing'] and r['envelope_comparison']['all_metrics_nonregressing'] and r['after_bounds']['all_motion_bounds_pass']
    assert r['strict_source_comparison']['metrics']['skin_speed_m_s']['worsened_rows']==1


def test_physical_last_row_regression_cannot_be_hidden_by_motion_allowance():
    before,policy=fixture();after={k:v.copy() for k,v in before.items()};after['skin_speed_m_s'][0]=3.5;after['contact_position'][-1]+=1e-14
    env=MotionEnvelope(policy,before,context_sha256=C,reference_metrics_sha256=R);r=env.compare(before,after)
    assert not r['envelope_comparison']['all_metrics_nonregressing'] and r['envelope_comparison']['metrics']['contact_position']['worsened_rows']==1
    for name in ['floor','contact_position']:np.testing.assert_array_equal(env.observe(before)[name],before[name])


def test_overall_peak_cannot_increase_even_by_a_tiny_value():
    before,policy=fixture();after={k:v.copy() for k,v in before.items()};after['skin_speed_m_s'][-1]+=1e-12
    r=MotionEnvelope(policy,before,context_sha256=C,reference_metrics_sha256=R).compare(before,after)
    assert not r['after_bounds']['all_motion_bounds_pass'] and not r['envelope_comparison']['all_metrics_nonregressing'] and r['after_bounds']['tracks']['skin_speed_m_s']['failed_rows']==1


def test_explicit_complete_per_interval_budgets_and_failed_reference_remain_visible():
    before,policy=fixture();policy['limits'][0]['upper']=[1.,1.,1.,1.];after={k:v.copy() for k,v in before.items()};after['skin_speed_m_s']-=.5;after['skin_speed_m_s'][0]=1.
    r=MotionEnvelope(policy,before,context_sha256=C,reference_metrics_sha256=R).compare(before,after)
    assert r['envelope_comparison']['all_metrics_nonregressing'] and not r['before_bounds']['all_motion_bounds_pass'] and not r['after_bounds']['all_motion_bounds_pass']


def test_policy_and_returned_values_are_owned_and_every_physical_metric_is_retained():
    before,policy=fixture();env=MotionEnvelope(policy,before,context_sha256=C,reference_metrics_sha256=R);policy['limits'][0]['upper']=999
    output=env.observe(before);output['floor'][:]=999
    assert env.caps['skin_speed_m_s'].max()==4 and before['floor'].max()==1
    assert len(output)==len(before) and sum(v.size for v in output.values())==sum(v.size for v in before.values())


@pytest.mark.parametrize('fault',['context','reference','unit','missing','duplicate','clock','negative','nan','bool','partial','unknown','physical_override'])
def test_invalid_or_unbound_author_policies_reject(fault):
    values,policy=fixture()
    if fault=='context':policy['context_sha256']='3'*64
    elif fault=='reference':policy['reference_metrics_sha256']='4'*64
    elif fault=='unit':policy['limits'][0]['unit']='degrees/s'
    elif fault=='missing':policy['limits'].pop()
    elif fault=='duplicate':policy['limits'][-1]=copy.deepcopy(policy['limits'][0])
    elif fault=='clock':policy['frames']=6
    elif fault=='negative':policy['limits'][0]['upper']=-1
    elif fault=='nan':policy['limits'][0]['upper']=float('nan')
    elif fault=='bool':policy['limits'][0]['upper']=True
    elif fault=='partial':policy['limits'][0]['upper']=[1.,2.]
    elif fault=='unknown':policy['limits'][0]['metric']='ignored'
    else:policy['limits'][0]['metric']='floor'
    with pytest.raises(ValueError):MotionEnvelope(policy,values,context_sha256=C,reference_metrics_sha256=R)


def test_observation_names_or_rows_cannot_change_after_policy_compilation():
    values,policy=fixture();env=MotionEnvelope(policy,values,context_sha256=C,reference_metrics_sha256=R)
    for modified in [dict(values,extra=np.ones(1)),{k:v for k,v in values.items() if k!='floor'},dict(values,skin_speed_m_s=np.ones(3))]:
        with pytest.raises(ValueError):env.observe(modified)


def test_reserved_output_names_cannot_overwrite_an_original_condition():
    values,policy=fixture();values['motion_excess.skin_speed_m_s']=np.zeros(4)
    with pytest.raises(ValueError,match='reserved'):MotionEnvelope(policy,values,context_sha256=C,reference_metrics_sha256=R)


def test_cli_creates_bound_explicit_policy_and_preserves_existing_output(tmp_path):
    import json,subprocess
    from strep import sha256
    values,_=fixture();context=tmp_path/'context.json';reference=tmp_path/'metrics.npz';output=tmp_path/'policy.json'
    context.write_text(json.dumps(dict(schema='strep-authored-scene-guidance-v1',frames=5)),encoding='utf-8');np.savez(reference,**values)
    command=[sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/scene_motion_envelope.py'),str(context),str(reference),str(output)]
    result=__import__('subprocess').run(command,capture_output=True,text=True);assert result.returncode==0,result.stderr
    saved=output.read_bytes();policy=json.loads(saved);assert policy['context_sha256']==sha256(context) and policy['reference_metrics_sha256']==sha256(reference)
    assert MotionEnvelope(policy,values,context_sha256=sha256(context),reference_metrics_sha256=sha256(reference)).assess(values)['all_motion_bounds_pass']
    assert subprocess.run(command,capture_output=True).returncode!=0 and output.read_bytes()==saved
