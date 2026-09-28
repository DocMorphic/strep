import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from support_comparison_protocol import match_studies


def pair():
    before=dict(steps_per_block=12,midpoint_constraints=True,fractions=[1.,.5,.25,.125],
        cases=[dict(id='one',source_sha256='source')],trusts=[.005,.001,.0002],
        implementation={'coupled_support_block.py':'old','study_coupled_support.py':'old','verify.py':'fixed'})
    after=copy.deepcopy(before);after['fractions']=[2.**-n for n in range(11)]
    after['implementation'].update({'coupled_support_block.py':'new','study_coupled_support.py':'new'})
    return before,after


def test_explicit_backtracking_match_preserves_iteration_only_rejection():
    a,b=pair()
    assert match_studies(a,b,'backtracking')==['coupled_support_block.py','study_coupled_support.py']
    with pytest.raises(ValueError):match_studies(a,b,'iterations')
    with pytest.raises(ValueError):match_studies(a,b,'unknown')


@pytest.mark.parametrize('change',[
    {'steps_per_block':13},{'midpoint_constraints':False},{'trusts':[.05]},
    {'cases':[dict(id='one',source_sha256='changed')]},
    {'fractions':[1.,.5,.25,.125]}, {'fractions':[1.,.5,.25,.125,.06]},
    {'fractions':[True,.5,.25,.125,.0625]},
    {'fractions':[2.**-n for n in range(12)]},
])
def test_unmatched_experiment_is_rejected(change):
    a,b=pair();b.update(change)
    with pytest.raises(ValueError):match_studies(a,b,'backtracking')


def test_changed_validator_or_dependency_cannot_hide_in_solver_change():
    a,b=pair();b['implementation']['verify.py']='changed'
    with pytest.raises(ValueError):match_studies(a,b,'backtracking')
    a,b=pair();b['implementation']['new.py']='extra'
    with pytest.raises(ValueError):match_studies(a,b,'backtracking')
