"""Verify expanded-hull fitting queries against retained and fresh references."""
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
from unique_fractional_skin import UniqueBoundedPathFitter
from paired_hand_clearance import correspondences as original
from hull_surface_correspondences import correspondences as filtered


def compare(records,diagnostics,expected,old):
    if len(records)!=2 or len(diagnostics)!=2 or len(expected)!=2 or len(old)!=2:raise ValueError('Both query directions required')
    bary_error=normal_error=depth_error=0.
    for a,b in zip(diagnostics,old):
        for key in ['source','target','vertices_checked','vertices_over_5mm','active_constraints']:
            if a[key]!=b[key]:raise ValueError('Query diagnostic differs: '+key)
        depth_error=max(depth_error,abs(a['max_depth_m']-b['max_depth_m']))
    for a,b in zip(records,expected):
        if a['source']!=b['source'] or a['target']!=b['target'] or len(a['points'])!=len(b['points']):raise ValueError('Correspondence direction/count differs')
        for pa,pb in zip(a['points'],b['points']):
            if pa[0]!=pb[0] or pa[1]!=pb[1]:raise ValueError('Active source vertex/target triangle changed')
            bary_error=max(bary_error,float(np.max(np.abs(np.asarray(pa[2])-pb[2]))))
            normal_error=max(normal_error,float(np.max(np.abs(np.asarray(pa[3])-pb[3]))))
    if max(bary_error,normal_error,depth_error)>1e-10:raise ValueError('Correspondence geometry differs')
    return dict(rows=sum(len(r['points']) for r in records),depth_error_m=depth_error,barycentric_error=bary_error,normal_error=normal_error)


def run(proof,changed,output):
    proof,changed,output=[Path(p).resolve() for p in (proof,changed,output)]
    preq=read(proof/'request.json');done=read(proof/'completion.json');source=Path(preq['source']);recipe=read(source/'request.json')
    after=read(changed/'completion.json');candidate=read(changed/'candidate.json');creq=read(changed/'request.json')
    if (read(changed/'pipeline.json')['status']!='complete' or after['candidate_sha256']!=sha256(changed/'candidate.json')
        or creq['proof_request_sha256']!=sha256(proof/'request.json') or done['results_sha256']!=sha256(proof/'results.json')
        or preq['source_request_sha256']!=sha256(source/'request.json') or preq['initial_sha256']!=sha256(source/'initial-parameters.json')):
        raise ValueError('Reference provenance mismatch')
    rows=read(proof/'results.json')['rows']
    if [r['frame'] for r in rows]!=recipe['frames']:raise ValueError('Reference clock differs')
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir();(output/'surfaces').mkdir()
    names=sorted(set(preq['implementation'])|{'verify_hull_correspondences.py','hull_surface_correspondences.py','convex_partner_surface.py'})
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    proc=psutil.Process();request=dict(at=now(),pid=proc.pid,created=proc.create_time(),proof=str(proof),changed=str(changed),
        proof_request_sha256=sha256(proof/'request.json'),proof_completion_sha256=sha256(proof/'completion.json'),
        changed_completion_sha256=sha256(changed/'completion.json'),changed_candidate_sha256=sha256(changed/'candidate.json'),
        initializer_frames=recipe['frames'],changed_frames=[66.,74.,75.],margin_m=.003,
        implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False)
    save(output/'request.json',request)
    def phase(status,**details):save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**details));print(status,details,flush=True)
    try:
        for name,digest in preq['implementation'].items():
            if sha256(proof/'implementation'/name)!=digest or sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Reference implementation changed')
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
        fitter=UniqueBoundedPathFitter(actors);initial=read(source/'initial-parameters.json');x=np.asarray(initial['controls'])
        for name,value in [('basis',fitter.matrix),('control_bounds',fitter.bounds),('control_radii',fitter.control_radii)]:
            if not np.array_equal(np.asarray(initial[name]),value):raise ValueError('Control protocol differs')
        results=[]
        with threadpool_limits(limits=1):
            for row in rows:
                frame=row['frame'];phase('initializer',frame=frame,completed=len(results))
                path=proof/'surfaces'/row['correspondences_file']
                if sha256(path)!=row['correspondences_sha256']:raise ValueError('Retained surface changed')
                reference=read(path);stats=[];start=time.perf_counter();records,diagnostics=filtered(fitter.actors,frame,x,faces,margin=.003,stats=stats);elapsed=time.perf_counter()-start
                checks=compare(records,diagnostics,reference['records'],reference['diagnostics'])
                save(output/'surfaces'/row['correspondences_file'],dict(frame=frame,records=records,diagnostics=diagnostics,broadphase=stats))
                results.append(dict(state='initializer',frame=frame,filtered_seconds=elapsed,broadphase=stats,**checks));save(output/'results.json',dict(rows=results,quality_approved=False))
            for frame in request['changed_frames']:
                phase('changed_candidate',frame=frame,completed=len(results));stats=[];controls=np.asarray(candidate['controls'])
                start=time.perf_counter();expected,old=original(fitter.actors,frame,controls,faces,margin=.003);old_seconds=time.perf_counter()-start
                start=time.perf_counter();records,diagnostics=filtered(fitter.actors,frame,controls,faces,margin=.003,stats=stats);elapsed=time.perf_counter()-start
                save(output/'surfaces'/f'changed-{frame}.json',dict(frame=frame,reference_records=expected,reference_diagnostics=old,records=records,diagnostics=diagnostics,broadphase=stats))
                checks=compare(records,diagnostics,expected,old)
                results.append(dict(state='changed_candidate',frame=frame,original_seconds=old_seconds,filtered_seconds=elapsed,broadphase=stats,**checks));save(output/'results.json',dict(rows=results,quality_approved=False))
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Implementation changed')
        for path,digest in [(proof/'request.json',request['proof_request_sha256']),(proof/'completion.json',request['proof_completion_sha256']),
            (changed/'completion.json',request['changed_completion_sha256']),(changed/'candidate.json',request['changed_candidate_sha256'])]:
            if sha256(path)!=digest:raise ValueError('Bound reference changed')
        save(output/'completion.json',dict(at=now(),comparisons=len(results),initializer_frames=len(rows),changed_frames=3,
            results_sha256=sha256(output/'results.json'),quality_approved=False,
            scope='All30 retained initial correspondence batches and3 fresh scaled-candidate batches. Same signed-distance queries and32point bound. No optimizer, animation quality, export or full-clip claim.'))
        phase('complete')
    except BaseException as exc:phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['proof','changed','output']:p.add_argument(name,type=Path)
    a=p.parse_args();run(a.proof,a.changed,a.output)
