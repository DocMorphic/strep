"""Population selection must not hide failed or unretained reference cases."""
import pytest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from study_support_fallback_pilot import planned_cases


def fixture():
    cases=[dict(id='motion-036-rig-02',eligible=True),
           dict(id='control',eligible=False),dict(id='motion-031-rig-02',eligible=True)]
    rows=[dict(id=c['id'],status='failed' if i==2 else 'candidate_preserved') for i,c in enumerate(cases)]
    return dict(cases=cases),dict(rows=rows)


def test_full_population_keeps_failed_reference_target():
    protocol,complete=fixture()
    assert planned_cases(protocol,complete,True)==['motion-036-rig-02','motion-031-rig-02']
    assert complete['rows'][2]['status']=='failed'


def test_default_remains_two_declared_cases():
    protocol,complete=fixture()
    assert planned_cases(protocol,complete)==['motion-036-rig-02','motion-031-rig-02']


@pytest.mark.parametrize('mutation',['missing','duplicate','reorder'])
def test_incomplete_or_ambiguous_reference_rejected(mutation):
    protocol,complete=fixture()
    if mutation=='missing':complete['rows'].pop()
    elif mutation=='duplicate':protocol['cases'][2]['id']=protocol['cases'][0]['id']
    else:complete['rows'].reverse()
    with pytest.raises(ValueError):planned_cases(protocol,complete,True)


def test_no_targets_rejected():
    protocol,complete=fixture()
    for c in protocol['cases']:c['eligible']=False
    with pytest.raises(ValueError):planned_cases(protocol,complete,True)
