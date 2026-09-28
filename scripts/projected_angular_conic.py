"""Box-projected conic proposals; unchanged actual angular and foot safeguards."""
import numpy as np
from scipy import sparse
from conic_root_descent import solver_module,cone_rows,tightened_cap,affine_constraints as foot_constraints


def affine_constraints(p,x,quantized=True):
    c,j,cones=foot_constraints(p,x,quantized)
    cones=[v for v in cones if v['kind']!='root_acceleration']
    vectors,derivative=p.angular_pair(x,quantized)
    for index in p.edges-1:
        for joint in range(len(p.fitter.nodes)):
            cap=p.rotation_caps[index,joint]
            cones.append(dict(vector=vectors[index,joint],jacobian=derivative[index,joint],cap=float(cap),scale=max(float(cap),1e-3),kind='angular_step'))
    return c,j,cones


def project_step(x,delta,bounds,trust):
    x,delta,bounds=[np.asarray(v,float) for v in (x,delta,bounds)]
    if x.shape!=delta.shape or x.shape!=bounds.shape or not all(np.isfinite(v).all() for v in (x,delta,bounds)) or not np.isfinite(trust) or trust<=0 or np.any(bounds<0):
        raise ValueError('Finite matching coordinates and nonnegative bounds required')
    lower=np.maximum(-trust,-bounds-x);upper=np.minimum(trust,bounds-x)
    if np.any(lower>upper):raise ValueError('Current coordinates cannot reach the original box within trust')
    return np.clip(delta,lower,upper)


def direction(p,x,trust,buffers=None):
    clarabel=solver_module();evaluation=p.evaluate(x);g=evaluation[1]
    if not np.isfinite(g).all() or np.max(np.abs(g))==0:return None,dict(status='ZeroGradient',trust=trust)
    c,j,cones=affine_constraints(p,x);bounds=np.tile(p.fitter.bounds[p.free],len(p.frames))
    lower=np.maximum(-1.,(-bounds-x)/trust);upper=np.minimum(1.,(bounds-x)/trust)
    mats=[-sparse.csc_matrix(j*trust),sparse.eye(len(x),format='csc'),-sparse.eye(len(x),format='csc')]
    rhs=[c,upper,-lower];types=[clarabel.NonnegativeConeT(len(c)+2*len(x))]
    for item in cones:
        a,b=cone_rows(item['vector'],item['jacobian'],tightened_cap(item,buffers),item['scale'],trust);mats.append(a);rhs.append(b);types.append(clarabel.SecondOrderConeT(len(b)))
    settings=clarabel.DefaultSettings();settings.verbose=False;settings.max_iter=100;settings.time_limit=30.
    settings.tol_gap_abs=settings.tol_gap_rel=settings.tol_feas=1e-10
    if hasattr(settings,'max_threads'):settings.max_threads=1
    solver=clarabel.DefaultSolver(sparse.eye(len(x),format='csc')*1e-4,g/np.max(np.abs(g)),sparse.vstack(mats,format='csc'),np.concatenate(rhs),types,settings)
    result=solver.solve();delta=np.asarray(result.x)*trust
    record=dict(status=str(result.status),iterations=result.iterations,trust=trust,linear_rows=len(c),norm_cones=len(cones),
        predicted_objective_change=float(g@delta),max_coordinate_step=float(np.abs(delta).max()),proposal_buffers=buffers or {},
        tightened_cones=sum(tightened_cap(t,buffers)<t['cap'] for t in cones))
    # A solver status is proposal metadata, never final animation acceptance.
    if str(result.status) not in ['Solved','AlmostSolved'] or not np.isfinite(delta).all():return None,record
    raw=delta.copy();delta=project_step(x,delta,bounds,trust)
    record.update(raw_proposed_delta=raw.tolist(),raw_max_coordinate_step=record['max_coordinate_step'],max_projection_change=float(np.abs(delta-raw).max()),max_coordinate_step=float(np.abs(delta).max()),predicted_objective_change=float(g@delta))
    record['predicted_linear_minimum']=float((c+j@delta).min())
    record['predicted_norm_max_excess']=max(float(np.linalg.norm(t['vector']+t['jacobian']@delta)-t['cap'])/t['scale'] for t in cones)
    record['predicted_buffered_norm_max_excess']=max(float(np.linalg.norm(t['vector']+t['jacobian']@delta)-tightened_cap(t,buffers))/t['scale'] for t in cones)
    return delta,record


def solve(p,steps,trusts,progress,buffers,schedule):
    x=p.initial[np.ix_(p.frames,p.free)].ravel();initial=x.copy();before=p.evaluate(x);history=[]
    if before[2].min()<-1e-8 or not p.geometric_guard(before[5]):raise ValueError('Strictly feasible source required')
    for iteration in range(steps):
        current=p.evaluate(x)
        if current[0]==0.:break
        attempts=[];accepted=False
        for entry in schedule:
            trust=entry['trust'];chosen={k:v*entry['buffer_scale'] for k,v in buffers.items()}
            delta,record=direction(p,x,trust,chosen);record['trials']=[];record['buffer_scale']=entry['buffer_scale']
            if delta is not None and record['predicted_objective_change']<0:
                record['proposed_delta']=delta.tolist()
                for index in range(8):
                    alpha=.5**index;trial=p.evaluate(x+alpha*delta)
                    feasible=bool(np.isfinite(trial[0]) and np.isfinite(trial[2]).all() and trial[2].min()>=-1e-8)
                    geometry=p.geometric_guard(trial[5]) if feasible else False;good=bool(feasible and geometry and trial[0]<current[0]-1e-9)
                    record['trials'].append(dict(fraction=alpha,objective=trial[0],minimum_constraint=float(trial[2].min()),geometry=geometry,accepted=good))
                    if good:x+=alpha*delta;accepted=True;break
            attempts.append(record)
            if accepted:break
        history.append(dict(iteration=iteration+1,objective_before=current[0],attempts=attempts,accepted=accepted))
        if progress:progress(dict(iteration=iteration+1,accepted=accepted,objective=p.evaluate(x)[0]))
        if not accepted:break
    final=p.evaluate(x)
    return p.values(x),dict(method='scheduled_conic_descent',steps_limit=steps,trusts=list(trusts),proposal_buffers=buffers or {},history=history,
        starting_coordinates=initial.tolist(),final_coordinates=x.tolist(),variable_frames=p.frames.tolist(),free_columns=p.free.tolist(),
        objective_before=before[0],objective_after=final[0],minimum_constraint=float(final[2].min()),target_satisfied=final[0]==0.,quality_approved=False)
