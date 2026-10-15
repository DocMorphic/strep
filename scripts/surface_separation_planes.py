"""Complete-vertex projection guides for pre-contact pose proposals.

Positive projection separation implies disjoint selected triangle hulls in exact
arithmetic. Ordinary Float64 bounds here are not certified arithmetic, anatomy,
physical contact, full-scene collision, temporal or quality approval. Overlapping
projections do not imply intersecting geometry.
"""
import numpy as np


def require(value,message):
    if not value:raise ValueError(message)


def planes(left_vertices,right_vertices,axis_world,clearance_m):
    """Return two fixed halfspaces about the original projected midpoint.

Both complete caller-supplied populations participate, with first original
vertex witnesses on ties. Axis/clearance are explicit authorship, not inferred
palm normals. Plane convention matches native pose guidance: n dot p >= offset.
    """
    left,right,axis=[np.asarray(v,dtype=float) for v in (left_vertices,right_vertices,axis_world)]
    require(all(v.ndim==2 and v.shape[1:]==(3,) and len(v)>0 and np.isfinite(v).all() for v in (left,right)),
        'Complete finite nonempty vertex populations required')
    require(axis.shape==(3,) and np.isfinite(axis).all(),'Finite three-dimensional authored axis required')
    require(type(clearance_m) in (int,float) and np.isfinite(clearance_m) and clearance_m>=0,
        'Explicit finite nonnegative clearance required')
    try:
        with np.errstate(over='raise',invalid='raise'):
            length=float(np.linalg.norm(axis))
            require(abs(length-1)<=1e-12,'Unit authored axis required; no normalization inferred')
            a=left@axis;b=right@axis
    except FloatingPointError as exc:raise ValueError('Finite projection arithmetic required') from exc
    require(np.isfinite(a).all() and np.isfinite(b).all(),'Finite complete projections required')
    li,ri=int(a.argmax()),int(b.argmin());maximum,minimum=float(a[li]),float(b[ri]);gap=minimum-maximum
    midpoint=maximum*.5+minimum*.5;left_limit=midpoint-clearance_m*.5;right_limit=midpoint+clearance_m*.5
    require(all(np.isfinite(v) for v in (gap,midpoint,left_limit,right_limit)),'Finite separation bounds required')
    return dict(schema='strep-surface-separation-planes-v1',axis_world=axis.tolist(),clearance_m=float(clearance_m),
        left_vertices=len(left),right_vertices=len(right),left_maximum_projection_m=maximum,right_minimum_projection_m=minimum,
        left_witness_vertex=li,right_witness_vertex=ri,signed_projection_gap_m=gap,
        clearance_condition_pass=bool(gap>=clearance_m),strict_projection_separation=bool(gap>0),
        left_guide_plane=dict(normal_world=(-axis).tolist(),offset_m=-left_limit),
        right_guide_plane=dict(normal_world=axis.tolist(),offset_m=right_limit),
        all_supplied_vertices_considered=True,axis_inferred=False,anatomy_verified=False,
        continuous_collision_certified=False,quality_approved=False,release_approved=False,
        scope='Two authored complete-population halfspace guides at one pose. Positive separation is a sufficient '
            'exact-arithmetic condition for triangles whose vertices are all included; failed projection separation '
            'does not imply a collision. Zero clearance can permit touching. No geometry queries, '
            'Float64 certification, source motion budgets, contact timing or animation approval.')


def face_planes(first_vertices,second_vertices,clearance_m,*,maximum_axes=4096,workspace_bytes=64*1024**2):
    """Finite geometry-derived guidance: XYZ plus every returned hull facet normal.

Every original supplied point participates in every projection. No edge-cross
axes are added, so this is not a complete separating-axis test or minimum
translation solver. Hulls select candidate directions only, never acceptance.
    """
    from scipy.spatial import ConvexHull,QhullError
    first,second=[np.asarray(v,dtype=float) for v in (first_vertices,second_vertices)]
    require(all(v.ndim==2 and v.shape[1:]==(3,) and 4<=len(v)<=32768 and np.isfinite(v).all() for v in (first,second)),
        'Complete finite 3D populations of 4-32768 vertices required')
    planes(first,second,[1.,0.,0.],clearance_m)
    require(type(maximum_axes) is int and 1<=maximum_axes<=262147,'Explicit positive candidate budget required')
    column_bytes=(len(first)+len(second))*np.dtype(float).itemsize
    require(type(workspace_bytes) is int and workspace_bytes>=column_bytes,'Projection workspace must hold one complete candidate column')
    try:hulls=[ConvexHull(v) for v in (first,second)]
    except QhullError as exc:raise ValueError('Nondegenerate complete 3D populations required; no points joggled or discarded') from exc
    counts=[len(h.equations) for h in hulls];total=3+sum(counts)
    require(total<=maximum_axes,'Complete hull-facet candidate population exceeds explicit budget; no axes discarded')
    raw=np.concatenate([np.eye(3),*[h.equations[:,:3] for h in hulls]])
    lengths=np.linalg.norm(raw,axis=1)
    require(np.isfinite(raw).all() and np.isfinite(lengths).all() and np.all(lengths>0),'Finite nonzero complete facet normals required')
    axes=raw/lengths[:,None];gaps=np.empty(total);left=np.empty(total,dtype=np.int64)
    width=min(total,workspace_bytes//column_bytes)
    try:
        with np.errstate(over='raise',invalid='raise'):
            for start in range(0,total,width):
                stop=min(total,start+width);a=first@axes[start:stop].T;b=second@axes[start:stop].T
                order=a.mean(0)<=b.mean(0)
                gaps[start:stop]=np.where(order,b.min(0)-a.max(0),a.min(0)-b.max(0))
                left[start:stop]=np.where(order,0,1)
                del a,b
    except FloatingPointError as exc:raise ValueError('Finite complete facet projection arithmetic required') from exc
    require(np.isfinite(gaps).all(),'Finite complete candidate gaps required')
    index=int(gaps.argmax());populations=[first,second];li=int(left[index]);ri=1-li
    selected=planes(populations[li],populations[ri],axes[index],clearance_m)
    selected.update(axis_inferred=True,anatomical_axis_inferred=False,
        scope='Geometry-derived finite facet-axis guide on complete supplied populations. No anatomical normal, full scene query, continuous-time or motion approval.')
    return dict(schema='strep-surface-facet-plane-guidance-v1',selected=selected,selected_axis_index=index,
        left_population=li,right_population=ri,population_vertices=[len(first),len(second)],hull_facet_counts=counts,
        axes_world=axes.tolist(),signed_projection_gaps_m=gaps.tolist(),left_population_per_axis=left.tolist(),
        candidate_count=total,all_returned_hull_facet_normals_considered=True,all_supplied_vertices_considered=True,
        axis_order='world XYZ, first hull returned facet order, second hull returned facet order; first maximum gap on ties',
        orientation_rule='lower complete-population mean projection is left; first population on exact ties',
        geometry_axis_inferred=True,anatomical_axis_inferred=False,edge_cross_axes_included=False,
        projection_workspace_bytes=workspace_bytes,projection_columns_per_batch=width,
        collision_certified=False,minimum_translation_certified=False,quality_approved=False,release_approved=False)
