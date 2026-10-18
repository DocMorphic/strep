"""Sufficient obstruction for fixed represented meshes and an ideal rigid box.

Discovery uses floating Delaunay proposals; only exact rational checks certify.
No witness is not feasibility. Character edits and earlier rounding are outside
this model. Connectivity is checked on original mesh edges, never a hull proxy.
"""
from collections import deque
from fractions import Fraction as Q
from itertools import product
import numpy as np
from scipy.spatial import Delaunay,QhullError
from exact_triangle_crossing_witness import sub,dot,cross

SCHEMA='strep-fixed-grip-box-obstruction-v1'


def points(value):
    if any(isinstance(x,(bool,np.bool_)) for x in np.asarray(value,dtype=object).flat):raise ValueError('Boolean coordinates are not numeric source geometry')
    raw=np.asarray(value)
    if raw.dtype.kind not in 'fiu' or raw.ndim!=2 or raw.shape[1]!=3 or not len(raw) or not np.isfinite(raw).all():raise ValueError('Finite represented numeric points (N,3) required')
    return raw.astype(float)


def exact(point):return tuple(Q(float(x)) for x in point)


def topology(value,count):
    raw=np.asarray(value)
    if raw.dtype.kind not in 'iu' or raw.ndim!=2 or raw.shape[1]!=3 or not len(raw) or np.any(raw<0) or np.any(raw>=count):raise ValueError('Complete in-range integer triangle topology required')
    if any(len(set(row))!=3 for row in raw):raise ValueError('Distinct triangle indices required')
    return raw


def box_model(vertices,faces,grip,tolerance):
    vertices=points(vertices);faces=topology(faces,len(vertices));g=exact(points([grip])[0])
    if isinstance(tolerance,(bool,np.bool_)) or not isinstance(tolerance,(int,float,np.integer,np.floating)) or not np.isfinite(tolerance) or tolerance<0:raise ValueError('Finite nonnegative grip tolerance required')
    eps=Q(float(tolerance));v=list(map(exact,vertices));lo=tuple(min(p[j] for p in v) for j in range(3));hi=tuple(max(p[j] for p in v) for j in range(3))
    if len(v)!=8 or len(faces)!=12 or any(a>=b for a,b in zip(lo,hi)) or set(v)!=set(product(*zip(lo,hi))):raise ValueError('Recognized eight-corner twelve-triangle axis box required')
    covered=set()
    for axis in range(3):
        for side,level in enumerate([lo[axis],hi[axis]]):
            ids=[i for i,f in enumerate(faces) if all(v[int(k)][axis]==level for k in f)]
            if len(ids)!=2:raise ValueError('Every box face must have two covering triangles')
            a,b=[list(map(int,faces[i])) for i in ids];common=set(a)&set(b)
            if len(common)!=2 or len(set(a)|set(b))!=4:raise ValueError('Full original box face coverage required')
            x,y=sorted(common)
            if any(v[x][j]==v[y][j] for j in range(3) if j!=axis):raise ValueError('Face triangles must share a diagonal')
            area=Q(0)
            for face in [a,b]:
                normal=cross(sub(v[face[1]],v[face[0]]),sub(v[face[2]],v[face[0]]))
                if normal[axis]*(1 if side else -1)<=0:raise ValueError('Outward box triangle winding required')
                area+=abs(normal[axis])
            other=[j for j in range(3) if j!=axis]
            if area!=2*(hi[other[0]]-lo[other[0]])*(hi[other[1]]-lo[other[1]]):raise ValueError('Exact face area coverage required')
            covered.update(ids)
    if covered!=set(range(12)):raise ValueError('Every box triangle must belong to one face')
    boundary=[(j,s) for j in range(3) for s,level in enumerate([lo[j],hi[j]]) if g[j]==level]
    if len(boundary)!=1 or any(not lo[j]<=g[j]<=hi[j] for j in range(3)):raise ValueError('Grip strictly inside exactly one box face required')
    axis,side=boundary[0];margins=[hi[axis]-lo[axis]]+[d for j in range(3) if j!=axis for d in [g[j]-lo[j],hi[j]-g[j]]]
    radius=min(margins)*Q(99,100)
    if radius<=eps:raise ValueError('No positive inward half-ball beyond grip tolerance')
    sweep=max(sum(abs(p[j]-g[j]) for j in range(3)) for p in v)+eps
    return radius,eps,sweep


