"""Differentiable local relative-rotation rate-step diagnostics."""
import torch


def rotation_log(matrix):
    vector=.5*torch.stack([matrix[...,2,1]-matrix[...,1,2],matrix[...,0,2]-matrix[...,2,0],matrix[...,1,0]-matrix[...,0,1]],dim=-1)
    sine2=(vector*vector).sum(-1);sine=torch.sqrt(sine2.clamp_min(1e-24));cosine=(matrix.diagonal(dim1=-2,dim2=-1).sum(-1)-1)*.5
    if bool(torch.any((cosine<0)&(sine2<1e-12)).detach()):raise ValueError('Near-pi local step is outside this diagnostic domain')
    coefficient=torch.atan2(sine,cosine)/sine
    small=(sine2<1e-8)&(cosine>0)
    coefficient=torch.where(small,1+sine2/6+3*sine2*sine2/40,coefficient)
    return coefficient[...,None]*vector


def angular_steps(local,fps=30.):
    relative=local[:-1].transpose(-1,-2)@local[1:]
    rates=rotation_log(relative)*fps
    return torch.linalg.vector_norm(rates[1:]-rates[:-1],dim=-1)
