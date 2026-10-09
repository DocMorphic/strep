"""Trust-box proposals retained only by complete nonlinear inequality replay.

Feasible rows remain feasible. Rowwise mode protects individual failures; merit
mode permits explicitly selected failed-row tradeoffs with improving complete
scores. Linear or nonlinear proposal subproblems never approve a pose.
"""
import time
import numpy as np
from scipy.optimize import minimize,linprog


def score(slacks):
    values=np.asarray(slacks,dtype=float)
    if values.ndim!=1 or not len(values) or not np.isfinite(values).all():
        raise ValueError('Complete finite inequality population required')
    violation=np.maximum(-values,0)
    return float(violation.max()),float(violation@violation)


def tradeoff_rows(size,policy,mask):
    if policy not in ['rowwise','merit']:raise ValueError('Explicit failed-row policy required')
    if mask is None:return np.ones(size,dtype=bool) if policy=='merit' else np.zeros(size,dtype=bool)
    result=np.asarray(mask)
    if result.dtype!=bool or result.shape!=(size,):raise ValueError('Complete Boolean tradeoff-row mask required')
    return result.copy() if policy=='merit' else np.zeros(size,dtype=bool)


def retain(before,after,*,failure_policy='rowwise',tradeoff_mask=None):
    before=np.asarray(before,dtype=float);after=np.asarray(after,dtype=float)
    old=score(before);new=score(after)
    if after.shape!=before.shape:raise ValueError('Original inequality population must be retained')
    allowed=tradeoff_rows(len(before),failure_policy,tradeoff_mask)&(before<0)
    protected=~allowed
    improved=new[1]<old[1]-1e-12 or (np.all(after>=0) and np.any(before<0))
    return bool(np.all(after[protected]>=np.minimum(before[protected],0)) and new[0]<=old[0] and improved)


def _linear_feasible_start(values,jac,caps,lower,upper,seconds):
    """Smallest L1 step inside the complete first-order proposal system."""
    size=len(lower);eye=np.eye(size);zeros=np.zeros_like(jac)
    maximum=np.maximum(np.abs(lower),np.abs(upper))
    started=time.monotonic()
    result=linprog(np.r_[np.zeros(size),np.ones(size)],
        A_ub=np.block([[-jac,zeros],[eye,-eye],[-eye,-eye]]),
        b_ub=np.r_[values-caps,np.zeros(2*size)],
        bounds=list(zip(lower,upper))+list(zip(np.zeros(size),maximum)),method='highs',
        options=dict(time_limit=min(20.,seconds),primal_feasibility_tolerance=1e-9,dual_feasibility_tolerance=1e-9))
    report=dict(status=int(result.status),success=bool(result.success),message=str(result.message),
        seconds=time.monotonic()-started,time_limit_seconds=min(20.,seconds),
        objective='Minimum L1 normalized step',caps=caps.tolist(),lower_delta=lower.tolist(),upper_delta=upper.tolist(),
        scope='First-order proposal initialization only. No nonlinear feasibility, retained-step or path certificate.')
    if not result.success:return None,report
    raw=np.asarray(result.x,dtype=float)
    if raw.shape!=(2*size,) or not np.isfinite(raw).all():raise ValueError('Complete finite linear-start controls required')
    if (np.any(raw[size:]< -1e-8) or np.any(raw[size:]+1e-8<np.abs(raw[:size]))
            or np.any(raw[:size]<lower-1e-8) or np.any(raw[:size]>upper+1e-8)):
        raise ValueError('Linear start violated original step or auxiliary bounds')
    delta=np.clip(raw[:size],lower,upper);slack=values+jac@delta-caps
    if not np.isfinite(slack).all() or np.any(slack< -1e-8):raise ValueError('Linear start failed complete first-order replay')
    report.update(raw_delta=raw[:size].tolist(),delta=delta.tolist(),minimum_linear_slack=float(slack.min()),
        clipped_to_step_bounds=bool(np.any(delta!=raw[:size])),l1_step=float(np.abs(delta).sum()))
    return delta,report


