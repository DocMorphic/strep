"""One inner-solve diagnostic using the completed 30-frame frozen surface proof.

No correspondence query is repeated to construct the initializer. The proposed
controls receive one fresh all-30-frame scan and the unchanged step guard.
This is not the three-outer-step matched trial or a full exported audit.
"""
import argparse
from pathlib import Path
import shutil
import time
import traceback
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset, array
from paired_palm_region import RegionActor, contact_records, CorrespondenceEvaluator
from paired_hand_clearance import correspondences
from unique_fractional_skin import UniqueBoundedPathFitter
from projected_temporal_surface import ProjectedTemporalSurface
from screen_path_guard import SCREEN, select_step
from verify_palm_region import measure
from frame_capped_restoration import frame_caps, row_budgets, solve


def run(proof, output):
    proof, output = Path(proof).resolve(), Path(output).resolve()
    preq, completion = read(proof/'request.json'), read(proof/'completion.json')
    source = Path(preq['source']); recipe = read(source/'request.json')
    initial = read(source/'initial-parameters.json'); witness = read(proof/'initial-history.json')
    checks = read(proof/'results.json')['rows']
    if (completion['frames'] != len(recipe['frames']) or completion['comparisons'] != 4*len(recipe['frames'])
        or completion['results_sha256'] != sha256(proof/'results.json')
        or completion['initial_history_sha256'] != sha256(proof/'initial-history.json')
        or preq['source_request_sha256'] != sha256(source/'request.json')
        or preq['initial_sha256'] != sha256(source/'initial-parameters.json')):
        raise ValueError('Completed projection proof does not bind these inputs')
    if [r['frame'] for r in checks] != recipe['frames'] or [r['frame'] for r in witness['window']] != recipe['frames']:
        raise ValueError('Frozen witness clock differs')
    for row in checks:
        if sha256(proof/'surfaces'/row['correspondences_file']) != row['correspondences_sha256']:
            raise ValueError('Frozen correspondence changed')
        if len(row['checks']) != 4 or any(c['value_error_m']>1e-11 or c['derivative_max_element_error']>2e-6 for c in row['checks']):
            raise ValueError('Projection equivalence failed')
    for name,digest in preq['implementation'].items():
        if sha256(proof/'implementation'/name)!=digest or sha256(ROOT/'scripts'/name)!=digest:
            raise ValueError('Projection implementation changed: '+name)
    output.mkdir(parents=True,exist_ok=False); (output/'implementation').mkdir()
    names = sorted(set(preq['implementation']) | {'study_frame_capped_restoration.py','frame_capped_restoration.py'})
    for name in names: shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    proc = psutil.Process()
    request = dict(at=now(),pid=proc.pid,created=proc.create_time(),proof=str(proof),
        proof_request_sha256=sha256(proof/'request.json'),proof_completion_sha256=sha256(proof/'completion.json'),
        source=str(source),source_request_sha256=sha256(source/'request.json'),frames=recipe['frames'],
        implementation={n:sha256(output/'implementation'/n) for n in names},
        method='one_inner_solve_frame_capped_restoration',maxiter=60,selection_screen=SCREEN,quality_approved=False)
    save(output/'request.json',request)
    def phase(status,**details):
        save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**details));print(status,details,flush=True)
    try:
        phase('loading_frozen_surfaces')
        if sha256(recipe['source_scene'])!=recipe['source_scene_sha256'] or sha256(source/'palm-region.json')!=recipe['palm_region_sha256']:
            raise ValueError('Scene/patch changed')
        scene=read(recipe['source_scene'])['scene'];patches=read(source/'palm-region.json');actors=[]
        for label in ['A','B']:
            item=recipe['sources'][label]; path=Path(item['raw_glb']); local_path=source/(label+'-source-local.npz')
            if sha256(path)!=item['raw_glb_sha256'] or sha256(local_path)!=item['local_npz_sha256']:raise ValueError('Actor input changed')
            rig=RigAsset.load(path);local=np.load(local_path,allow_pickle=False)['authored_finger_local'];primitive=rig.document['meshes'][0]['primitives'][0]
            triangles=array(rig.document,rig.binary,primitive['indices']).reshape(-1,3)
            if actors and not np.array_equal(triangles,faces):raise ValueError('Topology differs')
            faces=triangles
            actors.append(RegionActor(rig,local,'LeftHand',scene['contacts'][0]['effector']['surface_vertex'],faces,scene['actors'][label]['transform'],patch=patches[label]))
        fitter=UniqueBoundedPathFitter(actors);x=np.asarray(initial['controls'],float)
        for name,value in [('basis',fitter.matrix),('control_bounds',fitter.bounds),('control_radii',fitter.control_radii)]:
            if not np.array_equal(np.asarray(initial[name]),value):raise ValueError('Control protocol differs')
        if not np.array_equal(x,witness['parameters']):raise ValueError('Witness initializer differs')
        surfaces=[];depths=[];counts=[]
        for row,expected in zip(checks,witness['window']):
            saved=read(proof/'surfaces'/row['correspondences_file'])
            if saved['frame']!=row['frame'] or saved['diagnostics']!=expected['collision']:raise ValueError('Frozen witness diagnostic differs')
            surface=ProjectedTemporalSurface(fitter,row['frame'],saved['records'])
            if surface.count!=row['constraints']:raise ValueError('Row count differs')
            surfaces.append(surface);counts.append(surface.count);depths.append(max(c['max_depth_m'] for c in saved['diagnostics']))
        budgets=row_budgets(depths,counts,.001,SCREEN['max_sample_penetration_m']);count=len(budgets)
        if count!=completion['constraints']:raise ValueError('Surface population differs')
        save(output/'budgets.json',dict(frames=recipe['frames'],depths_m=depths,frame_caps_m=frame_caps(depths,SCREEN['max_sample_penetration_m']).tolist(),counts=counts,clearance_margin_m=.001,row_budgets_m=budgets.tolist()))
        cache=None;cached=None
        def inequalities(value):
            nonlocal cache,cached
            if cache is None or not np.array_equal(cache,value):
                pairs=[s.clearance(value) for s in surfaces]+[fitter.step_pair(value)]
                cached=(np.concatenate([p[0] for p in pairs]),np.vstack([p[1] for p in pairs]));cache=value.copy()
            return cached
        with threadpool_limits(limits=1):
            records,metrics=contact_records(fitter.base.actors,fitter.event,fitter.event_map@x,faces)
            evaluator=CorrespondenceEvaluator(fitter.base,records)
            def objective(value):
                event=fitter.event_map@value;r,j=fitter.base.objective_pair(event);cr,cj=evaluator.contact(event)
                residual=np.r_[r,cr,(value-x)*.1];jac=np.vstack([j@fitter.event_map,cj@fitter.event_map,np.eye(len(x))*.1])
                g,dg=inequalities(value)
                residual=np.r_[residual,np.minimum(g[:count],0)*100];jac=np.vstack([jac,dg[:count]*(g[:count]<0)[:,None]*100])
                return .5*float(residual@residual),jac.T@residual
            lower=np.maximum(-fitter.bounds,x-np.radians(5));upper=np.minimum(fitter.bounds,x+np.radians(5))
            old_energy=objective(x)[0];phase('solving',constraints=count,controls=len(x));start=time.perf_counter()
            result=solve(objective,inequalities,x,lower,upper,budgets);elapsed=time.perf_counter()-start
            candidate=np.clip(result.x,lower,upper)
            if not np.isfinite(candidate).all():raise ValueError('Nonfinite candidate')
            new_energy=objective(candidate)[0]
            solve_record=dict(at=now(),controls=candidate.tolist(),success=bool(result.success),message=str(result.message),iterations=int(result.nit),
                solve_seconds=elapsed,restoration_fraction=result.restoration_fraction,restoration_slack_m=result.restoration_slack_m,
                relaxed_constraint_min=result.relaxed_constraint_min,minimum_step_slack=float(fitter.step_pair(candidate)[0].min()),
                old_energy=old_energy,new_energy=new_energy,quality_approved=False)
            save(output/'candidate.json',solve_record)
            actual=[]
            for frame in recipe['frames']:
                phase('fresh_geometry',frame=frame,completed_frames=len(actual))
                _,diagnostics=correspondences(fitter.actors,frame,candidate,faces,margin=.003)
                actual.append(dict(frame=frame,collision=diagnostics));save(output/'geometry.json',dict(rows=actual,quality_approved=False))
            parts=np.split(candidate,[fitter.sizes[0]])
            points=[a.rig.vertices(a.pose(fitter.event,v))@a.rotation.T+a.translation for a,v in zip(fitter.actors,parts)]
            region=measure(points,[a.patch for a in fitter.actors],faces,SCREEN['max_contact_distance_m'])
            after=[max(c['max_depth_m'] for c in r['collision']) for r in actual]
            decision=select_step(depths,after,old_energy,new_energy,region)
            decision['hard_edit_bounds_pass']=bool(np.all(np.abs(candidate)<=fitter.bounds+1e-10) and solve_record['minimum_step_slack']>=-1e-8)
            decision['accepted']=decision['accepted'] and decision['hard_edit_bounds_pass']
            save(output/'decision.json',dict(**decision,event_region=region,before_depths_m=depths,after_depths_m=after,
                scope='One fixed-correspondence inner solve and fresh fitting-clock geometry only; no backtracking, outer refinement, export, held-out or human approval.'))
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:raise ValueError('Implementation changed')
        for name,digest in [('request.json',request['proof_request_sha256']),('completion.json',request['proof_completion_sha256'])]:
            if sha256(proof/name)!=digest:raise ValueError('Proof changed')
        save(output/'completion.json',dict(at=now(),candidate_sha256=sha256(output/'candidate.json'),geometry_sha256=sha256(output/'geometry.json'),decision_sha256=sha256(output/'decision.json'),frames=len(actual),quality_approved=False))
        phase('complete',step_accepted=decision['accepted'])
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('proof',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();run(args.proof,args.output)
