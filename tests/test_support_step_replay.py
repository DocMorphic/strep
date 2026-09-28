import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from probe_support_backtracking import replay


def log():
    return dict(frames=[1,2],history=[dict(accepted=True,attempts=[
        dict(delta=[9]*6,trials=[dict(fraction=1,accepted=False)]),
        dict(delta=[1,2,3,4,5,6],trials=[dict(fraction=.5,accepted=True)])]),
        dict(accepted=False,attempts=[dict(delta=[99]*6,trials=[dict(fraction=1,accepted=False)])])])


def test_replay_uses_only_retained_steps_and_keeps_untouched_frames():
    initial=np.arange(15,dtype=float).reshape(5,3);before=initial.copy()
    actual=replay(initial,log());expected=initial.copy();expected[1:3]+=.5*np.arange(1,7).reshape(2,3)
    np.testing.assert_array_equal(actual,expected)
    np.testing.assert_array_equal(initial,before)


def test_replay_rejects_missing_acceptance_and_invalid_delta():
    data=log();data['history'][0]['accepted']=False
    with pytest.raises(ValueError):replay(np.zeros((5,3)),data)
    data=log();data['history'][0]['attempts'][1]['delta'][0]=float('nan')
    with pytest.raises(ValueError):replay(np.zeros((5,3)),data)
    data=log();data['frames']=[1,1]
    with pytest.raises(ValueError):replay(np.zeros((5,3)),data)
