"""Measure one fixed linear least-squares system at declared iteration caps."""
import time
import numpy as np
from scipy.sparse.linalg import aslinearoperator,lsmr


def measure(operator,rhs,options,solver=lsmr):
    a=aslinearoperator(operator);rhs=np.asarray(rhs,dtype=float)
    if rhs.shape!=(a.shape[0],) or not np.isfinite(rhs).all():raise ValueError('Finite matching right-hand side required')
    started=time.monotonic();fit=solver(a,rhs,**options);x=fit[0]
    residual=a@x-rhs;damp=float(options.get('damp',0.))
    normal=a.T@residual+damp*damp*x
    record=dict(options=options,seconds=time.monotonic()-started,stop_code=int(fit[1]),iterations=int(fit[2]),
        reported_residual_norm=float(fit[3]),reported_normal_norm=float(fit[4]),
        residual_norm=float(np.linalg.norm(residual)),regularized_residual_norm=float(np.sqrt(residual@residual+damp*damp*(x@x))),
        normal_norm=float(np.linalg.norm(normal)),normal_infinity=float(abs(normal).max()),solution_norm=float(np.linalg.norm(x)),
        condition_estimate=float(fit[6]),solution=x.tolist())
    if not all(np.isfinite(record[k]) for k in ['residual_norm','normal_norm','solution_norm']):raise ValueError('Nonfinite linear solution')
    return fit,record
