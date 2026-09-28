"""Paired CPU-only evaluation benchmark; no fitting or model generation."""
import argparse
import shutil
import time
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from cached_patch_contact import CachedPatchFitter
from reference_temporal_patch_frame import evaluate
from run_prepared_contact_trajectory import load_plan
from rig_transition import localize
from strep import ROOT,now,read,save,sha256


def run(plan,output):
    if output.exists():raise ValueError('Preserve earlier performance comparisons')
    protocol,spec,data,rig,plain,_=load_plan(plan)
    cached=CachedPatchFitter(rig,spec,localize(data['limb'],rig.parents))
    sequence=[]
    for frame in [47,60,61,62,89,102]:
        for delta in [0.,1e-5,-1e-5]:
            x=data['initial'][frame].copy();x[0]+=delta
            sequence.append((frame,x,[data['initial'][frame-1],data['initial'][frame+1]],
                data['reference'][frame],[data['reference'][frame-1],data['reference'][frame+1]]))
    timings=[]
    with threadpool_limits(limits=1):
        for args in sequence:
            a=evaluate(plain,*args);b=evaluate(cached,*args)
            for x,y in zip(a,b):np.testing.assert_array_equal(x,y)
        for repeat in range(3):
            for label,fitter in ([('plain',plain),('cached',cached)] if repeat%2==0 else [('cached',cached),('plain',plain)]):
                cpu=time.process_time();wall=time.perf_counter()
                for args in sequence:evaluate(fitter,*args)
                timings.append(dict(repeat=repeat,method=label,process_cpu_s=time.process_time()-cpu,wall_s=time.perf_counter()-wall))
    medians={name:float(np.median([r['process_cpu_s'] for r in timings if r['method']==name])) for name in ['plain','cached']}
    output.mkdir(parents=True);(output/'implementation').mkdir()
    names=['profile_cached_patch_contact.py','cached_patch_contact.py','reference_temporal_patch_frame.py','analytic_patch_contact.py']
    for n in names:shutil.copyfile(ROOT/'scripts'/n,output/'implementation'/n)
    save(output/'verification.json',dict(at=now(),plan=str(plan),plan_protocol_sha256=sha256(plan/'protocol.json'),
        prepared_sha256=sha256(plan/'prepared.npz'),implementation={f'scripts/{n}':sha256(ROOT/'scripts'/n) for n in names},
        tested_evaluations=len(sequence),all_objective_gradient_constraints_jacobian_exactly_equal=True,
        repetitions=3,timings=timings,median_process_cpu_s=medians,median_cpu_speedup=medians['plain']/medians['cached'],
        cache_hits=cached.surface_hits,cache_misses=cached.surface_misses,fit_executed=False,production_changed=False,
        scope='Same real prepared poses, changed root parameters, frames with/without held contacts. Single-thread paired objective evaluations only. Another solver process remains active; process CPU time reduces scheduling noise but this is not isolated end-to-end inference/fit timing. No approximation or new acceptance threshold.'))
    print(dict(evaluations=len(sequence),exactly_equal=True,median_process_cpu_s=medians,cpu_speedup=medians['plain']/medians['cached']))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('plan',type=Path);parser.add_argument('output',type=Path)
    a=parser.parse_args();run(a.plan.resolve(),a.output.resolve())
