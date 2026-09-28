import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from compare_support_iterations import match_protocols,selected_metrics


def test_match_rejects_changed_solver_inputs_budgets_or_contact_protocol():
    a=dict(steps_per_block=3,midpoint_constraints=True,cases=[dict(id='a')],trusts=[.005],implementation={'solver.py':'fixed','study_coupled_support.py':'old'})
    b={**a,'steps_per_block':12,'implementation':{**a['implementation'],'study_coupled_support.py':'new'}}
    assert match_protocols(a,b)==['study_coupled_support.py']
    for changed in [{**b,'trusts':[.05]},{**b,'steps_per_block':3},{**b,'midpoint_constraints':False},
                    {**b,'implementation':{**b['implementation'],'solver.py':'changed'}},
                    {**b,'cases':[]}]:
        with pytest.raises(ValueError):match_protocols(a,changed)


def test_rejected_low_objective_cannot_improve_selected_metrics():
    audit=dict(passed=False,checks={'floor':False},source_sha256='input',candidate_sha256='rejected',
        foot_speed_excess_energy_before=.2,foot_speed_excess_energy_after=0.,
        feet=[dict(side='Left',raw_peak_target_m_s=.1,support_peak_before_m_s=.5,support_peak_after_m_s=.05)])
    result=dict(status='input_retained',selected_sha256='input')
    selected=selected_metrics(audit,result)
    assert selected['selected_energy']==.2
    assert selected['feet'][0]['selected_peak_m_s']==.5
    assert selected['remaining_peak_regressions']==['Left']
    with pytest.raises(ValueError):selected_metrics(audit,dict(status='candidate_preserved',selected_sha256='rejected'))
    with pytest.raises(ValueError):selected_metrics(audit,{**result,'selected_sha256':'wrong'})


def test_accepted_candidate_must_have_passed_checks_and_exact_identity():
    audit=dict(passed=True,checks={'floor':True},source_sha256='input',candidate_sha256='candidate',
        foot_speed_excess_energy_before=.2,foot_speed_excess_energy_after=.01,
        feet=[dict(side='Left',raw_peak_target_m_s=.1,support_peak_before_m_s=.5,support_peak_after_m_s=.1005)])
    result=dict(status='candidate_preserved',selected_sha256='candidate')
    assert selected_metrics(audit,result)['remaining_peak_regressions']==[]
    with pytest.raises(ValueError):selected_metrics(audit,{**result,'selected_sha256':'different'})
