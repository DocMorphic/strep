import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from coupled_constraint_report import breakdown
from hand_norm_proposal import measurement


def sample():
    # Four frames, two joints: 6 speed, 4 acceleration, 6 angular speed,
    # 4 angular acceleration, then three palm points and two normals.
    return dict(vectors=np.zeros((25,3)),caps=np.ones(25),scales=np.ones(25),margins=np.ones(6),depths=np.ones(9)*.01)


def test_reports_distinct_physical_and_scaled_violations_without_rebasing():
    data=sample();data['vectors'][18,0]=1.002;data['vectors'][24,0]=1.001;data['margins'][5]=-.003
    result=breakdown(data,['A:hand','B:hand'],4,2,3)
    assert not result['passed'] and measurement(data)['minimum_margin']<0
    angular=result['vector_groups'][3]
    assert angular['failed_indices']==[2] and angular['unit']=='rad/s^2'
    assert angular['worst']['joint']=='A:hand' and angular['worst']['sample']==1
    assert angular['maximum_excess']==pytest.approx(.002)
    assert result['vector_groups'][5]['failed_indices']==[1]
    assert result['scalar_groups'][2]['failed_indices']==[2]
    np.testing.assert_array_equal(data['caps'],np.ones(25))


def test_zero_margins_pass_without_approving_motion_quality():
    data=sample();data['vectors'][:,0]=1.;data['margins'][:]=0
    result=breakdown(data,['A','B'],4,2,3)
    assert result['passed'] and not result['quality_approved']


@pytest.mark.parametrize('frames,guides,witnesses',[(3,2,3),(4,1,3),(4,2,2),(4,0,5)])
def test_population_mismatch_is_not_silently_relabelled(frames,guides,witnesses):
    with pytest.raises(ValueError):breakdown(sample(),['A','B'],frames,guides,witnesses)
