"""Nested timed arm controls: increase temporal freedom without changing input motion."""
import numpy as np
from unique_fractional_skin import UniqueBoundedPathFitter


def refine(fitter, controls, knots):
    old=np.asarray(fitter.knots,float);new=np.asarray(knots,float)
    if new.ndim!=1 or not np.isfinite(new).all() or len(new)>40 or np.any(np.diff(new)<=0) or not set(old)<=set(new) or new[0]!=old[0] or new[-1]!=old[-1]:
        raise ValueError('Use a sorted refinement containing every original knot and the same endpoints')
    x=np.asarray(controls,float)
    if x.shape!=(sum(fitter.sizes),) or not np.isfinite(x).all():raise ValueError('Finite original controls required')
    result=UniqueBoundedPathFitter(fitter.base.actors,event=fitter.event,fade=30,knots=new.tolist())
    if not np.array_equal(result.base.envelope,fitter.base.envelope):raise ValueError('Refinement must preserve the original envelope')
    values=[]
    for actor,part in zip(fitter.base.actors,np.split(x,np.cumsum(fitter.sizes)[:-1])):
        vectors=part.reshape(len(old),actor.dim)
        values.append(np.stack([np.interp(new,old,vectors[:,j]) for j in range(actor.dim)],axis=1).ravel())
    refined=np.concatenate(values)
    error=float(np.abs(result.values(refined)-fitter.values(x)).max())
    if error>1e-12 or not np.array_equal(result.values(refined)[fitter.event],fitter.values(x)[fitter.event]):
        raise ValueError('Knot insertion changed the source motion or event')
    if result.step_pair(refined)[0].min()<-1e-8:raise ValueError('Refined source violates unchanged hard limits')
    return result,refined,dict(original_knots=old.tolist(),refined_knots=new.tolist(),source_control_count=len(x),refined_control_count=len(refined),max_edit_vector_error=error,event_exact=True)
