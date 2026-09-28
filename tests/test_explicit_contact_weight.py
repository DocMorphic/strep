import sys
from pathlib import Path
import torch
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from support_contact_v3 import contact_losses


def test_one_frame_target_not_diluted_by_long_inferred_contact():
    for frames in [10,1000]:
        errors=torch.ones((frames,3),dtype=torch.float64,requires_grad=True)
        weights=torch.ones_like(errors);weights[:,2]=0;weights[5,2]=.2
        inferred,authored=contact_losses(errors,weights,torch.tensor([False,False,True]))
        assert inferred.item()==pytest.approx(1)
        assert authored.item()==pytest.approx(1)
        authored.backward();assert errors.grad[5,2].item()==pytest.approx(1)
        assert errors.grad[:,:2].abs().sum()==0


def test_authored_regions_equal_weight_and_empty_groups_finite():
    errors=torch.tensor([[1.,4.],[1.,4.],[1.,4.]])
    weights=torch.tensor([[1.,1.],[1.,0.],[1.,0.]])
    inferred,authored=contact_losses(errors,weights,torch.tensor([True,True]))
    assert inferred==0
    assert authored.item()==pytest.approx(2.5)
    a,b=contact_losses(errors,weights*0,torch.tensor([False,True]))
    assert a==0 and b==0
