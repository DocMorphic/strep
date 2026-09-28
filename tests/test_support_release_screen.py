import copy
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from study_support_release import compare


def fixture():
    metrics=dict(floor_depth_max_m=.001,half_frame_floor_depth_max_m=.001,root_acceleration_max_m_s2=2.,local_rotation_step_max_degrees=3.,
        feet={s:dict(predicted_support_hover_max_m=.001) for s in ['Left','Right']})
    proof=dict(metrics={v:copy.deepcopy(metrics) for v in ['input','candidate']},bounds_and_preservation_passed=True)
    trace=dict(variants=[dict(variant=v,feet={s:dict(predicted_support_max_m_s=.04,predicted_support_p95_m_s=.03) for s in ['Left','Right']}) for v in ['input','candidate']])
    dynamics={v:dict(feet={s:dict(global_acceleration_max_m_s2=4.,releases=[dict(release_frame=7,acceleration_max_m_s2=3.)]) for s in ['Left','Right']}) for v in ['input','prior','candidate']}
    return proof,copy.deepcopy(proof),trace,copy.deepcopy(trace),dynamics


def test_improved_stance_cannot_hide_worse_release_dynamics():
    args=fixture();args[3]['variants'][1]['feet']['Left']['predicted_support_max_m_s']=.01
    args[4]['candidate']['feet']['Left']['releases'][0]['acceleration_max_m_s2']=3.2
    r=compare(*args)
    assert r['checks']['Left_support_max_no_worse'] and not r['checks']['Left_every_release_acceleration_no_worse']
    assert not r['passes_development_screen'] and not r['quality_approved']


def test_reducing_bad_prior_slip_still_fails_raw_speed_cap():
    args=fixture();args[2]['variants'][1]['feet']['Right']['predicted_support_max_m_s']=.3
    args[3]['variants'][1]['feet']['Right']['predicted_support_max_m_s']=.2
    r=compare(*args)
    assert r['checks']['Right_support_max_no_worse'] and not r['checks']['Right_support_max_raw_cap']


def test_missing_release_or_changed_clock_is_rejected():
    import pytest
    args=fixture();args[4]['candidate']['feet']['Left']['releases']=[]
    with pytest.raises(ValueError,match='population'):compare(*args)
    args=fixture();args[4]['candidate']['feet']['Left']['releases'][0]['release_frame']=8
    with pytest.raises(ValueError,match='clock'):compare(*args)


def test_numerical_pass_is_never_quality_approval():
    r=compare(*fixture())
    assert r['passes_development_screen'] and not r['quality_approved']
