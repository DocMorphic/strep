"""Small fixed solver parity experiment; not an animation quality study."""
import argparse
import copy
from pathlib import Path
import time
import numpy as np
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from profile_support_surface import load
from support_reference_fit import SupportReferenceFitter
from sparse_support_surface import SparseSupportReferenceFitter
from relax_whole_support import relax


def run(output):
    if output.exists():raise ValueError('Preserve previous parity experiment')
    proof=ROOT/'reports/sparse-support-surface-proof-v1.json'
    proof_data=read(proof)
    if not proof_data['passed']:raise ValueError('Missing surface proof')
    for path,digest in proof_data['implementation'].items():
        if sha256(path)!=digest:raise ValueError('Surface proof implementation changed')
    output.mkdir(parents=True)
    rows=[]
    for identifier,start in [('motion-026-rig-01',0),('motion-036-rig-01',14)]:
        folder=ROOT/'reports/whole-support-breadth-v1/takes'/identifier
        template,_=load(folder);stop=start+12
        spec=copy.deepcopy(template.spec);spec['frames']=12;spec['max_nfev']=12
        guides=copy.deepcopy(template.support_guides)
        for guide in guides.values():
            guide['weights']=guide['weights'][start:stop]
            guide['anchors_xz_m']=guide['anchors_xz_m'][start:stop]
        targets={k:np.asarray(v)[start:stop] for k,v in template.targets.items()}
        results={}
        for label,cls in [('dense',SupportReferenceFitter),('sparse',SparseSupportReferenceFitter)]:
            fitter=cls(template.rig,spec,template.local[start:stop],targets,np.ones(12),
                template.unplanted_reference[start:stop],guides=guides,support_weight=40.)
            initial=np.zeros((12,len(fitter.bounds)));begin=time.perf_counter()
            parameters,records,convergence=relax(fitter,initial,curvature_weight=10.,sweeps=2)
            seconds=time.perf_counter()-begin
            dest=output/identifier/label;dest.mkdir(parents=True)
            np.savez_compressed(dest/'parameters.npz',parameters=parameters)
            save(dest/'solver.json',records);save(dest/'convergence.json',convergence)
            results[label]=dict(parameters=parameters,records=records,convergence=convergence,seconds=seconds,
                hashes={name:sha256(dest/name) for name in ['parameters.npz','solver.json','convergence.json']})
        a,b=results['dense'],results['sparse']
        error=float(np.max(np.abs(a['parameters']-b['parameters'])))
        if error>1e-12 or a['records']!=b['records'] or a['convergence']!=b['convergence']:
            raise ValueError('Solver behavior changed')
        rows.append(dict(case=identifier,source_start_frame=start,frames=12,sweeps=2,max_nfev=12,
            maximum_parameter_difference=error,solver_records_identical=True,convergence_identical=True,
            dense_seconds=a['seconds'],sparse_seconds=b['seconds'],measured_solver_speedup=a['seconds']/b['seconds'],
            artifacts={k:v['hashes'] for k,v in results.items()}))
        print(rows[-1],flush=True)
    save(output/'completion.json',dict(at=now(),passed=True,rows=rows,surface_proof_sha256=sha256(proof),
        implementation={n:sha256(ROOT/'scripts'/n) for n in ['verify_sparse_support_solver.py','relax_whole_support.py','sparse_support_surface.py']},
        quality_approved=False,scope='Two cropped12-frame numerical parity experiments, two sweeps and12 local evaluations. Boundary context is deliberately cropped equally. No full-clip optimization, export or quality claim; timings while other workers live.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args()
    with threadpool_limits(limits=1):run(a.output.resolve())
