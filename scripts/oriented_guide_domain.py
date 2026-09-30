"""Coupled vector-domain and adjacent-key guide limits for oriented arm edits."""
import numpy as np


def validate(native,limits):
    native,limits=np.asarray(native,float),np.asarray(limits,float)
    if native.ndim!=1 or len(native)<3 or not np.isfinite(native).all() or np.any(np.diff(native)<=0):raise ValueError('Increasing native support required')
    if limits.shape!=(3,) or not np.isfinite(limits).all() or np.any(limits<=0):raise ValueError('Positive wrist and elbow guide limits required')
    return native,limits


def control_scales(native,limits):
    native,limits=validate(native,limits)
    distance=np.minimum(native[1:-1]-native[0],native[-1]-native[1:-1])
    return np.array([np.r_[np.repeat(min(.06,limits[0]*d),3),np.minimum(30.,limits[1:]*d),np.repeat(min(30.,300.*d),6)] for d in distance]).ravel()


def margins(controls,native,limits):
    native,limits=validate(native,limits);controls=np.asarray(controls,float)
    if controls.shape!=(11*(len(native)-2),) or not np.isfinite(controls).all():raise ValueError('Finite oriented controls matching native keys required')
    rows=controls.reshape(-1,11);scale=control_scales(native,limits).reshape(-1,11)
    domain=np.c_[1-np.linalg.norm(rows[:,:3],axis=1)/scale[:,0],1-np.abs(rows[:,3:5])/scale[:,3:5],
                 1-np.linalg.norm(rows[:,5:8],axis=1)/scale[:,5],1-np.linalg.norm(rows[:,8:11],axis=1)/scale[:,8]]
    rates=np.diff(np.vstack([np.zeros(11),rows,np.zeros(11)]),axis=0)/np.diff(native)[:,None]
    transitions=np.c_[1-np.linalg.norm(rates[:,:3],axis=1)/limits[0],1-np.abs(rates[:,3:5])/limits[1:],
                      1-np.linalg.norm(rates[:,5:8],axis=1)/300.,1-np.linalg.norm(rates[:,8:11],axis=1)/300.]
    return np.r_[domain.ravel(),transitions.ravel()]
