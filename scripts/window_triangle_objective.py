"""Compile every observed crossing across a fixed clock, retaining control scope."""
import numpy as np
from triangle_separation_objective import choose_axes, gaps


def compile_window(times, samples, faces, points, support):
    """Support flags mean potentially influenced, not reachable or feasible.

    All observed pairs remain in the result, including pairs outside the control
    support. No count cap, worst-pair sampling or success-based selection occurs.
    """
    times=np.asarray(times,float)
    if (times.ndim!=1 or not len(times) or not np.isfinite(times).all() or times[0]<0
            or np.any(np.diff(times)<=0) or len(samples)!=len(times) or len(points)!=len(times)
            or len(support)!=len(times) or len(faces)!=2):
        raise ValueError('Complete paired geometry on an increasing clock required')
    faces=[np.asarray(f) for f in faces]
    if any(f.ndim!=2 or f.shape[1:]!=(3,) or not len(f) or not np.issubdtype(f.dtype,np.integer) or f.min()<0 for f in faces):
        raise ValueError('Two nonempty integer face arrays required')
    rows=[]
    for frame,(stamp,sample,vertices,masks) in enumerate(zip(times,samples,points,support)):
        if sample['time_s']!=stamp or len(vertices)!=2 or len(masks)!=2: raise ValueError('Fixed paired clock required')
        for v,m,f in zip(vertices,masks,faces):
            v,m=np.asarray(v),np.asarray(m)
            if (v.ndim!=2 or v.shape[1:]!=(3,) or not len(v) or not np.isfinite(v).all()
                    or f.max()>=len(v) or m.shape!=(len(v),) or m.dtype!=bool):
                raise ValueError('Complete finite vertices and boolean control support required')
        pairs=sample['proper']
        if not pairs: continue
        pairs=np.asarray(pairs)
        if (pairs.ndim!=2 or pairs.shape[1:]!=(2,) or not np.issubdtype(pairs.dtype,np.integer)
                or len(np.unique(pairs,axis=0))!=len(pairs) or pairs.min()<0
                or any(pairs[:,i].max()>=len(faces[i]) for i in range(2))):
            raise ValueError('Unique in-range crossing pairs required')
        ids=[faces[i][pairs[:,i]] for i in range(2)]
        triangles=[np.asarray(vertices[i])[ids[i]] for i in range(2)]
        axes=choose_axes(*triangles); residual=np.maximum(0.,1e-8-gaps(*triangles,axes).min(axis=1))
        influence=np.stack([np.asarray(masks[i])[ids[i]].any(axis=1) for i in range(2)],axis=1)
        for j,pair in enumerate(pairs):
            rows.append(dict(time_s=float(stamp),frame=frame,left_triangle=int(pair[0]),right_triangle=int(pair[1]),
                vertices=[v[j].tolist() for v in ids],axis=axes[j].tolist(),
                fixed_axis_violation_m=float(residual[j]),influenced_actors=influence[j].tolist(),
                potentially_editable=bool(influence[j].any())))
    if not rows: raise ValueError('At least one observed crossing required')
    summary=[]
    for stamp in times:
        group=[r for r in rows if r['time_s']==stamp];editable=[r for r in group if r['potentially_editable']]
        frozen=[r for r in group if not r['potentially_editable']]
        summary.append(dict(time_s=float(stamp),crossing_pairs=len(group),potentially_editable_pairs=len(editable),unaffected_pairs=len(frozen),
            editable_peak_m=max([r['fixed_axis_violation_m'] for r in editable],default=0.),
            unaffected_peak_m=max([r['fixed_axis_violation_m'] for r in frozen],default=0.)))
    return dict(rows=rows,summary=summary,all_crossing_pairs=len(rows),potentially_editable_pairs=sum(r['potentially_editable'] for r in rows),
        quality_approved=False,scope='Complete sampled crossing population. Positive control support is not a feasibility proof; fixed-axis residual is not penetration depth.')


def finger_support(model, skin, times):
    """Conservative skin support including edited-node descendants and key timing."""
    times=np.asarray(times,float)
    result=np.zeros((len(times),len(skin.weights)),dtype=bool)
    for entry in model.model.entries:
        node=entry['node'];descendants=[]
        for n in range(len(model.rig.parents)):
            parent=n
            while parent>=0 and parent!=node: parent=model.rig.parents[parent]
            if parent==node:descendants.append(n)
        influenced=np.any(np.isin(skin.nodes,descendants)&(skin.weights>0),axis=1)
        weights=np.zeros(len(entry['clock']));weights[entry['ids']]=entry['weights'][:,0]
        active=np.interp(times,entry['clock'],weights,left=weights[0],right=weights[-1])>0
        result|=active[:,None]&influenced[None,:]
    return result
