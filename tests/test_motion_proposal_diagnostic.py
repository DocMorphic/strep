import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from motion_proposal_diagnostic import compare


def sample(value):
    return dict(vectors=np.array([[value,0.,0.]]),caps=np.ones(1),scales=np.ones(1),margins=np.ones(1),depths=np.ones(1))


def run(exact,smooth,jac=.1):
    model=dict(base=exact(np.zeros(1)),point=np.zeros(1),jacobian=dict(vectors=np.array([[[jac],[0.],[0.]]])))
    return compare(model,exact,smooth,[1.],[1.],lambda i:dict(kind='test'))


def test_changed_serialization_error_is_separated_from_curvature():
    result=run(lambda x:sample(.8+.1*x[0]+(.2 if x[0] else 0)),lambda x:sample(.7+.1*x[0]))
    row=result['trials'][0]
    assert row['serialization_only_failures']==[0] and not row['curvature_only_failures']
    assert row['rows'][0]['serialization_change_error']==pytest.approx(.2)
    assert row['rows'][0]['curvature_vector_error']==pytest.approx(0.)
    assert not result['accepted_for_publication']


def test_curvature_is_separate_from_serialization():
    fn=lambda x:sample(.8+.1*x[0]+.2*x[0]**2)
    row=run(fn,fn)['trials'][0]
    assert row['curvature_only_failures']==[0] and not row['serialization_only_failures']
    assert row['rows'][0]['curvature_vector_error']==pytest.approx(.2)


def test_constant_rounding_offset_does_not_become_false_error():
    result=run(lambda x:sample(.8+.1*x[0]),lambda x:sample(.9+.1*x[0]))
    row=result['trials'][0]
    assert row['groups']['smooth_increment']['failed_rows']==0
    assert row['groups']['serialized']['failed_rows']==0


def test_rebased_caps_rejected():
    def smooth(x):
        value=sample(.8);value['caps']*=2;return value
    with pytest.raises(ValueError,match='Original populations'):run(lambda x:sample(.8),smooth)


def test_saved_seed_must_reproduce():
    with pytest.raises(AssertionError):
        compare(dict(base=sample(.8),point=np.zeros(1),jacobian=dict(vectors=np.zeros((1,3,1)))),
            lambda x:sample(.9),lambda x:sample(.9),[.1],[1.],lambda i:{})
