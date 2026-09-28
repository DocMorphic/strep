"""Try shorter fractions only after all original trust-setting attempts fail."""
import numpy as np
from coupled_support_block import direction


ORIGINAL_FRACTIONS=(1., .5, .25, .125)
FALLBACK_FRACTIONS=tuple(2.**-n for n in range(4,11))


def trial(problem,x,delta,fraction,old,phase):
    evaluated=problem.pair(x+fraction*delta)
    margins=evaluated[2].margins()
    feasible=all(np.isfinite(v) and v>=-1e-9 for v in margins.values())
    geometry,excess=problem.midpoint_guard(evaluated[3]) if feasible else (False,None)
    accepted=bool(feasible and geometry and evaluated[0]<old-max(1e-9,old*.001))
    return dict(fraction=fraction,objective=evaluated[0],margins=margins,
        midpoint_pass=geometry,midpoint_excess_m=excess,accepted=accepted,phase=phase)


def solve(problem,steps=12,trusts=(.005,.001,.0002)):
    if type(steps) is not int or not 1<=steps<=30:
        raise ValueError('Finite step budget from1to30 required')
    x=problem.initial[problem.frames].ravel().copy();history=[]
    initial=problem.pair(x)
    if min(initial[2].margins().values()) < -1e-8:
        raise ValueError('Source reconstruction violates frozen block constraints')
    for iteration in range(steps):
        old=problem.pair(x)[0];attempts=[];cached=[];accepted=False
        # Preserve the legacy search priority, including later trust settings.
        for trust in trusts:
            delta,record=direction(problem,x,trust);record['trials']=[];attempts.append(record)
            if delta is None or record['predicted_change']>=0:continue
            record['delta']=delta.tolist();cached.append((delta,record))
            for fraction in ORIGINAL_FRACTIONS:
                tested=trial(problem,x,delta,fraction,old,'original');record['trials'].append(tested)
                if tested['accepted']:
                    x+=fraction*delta;accepted=True;break
            if accepted:break
        if not accepted:
            # These directions were computed at the same unchanged x. Reuse them.
            for delta,record in cached:
                for fraction in FALLBACK_FRACTIONS:
                    tested=trial(problem,x,delta,fraction,old,'fallback');record['trials'].append(tested)
                    if tested['accepted']:
                        x+=fraction*delta;accepted=True;break
                if accepted:break
        history.append(dict(iteration=iteration,accepted=accepted,attempts=attempts))
        if not accepted:break
    return problem.values(x),dict(initial_objective=initial[0],final_objective=problem.pair(x)[0],
        frames=problem.frames.tolist(),history=history,steps_limit=steps,trusts=list(trusts),
        fractions=list(ORIGINAL_FRACTIONS+FALLBACK_FRACTIONS),
        search_order='original_then_fallback',quality_approved=False)
