"""Compare full surfaces, derivatives and objectives on all three test rigs."""
import argparse
from pathlib import Path
import time
import numpy as np
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from profile_support_surface import load
from sparse_support_surface import SparseSupportReferenceFitter


def run(output):
    if output.exists():raise ValueError('Preserve previous proof')
    rows=[];inputs={};rng=np.random.default_rng(19432)
    for identifier in ['motion-036-rig-01','motion-036-rig-02','motion-036-rig-03','motion-026-rig-01']:
        folder=ROOT/'reports/whole-support-breadth-v1/takes'/identifier
        dense,parameters=load(folder);sparse,_=load(folder,SparseSupportReferenceFitter)
        records=[];timings={'dense':[],'sparse':[]}
        frames=[0,1,len(parameters)//2,len(parameters)-1]
        for frame in frames:
            for label,x in [('fitted',parameters[frame]),('random',rng.uniform(-.8,.8,len(dense.bounds))*dense.bounds),('zero',np.zeros_like(parameters[frame]))]:
                neighbors=[parameters[n] for n in (frame-1,frame+1) if 0<=n<len(parameters)]
                a,b=dense.surface_jacobian(frame,x),sparse.surface_jacobian(frame,x)
                errors=[float(np.max(np.abs(u-v))) for u,v in zip(a,b)]
                ar,aj=dense.objective_pair(frame,x,neighbors);br,bj=sparse.objective_pair(frame,x,neighbors)
                errors += [float(np.max(np.abs(ar-br))),float(np.max(np.abs(aj-bj)))]
                if max(errors)>1e-12:raise ValueError('Changed geometry, objective or derivative')
                # Alternating order limits a simple warm-up/order bias.
                order=[('dense',dense),('sparse',sparse)]
                if len(records)%2:order.reverse()
                for name,fitter in order:
                    begin=time.perf_counter()
                    for _ in range(3):fitter.objective_pair(frame,x,neighbors)
                    timings[name].append((time.perf_counter()-begin)/3)
                records.append(dict(frame=frame,pose=label,errors=errors))
        dense_time=float(np.median(timings['dense']));sparse_time=float(np.median(timings['sparse']))
        influences=sum(len(ids) for part in sparse.sparse_surface.parts for ids,weights in part[4])
        rows.append(dict(case=identifier,vertices=dense.skin.count,edited_joints=len(dense.nodes),
            dense_joint_vertex_pairs=dense.skin.count*len(dense.nodes),nonzero_joint_vertex_pairs=influences,
            records=records,timings_seconds=timings,dense_median_seconds=dense_time,sparse_median_seconds=sparse_time,
            measured_objective_speedup=dense_time/sparse_time))
        for name in ['input/character.glb','spec.json','request.json','fit.npz']:
            inputs[str(folder/name)]=sha256(folder/name)
        print(dict(case=identifier,maximum_error=max(max(r['errors']) for r in records),speedup=dense_time/sparse_time),flush=True)
    implementation={str(ROOT/'scripts'/n):sha256(ROOT/'scripts'/n) for n in
        ['sparse_support_surface.py','verify_sparse_support_surface.py','profile_support_surface.py',
         'rig_clearance_fit.py','support_reference_fit.py','breadth_contact_fit.py','target_rig_contact.py']}
    save(output,dict(at=now(),passed=True,inputs=inputs,implementation=implementation,rows=rows,
        quality_approved=False,scope='48 complete surfaces and objectives across three rig proportions plus gesture. Tests zero, retained fitted and seeded random legal-box parameters. Numerical equivalence and local objective timings only; other processes are live. No solver, animation or release quality claim.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args()
    with threadpool_limits(limits=1):run(a.output.resolve())