def _geometry_descent_start(values,jac,caps,lower,upper,seconds,vectors):
    """Convex vector-distance proposal with a complete merit descent check."""
    offsets=np.asarray(vectors['offsets'],dtype=float);derivatives=np.asarray(vectors['jacobian'],dtype=float)
    radii=np.asarray(vectors['limits'],dtype=float);scales=np.asarray(vectors['scales'],dtype=float)
    rows=np.asarray(vectors['rows']);distance=np.asarray(vectors['distance'])
    count=len(radii);size=len(lower)
    if (not count or offsets.shape!=(count,3) or derivatives.shape!=(count,3,size)
            or scales.shape!=(count,) or rows.shape!=(count,) or rows.dtype.kind not in 'iu'
            or distance.shape!=(count,) or distance.dtype!=bool or np.any(rows<0) or np.any(rows>=len(values))
            or not np.isfinite(np.r_[offsets.ravel(),derivatives.ravel(),radii,scales]).all()
            or np.any(radii<=0) or np.any(scales<=0)):
        raise ValueError('Complete finite vector-distance controls, row identities and scales required')
    length=np.linalg.norm(offsets,axis=1)
    vector_values=np.where(distance,(radii-length)/scales,1-length**2/radii**2)
    envelope=np.full(len(values),np.inf);np.minimum.at(envelope,rows,vector_values);covered=np.isfinite(envelope)
    np.testing.assert_allclose(envelope[covered],values[covered],rtol=1e-10,atol=1e-10)
    effective=np.empty_like(radii);effective[distance]=radii[distance]-scales[distance]*caps[rows[distance]]
    effective[~distance]=radii[~distance]*np.sqrt(np.maximum(1-caps[rows[~distance]],0))
    limit=min(20.,seconds);started=time.monotonic();gradient=2*jac.T@np.minimum(values,0)
    report=dict(objective='Minimize first-order squared violation with vector-norm feasibility',
        caps=caps.tolist(),lower_delta=lower.tolist(),upper_delta=upper.tolist(),time_limit_seconds=limit,
        gradient=gradient.tolist(),vectors={k:np.asarray(vectors[k]).tolist() for k in ['offsets','jacobian','limits','scales','rows','distance']},
        scope='Vector-affine geometry and first-order merit only; no nonlinear feasibility, retained-step or path certificate.')
    if np.any(effective<=0):return None,dict(report,success=False,status='empty_vector_radius',seconds=time.monotonic()-started)
    # Convex norm balls admit global supporting-plane relaxations. Replay every
    # ball after each LP; cut-system feasibility alone never supplies a start.
    planes=[];bounds=[];cuts=[];report.update(algorithm='Norm-ball supporting planes',cuts=cuts,effective_radii=effective.tolist())
    for iteration in range(64):
        remaining=limit-(time.monotonic()-started)
        if remaining<=0:return None,dict(report,success=False,status='geometry_start_time_guard',seconds=time.monotonic()-started)
        result=linprog(gradient,A_ub=np.vstack([-jac,*planes]) if planes else -jac,
            b_ub=np.concatenate([values-caps,*bounds]),bounds=list(zip(lower,upper)),method='highs',
            options=dict(time_limit=remaining,primal_feasibility_tolerance=1e-9,dual_feasibility_tolerance=1e-9))
        report['linear_status']=int(result.status)
        if not result.success:return None,dict(report,success=False,status='linear_start_unavailable',seconds=time.monotonic()-started)
        raw=np.asarray(result.x,dtype=float)
        if raw.shape!=(size,) or not np.isfinite(raw).all():raise ValueError('Finite complete geometry start required')
        if np.any(raw<lower-1e-8) or np.any(raw>upper+1e-8):raise ValueError('Geometry start violated original step bounds')
        delta=np.clip(raw,lower,upper);slack=values+jac@delta-caps
        if np.any(slack< -1e-8):raise ValueError('Geometry start failed complete linear replay')
        point=offsets+np.einsum('rkd,d->rk',derivatives,delta);length=np.linalg.norm(point,axis=1)
        balls=1-length**2/effective**2;descent=float(gradient@delta)
        report.update(raw_delta=raw.tolist(),delta=delta.tolist(),minimum_linear_slack=float(slack.min()),
            minimum_vector_slack=float(balls.min()),directional_merit=descent,seconds=time.monotonic()-started)
        if descent>=-1e-8:return None,dict(report,success=False,status='no_checked_geometry_descent')
        if np.all(balls>=-1e-8):return delta,dict(report,success=True,status='usable')
        ids=np.argsort(balls)[:32];ids=ids[balls[ids]<-1e-8]
        normal=point[ids]/length[ids,None]
        plane=np.einsum('rk,rkd->rd',normal,derivatives[ids])/effective[ids,None]
        bound=np.einsum('rd,d->r',plane,delta)-(length[ids]/effective[ids]-1)
        planes.append(plane);bounds.append(bound)
        cuts.append(dict(iteration=iteration+1,controls_delta=delta.tolist(),vector_indices=ids.tolist(),planes=plane.tolist(),bounds=bound.tolist()))
    return None,dict(report,success=False,status='geometry_cut_iteration_guard',seconds=time.monotonic()-started)


