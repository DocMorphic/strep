"""Differentiable proxy for the native exporter's linear-TRS joint trajectory.

Uses float32 key times and shortest-path quaternion interpolation like the GLB
sampler. Channel-value quantization and native reconstruction rounding remain
outside this proxy; independently audit actual exported files after fitting.
"""
import torch


def matrix_quaternion(matrix):
    """Unit wxyz quaternion, using the largest component for stable division."""
    m=matrix
    values=torch.stack([1+m[...,0,0]+m[...,1,1]+m[...,2,2],
                        1+m[...,0,0]-m[...,1,1]-m[...,2,2],
                        1-m[...,0,0]+m[...,1,1]-m[...,2,2],
                        1-m[...,0,0]-m[...,1,1]+m[...,2,2]],-1)
    s=2*torch.sqrt(values.clamp_min(1e-12))
    candidates=torch.stack([
        torch.stack([s[...,0]/4,(m[...,2,1]-m[...,1,2])/s[...,0],(m[...,0,2]-m[...,2,0])/s[...,0],(m[...,1,0]-m[...,0,1])/s[...,0]],-1),
        torch.stack([(m[...,2,1]-m[...,1,2])/s[...,1],s[...,1]/4,(m[...,0,1]+m[...,1,0])/s[...,1],(m[...,0,2]+m[...,2,0])/s[...,1]],-1),
        torch.stack([(m[...,0,2]-m[...,2,0])/s[...,2],(m[...,0,1]+m[...,1,0])/s[...,2],s[...,2]/4,(m[...,1,2]+m[...,2,1])/s[...,2]],-1),
        torch.stack([(m[...,1,0]-m[...,0,1])/s[...,3],(m[...,0,2]+m[...,2,0])/s[...,3],(m[...,1,2]+m[...,2,1])/s[...,3],s[...,3]/4],-1)],-2)
    index=values.argmax(-1)[...,None,None].expand(*values.shape[:-1],1,4)
    q=candidates.gather(-2,index).squeeze(-2)
    return q/torch.linalg.vector_norm(q,dim=-1,keepdim=True)


def quaternion_matrix(q):
    q=q/torch.linalg.vector_norm(q,dim=-1,keepdim=True)
    w,x,y,z=q.unbind(-1)
    return torch.stack([1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),
                        2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),
                        2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)],-1).reshape(*q.shape[:-1],3,3)


def slerp(a,b,t):
    a=a/torch.linalg.vector_norm(a,dim=-1,keepdim=True)
    b=b/torch.linalg.vector_norm(b,dim=-1,keepdim=True)
    dot=(a*b).sum(-1,keepdim=True)
    b=torch.where(dot<0,-b,b);dot=dot.abs()
    # The unused curved branch must also have finite derivatives at identity.
    angle=torch.acos(dot.clamp(0,1-torch.finfo(dot.dtype).eps))
    curved=(torch.sin((1-t)*angle)*a+torch.sin(t*angle)*b)/torch.sin(angle)
    result=torch.where(dot>1-5e-13,(1-t)*a+t*b,curved)
    return result/torch.linalg.vector_norm(result,dim=-1,keepdim=True)


def joint_trajectory(rotations,positions,parents,subdivisions=4,fps=30,*,return_rotations=False):
    if type(return_rotations)!=bool:raise ValueError('Explicit rotation-return boolean required')
    if rotations.ndim!=4 or rotations.shape[-2:]!=(3,3) or positions.shape!=rotations.shape[:2]+(3,):
        raise ValueError('Matching frame/joint rotation and position arrays required')
    if rotations.dtype!=torch.float64 or positions.dtype!=torch.float64:
        raise ValueError('Float64 is required for differentiable export-clock metrics')
    frames,joints=positions.shape[:2]
    if frames<2 or len(parents)!=joints or any(p>=j or p < -1 for j,p in enumerate(parents)):
        raise ValueError('At least two frames and a parent-first skeleton required')
    if type(subdivisions)!=int or subdivisions<1 or type(fps) not in [int,float] or not 0<fps<1000:
        raise ValueError('Positive sample subdivision and finite frame rate required')
    local_r=[];local_p=[]
    for j,parent in enumerate(parents):
        if parent<0:local_r.append(rotations[:,j]);local_p.append(positions[:,j])
        else:
            inverse=rotations[:,parent].transpose(-1,-2)
            local_r.append(inverse@rotations[:,j])
            local_p.append((inverse@(positions[:,j]-positions[:,parent])[...,None]).squeeze(-1))
    quaternions=matrix_quaternion(torch.stack(local_r,1));translation=torch.stack(local_p,1)
    key_times=(torch.arange(frames,dtype=torch.float32,device=positions.device)/fps).to(positions.dtype)
    times=torch.arange((frames-1)*subdivisions+1,dtype=positions.dtype,device=positions.device)/(subdivisions*fps)
    left=(torch.searchsorted(key_times,times,right=True)-1).clamp(0,frames-2)
    fraction=((times-key_times[left])/(key_times[left+1]-key_times[left])).clamp(0,1)[:,None,None]
    r=quaternion_matrix(slerp(quaternions[left],quaternions[left+1],fraction))
    p=translation[left]*(1-fraction)+translation[left+1]*fraction
    world_r=[];world_p=[]
    for j,parent in enumerate(parents):
        if parent<0:world_r.append(r[:,j]);world_p.append(p[:,j])
        else:
            world_r.append(world_r[parent]@r[:,j])
            world_p.append(world_p[parent]+(world_r[parent]@p[:,j,:,None]).squeeze(-1))
    positions=torch.stack(world_p,1)
    return (torch.stack(world_r,1),positions) if return_rotations else positions


def motion_rates(trajectory,fps=30,subdivisions=4):
    frequency=fps*subdivisions
    return (torch.linalg.vector_norm(torch.diff(trajectory,dim=0)*frequency,dim=-1),
            torch.linalg.vector_norm(torch.diff(trajectory,n=2,dim=0)*frequency**2,dim=-1))
