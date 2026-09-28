"""Bounded contact trial with true moving-surface distances for retained witnesses."""
import argparse
import copy
from pathlib import Path
import shutil
import time
import traceback
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from contact_restoration_problem import FrozenContactProblem
from dynamic_contact_witness import DynamicWitnessSurface
from projected_temporal_surface import ProjectedTemporalSurface
from hull_surface_correspondences import correspondences
from scaled_frame_restoration import solve
from screen_path_guard import SCREEN,select_step
from verify_palm_region import measure


def run(proof,output):
    proof,output=Path(proof).resolve(),Path(output).resolve();verified=read(proof/'completion.json');vreq=read(proof/'request.json')
    if not verified['passed'] or verified['results_sha256']!=sha256(proof/'results.json') or verified['summary_sha256']!=sha256(proof/'summary.json'):
        raise ValueError('Real-rig dynamic witness verification required')
    projected=Path(vreq['proof']);static=Path(vreq['static']);recipe=read(static/'request.json')
    inputs={**vreq['inputs'],str(proof/'request.json'):sha256(proof/'request.json'),str(proof/'completion.json'):sha256(proof/'completion.json')}
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Verified input changed: '+path)
    for name,digest in vreq['implementation'].items():
        if sha256(proof/'implementation'/name)!=digest or sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Verified implementation changed: '+name)
    names=sorted(set(vreq['implementation'])|{'study_dynamic_witness_cuts.py'})
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    for name in ['initial-parameters.json','palm-region.json','A-source-local.npz','B-source-local.npz','scene.json']:
        shutil.copyfile(static/name,output/name)
    proc=psutil.Process();request=copy.deepcopy(recipe)
    request.update(at=now(),pid=proc.pid,created=proc.create_time(),method='dynamic_signed_distance_witness_constraints',
        inputs=inputs,dynamic_proof=str(proof),initial_witnesses=vreq['groups'],max_witness_rounds=3,
        implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False,
        scope='Same original core5272 rows, objective, hard edits, original seed and frame caps. Seven verified identities seed dynamic cuts; nearest geometry is refreshed on every evaluation. Add all new violating identities after full30-time geometry. Three rounds maximum. Accepted step requires whole-clip export/engine/human validation; no root/leg/floor repair.')
    save(output/'request.json',request)
    def phase(status,**kw):save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**kw));print(status,kw,flush=True)
    try:
        with threadpool_limits(limits=1):
            problem=FrozenContactProblem(projected);fitter=problem.fitter;fitter.witness_faces=problem.faces;initial=problem.initial
            old_energy=problem.objective(initial)[0]
            if abs(old_energy-read(static/'round-01'/'candidate.json')['old_energy'])>1e-7:raise ValueError('Original objective differs')
            groups={r['frame']:set(map(tuple,r['keys'])) for r in vreq['groups']}
            history=[read(projected/'initial-history.json')];accepted=False;selected=initial.copy();reason='round_budget_exhausted'
            for number in range(1,request['max_witness_rounds']+1):
                folder=output/f'round-{number:02d}';folder.mkdir();(folder/'surfaces').mkdir();cuts=[];witnesses=[]
                for frame,keys in sorted(groups.items()):
                    surface=DynamicWitnessSurface(fitter,frame,sorted(keys));cap=float(problem.caps[problem.frames.index(frame)])
                    seed_depth=-surface.clearance(initial,0.)[0]
                    feasible=bool(np.all(seed_depth<=cap+3e-10));witnesses.append(dict(frame=frame,keys=sorted(keys),cap_m=cap,seed_depths_m=seed_depth.tolist(),seed_feasible=feasible))
                    cuts.append((surface,cap))
                save(folder/'witnesses.json',dict(rows=witnesses,quality_approved=False))
                if not all(r['seed_feasible'] for r in witnesses):reason='true_distance_witness_infeasible_at_original_seed';break
                budgets=problem.augmented_budgets(cuts);phase('solving',round=number,core_rows=problem.count,cut_rows=len(budgets)-problem.count)
                start=time.perf_counter();result=solve(problem.objective,lambda x:problem.inequalities(x,cuts),initial,problem.lower,problem.upper,budgets)
                current=np.clip(result.x,problem.lower,problem.upper)
                if not np.isfinite(current).all():raise ValueError('Nonfinite dynamic witness proposal')
                new_energy=problem.objective(current)[0]
                inner=dict(success=bool(result.success),message=str(result.message),iterations=int(result.nit),seconds=time.perf_counter()-start,
                    restoration_fraction=result.restoration_fraction,relaxed_constraint_min=result.relaxed_constraint_min,
                    core_rows=problem.count,cut_rows=len(budgets)-problem.count,old_energy=old_energy,new_energy=new_energy,
                    controls=current.tolist(),minimum_step_slack=float(fitter.step_pair(current)[0].min()),quality_approved=False)
                save(folder/'candidate.json',inner);geometry=[];new_keys=[]
                for frame,initial_depth,cap in zip(problem.frames,problem.depths,problem.caps):
                    phase('fresh_geometry',round=number,frame=frame,completed_frames=len(geometry))
                    records,diagnostics=correspondences(fitter.actors,frame,current,problem.faces,margin=.003)
                    save(folder/'surfaces'/f'after-{float(frame)}.json',dict(frame=frame,records=records,diagnostics=diagnostics))
                    geometry.append(dict(frame=frame,collision=diagnostics));save(folder/'geometry.json',dict(rows=geometry,quality_approved=False))
                    epsilon=1e-9 if initial_depth>SCREEN['max_sample_penetration_m'] or max(problem.depths)<SCREEN['max_sample_penetration_m'] else 0.
                    if max(r['max_depth_m'] for r in diagnostics)>cap+epsilon:
                        actual=-ProjectedTemporalSurface(fitter,frame,records).clearance(current,0.)[0]
                        ids=[(r['source'],r['target'],p[0]) for r in records for p in r['points']]
                        if len(actual)!=len(ids):raise ValueError('Witness identity order differs')
                        for key,depth in zip(ids,actual):
                            if depth>cap+epsilon and key not in groups.get(frame,set()):new_keys.append((frame,key))
                parts=np.split(current,[fitter.sizes[0]]);points=[a.rig.vertices(a.pose(fitter.event,v))@a.rotation.T+a.translation for a,v in zip(fitter.actors,parts)]
                region=measure(points,[a.patch for a in fitter.actors],problem.faces,SCREEN['max_contact_distance_m'])
                depths=[max(c['max_depth_m'] for c in sample['collision']) for sample in geometry]
                decision=select_step(problem.depths,depths,old_energy,new_energy,region)
                decision['hard_edit_bounds_pass']=bool(np.all(np.abs(current)<=fitter.bounds+1e-10) and inner['minimum_step_slack']>=-1e-8)
                decision['accepted']=decision['accepted'] and decision['hard_edit_bounds_pass']
                save(folder/'decision.json',dict(**decision,event_region=region,before_depths_m=problem.depths,after_depths_m=depths,new_witnesses=new_keys))
                history.append(dict(iteration=number,parameters=current.tolist(),window=geometry,solver=inner,decision=decision,
                    **{name+'_sha256':sha256(folder/(name+'.json')) for name in ['candidate','witnesses','geometry','decision']}))
                save(output/'history.json',dict(iterations=history,quality_approved=False))
                if decision['accepted']:selected=current.copy();accepted=True;reason='first_step_passing_unchanged_guard';break
                if not new_keys:reason='no_new_violating_witness_identities';break
                for frame,key in new_keys:groups.setdefault(frame,set()).add(key)
            save(output/'history.json',dict(iterations=history,quality_approved=False))
            save(output/'parameters.json',dict(controls=selected.tolist(),trajectory_values=fitter.values(selected).tolist(),control_bounds=fitter.bounds.tolist(),
                control_radii=fitter.control_radii.tolist(),basis=fitter.matrix.tolist(),minimum_constraint_slack=float(fitter.step_pair(selected)[0].min()),
                selection='accepted_step' if accepted else 'original_initializer_no_accepted_step',quality_approved=False))
        for path,digest in request['inputs'].items():
            if sha256(path)!=digest:raise ValueError('Input changed: '+path)
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:raise ValueError('Implementation changed: '+name)
        save(output/'completion.json',dict(at=now(),accepted_step=accepted,reason=reason,solved_rounds=len(history)-1,
            history_sha256=sha256(output/'history.json'),parameters_sha256=sha256(output/'parameters.json'),quality_approved=False))
        phase('complete_pending_export_and_full_geometry' if accepted else 'complete_no_accepted_step',reason=reason)
    except BaseException as exc:phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('proof',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.proof,a.output)
