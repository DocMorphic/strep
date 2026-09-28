"""Directional finite differences of objective and every fixed constraint row."""
import numpy as np


def probe(objective, inequalities, states):
    rows=[]
    for label,x in states:
        x=np.asarray(x,float);value,gradient=objective(x);g,jac=inequalities(x)
        if not np.isfinite(np.r_[value,gradient,g,jac.ravel()]).all():raise ValueError('Nonfinite probe input')
        rng=np.random.default_rng(6139);directions=rng.normal(size=(6,len(x)))
        directions/=np.linalg.norm(directions,axis=1)[:,None]
        directions=np.vstack([directions,np.eye(len(x))[int(np.argmax(np.abs(gradient)))]])
        for i,direction in enumerate(directions):
            expected=float(gradient@direction);projected=jac@direction
            for step in [1e-4,1e-5,1e-6]:
                fp=objective(x+step*direction)[0];fm=objective(x-step*direction)[0]
                gp=inequalities(x+step*direction)[0];gm=inequalities(x-step*direction)[0]
                fd=(fp-fm)/(2*step);gd=(gp-gm)/(2*step)
                row=dict(state=label,direction=i,step=step,objective_direction=expected,
                    objective_absolute_error=float(abs(fd-expected)),
                    objective_scaled_error=float(abs(fd-expected)/max(1.,abs(fd),abs(expected))),
                    inequality_max_absolute_error=float(np.max(np.abs(gd-projected),initial=0.)),
                    inequality_max_scaled_error=float(np.max(np.abs(gd-projected)/np.maximum(1.,np.maximum(np.abs(gd),np.abs(projected))),initial=0.)))
                row['passes_declared_screen']=bool(row['objective_scaled_error']<1e-5 and row['inequality_max_scaled_error']<1e-5)
                rows.append(row)
    return dict(rows=rows,passed=all(r['passes_declared_screen'] for r in rows if r['step']==1e-5),
        decisive_step=1e-5,relative_floor=1.,tolerance=1e-5,quality_approved=False,
        scope='Six fixed random unit directions and the largest-gradient coordinate at each declared state; not an exhaustive Jacobian proof. Other step sizes retained as sensitivity diagnostics.')
