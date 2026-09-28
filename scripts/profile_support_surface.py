"""Bounded read-only profile of a retained full support objective."""
import argparse
import cProfile
from pathlib import Path
import pstats
import time
import numpy as np
from threadpoolctl import threadpool_limits
from strep import read, save, sha256, now
from rig_asset import RigAsset
from target_rig_contact import baseline
from support_reference_fit import SupportReferenceFitter


def load(folder, cls=SupportReferenceFitter):
    spec=read(folder/'spec.json');request=read(folder/'request.json')
    rig=RigAsset.load(folder/'input/character.glb');before,local=baseline(rig,spec['frames'])
    surfaces=np.array([rig.vertices(w) for w in before])
    fitter=cls(rig,spec,local,request['targets_m'],np.ones(len(before)),surfaces,
        guides=request['support']['guides'],support_weight=request['support_weight'])
    parameters=np.load(folder/'fit.npz',allow_pickle=False)['parameters']
    return fitter,parameters


def run(folder,output):
    if output.exists():raise ValueError('Preserve previous profile')
    fitter,parameters=load(folder)
    frames=[0,1,len(parameters)//2,len(parameters)-1]
    profile=cProfile.Profile();timings=[]
    for _ in range(3):
        for frame in frames:
            neighbors=[parameters[n] for n in (frame-1,frame+1) if 0<=n<len(parameters)]
            start=time.perf_counter();profile.enable()
            fitter.objective_pair(frame,parameters[frame],neighbors)
            profile.disable();timings.append(time.perf_counter()-start)
    stats=pstats.Stats(profile);rows=[]
    for (file,line,name),(primitive,total,own,cumulative,callers) in stats.stats.items():
        rows.append(dict(file=file,line=line,function=name,primitive_calls=primitive,total_calls=total,self_seconds=own,cumulative_seconds=cumulative))
    rows.sort(key=lambda r:r['cumulative_seconds'],reverse=True)
    inputs={str(folder/n):sha256(folder/n) for n in ['input/character.glb','fit.npz','spec.json','request.json']}
    save(output,dict(at=now(),inputs=inputs,implementation_sha256=sha256(__file__),calls=len(timings),
        seconds=timings,median_seconds=float(np.median(timings)),vertices=fitter.skin.count,parameters=len(fitter.bounds),
        rows=rows,quality_approved=False,scope='Twelve objective calls on retained gesture rig01, single BLAS thread; other studies remain live. Not a wall-clock inference or complete-solver benchmark.'))
    print(dict(median_seconds=float(np.median(timings)),vertices=fitter.skin.count,parameters=len(fitter.bounds),top=rows[:8]))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    with threadpool_limits(limits=1):run(a.folder.resolve(),a.output.resolve())
