import sys
from pathlib import Path
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from export_rate_objective import ExportRateObjective


def fixture():
    rotations=torch.eye(3,dtype=torch.float64).repeat(3,1,1,1)
    positions=torch.tensor([[[0.,0.,0.]],[[.01,0.,0.]],[[.04,0.,0.]]],dtype=torch.float64)
    return rotations,positions


def test_source_ceiling_and_increased_rates_have_correct_gradients():
    r,p=fixture();objective=ExportRateObjective(r,p,[-1])
    assert objective.loss(r,p)==0
    scaled=(p*1.2).requires_grad_()
    loss=objective.loss(r,scaled)
    assert loss>0
    assert torch.autograd.gradcheck(lambda x:objective.loss(r,x),(scaled,),atol=1e-3)
    objective.loss(r,scaled)
    assert all(g.max()>0 for g in objective.last)
    before=[m.clone() for m in objective.multipliers]
    objective.advance_stage(4.)
    assert all((m>b).any() for m,b in zip(objective.multipliers,before))
    assert objective.record()['penalty']==40.


def test_margin_tightens_acceleration_only_and_preserves_reference():
    r,p=fixture();original=p.clone();objective=ExportRateObjective(r,p,[-1],.01)
    assert objective.ceilings[0]==objective.reference_peaks[0]
    assert objective.ceilings[1]==objective.reference_peaks[1]*.99
    assert objective.loss(r,p)>0
    assert torch.equal(p,original)


def test_static_reference_is_finite_and_rejects_new_movement():
    r,p=fixture();p.zero_();objective=ExportRateObjective(r,p,[-1])
    p.requires_grad_();loss=objective.loss(r,p)
    assert loss==0
    assert torch.isfinite(torch.autograd.grad(loss,p)[0]).all()
    moving=p.detach().clone();moving[1,0,0]=.001
    assert objective.loss(r,moving)>0


@pytest.mark.parametrize('margin',[-.01,1.,float('inf'),float('nan'),True])
def test_invalid_margin_rejected(margin):
    r,p=fixture()
    with pytest.raises(ValueError):ExportRateObjective(r,p,[-1],margin)


def test_multiplier_update_requires_accepted_evaluation():
    r,p=fixture()
    with pytest.raises(ValueError):ExportRateObjective(r,p,[-1]).advance_stage(4.)
