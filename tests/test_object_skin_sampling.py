import sys
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from support_contact_v8 import object_sampling_layout,torch_primitive_clearance_violation
from object_geometry import Geometry


def test_full_object_sample_detects_omitted_vertex_without_changing_floor_penalty():
    # The omitted point penetrates the box and has a lower floor height.
    world=torch.tensor([[[2.,1.,0.],[0.,-.1,0.],[2.,2.,0.]]],dtype=torch.float64,requires_grad=True)
    old,floor_old=object_sampling_layout({0,2},3,False)
    full,floor_full=object_sampling_layout({0,2},3,True)
    np.testing.assert_array_equal(full[floor_full],old[floor_old])
    position=torch.zeros((1,3),dtype=torch.float64);rotation=torch.eye(3,dtype=torch.float64)[None]
    geometry=Geometry('box',(1.,1.,1.))
    assert torch_primitive_clearance_violation(world[:,old],position,rotation,geometry,.002).max()<0
    assert torch_primitive_clearance_violation(world[:,full],position,rotation,geometry,.002).max()>.4
    losses=[torch.relu(.002-world[:,ids[floor],1]).square().amax(1).mean() for ids,floor in [(old,floor_old),(full,floor_full)]]
    assert losses[0].item()==losses[1].item()==0
    assert torch.relu(.002-world[:,full,1]).square().max()>0


@pytest.mark.parametrize('ids,total,full',[([0,0],3,True),([-1],3,True),([3],3,True),([.5],3,True),([0],3,1)])
def test_bad_sampling_request_fails_closed(ids,total,full):
    with pytest.raises(ValueError):object_sampling_layout(ids,total,full)
