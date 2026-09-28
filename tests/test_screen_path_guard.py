import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from screen_path_guard import select_step


def contact():
    return dict(opposing_normal_degrees=10., directions=[dict(source=a, target=b,
        within_tolerance_count=3, source_area_witness=dict(area_m2=3e-5),
        target_area_witness=dict(area_m2=3e-5)) for a,b in [(0,1),(1,0)]])


def test_smaller_peak_can_redistribute_within_existing_screen_without_approval():
    result = select_step([.024,0.,.002], [.022,.0015,.0044], 20.,19.,contact())
    assert result['accepted'] and not result['quality_approved']


@pytest.mark.parametrize('after,energy,failed', [
    ([.022,.005001,.004],19.,'passing_samples_stay_below_screen'),
    ([.0241,.001,.004],19.,'failing_samples_do_not_worsen'),
    ([.022,.001,.004],21.,'objective_does_not_worsen')])
def test_collision_and_energy_regressions_rejected(after,energy,failed):
    result = select_step([.024,0.,.002],after,20.,energy,contact())
    assert not result['accepted'] and not result['checks'][failed]


def test_no_new_peak_even_if_all_samples_remain_below_screen():
    assert not select_step([.001,0.],[.002,.001],2.,1.,contact())['accepted']


@pytest.mark.parametrize('field,value', [('normal',21.),('area',1e-5),('count',2)])
def test_contact_loss_rejected(field,value):
    region=contact()
    if field=='normal':region['opposing_normal_degrees']=value
    elif field=='area':region['directions'][1]['target_area_witness']['area_m2']=value
    else:region['directions'][0]['within_tolerance_count']=value
    assert not select_step([.024],[.022],2.,1.,region)['accepted']


def test_invalid_or_incomplete_measurements_fail_closed():
    for after in [[np.nan],[np.inf],[-.01],[]]:
        with pytest.raises(ValueError):select_step([.024],after,2.,1.,contact())
    region=contact();region['directions'].pop()
    with pytest.raises(ValueError):select_step([.024],[.022],2.,1.,region)
    region=contact();region['opposing_normal_degrees']=float('nan')
    with pytest.raises(ValueError):select_step([.024],[.022],2.,1.,region)
