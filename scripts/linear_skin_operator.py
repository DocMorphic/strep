"""Constant sparse LBS operator, retaining all nonzero skin influences.

Maps global affine joint transforms to posed vertices without gathering a
frame/vertex/influence array of 3x3 matrices. No geometry is approximated.
"""
import torch


class LinearSkinOperator:
    def __init__(self, indices, weights, bind_points, joint_count):
        if indices.ndim!=2 or weights.shape!=indices.shape or bind_points.shape!=indices.shape+(3,):
            raise ValueError('Matching vertex/influence indices, weights and bind points required')
        if indices.dtype!=torch.long or type(joint_count)!=int or joint_count<1:
            raise ValueError('Long joint indices and a positive joint count required')
        if indices.numel()==0 or indices.min()<0 or indices.max()>=joint_count:
            raise ValueError('Skin influence joint is out of range')
        if weights.dtype!=bind_points.dtype or weights.device!=bind_points.device or indices.device!=weights.device:
            raise ValueError('Skin tensors must share dtype and device')
        if not weights.is_floating_point() or not torch.isfinite(weights).all() or not torch.isfinite(bind_points).all():
            raise ValueError('Finite floating skin coefficients required')
        if weights.requires_grad or bind_points.requires_grad:
            raise ValueError('Skin bind data must be constant')
        vertex_count=indices.shape[0]
        rows=torch.arange(vertex_count,device=indices.device)[:,None,None].expand(*indices.shape,4)
        columns=indices[...,None]*4+torch.arange(4,device=indices.device)
        values=weights[...,None]*torch.cat([bind_points,torch.ones_like(weights[...,None])],-1)
        nonzero=values!=0
        self.operator=torch.sparse_coo_tensor(torch.stack([rows[nonzero],columns[nonzero]]),values[nonzero],
                                              (vertex_count,joint_count*4)).coalesce()
        self.joint_count=joint_count

    def __call__(self, rotations, positions):
        if rotations.ndim!=4 or rotations.shape[1:]!=(self.joint_count,3,3) or positions.shape!=rotations.shape[:2]+(3,):
            raise ValueError('Matching frame/joint transforms required')
        affine=torch.cat([rotations,positions[...,None]],-1)
        columns=affine.permute(1,3,0,2).reshape(self.joint_count*4,-1)
        return torch.sparse.mm(self.operator,columns).reshape(-1,len(rotations),3).permute(1,0,2)
