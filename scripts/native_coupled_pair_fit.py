"""Bounded, unselected native self/partner correction proposals.

Only declared directional and pose conditions are enforced. Callers retain
runtime admission and independent saved-mesh, motion, engine and human checks.
"""
import numpy as np
from scipy.optimize import minimize
from native_coupled_key_pair_rows import CoupledKeyPairRows


def _support(problem,value,*,check_source=True):
    if not isinstance(problem,CoupledKeyPairRows):
        raise ValueError('Qualified complete coupled native problem required')
    problem._value(value)
    offsets=[];size=0
    for spec in problem._specs:
        last=size+3*len(spec['active_pairs']);offsets.append((size,last));size=last
    if offsets!=problem._offsets or size!=problem.size:
        raise ValueError('Complete coupled native variable layout changed')
    expected=[];fixed=[];cursor=0;pair_cursor=0
    for stamp,contexts,gaps in problem._samples:
        dependent=[]
        for side,(mapper,helper) in enumerate(contexts):
            spec=problem._specs[side]
            if check_source:mapper._check()
            key=int(np.searchsorted(mapper.clock,stamp,side='left'))
            if key==0:bracket=[0]
            elif key==len(mapper.clock):bracket=[len(mapper.clock)-1]
            elif mapper.clock[key]==stamp:bracket=[key]
            else:bracket=[key-1,key]
            active=tuple(i for i,(k,n) in enumerate(mapper.pairs) if k in bracket)
            if (mapper.time_s!=stamp or mapper.pairs!=tuple(map(tuple,spec['active_pairs']))
                    or not np.array_equal(mapper.clock,spec['clock'])
                    or not np.array_equal(mapper.seed,spec['seed_controls'])
                    or not np.array_equal(mapper.bracket,bracket) or mapper.dependent!=active):
                raise ValueError('Original structural native edit support changed')
            dependent.append(bool(active));last=cursor+helper.hard_rows
            row=('pose',stamp,side,cursor,last,not bool(active));expected.append(row)
            if row[-1]:fixed.append((row,None))
            cursor=last
        for context,(sides,gap) in enumerate(gaps):
            report=gap.report;last=cursor+report['rows'];pair_last=pair_cursor+report['pair_references']
            row=('gap',stamp,context,cursor,last,not any(dependent[side] for side in sides));expected.append(row)
            if row[-1]:fixed.append((row,(pair_cursor,pair_last)))
            cursor=last;pair_cursor=pair_last
    for side,spec in enumerate(problem._specs):
        last=cursor+len(spec['active_pairs']);expected.append(('native',None,side,cursor,last,False));cursor=last
    if tuple(expected)!=problem.layout or cursor!=problem.rows or pair_cursor!=problem.report['original_pair_references']:
        raise ValueError('Complete coupled row or pair layout changed')
    return fixed


def _failures(fixed,checked):
    failures=[]
    for (kind,stamp,context,first,last,is_fixed),pair_range in fixed:
        bad={mode:np.flatnonzero(checked[mode+'_rows'][first:last]<0)+first for mode in ('raw','encoded')}
        pairs={mode:np.empty(0,dtype=int) for mode in ('raw','encoded')}
        if pair_range is not None:
            a,b=pair_range
            pairs={mode:np.flatnonzero(checked[mode+'_pair_rows'][a:b]<0)+a for mode in ('raw','encoded')}
        if any(len(v) for v in [*bad.values(),*pairs.values()]):
            failures.append(dict(kind=kind,time_s=stamp,context=context,
                raw_global_rows=bad['raw'].tolist(),encoded_global_rows=bad['encoded'].tolist(),
                raw_original_pairs=pairs['raw'].tolist(),encoded_original_pairs=pairs['encoded'].tolist(),
                reason='No editable native endpoint influences the actors in this physical condition'))
    return failures


def _preflight(problem,value,checked):
    fixed=_support(problem,value);failures=_failures(fixed,checked)
    return dict(rejected=bool(failures),fixed_conditions_failed=failures,
        fixed_rows=sum(row[4]-row[3] for row,pairs in fixed),
        fixed_original_pairs=sum(b-a for row,pair in fixed if pair is not None for a,b in [pair]),
        declared_conditions_pass=checked['declared_conditions_pass'],
        scope='Exact raw/Float32 physical rows and all original pairs outside structural native edit support only; no smooth-surrogate, reserve-margin, zero-gradient or whole-rig/action infeasibility inference')


def preflight(problem,value=None):
    if not isinstance(problem,CoupledKeyPairRows):raise ValueError('Qualified complete coupled native problem required')
    value=problem.initial.copy() if value is None else problem._value(value).copy()
    _support(problem,value);checked=problem.postcheck(value)
    return _preflight(problem,value,checked)


class _Feasible(Exception):pass
class _EvaluationLimit(Exception):pass


