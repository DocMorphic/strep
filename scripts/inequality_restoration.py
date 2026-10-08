"""Residual and Jacobian for bounded numerical inequality restoration.

Positive slack is feasible. The small seed regularizer stabilizes free controls;
neither a stationary point nor a low residual is an acceptance certificate.
"""
import numpy as np


def restoration_residual(parameters,seed,slacks,jacobian,regularization=1e-5):
    parameters=np.asarray(parameters,dtype=float);seed=np.asarray(seed,dtype=float)
    slacks=np.asarray(slacks,dtype=float);jacobian=np.asarray(jacobian,dtype=float)
    if (parameters.ndim!=1 or len(parameters)==0 or seed.shape!=parameters.shape
            or slacks.ndim!=1 or len(slacks)==0 or jacobian.shape!=(len(slacks),len(parameters))
            or any(not np.isfinite(a).all() for a in [parameters,seed,slacks,jacobian])
            or type(regularization) not in (int,float) or not np.isfinite(regularization) or regularization<=0):
        raise ValueError('Finite matching residual inputs and positive regularizer required')
    violated=slacks<0
    residual=np.r_[np.minimum(slacks,0),regularization*(parameters-seed)]
    derivative=np.concatenate([jacobian*violated[:,None],regularization*np.eye(len(parameters))])
    return residual,derivative
