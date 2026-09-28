from pathlib import Path
import sys
import copy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from reconstruct_descent import reconstruct


def fixture():
    initial=np.zeros((3,3));request=dict(steps=2,trusts=[.1,.01])
    trial=dict(fraction=1.,accepted=True,objective=.5,geometry=True,minimum_constraint=0.)
    solver=dict(starting_coordinates=[0.],final_coordinates=[.05],history=[dict(objective_before=1.,accepted=True,
        attempts=[dict(trust=.1,trials=[trial],proposed_delta=[.05])])])
    return initial,solver,request,[1],[2]


def test_reconstruction_preserves_unselected_coordinates():
    args=fixture();result=reconstruct(*args);expected=np.zeros((3,3));expected[1,2]=.05;np.testing.assert_array_equal(result,expected)


def test_rejects_wrong_delta_schedule_or_claimed_feasibility():
    for kind in ['delta','schedule','guard']:
        args=list(fixture());solver=copy.deepcopy(args[1]);args[1]=solver;a=solver['history'][0]['attempts'][0]
        if kind=='delta':a['proposed_delta']=[.2]
        if kind=='schedule':a['trials'][0]['fraction']=.5
        if kind=='guard':a['trials'][0]['minimum_constraint']=-.01
        with pytest.raises(ValueError):reconstruct(*args)
