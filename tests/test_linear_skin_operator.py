import sys
from pathlib import Path
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from linear_skin_operator import LinearSkinOperator


def fixture():
    generator=torch.Generator().manual_seed(831)
    ids=torch.randint(0,4,(7,8),generator=generator)
    weights=torch.rand(7,8,dtype=torch.float64,generator=generator)
    weights[:,3]=0;weights/=weights.sum(-1,keepdim=True)
    bind=torch.randn(7,8,3,dtype=torch.float64,generator=generator)
    r=torch.randn(3,4,3,3,dtype=torch.float64,generator=generator,requires_grad=True)
    p=torch.randn(3,4,3,dtype=torch.float64,generator=generator,requires_grad=True)
    return ids,weights,bind,r,p


def test_sparse_values_and_gradients_match_duplicate_and_zero_influences():
    ids,w,b,r,p=fixture();skin=LinearSkinOperator(ids,w,b,4)
    reference=(((r[:,ids]@b[None,...,None]).squeeze(-1)+p[:,ids])*w[None,...,None]).sum(2)
    actual=skin(r,p)
    torch.testing.assert_close(actual,reference,rtol=1e-12,atol=1e-12)
    cotangent=torch.arange(actual.numel(),dtype=r.dtype).reshape(actual.shape)/actual.numel()
    old=torch.autograd.grad((reference*cotangent).sum(),(r,p))
    new=torch.autograd.grad((actual*cotangent).sum(),(r,p))
    for a,b in zip(old,new):torch.testing.assert_close(a,b,rtol=1e-12,atol=1e-12)
    assert torch.autograd.gradcheck(skin,(r,p))


def test_invalid_or_trainable_bind_data_rejected():
    ids,w,b,r,p=fixture()
    for indices in [ids.float(),ids+4,ids-4]:
        with pytest.raises(ValueError):LinearSkinOperator(indices,w,b,4)
    with pytest.raises(ValueError):LinearSkinOperator(ids,w,b[:,:,:2],4)
    with pytest.raises(ValueError):LinearSkinOperator(ids,w.requires_grad_(),b,4)


def test_transform_layout_rejected():
    ids,w,b,r,p=fixture();skin=LinearSkinOperator(ids,w,b,4)
    with pytest.raises(ValueError):skin(r[:,:3],p[:,:3])