def actor_data(actors):
    if not isinstance(actors,dict) or not actors or len(actors)>16 or any(not isinstance(n,str) or not n for n in actors):raise ValueError('Named fixed actor meshes required')
    result={}
    for name,(vertices,faces) in actors.items():
        vertices=points(vertices);result[name]=(vertices,topology(faces,len(vertices)))
    return result


def referenced(actors,refs):
    if not isinstance(refs,list) or len(refs)!=4:raise ValueError('Four original source references required')
    for ref in refs:
        if not isinstance(ref,list) or len(ref)!=2 or not isinstance(ref[0],str) or ref[0] not in actors or type(ref[1]) is not int or not 0<=ref[1]<len(actors[ref[0]][0]):raise ValueError('Original actor/vertex identity required')
    if len({tuple(r) for r in refs})!=4:raise ValueError('Distinct tetrahedron vertices required')
    return [exact(actors[n][0][i]) for n,i in refs]


def graph(faces):
    result={int(i):set() for i in np.unique(faces)}
    for a,b,c in faces:
        for x,y in [(int(a),int(b)),(int(b),int(c)),(int(c),int(a))]:result[x].add(y);result[y].add(x)
    return result


def certificate(vertices,faces,grip,centre,tolerance,actors,refs):
    radius,eps,sweep=box_model(vertices,faces,grip,tolerance);actors=actor_data(actors);p=exact(points([centre])[0]);v=referenced(actors,refs)
    e=[sub(v[i],v[0]) for i in [1,2,3]];d=sub(p,v[0]);det=dot(e[0],cross(e[1],e[2]))
    if not det:raise ValueError('Degenerate tetrahedron cannot certify')
    w=[dot(d,cross(e[1],e[2]))/det,dot(e[0],cross(d,e[2]))/det,dot(e[0],cross(e[1],d))/det];w=[1-sum(w)]+w
    if min(w)<=0:raise ValueError('Contact centre must be strictly inside tetrahedron')
    bounds=[]
    for opposite in range(4):
        a,b,c=[v[i] for i in range(4) if i!=opposite];normal=cross(sub(b,a),sub(c,a));bounds.append(abs(dot(sub(p,a),normal))/sum(map(abs,normal)))
    ball=min(bounds)
    if ball<=eps or any(dot(sub(q,p),sub(q,p))>=(radius-eps)**2 for q in v):raise ValueError('Strict half-ball reach and contained ball larger than tolerance required')
    paths=[];graphs={}
    for name,start in refs:
        if name not in graphs:graphs[name]=graph(actors[name][1])
        edges=graphs[name]
        if start not in edges:raise ValueError('Interior witness must belong to original mesh surface')
        previous={start:None};queue=deque([start]);far=None
        while queue:
            node=queue.popleft();delta=sub(exact(actors[name][0][node]),p)
            if dot(delta,delta)>sweep**2:far=node;break
            for other in sorted(edges[node]):
                if other not in previous:previous[other]=node;queue.append(other)
        if far is None:raise ValueError('Connected original surface must reach outside every box pose')
        path=[]
        while far is not None:path.append(far);far=previous[far]
        paths.append(list(reversed(path)))
    proof=dict(schema=SCHEMA,references=refs,barycentric_rational=list(map(str,w)),contained_ball_radius_lower_rational=str(ball),connected_paths=paths)
    verify(vertices,faces,grip,centre,tolerance,actors,proof)
    return proof


