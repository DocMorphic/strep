"""Freeze all fitting-time correspondences and verify direct distance operators."""
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
from unique_fractional_skin import UniqueBoundedPathFitter
from projected_temporal_surface import ProjectedTemporalSurface


def run(source,output):
    source,output=[Path(p).resolve() for p in [source,output]]
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir();(output/'surfaces').mkdir()
    recipe=read(source/'request.json');initial=read(source/'initial-parameters.json');history=read(source/'history.json')['iterations'][0]
    names=sorted(set(recipe['implementation'])|{'verify_projected_clock.py','projected_temporal_surface.py','unique_fractional_skin.py','batched_fractional_skin.py','batched_bounded_path.py'})
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    proc=psutil.Process()
    request=dict(at=now(),pid=proc.pid,created=proc.create_time(),source=str(source),source_request_sha256=sha256(source/'request.json'),initial_sha256=sha256(source/'initial-parameters.json'),frames=recipe['frames'],variants=['initializer','small_perturbation'],margins_m=[.001,.003],implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False)
    save(output/'request.json',request);save(output/'initial-history.json',history)
    def phase(status,**details):save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**details));print(status,details,flush=True)
    try:
        if sha256(recipe['source_scene'])!=recipe['source_scene_sha256'] or sha256(source/'palm-region.json')!=recipe['palm_region_sha256']:raise ValueError('Scene/patch changed')
        scene=read(recipe['source_scene'])['scene'];patches=read(source/'palm-region.json');actors=[]
        for label in ['A','B']:
            item=recipe['sources'][label];path=Path(item['raw_glb']);local_path=source/(label+'-source-local.npz')
            if sha256(path)!=item['raw_glb_sha256'] or sha256(local_path)!=item['local_npz_sha256']:raise ValueError('Actor input changed')
            rig=RigAsset.load(path);local=np.load(local_path,allow_pickle=False)['authored_finger_local'];primitive=rig.document['meshes'][0]['primitives'][0]
            triangles=array(rig.document,rig.binary,primitive['indices']).reshape(-1,3)
            if actors and not np.array_equal(triangles,faces):raise ValueError('Topology differs')
            faces=triangles
            actors.append(RegionActor(rig,local,'LeftHand',scene['contacts'][0]['effector']['surface_vertex'],faces,scene['actors'][label]['transform'],patch=patches[label]))
        old,new=FastBoundedPathFitter(actors),UniqueBoundedPathFitter(actors);controls=np.asarray(initial['controls'])
        for fitter in [old,new]:
            for name,value in [('basis',fitter.matrix),('control_bounds',fitter.bounds),('control_radii',fitter.control_radii)]:
                if not np.array_equal(np.asarray(initial[name]),value):raise ValueError('Control protocol differs')
        if not np.array_equal(controls,np.asarray(history['parameters'])):raise ValueError('Initial witness parameters differ')
        if [r['frame'] for r in history['window']]!=recipe['frames']:raise ValueError('Witness clock differs')
        rng=np.random.default_rng(9341);states=[controls,controls+rng.normal(0,.003,len(controls))];rows=[];geometry_seconds=0.
        with threadpool_limits(limits=1):
            for frame,expected in zip(recipe['frames'],history['window']):
                phase('geometry',frame=frame,completed_frames=len(rows));start=time.perf_counter()
                records,diagnostics=correspondences(old.actors,frame,controls,faces,margin=.003)
                geometry_seconds+=time.perf_counter()-start
                for actual,witness in zip(diagnostics,expected['collision']):
                    if actual['active_constraints']!=witness['active_constraints'] or abs(actual['max_depth_m']-witness['max_depth_m'])>1e-10:raise ValueError('Retained witness differs')
                filename=f'{float(frame):06.1f}.json';save(output/'surfaces'/filename,dict(frame=frame,records=records,diagnostics=diagnostics,quality_approved=False))
                start=time.perf_counter();reference=TemporalSurface(old,frame,records);projected=ProjectedTemporalSurface(new,frame,records);build_seconds=time.perf_counter()-start
                checks=[]
                for label,x in zip(request['variants'],states):
                    for margin in request['margins_m']:
                        a,b=reference.clearance(x,margin),projected.clearance(x,margin)
                        if a[0].shape!=b[0].shape or a[1].shape!=b[1].shape:raise ValueError('Constraint shape differs')
                        value_error=float(np.max(np.abs(a[0]-b[0]),initial=0.));jac_error=float(np.max(np.abs(a[1]-b[1]),initial=0.))
                        if value_error>1e-11 or jac_error>2e-6:raise ValueError('Projected rows/Jacobian mismatch')
                        checks.append(dict(variant=label,margin_m=margin,value_error_m=value_error,derivative_max_element_error=jac_error))
                times={}
                for label,fitter,surface in [('original',old,reference),('projected',new,projected)]:
                    samples=[]
                    for repeat in range(3):
                        for actor in fitter.actors:actor.cache=None
                        start=time.perf_counter();surface.clearance(controls);samples.append(time.perf_counter()-start)
                    times[label]=float(np.median(samples))
                rows.append(dict(frame=frame,constraints=projected.count,checks=checks,median_seconds=times,projection_build_seconds=build_seconds,correspondences_file=filename,correspondences_sha256=sha256(output/'surfaces'/filename)))
                save(output/'results.json',dict(rows=rows,quality_approved=False))
        if sha256(source/'request.json')!=request['source_request_sha256'] or sha256(source/'initial-parameters.json')!=request['initial_sha256']:raise ValueError('Study inputs changed')
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Implementation changed')
        assert len(rows)==len(request['frames'])
        save(output/'completion.json',dict(at=now(),frames=len(rows),comparisons=sum(len(r['checks']) for r in rows),constraints=sum(r['constraints'] for r in rows),results_sha256=sha256(output/'results.json'),initial_history_sha256=sha256(output/'initial-history.json'),geometry_seconds=geometry_seconds,
            median_evaluation_seconds_summed={name:sum(r['median_seconds'][name] for r in rows) for name in ['original','projected']},quality_approved=False,
            scope='Every retained fitting time at the original enriched initializer; actual correspondences frozen separately. Two states and two clearance margins. Integer analytic path retained. No optimization/export/animation-quality claim; timings exclude geometry and optimizer work.'))
        phase('complete')
    except BaseException as exc:phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.source,a.output)
