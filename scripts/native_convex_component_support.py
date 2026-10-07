"""Complete convex-component support guides; original mesh gates still decide.

Face normals and edge cross products supply candidate separating directions.
Float64 convexity/axis checks are diagnostic, not a certified collision predicate.
"""
import numpy as np


def _component(points, faces, tolerance):
    p=np.asarray(points,float);f=np.asarray(faces)
    if (p.ndim!=2 or p.shape[1:]!=(3,) or not 4<=len(p)<=64 or not np.isfinite(p).all()
            or f.ndim!=2 or f.shape[1:]!=(3,) or not 4<=len(f)<=256
            or not np.issubdtype(f.dtype,np.integer) or f.min()<0 or f.max()>=len(p)
            or np.any(np.diff(np.sort(f,axis=1),axis=1)==0)
            or len(np.unique(np.sort(f,axis=1),axis=0))!=len(f)
            or set(np.unique(f))!=set(range(len(p)))):
        raise ValueError('Complete finite referenced convex component vertices and distinct triangle indices required')
    incidence={};adjacency=[set() for _ in f]
    for i,face in enumerate(f):
        for u,v in zip(face,np.roll(face,-1)):
            key=tuple(sorted((int(u),int(v))))
            incidence.setdefault(key,[]).append((i,1 if u<v else -1))
    if any(len(items)!=2 or sum(s for _,s in items)!=0 for items in incidence.values()):
        raise ValueError('A closed consistently wound whole component is required')
    for items in incidence.values():
        a,b=[i for i,_ in items];adjacency[a].add(b);adjacency[b].add(a)
    visited={0};queue=[0]
    while queue:
        for other in adjacency[queue.pop()]-visited:visited.add(other);queue.append(other)
    if len(visited)!=len(f):raise ValueError('Exactly one connected component is required')
    triangles=p[f];cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    areas=np.linalg.norm(cross,axis=1)
    if not np.isfinite(areas).all() or np.any(areas<=1e-16):
        raise ValueError('Every component triangle must be nondegenerate')
    center=p.mean(axis=0)
    volume=float(np.einsum('ij,ij->',triangles[:,0]-center,cross)/6)
    if not np.isfinite(volume) or abs(volume)<=1e-18:raise ValueError('Nonzero finite enclosed component volume required')
    normals=cross/areas[:,None]
    outward=normals*np.sign(volume)
    plane_excess=np.einsum('fvj,fj->fv',p[None,:,:]-triangles[:,0,None,:],outward)
    if np.max(plane_excess)>tolerance:raise ValueError('Component is not convex under the explicit diagnostic tolerance')
    edges=np.array(sorted(incidence),int)
    vectors=p[edges[:,1]]-p[edges[:,0]]
    lengths=np.linalg.norm(vectors,axis=1)
    if not np.isfinite(lengths).all() or np.any(lengths<=0):raise ValueError('Finite nonzero component edges required')
    return p,f,normals,edges,vectors/lengths[:,None],dict(vertices=len(p),faces=len(f),edges=len(edges),
        signed_volume_m3=volume,maximum_convex_plane_excess_m=float(plane_excess.max()),
        winding='positive' if volume>0 else 'negative')


