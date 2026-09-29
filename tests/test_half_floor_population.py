import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from study_half_floor_population import pair_results


def rows():
    return [dict(id=f'{case}/{method}',case=str(case),method=method,status='accepted',
                 before=dict(objective=10.,peak_m_s2=5.,failing_centers=[3]),
                 after=dict(objective=9.,peak_m_s2=4.9,failing_centers=[3]),
                 accepted_steps=1,all_guards_passed=True,preserve_starting_root=True)
            for case in range(9) for method in ('keys_only','keys_and_halves')]


def test_keeps_regressions_and_rejected_outputs_separate_from_improvement():
    data=rows()
    data[1]['after'].update(objective=8.,failing_centers=[3,8])
    data[1].update(status='no_accepted_correction',all_guards_passed=False)
    proof=pair_results(data)
    first=proof['pairs'][0]
    assert first['half_minus_keys_objective']==-1.
    assert first['added_failures']['keys_and_halves']==[8]
    assert not first['both_preserved'] and not proof['quality_approved']
    assert first['methods']['keys_and_halves']['status']=='no_accepted_correction'


def test_failed_method_remains_in_denominator_without_success_claim():
    data=rows();data[1]=dict(id='0/keys_and_halves',case='0',method='keys_and_halves',status='failed')
    proof=pair_results(data)
    assert len(proof['pairs'])==9
    assert proof['pairs'][0]==dict(case='0',status='execution_failed')


@pytest.mark.parametrize('mutation',['missing','duplicate','mismatched_start','unfinished'])
def test_rejects_incomplete_or_unmatched_pairs(mutation):
    data=copy.deepcopy(rows())
    if mutation=='missing':data.pop()
    elif mutation=='duplicate':data[1]=data[0].copy()
    elif mutation=='mismatched_start':data[1]['before']['objective']=11.
    else:data[1]['status']='pending'
    with pytest.raises(ValueError):pair_results(data)
