import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from scaled_frame_restoration import scaled_energy,solve
from probe_restoration_derivatives import probe


def test_entire_objective_and_gradient_share_one_positive_scale():
    objective=lambda x:(x@x,2*x)
    y=np.array([.1,-.2,.7]);base=scaled_energy(objective,23.,1.)
    fn=scaled_energy(objective,23.,1000.)
    value,jac=fn(y);old,oldjac=base(y)
    assert value*1000==pytest.approx(old)
    np.testing.assert_allclose(jac*1000,oldjac)
    eps=1e-6
    finite=np.array([(fn(y+np.eye(3)[i]*eps)[0]-fn(y-np.eye(3)[i]*eps)[0])/(2*eps) for i in range(3)])
    np.testing.assert_allclose(jac,finite,atol=1e-10)


@pytest.mark.parametrize('scale',[1.,1000.])
def test_known_constrained_optimum_and_hard_limit(scale):
    result=solve(lambda x:((x[0]-.2)**2,np.array([2*(x[0]-.2)])),
        lambda x:(np.array([.1-x[0]]),np.array([[-1.]])),[0],[-1],[1],[],scale)
    assert result.success and result.x[0]==pytest.approx(.1,abs=1e-8)
    assert result.restoration_slack_m==0
    assert result.solver_ftol==1e-9/scale


@pytest.mark.parametrize('scale',[0.,-1.,float('nan'),float('inf'),1001.])
def test_invalid_scales_rejected(scale):
    with pytest.raises(ValueError):solve(lambda x:(x@x,2*x),lambda x:(np.array([1.]),np.zeros((1,1))),[0],[-1],[1],[],scale)


def test_directional_probe_detects_wrong_derivatives():
    objective=lambda x:(x@x,2*x)
    inequalities=lambda x:(np.array([np.sin(x[0]),1.-x@x]),np.array([[np.cos(x[0]),0.],-2*x]))
    states=[('test',np.array([.2,.3]))]
    correct=probe(objective,inequalities,states)
    assert correct['passed'] and len(correct['rows'])==21
    assert not probe(lambda x:(x@x,3*x),inequalities,states)['passed']
    assert not probe(objective,lambda x:(inequalities(x)[0],inequalities(x)[1]+.1),states)['passed']