def support_pair(left_points,left_faces,right_points,right_faces,*,convex_tolerance_m=1e-10,
                 minimum_cross_norm=1e-12,maximum_candidate_axes=4096,maximum_vertex_pairs=4096):
    """Select the largest signed whole-component gap and retain every pair row.

    Caller authenticates exact complete source-index component membership.
    The selected unit axis points from the right component toward the left.
    Every left/right vertex pair contributes (left-right) dot axis. Its minimum
    equals the gap between complete projected support intervals. All provided
    triangle normals and topological edge cross products are considered, with
    both signs; mesh diagonals add valid candidate axes without deleting edges.
    Near-parallel directions are explicitly recorded, never collision approval.
    """
    if (type(convex_tolerance_m) not in (int,float) or not np.isfinite(convex_tolerance_m) or not 0<=convex_tolerance_m<=1e-7
            or type(minimum_cross_norm) not in (int,float) or not np.isfinite(minimum_cross_norm) or not 0<minimum_cross_norm<=1e-8
            or type(maximum_candidate_axes) is not int or not 1<=maximum_candidate_axes<=4096
            or type(maximum_vertex_pairs) is not int or not 1<=maximum_vertex_pairs<=4096):
        raise ValueError('Explicit finite diagnostic thresholds and complete support budgets required')
    a,af,an,ae,av,ai=_component(left_points,left_faces,convex_tolerance_m)
    b,bf,bn,be,bv,bi=_component(right_points,right_faces,convex_tolerance_m)
    raw_count=len(an)+len(bn)+len(av)*len(bv)
    pairs=len(a)*len(b)
    if 2*raw_count>maximum_candidate_axes or pairs>maximum_vertex_pairs:
        raise ValueError('Complete component axes or vertex-pair population exceeds its explicit budget')
    raw=np.concatenate([an,bn,np.cross(av[:,None,:],bv[None,:,:]).reshape(-1,3)])
    lengths=np.linalg.norm(raw,axis=1)
    if not np.isfinite(lengths).all():raise ValueError('Finite complete candidate directions required')
    available=lengths>minimum_cross_norm
    indices=np.flatnonzero(available)
    unit=raw[available]/lengths[available,None]
    axes=np.stack([unit,-unit],axis=1).reshape(-1,3)
    left_projection=a@axes.T;right_projection=b@axes.T
    gaps=left_projection.min(axis=0)-right_projection.max(axis=0)
    if not np.isfinite(gaps).all():raise ValueError('Finite complete support projections required')
    chosen=int(np.argmax(gaps));raw_index=int(indices[chosen//2]);axis=axes[chosen]
    pair_gaps=(a[:,None,:]-b[None,:,:])@axis
    # Different arithmetic groupings may differ by rounding; this is recorded,
    # never used as a motion/mesh acceptance allowance.
    discrepancy=float(abs(pair_gaps.min()-gaps[chosen]))
    if raw_index<len(an):identity=dict(kind='left-face',face=raw_index)
    elif raw_index<len(an)+len(bn):identity=dict(kind='right-face',face=raw_index-len(an))
    else:
        i,j=divmod(raw_index-len(an)-len(bn),len(bv))
        identity=dict(kind='edge-cross',left_edge=ae[i].tolist(),right_edge=be[j].tolist())
    report=dict(schema='strep-native-convex-component-support-v1',left_component=ai,right_component=bi,
        convex_tolerance_m=convex_tolerance_m,minimum_cross_norm=minimum_cross_norm,
        complete_raw_axis_count=raw_count,complete_signed_axis_budget=2*raw_count,
        tested_signed_axis_count=len(axes),skipped_raw_axis_indices=np.flatnonzero(~available).tolist(),
        selected_raw_axis_index=raw_index,selected_sign=1 if chosen%2==0 else -1,selected_axis_identity=identity,
        axis_world=axis.tolist(),maximum_signed_support_gap_m=float(gaps[chosen]),
        minimum_complete_pair_gap_m=float(pair_gaps.min()),pair_interval_arithmetic_discrepancy_m=discrepancy,
        complete_vertex_pair_rows=pairs,left_vertex_order=list(range(len(a))),right_vertex_order=list(range(len(b))),
        floating_convexity_check=True,certified_collision_predicate=False,continuous_collision_certified=False,
        original_mesh_gate_replaced=False,quality_approved=False,release_approved=False,
        scope='Complete closed convex source-index component support directions under explicit Float64 diagnostic checks. '
              'All input faces/edges and both axis signs, with recorded near-parallel skips. Complete vertex-pair support rows. '
              'Caller binds full component membership; no bounding-box replacement, anatomical inference, '
              'collision certificate, nonconvex mesh support or motion/quality approval.')
    return axis.copy(),pair_gaps,report