def fit(measure,linearize,seed,lower,upper,*,iterations=30,trust=.03,solve_iterations=100,
        seconds=300,maximum_calls=1000,observer=None,failure_policy='rowwise',tradeoff_mask=None,
        proposal='linear',proposal_feasible_mask=None,proposal_headroom=None,proposal_tangent_guard=False,proposal_start='zero',vectorize=None,record_store=None):
    seed=np.asarray(seed,dtype=float);lower=np.asarray(lower,dtype=float);upper=np.asarray(upper,dtype=float)
    if (seed.ndim!=1 or not len(seed) or lower.shape!=seed.shape or upper.shape!=seed.shape
            or not np.isfinite(np.r_[seed,lower,upper]).all() or np.any(lower>=upper)
            or np.any(seed<lower) or np.any(seed>upper)
            or type(iterations) is not int or not 1<=iterations<=100
            or type(solve_iterations) is not int or not 1<=solve_iterations<=300
            or type(maximum_calls) is not int or not 1<=maximum_calls<=10000
            or type(trust) not in (int,float) or not np.isfinite(trust) or not 1e-5<=trust<=.3
            or type(seconds) not in (int,float) or not np.isfinite(seconds) or not 1<=seconds<=1800
            or failure_policy not in ['rowwise','merit'] or proposal not in ['linear','nonlinear']
            or proposal_start not in ['zero','linear-feasible','geometry-descent'] or (proposal_start!='zero' and proposal!='nonlinear')
            or (proposal_start=='geometry-descent' and not callable(vectorize)) or (proposal_start!='geometry-descent' and vectorize is not None)
            or (record_store is not None and not callable(record_store))
            or type(proposal_tangent_guard) is not bool or (proposal_tangent_guard and proposal!='nonlinear')):
        raise ValueError('Finite seed, matching control bounds and explicit step budgets required')
    started=time.monotonic();calls=0;history=[];trials=[];queries=[];clips=[];linearizations=[];starts=[];value=seed.copy()
    def store_record(kind,record):return record if record_store is None else record_store(kind,record)
    class Exhausted(Exception):pass
    def check():
        if calls>=maximum_calls or time.monotonic()-started>=seconds:raise Exhausted()
    def observed(candidate):
        nonlocal calls
        check();calls+=1;result=np.asarray(measure(candidate),dtype=float);score(result)
        return result
    baseline=observed(value);mask=tradeoff_rows(len(baseline),failure_policy,tradeoff_mask)
    feasible=np.zeros(len(baseline),dtype=bool) if proposal_feasible_mask is None else np.asarray(proposal_feasible_mask)
    headroom=np.zeros(len(baseline)) if proposal_headroom is None else np.asarray(proposal_headroom,dtype=float)
    if (feasible.shape!=baseline.shape or feasible.dtype!=bool or headroom.shape!=baseline.shape
            or not np.isfinite(headroom).all() or np.any(headroom<0) or np.any(headroom>1e-3)):
        raise ValueError('Complete Boolean proposal feasibility mask and bounded finite headroom required')
    current=baseline.copy();stop='iteration_limit'
    if observer:observer('seed',value.copy(),current.copy(),False)
    try:
        for iteration in range(iterations):
            check()
            if np.all(current>=0):stop='inequalities_satisfied';break
            values,jac=linearize(value)
            values=np.asarray(values,dtype=float);jac=np.asarray(jac,dtype=float)
            if (values.shape!=current.shape or jac.shape!=(len(current),len(value))
                    or not np.isfinite(jac).all() or not np.isfinite(values).all()):
                raise ValueError('Every original nonlinear row and derivative required')
            np.testing.assert_allclose(values,current,rtol=1e-10,atol=1e-10)
            caps=np.minimum(current,0)
            caps[mask&(current<0)]=-score(current)[0]
            caps[feasible]=np.maximum(caps[feasible],0)
            caps+=headroom
            hard=~(mask&(current<0));preservation=np.minimum(current,0)
            if proposal_tangent_guard:
                # Search-only interior margin; retained tangents still use the
                # exact preservation caps. This is not a continuous-path gate.
                tangent_caps=preservation[hard]+1e-6
            if proposal_tangent_guard or proposal_start!='zero':
                linearizations.append(store_record('linearization',dict(iteration=iteration+1,controls=value.tolist(),slacks=current.tolist(),
                    jacobian=jac.tolist(),protected_rows=np.flatnonzero(hard).tolist(),
                    preservation_caps=preservation[hard].tolist(),tangent_proposal_caps=tangent_caps.tolist() if proposal_tangent_guard else None)))
            candidate_lower=np.maximum(lower,value-trust);candidate_upper=np.minimum(upper,value+trust)
            def bounded_candidate(delta):
                delta=np.asarray(delta,dtype=float)
                if delta.shape!=value.shape or not np.isfinite(delta).all():
                    raise ValueError('Finite complete nonlinear proposal query required')
                raw=value+delta;candidate=np.clip(raw,candidate_lower,candidate_upper)
                if not np.array_equal(raw,candidate):
                    clips.append(dict(iteration=iteration+1,requested_controls=raw.tolist(),bounded_controls=candidate.tolist()))
                return candidate
            cached=(np.zeros_like(value),current,jac)
            def query(delta):
                nonlocal cached
                check();candidate=bounded_candidate(delta);delta=candidate-value
                if np.array_equal(delta,cached[0]):return cached[1:]
                actual=observed(candidate);predicted,derivatives=linearize(candidate)
                predicted=np.asarray(predicted,dtype=float);derivatives=np.asarray(derivatives,dtype=float)
                if (actual.shape!=current.shape or predicted.shape!=current.shape
                        or derivatives.shape!=jac.shape or not np.isfinite(derivatives).all()):
                    raise ValueError('Every original nonlinear row and derivative required')
                np.testing.assert_allclose(predicted,actual,rtol=1e-10,atol=1e-10)
                label=f'iteration-{iteration+1}-query-{len(queries)+1}'
                queries.append(dict(label=label,iteration=iteration+1,controls=candidate.tolist(),
                    score=list(score(actual)),retained=False))
                if observer:observer(label,candidate.copy(),actual.copy(),False)
                cached=(delta.copy(),actual,derivatives)
                return actual,derivatives
            def objective(delta):
                check()
                if proposal=='nonlinear':delta=bounded_candidate(delta)-value
                # Solver-only headroom prevents stopping just below zero;
                # replay still uses each exact original inequality threshold.
                actual,derivatives=query(delta) if proposal=='nonlinear' else (current+jac@delta,jac)
                residual=np.minimum(actual-1e-6,0)
                return float(residual@residual+1e-8*(delta@delta)),2*(derivatives.T@residual+1e-8*delta)
            bounds=list(zip(candidate_lower-value,candidate_upper-value))
            constraints=[dict(type='ineq',
                    fun=lambda delta:(query(delta)[0] if proposal=='nonlinear' else current+jac@delta)-caps,
                    jac=lambda delta:query(delta)[1] if proposal=='nonlinear' else jac)]
            if proposal_tangent_guard and hard.any():
                constraints.append(dict(type='ineq',fun=lambda delta:current[hard]+jac[hard]@delta-tangent_caps,
                    jac=lambda delta:jac[hard]))
            def attempt(direction,stage):
                nonlocal value,current
                for fraction in [1.,.5,.25,.125,.0625,.03125,.015625,.0078125]:
                    candidate=value+fraction*direction
                    if proposal=='nonlinear':candidate=np.clip(candidate,candidate_lower,candidate_upper)
                    label=f'iteration-{iteration+1}-backoff-{len(trials)+1}'
                    if np.any(candidate<lower) or np.any(candidate>upper):
                        trials.append(dict(label=label,iteration=iteration+1,stage=stage,fraction=fraction,accepted=False,
                            controls=candidate.tolist(),rejection='outside_normalized_control_bounds',nonlinear_replay=False))
                        continue
                    after=observed(candidate);replay_keep=retain(current,after,failure_policy=failure_policy,tradeoff_mask=mask)
                    tangent=current[hard]+jac[hard]@(candidate-value)-preservation[hard]
                    tangent_keep=not proposal_tangent_guard or bool(np.all(tangent>=0));keep=replay_keep and tangent_keep
                    trials.append(dict(label=label,iteration=iteration+1,stage=stage,fraction=fraction,accepted=keep,
                        score=list(score(after)),controls=candidate.tolist(),retention_guard_passed=replay_keep,
                        tangent_guard_passed=tangent_keep,tangent_minimum_slack=float(tangent.min()) if proposal_tangent_guard and len(tangent) else None))
                    if observer:observer(label,candidate.copy(),after.copy(),keep)
                    if keep:value=candidate;current=after;return True
                return False
            initial=np.zeros_like(value)
            if proposal_start!='zero':
                check();start_caps=caps.copy()
                if proposal_tangent_guard:start_caps[hard]=np.maximum(start_caps[hard],tangent_caps)
                remaining=seconds-(time.monotonic()-started)
                if remaining<=0:raise Exhausted()
                if proposal_start=='geometry-descent':
                    vectors=vectorize(value);remaining=seconds-(time.monotonic()-started)
                    if remaining<=0:raise Exhausted()
                    initial,start_report=_geometry_descent_start(current,jac,start_caps,
                        candidate_lower-value,candidate_upper-value,remaining,vectors)
                else:initial,start_report=_linear_feasible_start(current,jac,start_caps,
                    candidate_lower-value,candidate_upper-value,remaining)
                starts.append(store_record('start',dict(iteration=iteration+1,controls=value.tolist(),retained=False,**start_report)))
                check()
                if initial is None:stop='linear_start_unavailable';break
                if proposal_start=='geometry-descent' and attempt(initial,'geometry-start'):
                    history.append(dict(iteration=iteration+1,accepted=True,solver_success=start_report['success'],
                        solver_message='Checked geometry-start backoff; nonlinear inner solve skipped',
                        score=list(score(current)),seconds=time.monotonic()-started))
                    continue
            result=minimize(objective,initial,method='SLSQP',jac=True,bounds=bounds,constraints=constraints,
                options=dict(maxiter=solve_iterations,ftol=1e-12))
            direction=np.asarray(result.x,dtype=float)
            if direction.shape!=value.shape or not np.isfinite(direction).all():raise ValueError('Finite proposal direction required')
            if proposal=='nonlinear':direction=bounded_candidate(direction)-value
            accepted=attempt(direction,'optimized')
            history.append(dict(iteration=iteration+1,accepted=accepted,solver_success=bool(result.success),
                solver_message=str(result.message),score=list(score(current)),seconds=time.monotonic()-started))
            if not accepted:stop='no_guarded_improvement';break
        if np.all(current>=0):stop='inequalities_satisfied'
    except Exhausted:stop='time_or_measurement_budget'
    # The retained point was already measured; budget expiry never selects a
    # last unaccepted solver query or proposal.
    if observer:observer('final',value.copy(),current.copy(),True)
    return value,dict(stop=stop,seconds=time.monotonic()-started,measurement_calls=calls,history=history,trials=trials,
        initial_slacks=baseline.tolist(),final_slacks=current.tolist(),initial_score=list(score(baseline)),final_score=list(score(current)),
        source_rows_preserved=bool(np.all(current>=np.minimum(baseline,0))),inequalities_satisfied=bool(np.all(current>=0)),
        source_passing_rows_preserved=bool(np.all(current[baseline>=0]>=0)),
        nontradeoff_rows_preserved=bool(np.all(current[~mask]>=np.minimum(baseline[~mask],0))),
        failure_policy=failure_policy,tradeoff_mask=mask.tolist(),proposal=proposal,proposal_queries=queries,
        proposal_start=proposal_start,proposal_starts=starts,linear_start_max_seconds=20.,
        bounded_proposal_queries=clips,
        proposal_feasible_mask=feasible.tolist(),proposal_headroom_normalized=headroom.tolist(),
        proposal_tangent_guard=proposal_tangent_guard,proposal_linearizations=linearizations,
        tangent_proposal_headroom_normalized=1e-6 if proposal_tangent_guard else 0.,
        solver_headroom_normalized=1e-6,
        quality_approved=False,release_approved=False)
