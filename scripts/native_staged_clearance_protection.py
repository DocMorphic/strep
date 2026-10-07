"""Carry every archived clearance axis/margin through fresh indexed point jets.

No old point or row derivatives are accepted. Caller binds complete original
descriptors, captured point populations and same-pose source provenance.
This preserves affine protections; actual exports and scene gates decide use.
"""
import copy
from dataclasses import dataclass
import numpy as np
from scipy import sparse
from native_triangle_separation_guards import SeparationGuards


@dataclass
class IndexedPointFrame:
    actor: str
    time_s: float
    vertex_ids: list
    points_world: np.ndarray
    point_jacobian: np.ndarray


def transport(fresh,descriptors,clearances_m,frames,required_times_s,required_actors,
              *,maximum_rows=400000,maximum_elements=60000000):
    """Validate entire populations, then append all original guards unchanged.

Every required actor/time needs one explicitly indexed current point frame.
Frames may contain full guide skins or complete selected components; missing
referenced vertices are rejected. No anatomical or full-time mesh claim follows.
Fresh rows must reproduce exactly from those same point columns. Archived
axes/margins and descriptor order survive; only gaps/columns are remeasured.
    """
    if not isinstance(fresh,SeparationGuards) or not isinstance(fresh.report,dict):
        raise ValueError('Complete fresh separation guard model required')
    n=fresh.report.get('controls')
    if (type(n) is not int or not 1<=n<=96 or fresh.report.get('complete_pair_partition') is not True
            or type(maximum_rows) is not int or not 1<=maximum_rows<=400000
            or type(maximum_elements) is not int or not 1<=maximum_elements<=60000000
            or not isinstance(descriptors,list) or not isinstance(fresh.descriptors,list)
            or len(descriptors)+len(fresh.descriptors)>maximum_rows
            or (len(descriptors)+len(fresh.descriptors))*n>maximum_elements
            or not isinstance(required_actors,list) or not 2<=len(required_actors)<=8
            or any(type(a) is not str or not a for a in required_actors)
            or len(set(required_actors))!=len(required_actors)
            or not isinstance(required_times_s,list) or not 1<=len(required_times_s)<=4096
            or any(type(t) not in (int,float) for t in required_times_s)
            or not isinstance(frames,list) or len(frames)!=len(required_actors)*len(required_times_s)):
        raise ValueError('Complete original clock, actors, rows and explicit budgets required')
    times=np.array(required_times_s,float)
    if not np.isfinite(times).all() or np.any(times<0) or np.any(np.diff(times)<=0):
        raise ValueError('Finite ordered original clock required')
    lookup={};elements=0
    for frame in frames:
        if (not isinstance(frame,IndexedPointFrame) or type(frame.actor) is not str
                or frame.actor not in required_actors or type(frame.time_s) not in (int,float)
                or frame.time_s not in required_times_s or (frame.actor,frame.time_s) in lookup
                or not isinstance(frame.vertex_ids,list) or not frame.vertex_ids
                or any(type(v) is not int or v<0 for v in frame.vertex_ids)
                or frame.vertex_ids!=sorted(set(frame.vertex_ids))):
            raise ValueError('One complete explicitly indexed frame per actor/time required')
        p,j=np.asarray(frame.points_world),np.asarray(frame.point_jacobian)
        if (p.shape!=(len(frame.vertex_ids),3) or j.shape!=(*p.shape,n)
                or p.dtype.kind not in 'fiu' or j.dtype.kind not in 'fiu'
                or not np.isfinite(p).all() or not np.isfinite(j).all()):
            raise ValueError('Every finite current point and control column required')
        elements+=j.size
        if elements>maximum_elements:raise ValueError('Complete point population exceeds budget')
        p,j=p.astype(float,copy=False),j.astype(float,copy=False)
        if not np.isfinite(p).all() or not np.isfinite(j).all():
            raise ValueError('Complete point population must remain finite in Float64')
        lookup[frame.actor,frame.time_s]=(p,j,{v:i for i,v in enumerate(frame.vertex_ids)})
    if set(lookup)!={(a,t) for a in required_actors for t in required_times_s}:
        raise ValueError('Every original actor/time must be represented')
    old_margin=np.asarray(clearances_m,float);fg=np.asarray(fresh.gaps_m,float);fm=np.asarray(fresh.clearances_m,float)
    fj=sparse.csr_matrix(fresh.jacobian,copy=True)
    if (old_margin.shape!=(len(descriptors),) or fg.shape!=(len(fresh.descriptors),)
            or fm.shape!=fg.shape or fj.shape!=(len(fg),n)
            or any(not np.isfinite(v).all() for v in (old_margin,fg,fm,fj.data))
            or np.any(old_margin<=0) or np.any(fm<=0)):
        raise ValueError('Complete finite fresh rows and original positive margins required')
    def project(d,margin):
        if not isinstance(d,dict):raise ValueError('Explicit original guard descriptor required')
        actors=d.get('actors');axis=d.get('axis_world');t=d.get('time_s')
        if (not isinstance(actors,list) or len(actors)!=2 or actors[0]==actors[1]
                or any(type(a) is not str or a not in required_actors for a in actors)
                or type(t) not in (int,float) or t not in required_times_s
                or not isinstance(axis,list) or len(axis)!=3 or any(type(v) not in (int,float) for v in axis)
                or not np.isfinite(axis).all() or abs(np.linalg.norm(axis)-1.)>1e-12
                or type(d.get('clearance_m')) not in (int,float) or d['clearance_m']!=margin):
            raise ValueError('Original source/time axis and margin required without normalization')
        points=[];jets=[]
        for actor,key in zip(actors,('left_vertex','right_vertex')):
            vertex=d.get(key);p,j,ids=lookup[actor,t]
            if type(vertex) is not int or vertex not in ids:
                raise ValueError('Every original referenced vertex must exist at its exact time')
            points.append(p[ids[vertex]]);jets.append(j[ids[vertex]])
        axis=np.array(axis,float);gap=float((points[0]-points[1])@axis);column=axis@(jets[0]-jets[1])
        if not np.isfinite(gap) or not np.isfinite(column).all():
            raise ValueError('Finite full guard projection required')
        return gap,column
    for i,(d,m) in enumerate(zip(fresh.descriptors,fm)):
        g,j=project(d,m)
        if g!=fg[i] or not np.array_equal(j,fj.getrow(i).toarray().ravel()):
            raise ValueError('Fresh rows must bind exactly to the supplied current point jets')
    gaps=[];columns=[]
    for d,m in zip(descriptors,old_margin):
        g,j=project(d,m);gaps.append(g);columns.append(j)
    report=copy.deepcopy(fresh.report)
    report.update(guard_rows=len(fg)+len(gaps),fresh_partition_guard_rows=len(fg),
        carried_original_guard_rows=len(gaps),complete_point_frames=len(frames),
        point_control_elements=elements,original_axes_margins_and_row_order_preserved=True,
        old_point_or_guard_derivatives_reused=False,source_provenance_verified=False,
        all_original_guards_retained=True,full_time_mesh_coverage_certified=False,
        nonlinear_or_export_certificate=False,quality_approved=False,release_approved=False)
    archived=sparse.csr_matrix(np.array(columns).reshape(len(gaps),n))
    return SeparationGuards(np.r_[fg,gaps],sparse.vstack([fj,archived],format='csr'),
        np.r_[fm,old_margin],copy.deepcopy(fresh.descriptors)+copy.deepcopy(descriptors),report)