def verify(vertices,faces,grip,centre,tolerance,actors,proof):
    """Check supplied certificate directly; no Delaunay or construction solver."""
    if not isinstance(proof,dict) or set(proof)!={'schema','references','barycentric_rational','contained_ball_radius_lower_rational','connected_paths'} or proof['schema']!=SCHEMA:raise ValueError('Complete explicit obstruction certificate required')
    radius,eps,sweep=box_model(vertices,faces,grip,tolerance);actors=actor_data(actors);p=exact(points([centre])[0]);v=referenced(actors,proof['references'])
    try:
        raw=proof['barycentric_rational'];bound=proof['contained_ball_radius_lower_rational']
        if not isinstance(raw,list) or len(raw)!=4 or any(not isinstance(x,str) or len(x)>4096 for x in raw) or not isinstance(bound,str) or len(bound)>4096:raise ValueError()
        w=list(map(Q,raw));ball=Q(bound)
    except (ValueError,ZeroDivisionError,TypeError) as exc:raise ValueError('Bounded rational weights and ball required') from exc
    if min(w)<=0 or sum(w)!=1 or any(sum(w[i]*v[i][j] for i in range(4))!=p[j] for j in range(3)) or ball<=eps:raise ValueError('Exact positive centre coordinates and strict ball bound required')
    for opposite in range(4):
        a,b,c=[v[i] for i in range(4) if i!=opposite];normal=cross(sub(b,a),sub(c,a));offset=dot(sub(p,a),normal)
        if dot(normal,normal)==0 or offset*dot(sub(v[opposite],a),normal)<=0 or offset**2<ball**2*dot(normal,normal):raise ValueError('Exact squared tetrahedron face distances failed')
    if any(dot(sub(q,p),sub(q,p))>=(radius-eps)**2 for q in v):raise ValueError('Exact half-ball reach failed')
    paths=proof['connected_paths']
    if not isinstance(paths,list) or len(paths)!=4:raise ValueError('Four original mesh paths required')
    graphs={}
    for (name,start),path in zip(proof['references'],paths):
        if name not in graphs:graphs[name]=graph(actors[name][1])
        edges=graphs[name]
        if not isinstance(path,list) or not path or len(path)>len(actors[name][0]) or any(type(i) is not int or i not in edges for i in path) or path[0]!=start or any(b not in edges[a] for a,b in zip(path,path[1:])):raise ValueError('Original connected surface edge path required')
        delta=sub(exact(actors[name][0][path[-1]]),p)
        if dot(delta,delta)<=sweep**2:raise ValueError('Path endpoint must be outside every rigid box pose')
    return dict(fixed_geometry_rigid_grip_obstruction_proved=True,contact_tolerance_m=float(eps),contained_ball_radius_lower_m=float(ball),box_halfball_radius_m=float(radius),character_edits_covered=False,earlier_rounding_certified=False,quality_approved=False,release_approved=False)


def discover(vertices,faces,grip,centre,tolerance,actors,*,maximum_candidates=10000,maximum_tetrahedra=128):
    """Bounded sufficient search. Unsupported/no witness always means unknown."""
    for value,cap in [(maximum_candidates,10000),(maximum_tetrahedra,512)]:
        if type(value) is not int or not 1<=value<=cap:raise ValueError('Explicit bounded discovery budget required')
    actors=actor_data(actors);p=points([centre])[0]
    try:radius,eps,_=box_model(vertices,faces,grip,tolerance)
    except ValueError as exc:return dict(status='unknown',reason=str(exc),proof=None,candidates=0,tetrahedra_checked=0)
    refs=[];selected=[]
    for name,(world,top) in actors.items():
        # Floating screening can only omit a proof, never accept one.
        distance=np.linalg.norm(world-p,axis=1)
        # A contact vertex exactly at p makes p a Delaunay vertex; every
        # incident simplex then has zero weights and cannot enclose a ball.
        # Omit that screening neighbourhood. Exact checks still accept proofs.
        ids=np.intersect1d(np.flatnonzero((distance<float(radius-eps))&(distance>2*float(eps))),np.unique(top))
        refs.extend([[name,int(i)] for i in ids]);selected.extend(world[ids])
        if len(refs)>maximum_candidates:return dict(status='unknown',reason='candidate_budget_exceeded_without_truncation',proof=None,candidates=len(refs),tetrahedra_checked=0)
    result=dict(status='unknown',reason='no_verified_witness',proof=None,candidates=len(refs),tetrahedra_checked=0)
    if len(refs)<4:return result
    selected=np.asarray(selected)
    try:mesh=Delaunay(selected)
    except QhullError:return dict(result,reason='discovery_triangulation_unavailable')
    first=int(mesh.find_simplex(p));order=([first] if first>=0 else [])+np.argsort(np.linalg.norm(selected[mesh.simplices].mean(axis=1)-p,axis=1)).tolist();seen=set()
    for index in order:
        if index in seen:continue
        if len(seen)>=maximum_tetrahedra:break
        seen.add(index);result['tetrahedra_checked']=len(seen)
        try:proof=certificate(vertices,faces,grip,p,tolerance,actors,[refs[i] for i in mesh.simplices[index]])
        except ValueError:continue
        return dict(result,status='proved_fixed_geometry_obstruction',reason='exact_certificate_verified',proof=proof)
    return result
