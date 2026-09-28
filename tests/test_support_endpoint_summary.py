from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from summarize_support_endpoints import trace_metrics


def foot():
    return dict(speed_m_s=[.01]*149+[.6],predicted_support_steps=[True]*150,support_p95_m_s=.01,support_max_m_s=.6,last_step_m_s=.6)


def test_percentile_cannot_hide_last_step_spike():
    result=trace_metrics(foot(),151,139)
    assert result['p95_m_s']==.01
    assert result['max_m_s']==result['tail_max_m_s']==result['tail_support_max_m_s']==result['last_step_m_s']==.6
    assert result['support_steps']==150 and result['tail_support_steps']==12


def test_unobserved_support_is_missing_not_zero_speed():
    data=foot();data.update(predicted_support_steps=[False]*150,support_max_m_s=None,support_p95_m_s=None)
    result=trace_metrics(data,151,139)
    assert result['p95_m_s'] is None and result['max_m_s'] is None and result['tail_support_max_m_s'] is None
    assert result['support_steps']==result['tail_support_steps']==0 and result['tail_max_m_s']==.6


@pytest.mark.parametrize('fault',['missing_speed','missing_mask','nan','negative','integer_mask','wrong_maximum','false_support_claim','wrong_last_step'])
def test_incomplete_or_misreported_trace_is_rejected(fault):
    data=foot()
    if fault=='missing_speed':data['speed_m_s'].pop()
    if fault=='missing_mask':data['predicted_support_steps'].pop()
    if fault=='nan':data['speed_m_s'][0]=float('nan')
    if fault=='negative':data['speed_m_s'][0]=-.01
    if fault=='integer_mask':data['predicted_support_steps'][0]=1
    if fault=='wrong_maximum':data['support_max_m_s']=.01
    if fault=='false_support_claim':data['support_p95_m_s']=None
    if fault=='wrong_last_step':data['last_step_m_s']=.01
    with pytest.raises(ValueError):trace_metrics(data,151,139)
