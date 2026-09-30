"""Continuous nearest-guide search with independently checked feasible incumbents."""
import numpy as np
from scipy.optimize import minimize
from sampled_motion_caps import measures,features


def project(models,caps,native,target,limits,*,max_evaluations=1200,observe=None,method='COBYLA',start='source'):
    native=np.asarray(native,float);target=np.asarray(target,float);limits=np.asarray(limits,float)
    if target.shape!=(len(native),3) or np.any(target[[0,-1]]) or not np.isfinite(target).all():raise ValueError('Matching finite target guide required')
    if limits.shape!=(3,) or not np.isfinite(limits).all() or np.any(limits<=0):raise ValueError('Three positive guide rate limits required')
    if type(max_evaluations) is not int or max_evaluations<1:raise ValueError('Positive evaluation limit required')
    if method not in ['COBYLA','SLSQP']:raise ValueError('Declared projection method required')
    if start not in ['source','target']:raise ValueError('Declared source or target initialization required')
    scale=np.array([.06,30.,30.]);desired=(target[1:-1]/scale).ravel();zero=np.zeros_like(desired)
    lower=np.tile([0.,-1.,-1.],len(native)-2);upper=np.ones_like(lower)
    cache={};best=None;records=[]

    def evaluate(x):
        nonlocal best
        x=np.asarray(x,float);key=x.tobytes()
        if key in cache:return cache[key]
        parameters=np.zeros_like(target);parameters[1:-1]=x.reshape(-1,3)*scale
        cost=float(np.mean((x-desired)**2));domain=np.r_[x-lower,upper-x]
        rates=np.max(np.abs(np.diff(parameters,axis=0)/np.diff(native)[:,None]),axis=0)
        count=sum(c.size for c in caps.caps) if method=='SLSQP' else 4
        margins=np.r_[np.full(count+1,-1.),(limits-rates)/limits,domain];error=None;worlds=None;motion=np.full(4,-1.).tolist()
        try:
            evaluated=[m.evaluate(parameters) for m in models];worlds=[r[0] for r in evaluated]
            parts=[features(w,m.rig.joints) for w,m in zip(worlds,models)]
            payload={k:np.concatenate([p[k] for p in parts],axis=1) for k in ['positions','rotations']}
            payload['indices']=np.arange(len(caps.times))
            values=measures(payload,caps.dt)
            # Reserve a numerical margin for scalar GLB export replay.
            rows=[(bound+.9*caps.tolerance-v)/np.maximum(bound,floor)
                  for v,bound,floor in zip(values,caps.caps,[.01,1.,.01,1.])]
            motion=[float(r.min()) for r in rows]
            margins[:count]=np.concatenate([r.ravel() for r in rows]) if method=='SLSQP' else motion
            margins[count]=(45.+1e-4-max(r[1] for r in evaluated))/45.
            feasible=bool(np.all(margins>=0) and caps.check(payload))
        except ValueError as exc:
            if 'outside two-bone reach' not in str(exc):raise
            error=str(exc);feasible=False
        record=dict(evaluation=len(records),objective=cost,minimum_margin=float(margins.min()),
            motion_margins=motion,feasible=feasible,parameters=parameters.tolist(),error=error)
        records.append(record);cache[key]=(cost,margins)
        # Full per-observation constraints are large; keep only a small replay cache.
        if len(cache)>32:del cache[next(iter(cache))]
        if feasible and (best is None or cost<best['objective']):best=record.copy()
        if observe is not None:observe(record,best)
        return cost,margins

    evaluate(zero)
    if best is None:raise ValueError('Unchanged source must remain feasible')
    # Evaluate the intended correction too, retaining its actual failure evidence.
    evaluate(desired)
    options=(dict(rhobeg=.1,tol=1e-5,catol=1e-9,maxiter=max_evaluations) if method=='COBYLA'
             else dict(maxiter=max_evaluations,ftol=1e-9,eps=1e-4))
    kwargs={} if method=='COBYLA' else dict(jac=lambda x:2*(x-desired)/len(desired))
    result=minimize(lambda x:evaluate(x)[0],zero if start=='source' else desired,method=method,bounds=list(zip(lower,upper)),
        constraints=[dict(type='ineq',fun=lambda x:evaluate(x)[1])],options=options,**kwargs)
    evaluate(result.x)
    return best,dict(success=bool(result.success),status=int(result.status),message=str(result.message),
        method=method,start=start,function_evaluations=int(result.nfev),recorded_evaluations=len(records),returned_objective=float(result.fun),
        returned_minimum_margin=float(evaluate(result.x)[1].min()),
        note='Only independently feasible observed controls are retained; optimizer success does not approve the motion.'),records
