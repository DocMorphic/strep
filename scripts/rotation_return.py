"""Local rotation return with endpoint body rates estimated from adjacent keys."""
import numpy as np
from scipy.spatial.transform import Rotation


def bounded_path_edits(vectors, limits, reserve=.001):
    vectors,limits=np.asarray(vectors,float),np.asarray(limits,float)
    if vectors.shape!=limits.shape+(3,) or not np.isfinite(vectors).all() or not np.isfinite(limits).all() or not np.isfinite(reserve) or reserve<=0 or np.any(limits<=reserve):
        raise ValueError('Finite rotation vectors and limits exceeding a positive reserve required')
    norms=np.linalg.norm(vectors,axis=-1)
    return vectors*np.minimum(1.,(limits-reserve)/np.maximum(norms,1e-30))[...,None]


def tangent_return(first, last, before, after, fraction, duration_steps):
    if not np.isfinite([fraction,duration_steps]).all() or not 0 <= fraction <= 1 or duration_steps <= 0:
        raise ValueError('Finite path fraction in [0, 1] and positive duration required')
    a,b,previous,next_=map(Rotation.from_matrix,[first,last,before,after])
    delta=(a.inv()*b).as_rotvec()
    start_rate=(previous.inv()*a).as_rotvec()*duration_steps
    end_rate=(b.inv()*next_).as_rotvec()*duration_steps
    # Inverse SO(3) right Jacobian maps the terminal body rate into the
    # derivative of the logarithm relative to the starting orientation.
    theta=np.linalg.norm(delta,axis=-1)
    coefficient=np.empty_like(theta); small=theta<1e-4
    coefficient[small]=1/12+theta[small]**2/720
    coefficient[~small]=(1-.5*theta[~small]/np.tan(.5*theta[~small]))/theta[~small]**2
    end_derivative=end_rate+.5*np.cross(delta,end_rate)+coefficient[...,None]*np.cross(delta,np.cross(delta,end_rate))
    t=fraction
    vector=(t**3-2*t*t+t)*start_rate+(-2*t**3+3*t*t)*delta+(t**3-t*t)*end_derivative
    return (a*Rotation.from_rotvec(vector)).as_matrix()
