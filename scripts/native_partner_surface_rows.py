"""Complete sampled partner-surface queries, yielding local scalar proposal rows.

Rows are guides for a subsequent solve, not a replacement for full decoded mesh
checks. Closest points and triangle axes must be rebuilt after motion changes.
"""
from itertools import combinations
import numpy as np
import trimesh
from native_scene_geometry import faces_for,policy_for
from convex_partner_surface import candidates
from triangle_crossing import audit
from native_object_surface_rows import append_rows


def separation_axis(left,right):
    left,right=np.asarray(left,float),np.asarray(right,float)
    if left.shape!=(3,3) or right.shape!=(3,3) or not np.isfinite(left).all() or not np.isfinite(right).all():
        raise ValueError('Finite complete triangle pairs required')
    ea=np.roll(left,-1,axis=0)-left;eb=np.roll(right,-1,axis=0)-right
    na=np.cross(ea[0],ea[1]);nb=np.cross(eb[0],eb[1])
    if min(np.linalg.norm(na),np.linalg.norm(nb))<=1e-16:raise ValueError('Nondegenerate triangle separation required')
    axes=[na,nb]+[np.cross(a,b) for a in ea for b in eb]
    axes += [np.cross(na,e) for e in ea]+[np.cross(nb,e) for e in eb]
    best=None
    for axis in axes:
        length=np.linalg.norm(axis)
        if length<=1e-16:continue
        axis=axis/length
        for normal in (axis,-axis):
            gap=float((left@normal).min()-(right@normal).max())
            if best is None or gap>best[0]:best=(gap,normal.copy())
    return best[1],best[0]


class SurfaceRows:
    def __init__(self,scene,rows,report):self.scene,self.rows,self.report=scene,rows,report

    def gaps(self,vertices=None):
        cache={}
        def query(actor,time):
            key=(actor,time)
            if key not in cache:
                source=self.scene.actors[actor]
                if vertices is None:
                    p,r=source['placement'];v=source['rig'].vertices(source['sampler'].sample(time))@r.T+p
                else:v=np.asarray(vertices(actor,time),float)
                if v.shape!=(len(source['skin'].nodes),3) or not np.isfinite(v).all():
                    raise ValueError('Complete finite posed surface population required')
                cache[key]=v
            return cache[key]
        values=[]
        for row in self.rows:
            def point(entry):return np.asarray(entry['weights'])@query(entry['actor'],row['time_s'])[entry['vertices']]
            value=float(point(row['left'])@np.asarray(row['normal_world']))
            value-=float(point(row['right'])@np.asarray(row['normal_world'])) if row['right'] is not None else row['constant_m']
            values.append(value)
        self.scene.check_inputs();return np.asarray(values)


