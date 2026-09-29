import sys
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import box_root_optimizer as module


def parameter(value):return torch.tensor(value,dtype=torch.float64,requires_grad=True)


def test_coupled_rotation_and_root_reach_known_box_constrained_optimum():
    rotation=parameter([0.,0.]);root=parameter([.000022,.000022]);optimizer=module.BoxRootOptimizer(rotation,root,.22,100)
    samples=[]
    def closure():
        optimizer.zero_grad();samples.append(root.detach().clone())
        loss=((rotation-root-parameter([.3,-.2]).detach())**2).sum()+((root-parameter([-.1,.5]).detach())**2).sum()
        loss.backward();return loss
    optimizer.step(closure)
    torch.testing.assert_close(root,parameter([0.,.22]),atol=1e-7,rtol=0)
    torch.testing.assert_close(rotation,parameter([.3,.02]),atol=1e-7,rtol=0)
    assert all(bool(((r>=0)&(r<=.22)).all()) for r in samples)
    assert optimizer.summary['success'] and not optimizer.summary['quality_approved']
    assert optimizer.summary['projected_gradient_inf']<1e-7


def test_restore_accepted_point_after_rejected_probe(monkeypatch):
    from types import SimpleNamespace
    rotation=parameter([0.]);root=parameter([.01]);optimizer=module.BoxRootOptimizer(rotation,root,.22,2)
    def fake_minimize(fun,initial,**kwargs):
        fun(np.array([2.,.1]))
        return SimpleNamespace(x=np.array([1.,.02]),jac=np.zeros(2),fun=0.,success=False,status=1,message='iteration budget',nit=2,nfev=1)
    monkeypatch.setattr(module,'minimize',fake_minimize)
    def closure():
        optimizer.zero_grad();loss=(rotation**2).sum()+(root**2).sum();loss.backward();return loss
    optimizer.step(closure)
    assert rotation.item()==1. and root.item()==.02
    assert not optimizer.summary['success'] and optimizer.summary['status']==1


def test_nonfinite_objective_and_outside_parameters_are_rejected():
    with pytest.raises(ValueError,match='bounds'):module.BoxRootOptimizer(parameter([0.]),parameter([-.01]),.22,2)
    with pytest.raises(ValueError,match='float64'):module.BoxRootOptimizer(torch.zeros(1,requires_grad=True),parameter([.01]),.22,2)
    optimizer=module.BoxRootOptimizer(parameter([0.]),parameter([.01]),.22,2)
    with pytest.raises(ValueError,match='bounds'):optimizer.assign(np.array([0.,.23]))
    with pytest.raises(ValueError,match='Nonfinite'):optimizer.step(lambda:torch.tensor(float('nan')))
