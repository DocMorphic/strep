"""Partial surface screen: all vertices with any positive hand-subtree weight.

Targets remain complete closed meshes. This is a sampled vertex rejection test,
not a full-body clearance or continuous collision certificate.
"""
import numpy as np
from elbow_swivel import descendants
from convex_partner_surface import penetration


def hand_vertices(rig,wrist):
    if len(rig.primitives)!=1 or rig.primitives[0]['joints'] is None:
        raise ValueError('One skinned primitive required for stable vertex IDs')
    primitive=rig.primitives[0]
    nodes=np.asarray(rig.joints)[primitive['joints']]
    weights=np.asarray(primitive['weights'])
    if weights.shape!=nodes.shape or not np.isfinite(weights).all() or np.any(weights<0):
        raise ValueError('Finite nonnegative matching skin weights required')
    mask=descendants(rig.parents,wrist)
    ids=np.flatnonzero(np.any(mask[nodes]&(weights>0),axis=1))
    if not len(ids):raise ValueError('No vertices influenced by the hand subtree')
    return ids


def screen(source,ids,target,faces,tolerance_m=.005):
    source=np.asarray(source);ids=np.asarray(ids)
    if (ids.ndim!=1 or ids.dtype.kind not in 'iu' or not len(ids) or
            np.any(ids<0) or np.any(ids>=len(source)) or len(np.unique(ids))!=len(ids)):
        raise ValueError('Unique nonempty source vertex IDs required')
    result=penetration(source[ids],target,faces,tolerance_m)
    local=result.pop('deepest_vertex')
    result['deepest_source_vertex']=None if local is None else int(ids[local])
    result['source_full_vertex_count']=len(source)
    return result
