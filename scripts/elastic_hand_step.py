"""Feasibility restoration for initially intersecting hand trajectories.

One explicit nonnegative slack relaxes surface rows only. Correction limits
remain hard. Slack is an optimization aid, never an accepted collision margin.
"""
import numpy as np
from scipy.optimize import minimize


def solve(objective,inequalities,x,lower,upper,surface_count):
    scale=.03
    initial=inequalities(x)[0]
    slack=max(0.,float(-initial[:surface_count].min())) if surface_count else 0.
    if slack>.12:raise ValueError('Restoration seed exceeds declared 120 mm slack cap')
    seed=np.r_[x,min(4.,(slack+1e-6)/scale)]
    def energy(y):
        value,gradient=objective(y[:-1])
        return value+.5*(y[-1]*30)**2,np.r_[gradient,y[-1]*900]
    def constraint(y):
        values,jac=inequalities(y[:-1]);values=values.copy();jac=np.c_[jac,np.zeros(len(values))]
        values[:surface_count]=values[:surface_count]/scale+y[-1]
        jac[:surface_count,:-1]/=scale;jac[:surface_count,-1]=1
        return values,jac
    result=minimize(energy,seed,jac=True,method='SLSQP',bounds=list(zip(lower,upper))+[(0.,4.)],
        constraints=[dict(type='ineq',fun=lambda y:constraint(y)[0],jac=lambda y:constraint(y)[1])],options=dict(maxiter=60,ftol=1e-9))
    result.restoration_slack_m=float(result.x[-1]*scale)
    result.relaxed_constraint_min=float(constraint(result.x)[0].min())
    result.x=result.x[:-1]
    return result
