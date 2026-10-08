import sys
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from object_playback_checkpoint import query_chunks,validate_chunk_frames
from object_geometry import Geometry
from linear_skin_operator import LinearSkinOperator
from support_contact_v8 import torch_primitive_clearance_violation,object_constraint_residuals


def fixture():
    generator=torch.Generator().manual_seed(6611)
    frames=11;indices=torch.randint(0,3,(17,8),generator=generator)
    weights=torch.rand(17,8,dtype=torch.float64,generator=generator);weights/=weights.sum(-1,keepdim=True)
    bind=torch.randn(17,8,3,dtype=torch.float64,generator=generator)*.015
    skin=LinearSkinOperator(indices,weights,bind,3)
    r=torch.eye(3,dtype=torch.float64).expand(frames,3,3,3).clone().requires_grad_()
    p=(torch.randn(frames,3,3,dtype=torch.float64,generator=generator)*.01).requires_grad_()
    # All shapes and different motion/buffer slices expose late-bound closures.
    queries=[]
    for i,geometry in enumerate([Geometry('box',(.04,.05,.06)),Geometry('sphere',(.022,)),Geometry('cylinder',(.025,.045))]):
        op=torch.zeros(frames,3,dtype=torch.float64);op[:,0]=torch.arange(frames)*.002+i*.003
        orr=torch.eye(3,dtype=torch.float64).expand(frames,3,3).clone()
        margin=torch.full((frames,17),.002,dtype=torch.float64);margin[3:8,:4]=0.
        queries.append((op,orr,geometry,margin))
    return r,p,skin,queries


@pytest.mark.parametrize('mode',['maximum','per_vertex'])
@pytest.mark.parametrize('chunk_frames',[1,4,32])
def test_complete_values_and_weighted_gradients_match_dense_without_changing_inputs(mode,chunk_frames):
    r,p,skin,queries=fixture();before=[(x[0].clone(),x[1].clone(),x[3].clone()) for x in queries]
    vertices=skin(r,p)
    reference=[object_constraint_residuals(torch_primitive_clearance_violation(vertices,op,orr,g,m),mode) for op,orr,g,m in queries]
    actual=query_chunks(r,p,skin,queries,torch_primitive_clearance_violation,object_constraint_residuals,mode,chunk_frames)
    assert len(actual)==len(reference)==3
    for a,b in zip(actual,reference):torch.testing.assert_close(a,b,atol=1e-14,rtol=1e-13)
    def loss(values):
        return sum((i+1)*(x*torch.arange(1,x.numel()+1,dtype=x.dtype).reshape(x.shape)).square().mean() for i,x in enumerate(values))
    old=torch.autograd.grad(loss(reference),(r,p),retain_graph=True)
    new=torch.autograd.grad(loss(actual),(r,p))
    for a,b in zip(old,new):
        assert torch.isfinite(b).all();torch.testing.assert_close(a,b,atol=1e-10,rtol=1e-12)
    for query,snapshot in zip(queries,before):
        for a,b in zip([query[0],query[1],query[3]],snapshot):torch.testing.assert_close(a,b,atol=0,rtol=0)


@pytest.mark.parametrize('defect',['missing_pose','trainable_pose','missing_buffer','trainable_buffer','empty_queries','zero_chunk'])
def test_invalid_or_mutable_checkpoint_queries_reject(defect):
    r,p,skin,queries=fixture();op,orr,g,margin=queries[0];chunk=4
    if defect=='missing_pose':op=op[:-1]
    if defect=='trainable_pose':op=op.requires_grad_()
    if defect=='missing_buffer':margin=margin[:-1]
    if defect=='trainable_buffer':margin=margin.requires_grad_()
    queries[0]=(op,orr,g,margin)
    if defect=='empty_queries':queries=[]
    if defect=='zero_chunk':chunk=0
    with pytest.raises(ValueError):query_chunks(r,p,skin,queries,torch_primitive_clearance_violation,object_constraint_residuals,'maximum',chunk)


@pytest.mark.parametrize('chunk',[True,-1,257,1.5,'32'])
def test_invalid_chunk_configuration_rejects(chunk):
    with pytest.raises(ValueError):validate_chunk_frames(chunk)


@pytest.mark.parametrize('extra',[
    dict(object_playback_checkpoint_frames=32),
    dict(object_playback_checkpoint_frames=True),
    dict(object_playback_checkpoint_frames=32,object_inequalities=True)])
def test_recomputation_cannot_silently_enable_without_intermediate_object_constraints(extra):
    from support_contact_v8 import refine
    with pytest.raises(ValueError):refine({}, {}, {},**extra)
