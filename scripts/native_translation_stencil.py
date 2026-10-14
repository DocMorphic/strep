"""Bounded complete Float32 translation stencils for proposal ranking only.

A sampled joint origin moves affinely with an ancestor's local translation
while its other tracks stay fixed. Coordinating all axes across up to three
native keys can rank useful proposals that single-axis triples omit. Every
candidate still needs a fresh full export, authoring, motion and geometry audit.
"""
import itertools
import numpy as np


def rank(nearest_keys,current_samples,weights,parent_linear,points,*,cap,dt,tolerance,
         maximum_population=19683,metric='acceleration'):
    """Rank every absolute -1/nearest/+1 choice on one translation support.

    Inputs describe two speed or three acceleration samples. ``nearest_keys`` is
    the original intended curve rounded to Float32, never an already adjusted
    value. All existing corrections outside these keys stay fixed in ``points``.
    This function neither exports nor approves a clip; predictions can differ
    from the decoder's arithmetic and do not assess any other condition.
    """
    nearest=np.asarray(nearest_keys)
    if (nearest.ndim!=2 or nearest.shape[1]!=3 or not 1<=len(nearest)<=3
            or not np.isfinite(nearest).all()
            or not np.array_equal(nearest,nearest.astype(np.float32).astype(float))):
        raise ValueError('One to three finite nearest Float32 translation keys required')
    if type(maximum_population) is not int or not 1<=maximum_population<=19683:
        raise ValueError('Explicit complete population budget up to 19683 required')
    count=3**nearest.size
    if count>maximum_population:
        raise ValueError('Complete translation stencil exceeds declared population budget')
    if type(metric) is not str or metric not in ('speed','acceleration'):
        raise ValueError('Explicit speed or acceleration proposal metric required')
    order=1 if metric=='speed' else 2;frames=order+1
    current=np.asarray(current_samples,float);weights=np.asarray(weights,float)
    parent=np.asarray(parent_linear,float);points=np.asarray(points,float)
    if (current.shape!=(frames,3) or points.shape!=(frames,3) or parent.shape!=(frames,3,3)
            or weights.shape!=(frames,len(nearest))
            or any(not np.isfinite(a).all() for a in (current,points,parent,weights))
            or np.any(weights<0) or np.any(weights>1)
            or not np.allclose(weights.sum(1),1,atol=1e-12,rtol=0)):
        raise ValueError('Complete finite three-sample ancestor/interpolation observations required')
    if any(type(v) not in (int,float) or not np.isfinite(v) for v in (cap,dt,tolerance)) or cap<0 or tolerance<0 or dt<=0:
        raise ValueError('Nonnegative original cap/tolerance and positive uniform step required')
    nearest=nearest.astype(np.float32)
    with np.errstate(over='ignore',invalid='ignore'):
        choices=np.stack([np.nextafter(nearest,np.float32(-np.inf)),nearest,
                          np.nextafter(nearest,np.float32(np.inf))])
    if not np.isfinite(choices).all():
        raise ValueError('Complete finite one-neighbor translation population required')
    steps=np.asarray(list(itertools.product((-1,0,1),repeat=nearest.size)),dtype=np.int8)
    values=choices[steps.reshape(-1,len(nearest),3)+1,
                   np.arange(len(nearest))[None,:,None],np.arange(3)[None,None,:]].astype(float)
    samples=np.einsum('tk,nkc->ntc',weights,values)
    predicted=points[None]+np.einsum('tij,ntj->nti',parent,samples-current)
    with np.errstate(over='ignore',invalid='ignore',divide='ignore'):
        residual=(np.linalg.norm(np.diff(predicted,n=order,axis=1)[:,0]/dt**order,axis=1)
                  -cap-tolerance)/max(cap,.001)
    if not np.isfinite(predicted).all() or not np.isfinite(residual).all():
        raise ValueError('Finite complete translation predictions required')
    return dict(schema='strep-native-translation-stencil-v1',absolute_steps=steps,
        candidate_key_values=values,predicted_points=predicted,predicted_excess=residual,
        order=np.argsort(residual,kind='stable'),population=count,
        metric=metric,proposal_only=True,geometry_assessed=False,quality_approved=False,release_approved=False)
