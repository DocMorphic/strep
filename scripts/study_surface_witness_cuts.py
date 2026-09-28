"""Add feasible fresh contact witnesses while preserving the original objective."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import time
import traceback
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from contact_restoration_problem import FrozenContactProblem
from projected_temporal_surface import ProjectedTemporalSurface
from hull_surface_correspondences import correspondences
from scaled_frame_restoration import solve
from surface_witness_cuts import select
from screen_path_guard import SCREEN,select_step
from verify_palm_region import measure


def run(hull,diagnostic,output):
    hull,diagnostic,output=[Path(p).resolve() for p in (hull,diagnostic,output)]
    hreq=read(hull/'request.json');hdone=read(hull/'completion.json')
    if hdone['comparisons']!=33 or hdone['results_sha256']!=sha256(hull/'results.json'):raise ValueError('Hull proof incomplete/changed')
    projected=Path(hreq['proof']);prior=Path(hreq['changed']);preq=read(prior/'request.json');pdone=read(prior/'completion.json')
    candidate=read(prior/'candidate.json');decision=read(prior/'decision.json')
    if (pdone['candidate_sha256']!=sha256(prior/'candidate.json') or pdone['decision_sha256']!=sha256(prior/'decision.json')
        or pdone['geometry_sha256']!=sha256(prior/'geometry.json') or hreq['changed_candidate_sha256']!=sha256(prior/'candidate.json')
        or hreq['proof_request_sha256']!=sha256(projected/'request.json') or hreq['proof_completion_sha256']!=sha256(projected/'completion.json')):
        raise ValueError('Scaled diagnostic does not match verified hull/projection inputs')
    summary=read(diagnostic/'summary.json')
    if (read(diagnostic/'completion.json')['summary_sha256']!=sha256(diagnostic/'summary.json')
        or summary['proof_completion_sha256']!=sha256(hull/'completion.json')):raise ValueError('Surface diagnostic changed')
    for row in summary['rows']:
        if sha256(hull/'surfaces'/f"changed-{float(row['frame'])}.json")!=row['fresh_correspondences_sha256']:
            raise ValueError('Cached fresh witness changed')
    source=Path(read(projected/'request.json')['source']);recipe=read(source/'request.json')
    names=sorted(set(hreq['implementation'])|set(preq['implementation'])|{
        'study_surface_witness_cuts.py','contact_restoration_problem.py','load_contact_trial.py','surface_witness_cuts.py'})
    for parent,parent_request in [(hull,hreq),(prior,preq)]:
        for name,digest in parent_request['implementation'].items():
            if sha256(parent/'implementation'/name)!=digest or sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Verified implementation changed: '+name)
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    for name in ['initial-parameters.json','palm-region.json','A-source-local.npz','B-source-local.npz','scene.json']:
        shutil.copyfile(source/name,output/name)
    proc=psutil.Process();request=copy.deepcopy(recipe)
    request.update(at=now(),pid=proc.pid,created=proc.create_time(),method='guard_witness_constraint_enrichment',
        source_study=str(source),source_request_sha256=sha256(source/'request.json'),
        hull_proof=str(hull),hull_request_sha256=sha256(hull/'request.json'),hull_completion_sha256=sha256(hull/'completion.json'),
        starting_candidate_study=str(prior),starting_candidate_sha256=sha256(prior/'candidate.json'),starting_completion_sha256=sha256(prior/'completion.json'),
        surface_diagnostic=str(diagnostic),surface_diagnostic_completion_sha256=sha256(diagnostic/'completion.json'),
        max_witness_rounds=3,inner_maxiter=60,objective_scale=1000.,solver_ftol=1e-12,clearance_margin_m=.001,query_margin_m=.003,
        initial_control_neighborhood_degrees=5.,selection_screen=SCREEN,
        implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False,
        scope='Same original core rows and motion objective; added fresh guard-violating rows are inequalities only. All original bounds and final screens retained. Each new row must permit the original seed. Three rounds maximum, every proposal gets all30 fresh fitting times. Accepted step still requires full exported/engine/human validation; root/legs/floor unchanged.')
    save(output/'request.json',request)
    def phase(status,**details):save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**details));print(status,details,flush=True)
    try:
        with threadpool_limits(limits=1):
            problem=FrozenContactProblem(projected);fitter=problem.fitter;initial=problem.initial
            if problem.frames!=preq['frames'] or problem.frames!=recipe['frames']:raise ValueError('Diagnostic clock differs')
            old_energy=problem.objective(initial)[0];current=np.asarray(candidate['controls']);energy=problem.objective(current)[0]
            if abs(old_energy-candidate['old_energy'])>1e-7 or abs(energy-candidate['new_energy'])>1e-7:raise ValueError('Original motion objective differs')
            if not np.array_equal(problem.budgets,read(prior/'budgets.json')['row_budgets_m']):raise ValueError('Core restoration budgets differ')
            current_geometry=read(prior/'geometry.json')['rows']
            if [r['frame'] for r in current_geometry]!=problem.frames:raise ValueError('Starting geometry incomplete')
            cached={r['frame']:read(hull/'surfaces'/f"changed-{float(r['frame'])}.json") for r in summary['rows']}
            history=[read(projected/'initial-history.json')];cuts=[];seen=set();accepted=False;reason='round_budget_exhausted';selected_controls=initial.copy()
            for number in range(1,request['max_witness_rounds']+1):
                folder=output/f'round-{number:02d}';folder.mkdir();(folder/'surfaces').mkdir()
                new_batches=[];witness_log=[];infeasible=False
                for frame,previous_depth,cap,current_sample in zip(problem.frames,problem.depths,problem.caps,current_geometry):
                    epsilon=1e-9 if previous_depth>SCREEN['max_sample_penetration_m'] or max(problem.depths)<SCREEN['max_sample_penetration_m'] else 0.
                    depth=max(c['max_depth_m'] for c in current_sample['collision'])
                    if depth<=cap+epsilon:continue
                    phase('refreshing_failed_surface',round=number,frame=frame)
                    if frame in cached:
                        fresh=cached[frame];records,diagnostics=fresh['records'],fresh['diagnostics'];origin='retained_matching_candidate'
                    else:
                        records,diagnostics=correspondences(fitter.actors,frame,current,problem.faces,margin=.003);origin='fresh_query'
                    for actual,expected in zip(diagnostics,current_sample['collision']):
                        for key in ['source','target','active_constraints','vertices_over_5mm']:
                            if actual[key]!=expected[key]:raise ValueError('Refreshed witness population differs')
                        if abs(actual['max_depth_m']-expected['max_depth_m'])>1e-10:raise ValueError('Refreshed witness depths differ')
                    full=ProjectedTemporalSurface(fitter,frame,records)
                    actual_depths=-full.clearance(current,0.)[0];seed_depths=-full.clearance(initial,0.)[0]
                    if abs(float(np.max(actual_depths,initial=0.))-depth)>1e-10:raise ValueError('Witness projection does not reconstruct measured depth')
                    chosen,selection=select(records,actual_depths,seed_depths,float(cap),epsilon)
                    save(folder/'surfaces'/f'before-{float(frame)}.json',dict(frame=frame,controls=current.tolist(),records=records,diagnostics=diagnostics,origin=origin))
                    log=dict(frame=frame,cap_m=float(cap),**selection,records=chosen);witness_log.append(log)
                    if not selection['seed_feasible']:infeasible=True
                    if selection['selected_rows']:
                        digest=hashlib.sha256(json.dumps(dict(frame=frame,records=chosen),sort_keys=True).encode()).hexdigest()
                        if digest not in seen:
                            new_batches.append((ProjectedTemporalSurface(fitter,frame,chosen),float(cap)));seen.add(digest)
                save(folder/'witnesses.json',dict(rows=witness_log,seed_feasible=not infeasible,quality_approved=False))
                if infeasible:
                    reason='refreshed_witness_infeasible_at_original_seed';break
                if not new_batches:
                    reason='no_new_depth_witnesses';break
                cuts.extend(new_batches);budgets=problem.augmented_budgets(cuts)
                phase('solving',round=number,core_rows=problem.count,cut_rows=len(budgets)-problem.count)
                start=time.perf_counter()
                result=solve(problem.objective,lambda value:problem.inequalities(value,cuts),initial,problem.lower,problem.upper,budgets)
                current=np.clip(result.x,problem.lower,problem.upper)
                if not np.isfinite(current).all():raise ValueError('Nonfinite witness-cut proposal')
                new_energy=problem.objective(current)[0]
                inner=dict(success=bool(result.success),message=str(result.message),iterations=int(result.nit),seconds=time.perf_counter()-start,
                    restoration_fraction=result.restoration_fraction,relaxed_constraint_min=result.relaxed_constraint_min,
                    core_rows=problem.count,cut_rows=len(budgets)-problem.count,old_energy=old_energy,new_energy=new_energy,
                    controls=current.tolist(),minimum_step_slack=float(fitter.step_pair(current)[0].min()),quality_approved=False)
                save(folder/'candidate.json',inner)
                current_geometry=[];cached={}
                for frame in problem.frames:
                    phase('fresh_geometry',round=number,frame=frame,completed_frames=len(current_geometry))
                    records,diagnostics=correspondences(fitter.actors,frame,current,problem.faces,margin=.003)
                    fresh=dict(frame=frame,records=records,diagnostics=diagnostics);cached[frame]=fresh
                    save(folder/'surfaces'/f'after-{float(frame)}.json',fresh)
                    current_geometry.append(dict(frame=frame,collision=diagnostics));save(folder/'geometry.json',dict(rows=current_geometry,quality_approved=False))
                parts=np.split(current,[fitter.sizes[0]])
                points=[a.rig.vertices(a.pose(fitter.event,v))@a.rotation.T+a.translation for a,v in zip(fitter.actors,parts)]
                region=measure(points,[a.patch for a in fitter.actors],problem.faces,SCREEN['max_contact_distance_m'])
                depths=[max(c['max_depth_m'] for c in sample['collision']) for sample in current_geometry]
                decision=select_step(problem.depths,depths,old_energy,new_energy,region)
                decision['hard_edit_bounds_pass']=bool(np.all(np.abs(current)<=fitter.bounds+1e-10) and inner['minimum_step_slack']>=-1e-8)
                decision['accepted']=decision['accepted'] and decision['hard_edit_bounds_pass']
                save(folder/'decision.json',dict(**decision,event_region=region,before_depths_m=problem.depths,after_depths_m=depths))
                history.append(dict(iteration=number,parameters=current.tolist(),window=current_geometry,solver=inner,decision=decision,
                    candidate_sha256=sha256(folder/'candidate.json'),witnesses_sha256=sha256(folder/'witnesses.json'),geometry_sha256=sha256(folder/'geometry.json'),decision_sha256=sha256(folder/'decision.json')))
                save(output/'history.json',dict(iterations=history,quality_approved=False))
                if decision['accepted']:
                    selected_controls=current.copy();accepted=True;reason='first_step_passing_unchanged_guard';break
            save(output/'history.json',dict(iterations=history,quality_approved=False))
            save(output/'parameters.json',dict(controls=selected_controls.tolist(),trajectory_values=fitter.values(selected_controls).tolist(),
                control_bounds=fitter.bounds.tolist(),control_radii=fitter.control_radii.tolist(),basis=fitter.matrix.tolist(),
                minimum_constraint_slack=float(fitter.step_pair(selected_controls)[0].min()),selection='accepted_step' if accepted else 'original_initializer_no_accepted_step',quality_approved=False))
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:raise ValueError('Implementation changed')
        for path,digest in [(hull/'request.json',request['hull_request_sha256']),(hull/'completion.json',request['hull_completion_sha256']),
            (prior/'candidate.json',request['starting_candidate_sha256']),(prior/'completion.json',request['starting_completion_sha256']),
            (diagnostic/'completion.json',request['surface_diagnostic_completion_sha256']),(source/'request.json',request['source_request_sha256'])]:
            if sha256(path)!=digest:raise ValueError('Input evidence changed')
        save(output/'completion.json',dict(at=now(),accepted_step=accepted,reason=reason,solved_rounds=len(history)-1,
            history_sha256=sha256(output/'history.json'),parameters_sha256=sha256(output/'parameters.json'),quality_approved=False))
        phase('complete_pending_export_and_full_geometry' if accepted else 'complete_no_accepted_step',reason=reason)
    except BaseException as exc:phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['hull','diagnostic','output']:p.add_argument(name,type=Path)
    a=p.parse_args();run(a.hull,a.diagnostic,a.output)
