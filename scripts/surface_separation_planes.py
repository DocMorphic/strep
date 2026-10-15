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
