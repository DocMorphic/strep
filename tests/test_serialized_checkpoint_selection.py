import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from serialized_checkpoint_selection import SerializedCheckpointSelector


def test_intermediate_feasible_candidate_survives_an_infeasible_final_step():
    def evaluate(x): return 1-float(x[0]), np.array([.6-x[0]]), 0., None
    selector=SerializedCheckpointSelector([0.],evaluate,bound=1.)
    selector.consider([.5],'iteration-20')
    selector.consider([1.],'final')
    assert selector.best['label']=='iteration-20'
    assert selector.controls[0]==.5
    assert not selector.records[-1]['serialized_attempts'][0]['feasible']


def test_all_backoffs_are_checked_even_when_full_step_is_feasible():
    def evaluate(x): return 1-2.6*x[0]+2.4*x[0]**2, np.array([1.]), 0., None
    selector=SerializedCheckpointSelector([0.],evaluate,bound=1.)
    r=selector.consider([1.],'iteration')
    assert len(r['serialized_attempts'])==9
    assert r['serialized_attempts'][0]['feasible']
    assert selector.controls[0]==.5 and selector.best['objective']==pytest.approx(.3)


def test_failed_limits_do_not_get_relaxed_to_find_an_improvement():
    def evaluate(x): return 1-x[0], np.array([-x[0]]), 0., None
    selector=SerializedCheckpointSelector([0.],evaluate,bound=1.)
    selector.consider([1.],'final')
    assert selector.best['label']=='source' and selector.controls[0]==0
    assert all(not a['feasible'] for a in selector.records[0]['serialized_attempts'])


def test_drift_bound_ties_and_input_arrays_are_preserved():
    def evaluate(x): return 1-x[0], np.array([1.]), (2e-6 if x[0]>.5 else 0.), None
    selector=SerializedCheckpointSelector([0.],evaluate,bound=1.)
    x=np.array([1.]);selector.consider(x,'first');x[:]=0
    selector.consider([.5],'later')
    assert selector.best['label']=='first' and selector.best['fraction']==.5
    assert selector.records[0]['proposed_controls']==[1.]
    assert selector.controls[0]==.5


def test_nonfinite_reports_and_invalid_controls_are_rejected():
    with pytest.raises(ValueError): SerializedCheckpointSelector([0.],lambda x:(float('nan'),[1.],0.,None))
    with pytest.raises(ValueError): SerializedCheckpointSelector([0.],lambda x:(1.,[-1.],0.,None))
    selector=SerializedCheckpointSelector([0.],lambda x:(1.,[1.],0.,None))
    with pytest.raises(ValueError):selector.consider([.2],'outside')
    with pytest.raises(ValueError):selector.consider([np.nan],'invalid')
