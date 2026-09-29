"""Compare exact full-mesh sparse skin values and gradients to gathered LBS."""
import argparse
import time
from pathlib import Path
import numpy as np
import torch
from strep import ROOT,save,sha256
from build_soma_preview import ASSET
from floor_contact import Surface
from linear_skin_operator import LinearSkinOperator


def run(motion_path,output):
    motion_path,output=Path(motion_path),Path(output)
    if output.exists():raise ValueError('Fresh report path required')
    torch.set_num_threads(2)
    motion=dict(np.load(motion_path,allow_pickle=False));skin=dict(np.load(ASSET,allow_pickle=False));surface=Surface(skin)
    ids=torch.tensor(skin['lbs_indices'],dtype=torch.long);weights=torch.tensor(skin['lbs_weights'],dtype=torch.float64)
    bind=torch.tensor(np.einsum('vwij,vj->vwi',surface.inverse[skin['lbs_indices']],surface.points)[:,:,:3],dtype=torch.float64)
    sparse=LinearSkinOperator(ids,weights,bind,len(skin['rig_joint_names']))
    maximum_position=0.;maximum_gradient=0.;timings=dict(gather=0.,sparse=0.)
    generator=torch.Generator().manual_seed(1771)
    for start in range(0,len(motion['posed_joints']),5):
        r=torch.tensor(motion['global_rot_mats'][start:start+5],dtype=torch.float64,requires_grad=True)
        p=torch.tensor(motion['posed_joints'][start:start+5],dtype=torch.float64,requires_grad=True)
        cotangent=torch.randn(len(r),len(ids),3,dtype=torch.float64,generator=generator)
        results=[];gradients=[]
        for mode in timings:
            began=time.perf_counter()
            v=((((r[:,ids]@bind[None,...,None]).squeeze(-1)+p[:,ids])*weights[None,...,None]).sum(2)
               if mode=='gather' else sparse(r,p))
            gradients.append(torch.autograd.grad((v*cotangent).sum(),(r,p)))
            timings[mode]+=time.perf_counter()-began;results.append(v.detach())
        maximum_position=max(maximum_position,float((results[0]-results[1]).abs().max()))
        maximum_gradient=max(maximum_gradient,max(float((a-b).abs().max()) for a,b in zip(*gradients)))
    # Also exercise the actual full-frame layout without materializing its
    # enormous gathered reference. Equivalence above covers every frame.
    r=torch.tensor(motion['global_rot_mats'],dtype=torch.float64,requires_grad=True)
    p=torch.tensor(motion['posed_joints'],dtype=torch.float64,requires_grad=True)
    began=time.perf_counter();v=sparse(r,p);g=torch.autograd.grad(v.square().mean(),(r,p))
    elapsed=time.perf_counter()-began
    if maximum_position>1e-12 or maximum_gradient>1e-10 or not all(torch.isfinite(x).all() for x in g):
        raise ValueError('Sparse skin values or derivatives differ from reference')
    report=dict(motion_sha256=sha256(motion_path),skin_sha256=sha256(ASSET),
                implementation_sha256=sha256(ROOT/'scripts/linear_skin_operator.py'),verifier_sha256=sha256(__file__),
                frames=len(r),vertices=len(ids),influences=ids.shape[1],maximum_position_difference_m=maximum_position,
                maximum_gradient_difference=maximum_gradient,chunked_forward_backward_seconds=timings,
                full_sparse_forward_backward_seconds=elapsed,operator_nonzero_coefficients=sparse.operator._nnz(),
                scope='All native input frames and full mesh; affine-transform gradients with fixed random cotangents. Timing is one local kernel run, not a solver speed or peak-memory claim.')
    save(output,report);print(report,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('motion',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.motion,a.output)
