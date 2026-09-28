"""Exact coordinate contribution of whole-track root-correction curvature."""
import numpy as np


def root_curvature_pair(values, frame, candidate, weight):
    values=np.asarray(values,dtype=float);candidate=np.asarray(candidate,dtype=float)
    if values.ndim!=2 or values.shape[1]<3 or len(values)<3 or candidate.shape!=(values.shape[1],):
        raise ValueError('Full parameter track and one matching candidate required')
    if type(frame) is not int or not 0<=frame<len(values) or not np.isfinite(weight) or weight<0:
        raise ValueError('Valid frame and nonnegative finite weight required')
    if not np.isfinite(values).all() or not np.isfinite(candidate).all():
        raise ValueError('Finite parameters required')
    residual=[];jacobian=[]
    # Changing frame f affects acceleration centers f-1, f, AND f+1.
    # Include all three, even where a center lies outside the editable window.
    for center in range(max(1,frame-1),min(len(values)-2,frame+1)+1):
        curvature=values[center-1,:3]-2*values[center,:3]+values[center+1,:3]
        coefficient=-2. if center==frame else 1.
        curvature=curvature+coefficient*(candidate[:3]-values[frame,:3])
        jac=np.zeros((3,len(candidate)));jac[:,:3]=np.eye(3)*coefficient*weight
        residual.append(curvature*weight);jacobian.append(jac)
    return np.concatenate(residual),np.vstack(jacobian)


def root_curvature_energy(values,weight):
    delta=np.diff(np.asarray(values)[:,:3],n=2,axis=0)*weight
    return float(np.sum(delta*delta))
