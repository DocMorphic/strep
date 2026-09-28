"""Bounded derivative probes that do not cross a hover minimum branch."""
import numpy as np
from check_piecewise_derivative import check_direction


def signature(p,x):
    values=p.values(x);active=[]
    for frame in p.frames:
        positions=p.fitter.surface_jacobian(int(frame),values[frame])[0]
        active.extend(int(ids[np.argmin(positions[ids,1])]) for side,ids in enumerate(p.patches) if p.envelope['active_frames'][frame][side])
    return active


def prove(p,x,affine_constraints):
    base=affine_constraints(p,x,False);rng=np.random.default_rng(117);rows=[]
    for _ in range(3):
        d=rng.normal(size=len(x));d/=np.linalg.norm(d)
        row=check_direction(lambda y:p.evaluate(y,False),lambda y:signature(p,y),x,d)
        step=row['selected_step']
        if step is not None:
            minus,plus=[affine_constraints(p,x+s*step*d,False) for s in [-1,1]]
            row.update(linear_error=float(np.abs((plus[0]-minus[0])/(2*step)-base[1]@d).max()),
                vector_error=max(float(np.abs((a['vector']-m['vector'])/(2*step)-v['jacobian']@d).max()) for v,m,a in zip(base[2],minus[2],plus[2])))
            row['passed']=bool(row['passed'] and max(row['linear_error'],row['vector_error'])<=2e-4)
        rows.append(row)
    return rows
