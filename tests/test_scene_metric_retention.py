"""Full row populations and exact rejection, including late hidden regression."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_metric_retention import compare_metrics,snapshot_metrics


def test_improvement_in_average_cannot_hide_last_row_regression():
    before={'depth':np.ones(10000),'contact':np.array([2.])};after={'depth':np.zeros(10000),'contact':np.array([1.])};after['depth'][-1]=1.000000000000001
    r=compare_metrics(before,after)
    assert not r['all_metrics_nonregressing'] and r['metrics']['depth']['worsened_rows']==1 and r['complete_metric_rows']==10001 and r['tolerance_added']==0


def test_snapshot_owns_every_array_and_exact_ties_pass():
    source={'floor':np.array([[0.,.02],[0.,0.]]),'count':np.array([3,0])};saved=snapshot_metrics(source)
    source['floor'][0,1]=1
    assert saved['floor'][0,1]==.02 and compare_metrics(saved,saved)['all_metrics_nonregressing']


@pytest.mark.parametrize('defect',['name','shape','nan','negative','bool','empty','budget'])
def test_invalid_or_reduced_population_rejects(defect):
    before={'x':np.ones(2)};after={'x':np.zeros(2)}
    if defect=='name':after={'y':after['x']}
    elif defect=='shape':after['x']=np.zeros(1)
    elif defect=='nan':after['x'][0]=np.nan
    elif defect=='negative':after['x'][0]=-1
    elif defect=='bool':after['x']=after['x'].astype(bool)
    elif defect=='empty':after={}
    else:after['x']=np.broadcast_to(np.array(0.),(3000000,))
    with pytest.raises(ValueError):compare_metrics(before,after)
