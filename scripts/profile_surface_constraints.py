"""Compare coupled derivatives on a real retained collision-witness batch."""
import argparse
from pathlib import Path
import shutil
import time
import traceback
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset,array
from paired_palm_region import RegionActor
from paired_hand_clearance import correspondences
from paired_hand_trajectory import TemporalSurface
from fast_bounded_path import FastBoundedPathFitter
from batched_bounded_path import BatchedBoundedPathFitter


def run(study,witness,output):
    study,witness,output=[Path(p).resolve() for p in [study,witness,output]]
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    source=read(study/'request.json');initial=read(study/'initial-parameters.json');history=read(witness/'history.json')
    sample=max(history['iterations'][0]['window'],key=lambda r:max(c['active_constraints'] for c in r['collision']))
    if float(sample['frame']).is_integer():raise ValueError('Expected a fractional maximum-size witness')
    names=sorted(set(source['implementation'])|{'profile_surface_constraints.py','fast_bounded_path.py','fast_path_skin.py','batched_bounded_path.py','batched_fractional_skin.py'})
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    proc=psutil.Process()
    request=dict(at=now(),pid=proc.pid,created=proc.create_time(),source=str(study),source_request_sha256=sha256(study/'request.json'),initial_sha256=sha256(study/'initial-parameters.json'),witness=str(witness),sample=sample,
                 implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False)
    save(output/'request.json',request)
    def phase(status,**details):save(output/'pipeline.json',dict(status=status,at=now(),quality_approved=False,**details));print(status,flush=True)
    try:
        if sha256(source['source_scene'])!=source['source_scene_sha256'] or sha256(study/'palm-region.json')!=source['palm_region_sha256']:raise ValueError('Scene/patch changed')
        scene=read(source['source_scene'])['scene'];patches=read(study/'palm-region.json');actors=[]
        for label in ['A','B']:
            item=source['sources'][label];path=Path(item['raw_glb']);local_path=study/(label+'-source-local.npz')
            if sha256(path)!=item['raw_glb_sha256'] or sha256(local_path)!=item['local_npz_sha256']:raise ValueError('Actor input changed')
            rig=RigAsset.load(path);local=np.load(local_path,allow_pickle=False)['authored_finger_local'];primitive=rig.document['meshes'][0]['primitives'][0]
            faces=array(rig.document,rig.binary,primitive['indices']).reshape(-1,3)
            actors.append(RegionActor(rig,local,'LeftHand',scene['contacts'][0]['effector']['surface_vertex'],faces,scene['actors'][label]['transform'],patch=patches[label]))
        old,new=FastBoundedPathFitter(actors),BatchedBoundedPathFitter(actors);controls=np.asarray(initial['controls']);frame=sample['frame']
        for fitter in [old,new]:
            for name,value in [('basis',fitter.matrix),('control_bounds',fitter.bounds),('control_radii',fitter.control_radii)]:
                if not np.array_equal(np.asarray(initial[name]),value):raise ValueError('Control protocol changed')
        rows=[]
        with threadpool_limits(limits=1):
            phase('building_real_correspondences');begin=time.perf_counter()
            records,diagnostics=correspondences(old.actors,frame,controls,faces,margin=.003)
            geometry_seconds=time.perf_counter()-begin
            for actual,expected in zip(diagnostics,sample['collision']):
                if actual['active_constraints']!=expected['active_constraints'] or abs(actual['max_depth_m']-expected['max_depth_m'])>1e-10:raise ValueError('Retained witness differs')
            save(output/'correspondences.json',dict(frame=frame,records=records,diagnostics=diagnostics,quality_approved=False))
            surfaces=[TemporalSurface(f,frame,records) for f in [old,new]];rng=np.random.default_rng(9341)
            phase('comparing_coupled_rows')
            for label,x in [('initializer',controls),('small_perturbation',controls+rng.normal(0,.003,len(controls)))]:
                pairs=[s.clearance(x) for s in surfaces]
                value_error=float(np.abs(pairs[0][0]-pairs[1][0]).max());jac_error=float(np.abs(pairs[0][1]-pairs[1][1]).max())
                if value_error>1e-11 or jac_error>2e-6:raise ValueError('Coupled row/Jacobian mismatch')
                timing={}
                for name,fitter,surface in zip(['whole_fk_difference','batched_local_difference'],[old,new],surfaces):
                    elapsed=[]
                    for repeat in range(3):
                        for actor in fitter.actors:actor.cache=None
                        begin=time.perf_counter();surface.clearance(x);elapsed.append(time.perf_counter()-begin)
                    timing[name]=float(np.median(elapsed))
                rows.append(dict(variant=label,rows=len(pairs[0][0]),parameters=len(x),value_error_m=value_error,derivative_max_element_error=jac_error,median_seconds=timing,speedup=timing['whole_fk_difference']/timing['batched_local_difference']))
                save(output/'results.json',dict(rows=rows,quality_approved=False))
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Profile implementation changed')
        save(output/'completion.json',dict(at=now(),results_sha256=sha256(output/'results.json'),correspondences_sha256=sha256(output/'correspondences.json'),geometry_seconds=geometry_seconds,
             median_speedup=float(np.median([r['speedup'] for r in rows])),quality_approved=False,
             scope='One real largest per-direction fractional witness at the retained initializer. Full coupled surface rows/Jacobians, same 1 mm linearized clearance margin, two parameter states and cold-cache timing. Not full optimization/export/geometry quality validation or whole-solver speedup.'))
        phase('complete')
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['study','witness','output']:p.add_argument(name,type=Path)
    a=p.parse_args();run(a.study,a.witness,a.output)
