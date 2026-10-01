import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from refine_serialized_witness_ray import refine


@pytest.mark.parametrize('target',[.484375,.515625])
def test_refinement_checks_both_directions_under_real_constraints(target):
    def sample(x):
        margin=.01 if x[0]==0 or x[1]==target else -.1
        return dict(vectors=np.zeros((1,3)),caps=np.ones(1),scales=np.ones(1),margins=np.array([margin,.5]),depths=np.array([.02-.01*x[0]]))
    point,report=refine(sample,[0.,0.],[.5,.5],[0.,1.],coarse_divisions=8,witness_start=0,witness_count=1,divisions=8)
    np.testing.assert_array_equal(point,[.5,target])
    assert len(report['branches'])==2 and report['numerically_feasible']
    assert not report['quality_approved']
