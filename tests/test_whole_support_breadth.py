from pathlib import Path
import sys
import copy
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from study_whole_support_breadth import select,check_engine,FAMILIES,RIGS


def protocol():
    return dict(rigs=[dict(id=r) for r in RIGS],motions=[dict(id=str(i),family=f,seed=1301,frames=150+i*30,fps=30,flat_floor_screen_applicable=True) for i,f in enumerate(FAMILIES)]+[
        dict(id='context',family='partner_interaction',seed=1301,frames=150,fps=30,flat_floor_screen_applicable=False)])


def test_complete_population_and_context_exclusion():
    p=protocol();before=copy.deepcopy(p);chosen,excluded=select(p)
    assert [m['family'] for m in chosen]==FAMILIES and len(chosen)==8
    assert [m['id'] for m in excluded]==['context'] and p==before


@pytest.mark.parametrize('change',['missing','duplicate','ineligible','new_eligible','missing_rig'])
def test_selection_fails_instead_of_silently_dropping_cases(change):
    p=protocol()
    if change=='missing':p['motions'].pop(0)
    if change=='duplicate':p['motions'].append(copy.deepcopy(p['motions'][0]))
    if change=='ineligible':p['motions'][0]['flat_floor_screen_applicable']=False
    if change=='new_eligible':p['motions'][-1]['flat_floor_screen_applicable']=True
    if change=='missing_rig':p['rigs'].pop()
    with pytest.raises(ValueError):select(p)


def test_engine_accounting_uses_variable_clip_lengths_and_rejects_mismatch():
    checks=[dict(id='a',frames=210,sha256='x'),dict(id='b',frames=210,sha256='y')]
    proof=dict(checks=[dict(id='a',frames=210,source_sha256='x'),dict(id='b',frames=210,source_sha256='y')])
    assert check_engine(proof,checks)==420
    proof['checks'][1]['frames']=150
    with pytest.raises(ValueError,match='clock'):check_engine(proof,checks)
    proof['checks'].pop()
    with pytest.raises(ValueError,match='population'):check_engine(proof,checks)
