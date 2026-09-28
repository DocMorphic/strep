"""Separate screen-preserving development trial; strict v1 remains unchanged."""
import numpy as np
from scipy.optimize import minimize
from paired_hand_clearance import correspondences
from paired_palm_region import contact_records,CorrespondenceEvaluator
from paired_hand_trajectory import TemporalSurface
from screen_path_guard import SCREEN,select_step
from verify_palm_region import measure


def refine(fitter,initial,faces,frames,iterations=3,progress=None,restoration=False):
    x=np.asarray(initial,dtype=float).copy();initial=x.copy();history=[]
    if x.shape!=fitter.bounds.shape or not np.isfinite(x).all() or np.any(np.abs(x)>fitter.bounds+1e-10) or fitter.step_pair(x)[0].min()<-1e-8:raise ValueError('Invalid trajectory seed')
    def scan(value):
        constraints=[];samples=[]
        for frame in frames:
            records,diagnostics=correspondences(fitter.actors,frame,value,faces,margin=.003)
            constraints.append(TemporalSurface(fitter,frame,records));samples.append(dict(frame=frame,collision=diagnostics))
        return constraints,samples
    for step in range(iterations+1):
        surfaces,samples=scan(x)
        event_values=fitter.event_map@x
        contact,metrics=contact_records(fitter.base.actors,fitter.event,event_values,faces)
        record=dict(iteration=step,parameters=x.tolist(),window=samples,contact=metrics,
            collision=next(s['collision'] for s in samples if s['frame']==fitter.event),minimum_step_slack=float(fitter.step_pair(x)[0].min()))
        if step:record.update(solver_success=bool(result.success),solver_message=str(result.message),solver_iterations=int(result.nit),step_trials=trials,
            restoration_slack_m=getattr(result,'restoration_slack_m',None),relaxed_constraint_min=getattr(result,'relaxed_constraint_min',None))
        history.append(record)
        if progress:progress(history)
        if step==iterations:break
        evaluator=CorrespondenceEvaluator(fitter.base,contact);cache=None;cached=None
        surface_count=sum(len(r['points']) for s in surfaces for r in s.records)
        def inequalities(value):
            nonlocal cache,cached
            if cache is None or not np.array_equal(cache,value):
                pairs=[s.clearance(value) for s in surfaces];pairs.append(fitter.step_pair(value))
                cached=(np.concatenate([p[0] for p in pairs]),np.vstack([p[1] for p in pairs]));cache=value.copy()
            return cached
        def objective(value):
            event=fitter.event_map@value;r,j=fitter.base.objective_pair(event);cr,cj=evaluator.contact(event)
            residual=np.r_[r,cr,(value-initial)*.1];jac=np.vstack([j@fitter.event_map,cj@fitter.event_map,np.eye(len(x))*.1])
            # Collision residual also guides a retained imperfect inner solve;
            # explicit inequalities remain in force and are checked separately.
            g,dg=inequalities(value);active=g<0
            # Step slack is dimensionless; keep its hard limit without mixing
            # it into the metre-valued surface penalty.
            count=surface_count
            residual=np.r_[residual,np.minimum(g[:count],0)*100]
            jac=np.vstack([jac,dg[:count]*active[:count,None]*100])
            return .5*float(residual@residual),jac.T@residual
        lower=np.maximum(-fitter.bounds,x-np.radians(5));upper=np.minimum(fitter.bounds,x+np.radians(5))
        if restoration:
            from elastic_hand_step import solve
            result=solve(objective,inequalities,x,lower,upper,surface_count)
        else:
            result=minimize(objective,x,jac=True,method='SLSQP',bounds=list(zip(lower,upper)),
                constraints=[dict(type='ineq',fun=lambda v:inequalities(v)[0],jac=lambda v:inequalities(v)[1])],options=dict(maxiter=60,ftol=1e-9))
        proposed=np.clip(result.x,lower,upper);trials=[]
        if not np.isfinite(proposed).all():raise ValueError('Nonfinite trajectory proposal')
        previous_depths=[max(c['max_depth_m'] for c in s['collision']) for s in samples];energy=objective(x)[0]
        for backtrack in range(8):
            alpha=2.**(-backtrack);candidate=x+alpha*(proposed-x);candidate_energy=objective(candidate)[0]
            if fitter.step_pair(candidate)[0].min()<-1e-8:
                trials.append(dict(alpha=alpha,accepted=False,reason='adjacent_edit_limit',parameters=candidate.tolist()));continue
            _,actual=scan(candidate);depths=[max(c['max_depth_m'] for c in s['collision']) for s in actual]
            parts=np.split(candidate,[fitter.sizes[0]])
            points=[a.rig.vertices(a.pose(fitter.event,v))@a.rotation.T+a.translation for a,v in zip(fitter.actors,parts)]
            region=measure(points,[a.patch for a in fitter.actors],faces,SCREEN['max_contact_distance_m'])
            decision=select_step(previous_depths,depths,energy,candidate_energy,region)
            trials.append(dict(alpha=alpha,accepted=decision['accepted'],depths_m=depths,energy=candidate_energy,
                parameters=candidate.tolist(),selection=decision,event_region=region))
            if decision['accepted']:x=candidate;break
    return x,history
