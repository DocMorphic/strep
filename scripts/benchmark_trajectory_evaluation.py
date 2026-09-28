"""Compare composite objective reuse against the preserved pre-refactor snapshot."""
import importlib.util
import sys
import time
import numpy as np
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_transition import localize
from rig_trajectory_fit import TrajectoryFitter
import rig_clearance_fit


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def run():
    folder=ROOT/'reports/trajectory-fit-v1/jump-204/trajectory';snapshot=folder/'implementation'
    old_base=load('clearance_before_reuse',snapshot/'rig_clearance_fit.py')
    try:
        sys.modules['rig_clearance_fit']=old_base
        old=load('trajectory_before_reuse',snapshot/'rig_trajectory_fit.py').TrajectoryFitter
    finally:sys.modules['rig_clearance_fit']=rig_clearance_fit
    rig=RigAsset.load(folder/'input/character.glb');request=read(folder/'request.json');spec=read(folder/'spec.json')
    sampler=AnimationSampler(rig.document,rig.binary,0);world=np.array([sampler.sample(float(np.float32(f/30))) for f in range(spec['frames'])]);local=localize(world,rig.parents)
    args=(rig,spec,local,{k:np.array(v) for k,v in request['targets_m'].items()},request['envelope'],read(folder/'support-targets.json')['supports'])
    before=old(*args);after=TrajectoryFitter(*args);rows=[]
    with threadpool_limits(limits=1):
        for frame in [0,24,37]:
            x=np.random.default_rng(112+frame).normal(size=len(before.bounds))*.003
            r,j=before.trajectory_pair(frame,x);nr,nj=after.trajectory_pair(frame,x)
            assert np.array_equal(r,nr) and np.array_equal(j,nj)
            times={'before':[],'after':[]}
            for repeat in range(12):
                for name,fitter in ([('before',before),('after',after)] if repeat%2==0 else [('after',after),('before',before)]):
                    start=time.perf_counter();fitter.trajectory_pair(frame,x);times[name].append(time.perf_counter()-start)
            rows.append(dict(frame=frame,exact_residual_and_jacobian=True,median_seconds={k:float(np.median(v)) for k,v in times.items()},samples_seconds=times))
    result=dict(cases=rows,old_trajectory_sha256=sha256(snapshot/'rig_trajectory_fit.py'),old_clearance_sha256=sha256(snapshot/'rig_clearance_fit.py'),new_trajectory_sha256=sha256(ROOT/'scripts/rig_trajectory_fit.py'),new_clearance_sha256=sha256(ROOT/'scripts/rig_clearance_fit.py'),scope='Single-thread objective evaluations on one retained rig at three frames, alternating order while the original study is running. Not end-to-end solver timing. Current study uses its preserved old implementation.')
    save(ROOT/'reports/trajectory-fit-v1/evaluation-reuse-benchmark.json',result)
    print([{k:v for k,v in row.items() if k!='samples_seconds'} for row in rows])


if __name__=='__main__':run()
