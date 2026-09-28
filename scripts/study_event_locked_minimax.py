"""Finite surface-path study: jointly reduce worst penetration with event locked."""
import argparse
from pathlib import Path
import shutil
import time
import traceback
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from load_contact_trial import load
from projected_temporal_surface import ProjectedTemporalSurface
from hull_surface_correspondences import correspondences
from event_locked_minimax import MinimaxStep


def run(study, component_audit, output):
    study, component_audit, output=[p.resolve() for p in (study,component_audit,output)]
    if output.exists():raise ValueError('Preserve previous experiment')
    recipe=read(study/'request.json');completed=read(study/'completion.json')
    if completed['parameters_sha256']!=sha256(study/'parameters.json'):raise ValueError('Starting controls changed')
    component=read(component_audit/'summary.json')
    if not component['complete'] or component['completed_states']!=7:raise ValueError('Completed component audit required')
    component_request=read(Path(component['study'])/'request.json');vertex_audit=Path(component_request['audit'])
    geometry=read(vertex_audit/'geometry-summary.json')
    raw_path=vertex_audit/'geometry/raw/samples.json'
    if next(r['samples_sha256'] for r in geometry['rows'] if r['variant']=='raw')!=sha256(raw_path):
        raise ValueError('Raw comparison geometry changed')
    raw={r['frame']:max(c['max_depth_m'] for c in r['collision']) for r in read(raw_path)['rows']}
    frames=recipe['frames'];surface_paths=[study/'round-01/surfaces'/f'after-{float(f)}.json' for f in frames]
    inputs=[study/n for n in ['request.json','completion.json','parameters.json','initial-parameters.json','A-source-local.npz','B-source-local.npz','palm-region.json']]
    inputs += [component_audit/'summary.json',Path(component['study'])/'request.json',vertex_audit/'geometry-summary.json',raw_path,*surface_paths]
    output.mkdir(parents=True);(output/'implementation').mkdir()
    names=sorted(set(recipe['implementation'])|{'event_locked_minimax.py','study_event_locked_minimax.py'})
    for name in names:
        if name in recipe['implementation'] and sha256(ROOT/'scripts'/name)!=recipe['implementation'][name]:
            raise ValueError('Starting implementation changed')
        shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    owner=psutil.Process()
    request=dict(at=now(),pid=owner.pid,created=owner.create_time(),study=str(study),component_audit=str(component_audit),
        inputs={str(p):sha256(p) for p in inputs},implementation={n:sha256(output/'implementation'/n) for n in names},
        frames=frames,rounds=3,trust_degrees=[1.,.5],solver_iterations=120,distance_scale_m=.005,regularizer=1e-4,
        minimum_peak_improvement_m=1e-6,query_margin_m=.003,quality_approved=False,
        scope='Development minimax objective over all retained near-surface vertices and30times, with fixed event controls. '
        'At most3rounds and2trust sizes per round. Fresh whole-mesh maximum must decrease, original hard edits and event skin must hold. '
        'Per-frame/raw regressions remain reported. No export, final5mm pass, full-clock or quality approval is implied.')
    save(output/'request.json',request)
    def phase(status,**details):
        save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**details));print(status,details,flush=True)
    try:
        with threadpool_limits(limits=1):
            _,fitter,faces,_=load(study)
            x=np.asarray(read(study/'parameters.json')['controls'],float)
            event_basis=fitter.matrix[fitter.event]
            if not np.array_equal(event_basis,[0,0,1,0,0]) or fitter.sizes!=[60,60]:raise ValueError('Unexpected event basis')
            locked=np.tile(np.repeat(event_basis!=0,12),2)
            def event_points(values):
                return [a.rig.vertices(a.pose(fitter.event,v))@a.rotation.T+a.translation
                        for a,v in zip(fitter.actors,np.split(values,[fitter.sizes[0]]))]
            original_event=event_points(x)
            current=[read(p) for p in surface_paths]
            start_depths=[max(c['max_depth_m'] for c in r['diagnostics']) for r in current]
            history=[];accepted_rounds=0;stop='round_budget_exhausted'
            for number in range(1,request['rounds']+1):
                folder=output/f'round-{number:02d}';folder.mkdir()
                gaps=[];jacobians=[];witnesses=[];linear_errors=[]
                for frame,record in zip(frames,current):
                    phase('linearizing',round=number,frame=frame)
                    surface=ProjectedTemporalSurface(fitter,frame,record['records']);g,j=surface.clearance(x,0.)
                    expected=max(c['max_depth_m'] for c in record['diagnostics'])
                    error=abs(max(0.,float((-g).max(initial=0)))-expected)
                    if error>1e-8:raise ValueError('Retained linearization differs from actual mesh depth')
                    gaps.append(g);jacobians.append(j);linear_errors.append(error)
                    witnesses.extend(dict(frame=frame,source=r['source'],target=r['target'],vertex=p[0])
                                     for r in record['records'] for p in r['points'])
                gap,jac=np.concatenate(gaps),np.vstack(jacobians)
                np.savez_compressed(folder/'linearization.npz',base=x,gaps=gap,jacobian=jac,locked=locked)
                save(folder/'witnesses.json',dict(rows=witnesses,depth_errors_m=linear_errors,quality_approved=False))
                old_peak=max(max(c['max_depth_m'] for c in r['diagnostics']) for r in current)
                accepted=False
                for trust in request['trust_degrees']:
                    attempt=folder/f'trust-{trust}';attempt.mkdir();(attempt/'surfaces').mkdir()
                    phase('solving',round=number,trust_degrees=trust,witnesses=len(gap))
                    solver=MinimaxStep(x,gap,jac,locked,fitter.bounds,fitter.step_pair,np.radians(trust),
                                       request['distance_scale_m'],request['regularizer'])
                    started=time.perf_counter();candidate,info=solver.solve(request['solver_iterations'])
                    info['seconds']=time.perf_counter()-started;info['controls']=candidate.tolist()
                    save(attempt/'solver.json',info)
                    hard=float(fitter.step_pair(candidate)[0].min())
                    valid=info['success'] and info['minimum_constraint_slack']>=-1e-8 and hard>=-1e-8
                    valid=valid and np.all(np.abs(candidate)<=fitter.bounds+1e-10) and info['locked_controls_exact']
                    valid=valid and all(np.array_equal(a,b) for a,b in zip(original_event,event_points(candidate)))
                    if not valid:
                        history.append(dict(round=number,trust_degrees=trust,accepted=False,reason='solver_or_hard_or_event_check_failed',solver_sha256=sha256(attempt/'solver.json')))
                        save(output/'history.json',dict(rows=history,quality_approved=False));continue
                    fresh=[]
                    for frame in frames:
                        phase('fresh_geometry',round=number,trust_degrees=trust,frame=frame)
                        records,diagnostics=correspondences(fitter.actors,frame,candidate,faces,margin=request['query_margin_m'])
                        record=dict(frame=frame,records=records,diagnostics=diagnostics);fresh.append(record)
                        save(attempt/'surfaces'/f'after-{float(frame)}.json',record)
                    depths=[max(c['max_depth_m'] for c in r['diagnostics']) for r in fresh]
                    accepted=max(depths)<old_peak-request['minimum_peak_improvement_m']
                    decision=dict(round=number,trust_degrees=trust,accepted=accepted,old_peak_m=old_peak,new_peak_m=max(depths),
                        raw_peak_m=max(raw[f] for f in frames),frames=frames,depths_m=depths,
                        frames_over_5mm=[f for f,d in zip(frames,depths) if d>.005],
                        raw_cap_regressions=[f for f,d in zip(frames,depths) if d>max(raw[f],.005)+2e-6],
                        event_geometry_exactly_preserved=True,minimum_hard_slack=hard,
                        solver_sha256=sha256(attempt/'solver.json'),quality_approved=False)
                    save(attempt/'decision.json',decision);history.append(decision)
                    save(output/'history.json',dict(rows=history,quality_approved=False))
                    if accepted:x=candidate;current=fresh;accepted_rounds+=1;break
                if not accepted:stop='no_accepted_step_at_fixed_trust_sizes';break
            save(output/'parameters.json',dict(controls=x.tolist(),locked_coordinates=np.flatnonzero(locked).tolist(),
                trajectory_values=fitter.values(x).tolist(),basis=fitter.matrix.tolist(),control_radii=fitter.control_radii.tolist(),
                control_bounds=fitter.bounds.tolist(),minimum_constraint_slack=float(fitter.step_pair(x)[0].min()),quality_approved=False))
            save(output/'summary.json',dict(initial_depths_m=start_depths,final_depths_m=[max(c['max_depth_m'] for c in r['diagnostics']) for r in current],
                frames=frames,accepted_rounds=accepted_rounds,reason=stop,quality_approved=False))
        for path,digest in request['inputs'].items():
            if sha256(path)!=digest:raise ValueError('Input changed')
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:raise ValueError('Implementation changed')
        save(output/'completion.json',dict(at=now(),accepted_rounds=accepted_rounds,reason=stop,summary_sha256=sha256(output/'summary.json'),
             parameters_sha256=sha256(output/'parameters.json'),history_sha256=sha256(output/'history.json'),quality_approved=False))
        phase('complete')
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for n in ['study','component_audit','output']:parser.add_argument(n,type=Path)
    args=parser.parse_args();run(args.study,args.component_audit,args.output)