def fit(problem,*,iterations=32,maximum_evaluations=128,search_reserve=None,on_evaluation=None,starting_value=None):
    if (not isinstance(problem,CoupledKeyPairRows) or type(iterations) is not int or not 1<=iterations<=64
            or type(maximum_evaluations) is not int or not 1<=maximum_evaluations<=512
            or on_evaluation is not None and not callable(on_evaluation)):
        raise ValueError('Qualified coupled problem, bounded iterations/evaluations and optional callback required')
    reserve=np.zeros(problem.rows) if search_reserve is None else np.asarray(search_reserve)
    if (reserve.dtype.kind not in 'fiu' or reserve.shape!=(problem.rows,) or not np.isfinite(reserve).all()
            or np.any(reserve<0) or np.any(reserve>.1)):
        raise ValueError('Complete finite nonnegative normalized search reserves up to0.1 required')
    reserve=reserve.astype(float,copy=True);initial=problem.initial.copy()
    start=initial.copy() if starting_value is None else problem._value(starting_value).copy()
    if np.any(np.abs(start)>1):raise ValueError('Starting proposal must be inside the declared scalar search box; no automatic clipping')
    _support(problem,start);initial_checks=problem.postcheck(start);early=_preflight(problem,start,initial_checks)
    nongap=np.ones(problem.rows,dtype=bool)
    for kind,stamp,context,first,last,fixed in problem.layout:
        if kind=='gap':nongap[first:last]=False
    history=[];cache=None;chosen=start.copy();result=None;solver_started=False
    def evaluate(value):
        nonlocal cache,chosen
        fresh=cache is None or not np.array_equal(cache[0],value)
        # Fresh kernels perform complete source checks themselves. Validate
        # structural support before they consume it; fully check cache hits.
        _support(problem,value,check_source=not fresh)
        if fresh:
            if len(history)>=maximum_evaluations:raise _EvaluationLimit()
            rows,jac=problem.evaluate(value);cache=(np.array(value,copy=True),rows,jac);chosen=cache[0].copy()
            history.append(dict(evaluation=len(history),minimum_smooth_row=float(rows.min()),
                failed_smooth_rows=int(np.count_nonzero(rows<0)),search_failed_rows=int(np.count_nonzero(rows<reserve))))
            if on_evaluation is not None:on_evaluation(dict(history[-1],controls=chosen.copy(),rows=rows.copy()))
            _support(problem,value,check_source=False)
            if np.all(rows[nongap]>=0):
                # Callbacks may change bindings. A fresh exact check validates
                # every source before any point can trigger a feasible stop.
                checked=problem.postcheck(value)
                if checked['declared_conditions_pass']:raise _Feasible()
        return cache[1],cache[2]
    if early['rejected']:stop='fixed_physical_condition_failure'
    elif initial_checks['declared_conditions_pass']:stop='initial_physical_conditions_pass'
    else:
        solver_started=True
        try:
            result=minimize(lambda x:.5*float((x-initial)@(x-initial)),start,jac=lambda x:x-initial,
                method='SLSQP',bounds=[(-1.,1.)]*problem.size,
                constraints=[dict(type='ineq',fun=lambda x:evaluate(x)[0]-reserve,jac=lambda x:evaluate(x)[1])],
                options=dict(maxiter=iterations,ftol=1e-10))
            chosen=problem._value(result.x).copy();stop='optimizer_returned'
        except _Feasible:stop='independently_postchecked_feasible_checkpoint'
        except _EvaluationLimit:stop='complete_evaluation_budget_exhausted'
    _support(problem,chosen);checked=problem.postcheck(chosen)
    counts={key:dict(rows=len(checked[key]),failed=int(np.count_nonzero(checked[key]<0)),
                    minimum=float(checked[key].min()) if len(checked[key]) else None)
            for key in ('raw_rows','encoded_rows','raw_pair_rows','encoded_pair_rows')}
    return chosen,dict(schema='strep-native-coupled-pair-fit-v1',solver='scipy SLSQP',stop=stop,
        solver_was_run=solver_started,optimizer_completion_claimed=result is not None,
        solver_success=bool(result.success) if result is not None else False,
        solver_status=int(result.status) if result is not None else None,
        solver_message=str(result.message) if result is not None else None,
        iterations=int(result.nit) if result is not None else None,maximum_iterations=iterations,
        maximum_evaluations=maximum_evaluations,complete_evaluations=len(history),history=history,
        preflight=early,physical_postchecks=counts,
        starting_value_provided=starting_value is not None,objective_reference='Unchanged problem.initial source-relative seed; starting_value never rebases source, caps, seeds or fixed poses',
        physical_declared_conditions_pass=checked['declared_conditions_pass'],
        search_reserve=reserve.tolist(),original_selected=True,quality_approved=False,release_approved=False,
        scope='Unselected distance-to-seed native proposal under every supplied self/partner/pose/native condition. Strict raw/Float32 postchecks, no acceptance tolerance. Search reserves are guidance, not physical conditions. Feasible checkpoint and solver completion are distinct. No collision-direction inference, permission changes, whole-curve/actual saved mesh/rates/dynamics/engine/human approval.')
