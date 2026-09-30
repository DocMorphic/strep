import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from study_refined_trust_limits import variants,objective_terms


def test_trust_and_physical_penalty_are_varied_independently():
    settings=variants(.1,5.,.025,.00002)
    assert len(settings)==8 and sorted({v['trust_degrees'] for v in settings})==[.1,.5,1.,5.]
    step=np.array([.001,-.002,.003]);solver=dict(predicted_peak_m=.02)
    original=objective_terms(step,solver,settings[0])
    for item in settings:
        found=objective_terms(step,solver,item)
        assert found['penalty_m']==pytest.approx(original['penalty_m']*item['penalty_multiplier'])
        assert found['total_m']==pytest.approx(found['peak_m']+found['penalty_m'])
        assert found['physical_penalty_coefficient']==pytest.approx(original['physical_penalty_coefficient']*item['penalty_multiplier'])


def test_declared_trust_never_exceeds_original_budget_or_duplicates_variants():
    settings=variants(.1,.3,.025,.00002)
    assert [s['trust_degrees'] for s in settings]==[.1,.1,.3,.3]
    assert len({s['name'] for s in settings})==len(settings)


@pytest.mark.parametrize('args',[(0,5,.025,.00002),(.1,0,.025,.00002),(.1,.05,.025,.00002),(.1,5,float('nan'),.00002),(.1,5,.025,-1)])
def test_invalid_experiment_settings_rejected(args):
    with pytest.raises(ValueError):variants(*args)
