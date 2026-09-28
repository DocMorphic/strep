"""Check whether a failed angular preflight crossed a hover minimum branch."""
import argparse
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from strep import read,save,sha256,now
from study_projected_angular_release import problem_for
from check_piecewise_derivative import check_direction


def signature(p,x):
    values=p.values(x);active=[]
    for frame in p.frames:
        positions=p.fitter.surface_jacobian(int(frame),values[frame])[0]
        active.extend(int(ids[np.argmin(positions[ids,1])]) for side,ids in enumerate(p.patches) if p.envelope['active_frames'][frame][side])
    return active


def run(folder,output):
    if output.exists():raise ValueError('Preserve prior diagnostic')
    with threadpool_limits(limits=1):
        p=problem_for(read(folder/'request.json'),read(folder/'envelope.json'));x=p.initial[np.ix_(p.frames,p.free)].ravel();rng=np.random.default_rng(117);rows=[]
        for _ in range(3):
            d=rng.normal(size=len(x));d/=np.linalg.norm(d)
            rows.append(check_direction(lambda y:p.evaluate(y,False),lambda y:signature(p,y),x,d))
    result=dict(at=now(),request_sha256=sha256(folder/'request.json'),failed_proof_sha256=sha256(folder/'derivative-proof.json'),implementation_sha256=sha256(__file__),rows=rows,passed=all(r['passed'] for r in rows),quality_approved=False,
        scope='Same three seeded directions and fixed diagnostic steps1e-6 then1e-7; smaller step only when hover minimum vertex changes. No source, trial outcome, constraints or derivative tolerance changed.')
    save(output,result);print(result)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.folder.resolve(),a.output.resolve())
