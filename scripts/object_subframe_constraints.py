"""Differentiable local-quaternion playback between authored pose keys.

Root/joint translations interpolate linearly; local rotations follow shortest
quaternion arcs before hierarchical FK. This does not interpolate global poses.
"""
import torch


def matrix_quaternions(values):
    """Real-first quaternions with finite derivatives in unselected branches.

    Select the largest component of a proper rotation. Its squared numerator
    is at least one; flooring other square roots therefore leaves that branch
    unchanged while avoiding the infinite derivative of sqrt(0).
    """
    m00,m01,m02,m10,m11,m12,m20,m21,m22=values.reshape(values.shape[:-2]+(9,)).unbind(-1)
    squared=torch.stack((1+m00+m11+m22,1+m00-m11-m22,
                         1-m00+m11-m22,1-m00-m11+m22),-1)
    absolute=squared.clamp(min=torch.finfo(values.dtype).eps).sqrt()
    candidates=torch.stack((
        torch.stack((squared[...,0],m21-m12,m02-m20,m10-m01),-1),
        torch.stack((m21-m12,squared[...,1],m10+m01,m02+m20),-1),
        torch.stack((m02-m20,m10+m01,squared[...,2],m12+m21),-1),
        torch.stack((m10-m01,m20+m02,m21+m12,squared[...,3]),-1)), -2)
    candidates=candidates/(2*absolute[...,None])
    index=absolute.argmax(-1)[...,None,None].expand(values.shape[:-2]+(1,4))
    return candidates.gather(-2,index).squeeze(-2)


def clock(frames, divisions, device=None):
    if type(frames) is not int or frames<2 or type(divisions) is not int or not 2<=divisions<=8:
        raise ValueError('Complete clock and 2–8 object interpolation divisions required')
    left=torch.arange(frames-1,device=device).repeat_interleave(divisions-1)
    fraction=torch.arange(1,divisions,device=device,dtype=torch.float64).repeat(frames-1)/divisions
    return left,fraction


def linear(values, left, fraction):
    a=fraction.to(dtype=values.dtype).reshape((-1,)+(1,)*(values.ndim-1))
    return values[left]*(1-a)+values[left+1]*a


def rotations(values, left, fraction):
    from kimodo.geometry import quaternion_to_matrix
    q=matrix_quaternions(values);q=q/torch.linalg.vector_norm(q,dim=-1,keepdim=True)
    first,last=q[left],q[left+1];dot=(first*last).sum(-1,keepdim=True)
    last=torch.where(dot<0,-last,last);dot=dot.abs().clamp(max=1-max(torch.finfo(values.dtype).eps,1e-12))
    angle=torch.acos(dot);a=fraction.to(dtype=values.dtype).reshape((-1,)+(1,)*(first.ndim-1))
    q=(torch.sin((1-a)*angle)*first+torch.sin(a*angle)*last)/torch.sin(angle)
    q=q/torch.linalg.vector_norm(q,dim=-1,keepdim=True)
    return quaternion_to_matrix(q)


def poses(local, offsets, root_positions, parents, left, fraction):
    if (local.ndim!=4 or local.shape[-2:]!=(3,3) or offsets.shape!=local.shape[:2]+(3,)
            or root_positions.shape!=(len(local),3) or not local.shape[1] or len(parents)!=local.shape[1]
            or parents[0]!=-1 or any(type(p) not in (int,) or not 0<=p<j for j,p in enumerate(parents[1:],1))):
        raise ValueError('Topologically ordered single-root native hierarchy required')
    local=rotations(local,left,fraction);offsets=linear(offsets,left,fraction);root=linear(root_positions,left,fraction)
    r=[];p=[]
    for j,parent in enumerate(parents):
        if parent<0:r.append(local[:,j]);p.append(root)
        else:r.append(r[parent]@local[:,j]);p.append(p[parent]+(r[parent]@offsets[:,j,:,None]).squeeze(-1))
    return torch.stack(r,1),torch.stack(p,1)
