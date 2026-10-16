"""Bounded actor stages for an unchanged coupled-scene validation contract.

Contacts remain a separate coupled observation. Extracting one actor's native
rows never evaluates partner contacts against a frozen, incorrect partner.
"""
import numpy as np
from native_scene_norms import NormRows
from native_scene_geometry import faces_for


def require(value,message):
    if not value:raise ValueError(message)


def observed(model,worlds):
    values=np.asarray(worlds)
    require(values.dtype.kind in 'fi' and values.shape==model.source_world.shape and np.isfinite(values).all(),
        'Complete finite original-clock actor worlds required')
    return values


def native_rows(model,value,worlds):
    model.check();worlds=observed(model,worlds);rows=model.rows(value,worlds)
    independent=len(model.times)*(len(model.nodes)+len(model.rig.joints))
    # Identical selection/order to PairKeyGuides.norms. Single-model contact
    # estimates are deliberately excluded; they do not observe both edits.
    ids=np.r_[np.arange(independent),np.arange(model.edit_count,len(rows.caps))]
    result=NormRows(rows.vectors[ids],rows.caps[ids],rows.scales[ids]);model.check()
    return result


def geometry_cache(model,worlds,sample_indices,*,maximum_bytes=64*1024**2):
    model.check();worlds=observed(model,worlds)
    if isinstance(sample_indices,(list,tuple)):
        require(all(type(x) is int or isinstance(x,np.integer) and not isinstance(x,np.bool_) for x in sample_indices),
            'Explicit integer mesh sample indices required')
    ids=np.asarray(sample_indices)
    require(ids.ndim==1 and ids.dtype.kind in 'iu' and len(ids)>0 and np.all(ids<len(model.times))
        and np.all(ids>=0) and np.all(np.diff(ids.astype(np.int64))>0),'Sorted unique original-clock mesh sample indices required')
    require(type(maximum_bytes) is int and maximum_bytes>0,'Explicit positive mesh cache budget required')
    vertices=len(model.skin.nodes);faces=faces_for(model.rig)[0]
    needed=len(ids)*vertices*3*8+faces.nbytes+2*len(ids)*8
    require(needed<=maximum_bytes,'Complete selected mesh cache exceeds budget; no samples or vertices discarded')
    p,r=model.actor['placement'];points=np.stack([model.rig.vertices(worlds[i])@r.T+p for i in ids])
    require(points.shape==(len(ids),vertices,3) and np.isfinite(points).all(),'Complete finite canonical world vertices required')
    model.check()
    return dict(times_s=model.times[ids].copy(),sample_indices=ids.copy(),vertices_world_m=points,faces=faces.copy()),dict(
        actor=model.name,samples=len(ids),original_clock_samples=len(model.times),complete_time_population=len(ids)==len(model.times),
        vertices_per_sample=vertices,faces=len(faces),required_array_bytes=int(needed),maximum_bytes=maximum_bytes,
        scope='Complete canonical meshes at explicitly selected original-clock times. Cached observations are not geometry, contact, engine or quality approval.',quality_approved=False,release_approved=False)
