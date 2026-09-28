"""Matched coarse/refined proposal comparison on identical measured surface planes."""
import argparse
from pathlib import Path
import numpy as np
from scipy.linalg import block_diag
from threadpoolctl import threadpool_limits
from strep import read,save,sha256,now
from load_contact_trial import load
from frame_guarded_partner_step import solve


def run(study,output):
    if output.exists():raise ValueError('Preserve previous diagnostic')
    request=read(study/'request.json');warm=Path(request['warm']);_,fitter,_,_=load(request['source'])
    x=np.asarray(read(warm/'parameters.json')['controls']);data=np.load(study/'linearization.npz')
    new=np.asarray(request['embedding']['refined_knots']);old=np.asarray(fitter.knots)
    interpolation=np.stack([np.interp(new,old,np.eye(len(old))[i]) for i in range(len(old))],axis=1)
    P=block_diag(*[np.kron(interpolation,np.eye(a.dim)) for a in fitter.base.actors])
    if not np.allclose(P@x,data['base'],atol=1e-14,rtol=0):raise ValueError('Warm controls differ')
    edge=block_diag(*[np.diff(m.reshape(150,12,size),axis=0).reshape(-1,size) for m,size in zip(fitter.maps,fitter.sizes)])
    if not np.allclose(data['edge_map']@P,edge,atol=1e-14,rtol=0):raise ValueError('Coarse and refined edge operators differ')
    locked=np.concatenate([np.repeat(fitter.matrix[fitter.event]!=0,a.dim) for a in fitter.base.actors]);rows=[]
    with threadpool_limits(limits=1):
        for trust in request['trust_degrees']:
            c,info=solve(x,data['gaps'],data['jacobian']@P,data['caps'],locked,fitter.control_radii,edge,np.radians(trust))
            rows.append(dict(trust_degrees=trust,coarse=info,controls=c.tolist() if c is not None else None))
    save(output,dict(at=now(),source_request_sha256=sha256(study/'request.json'),linearization_sha256=sha256(study/'linearization.npz'),
        rows=rows,quality_approved=False,scope='Same warm motion, frozen rows/caps and trust radii. Coarse constraints mapped exactly into refined controls. Linear predictions only; fresh geometry and finite-step curvature may differ. No lower bound on the nonlinear motion problem.'))
    print([(r['trust_degrees'],r['coarse']['predicted_peak_m']) for r in rows])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.study.resolve(),a.output.resolve())
