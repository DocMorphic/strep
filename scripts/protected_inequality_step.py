"""Trust-box proposals retained only by complete nonlinear inequality replay.

Feasible rows remain feasible. Rowwise mode protects individual failures; merit
mode permits explicitly selected failed-row tradeoffs with improving complete
scores. Linear or nonlinear proposal subproblems never approve a pose.
"""
import time
import numpy as np
from scipy.optimize import minimize


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


def fit(measure,linearize,seed,lower,upper,*,iterations=30,trust=.03,solve_iterations=100,
        seconds=300,maximum_calls=1000,observer=None,failure_policy='rowwise',tradeoff_mask=None,
        proposal='linear',proposal_feasible_mask=None,proposal_headroom=None,proposal_tangent_guard=False):
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
            or type(proposal_tangent_guard) is not bool or (proposal_tangent_guard and proposal!='nonlinear')):
        raise ValueError('Finite seed, matching control bounds and explicit step budgets required')
    started=time.monotonic();calls=0;history=[];trials=[];queries=[];clips=[];linearizations=[];value=seed.copy()
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
                linearizations.append(dict(iteration=iteration+1,controls=value.tolist(),slacks=current.tolist(),
                    jacobian=jac.tolist(),protected_rows=np.flatnonzero(hard).tolist(),
                    preservation_caps=preservation[hard].tolist(),tangent_proposal_caps=tangent_caps.tolist()))
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
            result=minimize(objective,np.zeros_like(value),method='SLSQP',jac=True,bounds=bounds,constraints=constraints,
                options=dict(maxiter=solve_iterations,ftol=1e-12))
            direction=np.asarray(result.x,dtype=float)
            if direction.shape!=value.shape or not np.isfinite(direction).all():raise ValueError('Finite proposal direction required')
            if proposal=='nonlinear':direction=bounded_candidate(direction)-value
            accepted=False
            for fraction in [1.,.5,.25,.125,.0625,.03125,.015625,.0078125]:
                candidate=value+fraction*direction
                if proposal=='nonlinear':candidate=np.clip(candidate,candidate_lower,candidate_upper)
                label=f'iteration-{iteration+1}-backoff-{len(trials)+1}'
                if np.any(candidate<lower) or np.any(candidate>upper):
                    trials.append(dict(label=label,iteration=iteration+1,fraction=fraction,accepted=False,
                        controls=candidate.tolist(),rejection='outside_normalized_control_bounds',nonlinear_replay=False))
                    continue
                after=observed(candidate);replay_keep=retain(current,after,failure_policy=failure_policy,tradeoff_mask=mask)
                tangent=current[hard]+jac[hard]@(candidate-value)-preservation[hard]
                tangent_keep=not proposal_tangent_guard or bool(np.all(tangent>=0))
                keep=replay_keep and tangent_keep
                trials.append(dict(label=label,iteration=iteration+1,fraction=fraction,accepted=keep,
                    score=list(score(after)),controls=candidate.tolist(),retention_guard_passed=replay_keep,
                    tangent_guard_passed=tangent_keep,tangent_minimum_slack=float(tangent.min()) if proposal_tangent_guard and len(tangent) else None))
                if observer:observer(label,candidate.copy(),after.copy(),keep)
                if keep:value=candidate;current=after;accepted=True;break
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
        bounded_proposal_queries=clips,
        proposal_feasible_mask=feasible.tolist(),proposal_headroom_normalized=headroom.tolist(),
        proposal_tangent_guard=proposal_tangent_guard,proposal_linearizations=linearizations,
        tangent_proposal_headroom_normalized=1e-6 if proposal_tangent_guard else 0.,
        solver_headroom_normalized=1e-6,
        quality_approved=False,release_approved=False)