def build(scene,policy,digest,*,clearance=.0005,maximum_rows=20000):
    if type(clearance) not in (int,float) or not np.isfinite(clearance) or not 0<=clearance<=.005:
        raise ValueError('Choose 0-5 mm explicit proposal clearance')
    if type(maximum_rows) is not int or not 1<=maximum_rows<=100000:raise ValueError('Finite explicit surface-row budget required')
    times,_,_=policy_for(policy,scene,digest);faces={n:faces_for(a['rig'])[0] for n,a in scene.actors.items()}
    used={n:np.unique(f) for n,f in faces.items()};rows=[];samples=[]
    def entry(actor,ids,weights):return dict(actor=actor,vertices=np.asarray(ids,int).tolist(),weights=np.asarray(weights,float).tolist())
    def add(kind,time,normal,left,right=None,constant=0.,**identity):
        if len(rows)>=maximum_rows:raise ValueError('Complete surface rows exceed explicit resource budget; no subset returned')
        rows.append(dict(kind=kind,time_s=float(time),normal_world=np.asarray(normal).tolist(),left=left,right=right,constant_m=float(constant),clearance_m=float(clearance),**identity))
    for time in times:
        vertices={};meshes={}
        for n,a in scene.actors.items():
            p,r=a['placement'];vertices[n]=a['rig'].vertices(a['sampler'].sample(float(time)))@r.T+p
            meshes[n]=trimesh.Trimesh(vertices[n][used[n]],np.searchsorted(used[n],faces[n]),process=False)
            for name,plane in policy['planes'].items():
                normal=np.array(plane['normal_world']);gap=vertices[n][used[n]]@normal-plane['offset_m']
                for v in used[n][gap<clearance]:add('world-plane',time,normal,entry(n,[v],[1.]),constant=plane['offset_m'],plane=name)
        pairs=[]
        for left,right in combinations(scene.actors,2):
            crossings=audit(vertices[left],faces[left],vertices[right],faces[right],tolerance_m=policy['limits']['surface_tolerance_m'])
            if any(crossings['degenerate_faces']):raise ValueError('Degenerate partner surfaces cannot produce complete rows')
            for record in crossings['records']:
                a,b=faces[left][record['left_triangle']],faces[right][record['right_triangle']]
                normal,gap=separation_axis(vertices[left][a],vertices[right][b])
                for av in a:
                    for bv in b:add('triangle-separation',time,normal,entry(left,[av],[1.]),entry(right,[bv],[1.]),left_triangle=record['left_triangle'],right_triangle=record['right_triangle'],observed_kind=record['kind'])
            inside=[]
            for source,target in [(left,right),(right,left)]:
                mesh=meshes[target];count=0;queried=0
                if mesh.is_volume:
                    selected,_=candidates(vertices[source][used[source]],vertices[target][used[target]])
                    selected=used[source][selected]
                    for start in range(0,len(selected),32):
                        ids=selected[start:start+32];points=vertices[source][ids]
                        signed=trimesh.proximity.signed_distance(mesh,points);queried+=len(ids)
                        if not np.isfinite(signed).all():raise ValueError('Nonfinite partner signed-distance query')
                        mask=signed>policy['limits']['surface_tolerance_m']
                        if not mask.any():continue
                        closest,distance,triangle=trimesh.proximity.closest_point(mesh,points[mask])
                        for v,q,d,t in zip(ids[mask],closest,distance,triangle):
                            if not np.isfinite(d) or d<=0:raise ValueError('Nonzero finite penetration witness required')
                            face=faces[target][t];bary=trimesh.triangles.points_to_barycentric(vertices[target][face][None],q[None])[0]
                            if not np.isfinite(bary).all() or bary.min()<-1e-7 or bary.max()>1+1e-7:raise ValueError('Contained barycentric witness required')
                            bary=np.maximum(bary,0);bary/=bary.sum();surface=bary@vertices[target][face]
                            if np.linalg.norm(surface-q)>1e-10:raise ValueError('Barycentric surface reconstruction differs')
                            normal=(q-vertices[source][v])/d
                            add('penetrating-vertex',time,normal,entry(source,[v],[1.]),entry(target,face,bary),target_triangle=int(t));count+=1
                inside.append(dict(source=source,target=target,containment_available=bool(mesh.is_volume),referenced_source_vertices=len(used[source]),queried_vertices=queried,witnesses=count))
            pairs.append(dict(actors=[left,right],complete_surface_records=len(crossings['records']),crossing_counts=crossings['counts'],containment=inside))
        objects=append_rows(scene,time,vertices,meshes,faces,policy,clearance,entry,add) if scene.objects else []
        samples.append(dict(time_s=float(time),pairs=pairs,actor_objects=objects))
    scene.check_inputs()
    report=dict(samples=samples,rows=len(rows),clearance_m=float(clearance),maximum_rows=maximum_rows,
        source_vertices={n:len(a['skin'].nodes) for n,a in scene.actors.items()},referenced_vertices={n:len(u) for n,u in used.items()},
        complete_triangle_populations={n:len(f) for n,f in faces.items()},objects_included=bool(scene.objects),
        scope='Complete partner surface broadphase/crossing and referenced-vertex containment queries at declared times. '
            'Local fixed-axis/barycentric scalar proposal rows only; recompute after motion changes and retain full decoded geometry checks. '
            'Declared primitive whole-triangle and center-enclosure support-plane guides included. '
            'No editable object trajectories, self-collision, continuous collision, solver feasibility, quality or release approval.',
        quality_approved=False,release_approved=False)
    return SurfaceRows(scene,rows,report)
