import sys
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pose_row_jacobian import row_jacobian


@pytest.mark.parametrize('chunk',[1,2,16,32])
def test_each_row_matches_scalar_backward_including_maximum_ties(chunk):
    x=torch.tensor([.2,.2,-.1],dtype=torch.float64,requires_grad=True)
    rows=torch.stack([x.square().sum(),x.max(),x.min(),x[0]*x[2],torch.sin(x[1]),x[2]*0])
    scalar=np.array([torch.autograd.grad(row,x,retain_graph=True)[0].detach().numpy() for row in rows])
    np.testing.assert_allclose(row_jacobian(rows,x,chunk),scalar,atol=1e-14,rtol=1e-14)
    assert x.grad is None


@pytest.mark.parametrize('chunk',[0,33,True,1.5])
def test_invalid_chunk_is_rejected_before_backward(chunk):
    x=torch.zeros(3,dtype=torch.float64,requires_grad=True)
    with pytest.raises(ValueError):row_jacobian(x.square(),x,chunk)


@pytest.mark.parametrize('kind',['empty','nonfinite','single','float32','detached'])
def test_invalid_population_is_rejected(kind):
    x=torch.zeros(3,dtype=torch.float64,requires_grad=True);rows=x.square()
    if kind=='empty':rows=rows[:0]
    if kind=='nonfinite':rows=rows*float('nan')
    if kind=='single':rows=rows.sum()
    if kind=='float32':rows=rows.float()
    if kind=='detached':rows=rows.detach()
    with pytest.raises(ValueError):row_jacobian(rows,x)
