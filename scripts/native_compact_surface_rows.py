"""Complete surface guidance using one nonlinear support gap per triangle pair.

min(A dot n) - max(B dot n) >= c is equivalent, in real arithmetic, to
all nine vertex-pair inequalities on the same fixed axis. Every triangle vertex
is reevaluated; extrema are not frozen to a selected vertex. Finite-difference
linearization of this nonsmooth gap is a local approximation, not an equivalent
nine-halfspace affine model or a collision certificate. Full decoded native and
geometry checks must still decide acceptance. Existing producers are unchanged.
"""
from itertools import combinations
import numpy as np
import trimesh
from native_scene_geometry import faces_for, policy_for, METHODS as GEOMETRY_METHODS
from convex_partner_surface import candidates
from triangle_crossing import audit
from native_partner_surface_rows import separation_axis
from native_object_surface_rows import append_rows

SCHEMA = 'strep-native-compact-surface-guidance-v1'
METHODS = tuple(dict.fromkeys(GEOMETRY_METHODS + ('native_partner_surface_rows.py',
    'native_object_surface_rows.py', 'native_compact_surface_rows.py')))


class CompactSurfaceRows:
    def __init__(self, scene, rows, report):
        self.scene, self.rows, self.report = scene, rows, report

    def gaps(self, vertices=None):
        """Reevaluate all six vertices, including changed extrema after a move."""
        cache = {}
        def query(actor, time):
            key = actor, time
            if key not in cache:
                source = self.scene.actors[actor]
                if vertices is None:
                    p,r = source['placement']; value = source['rig'].vertices(source['sampler'].sample(time)) @ r.T+p
                else: value = np.asarray(vertices(actor,time),float)
                if value.shape != (len(source['skin'].nodes),3) or not np.isfinite(value).all():
                    raise ValueError('Complete finite posed surface population required')
                cache[key] = value
            return cache[key]
        result = np.empty(len(self.rows),float)
        for i, row in enumerate(self.rows):
            normal = np.asarray(row['normal_world'])
            if row['kind'] == 'triangle-support-separation':
                left = query(row['left']['actor'],row['time_s'])[row['left']['vertices']]
                right = query(row['right']['actor'],row['time_s'])[row['right']['vertices']]
                result[i] = float((left @ normal).min()-(right @ normal).max())
            else:
                def point(entry): return np.asarray(entry['weights']) @ query(entry['actor'],row['time_s'])[entry['vertices']]
                value = float(point(row['left']) @ normal)
                value -= float(point(row['right']) @ normal) if row['right'] is not None else row['constant_m']
                result[i] = value
        self.scene.check_inputs()
        return result


def build(scene, policy, digest, *, clearance=.0005, maximum_rows=100000):
    if type(clearance) not in (int,float) or not np.isfinite(clearance) or not 0 <= clearance <= .005:
        raise ValueError('Choose 0-5 mm explicit proposal clearance')
    if type(maximum_rows) is not int or not 1 <= maximum_rows <= 100000:
        raise ValueError('Finite explicit compact surface-row budget required')
    times,_,_ = policy_for(policy,scene,digest)
    faces = {name:faces_for(a['rig'])[0] for name,a in scene.actors.items()}
    used = {name:np.unique(f) for name,f in faces.items()}; rows = []; samples = []; triangle_records = 0
    def entry(actor,ids,weights): return dict(actor=actor,vertices=np.asarray(ids,int).tolist(),weights=np.asarray(weights,float).tolist())
    def add(kind,time,normal,left,right=None,constant=0.,**identity):
        if len(rows) >= maximum_rows: raise ValueError('Complete compact surface rows exceed explicit resource budget; no subset returned')
        rows.append(dict(kind=kind,time_s=float(time),normal_world=np.asarray(normal).tolist(),left=left,right=right,
            constant_m=float(constant),clearance_m=float(clearance),**identity))
    for time in times:
        vertices = {}; meshes = {}
        for name,actor in scene.actors.items():
            p,r = actor['placement']; vertices[name] = actor['rig'].vertices(actor['sampler'].sample(float(time))) @ r.T+p
            meshes[name] = trimesh.Trimesh(vertices[name][used[name]],np.searchsorted(used[name],faces[name]),process=False)
            for plane_name,plane in policy['planes'].items():
                normal = np.array(plane['normal_world']); gaps = vertices[name][used[name]] @ normal-plane['offset_m']
                for v in used[name][gaps < clearance]:
                    add('world-plane',time,normal,entry(name,[v],[1.]),constant=plane['offset_m'],plane=plane_name)
        pairs = []
        for left,right in combinations(scene.actors,2):
            crossings = audit(vertices[left],faces[left],vertices[right],faces[right],tolerance_m=policy['limits']['surface_tolerance_m'])
            if any(crossings['degenerate_faces']): raise ValueError('Degenerate partner surfaces cannot produce complete rows')
            for record in crossings['records']:
                a,b = faces[left][record['left_triangle']],faces[right][record['right_triangle']]
                normal,_ = separation_axis(vertices[left][a],vertices[right][b])
                add('triangle-support-separation',time,normal,dict(actor=left,vertices=a.tolist()),dict(actor=right,vertices=b.tolist()),
                    left_triangle=record['left_triangle'],right_triangle=record['right_triangle'],observed_kind=record['kind'])
                triangle_records += 1
            inside = []
            for source,target in ((left,right),(right,left)):
                mesh = meshes[target]; count = 0; queried = 0
                if mesh.is_volume:
                    selected,_ = candidates(vertices[source][used[source]],vertices[target][used[target]])
                    selected = used[source][selected]
                    for start in range(0,len(selected),32):
                        ids = selected[start:start+32]; points = vertices[source][ids]
                        signed = trimesh.proximity.signed_distance(mesh,points); queried += len(ids)
                        if not np.isfinite(signed).all(): raise ValueError('Nonfinite partner signed-distance query')
                        mask = signed > policy['limits']['surface_tolerance_m']
                        if not mask.any(): continue
                        closest,distance,triangle = trimesh.proximity.closest_point(mesh,points[mask])
                        for v,q,d,t in zip(ids[mask],closest,distance,triangle):
                            if not np.isfinite(d) or d <= 0: raise ValueError('Nonzero finite penetration witness required')
                            face = faces[target][t]
                            bary = trimesh.triangles.points_to_barycentric(vertices[target][face][None],q[None])[0]
                            if not np.isfinite(bary).all() or bary.min() < -1e-7 or bary.max() > 1+1e-7:
                                raise ValueError('Contained barycentric witness required')
                            bary = np.maximum(bary,0); bary /= bary.sum()
                            if np.linalg.norm(bary @ vertices[target][face]-q) > 1e-10: raise ValueError('Barycentric surface reconstruction differs')
                            add('penetrating-vertex',time,(q-vertices[source][v])/d,entry(source,[v],[1.]),entry(target,face,bary),target_triangle=int(t))
                            count += 1
                inside.append(dict(source=source,target=target,containment_available=bool(mesh.is_volume),
                    referenced_source_vertices=len(used[source]),queried_vertices=queried,witnesses=count))
            pairs.append(dict(actors=[left,right],complete_surface_records=len(crossings['records']),crossing_counts=crossings['counts'],containment=inside))
        objects = append_rows(scene,time,vertices,meshes,faces,policy,clearance,entry,add) if scene.objects else []
        samples.append(dict(time_s=float(time),pairs=pairs,actor_objects=objects))
    scene.check_inputs()
    report = dict(schema=SCHEMA,samples=samples,rows=len(rows),triangle_support_blocks=triangle_records,
        expanded_triangle_rows=9*triangle_records,expanded_total_rows=len(rows)+8*triangle_records,
        clearance_m=float(clearance),maximum_rows=maximum_rows,
        source_vertices={name:len(a['skin'].nodes) for name,a in scene.actors.items()},
        referenced_vertices={name:len(ids) for name,ids in used.items()},complete_triangle_populations={name:len(f) for name,f in faces.items()},
        objects_included=bool(scene.objects),all_triangle_vertices_reduced=True,
        nonlinear_nine_pair_equivalence=True,affine_linearization_equivalence=False,
        quality_approved=False,release_approved=False,
        scope='All declared times, actor triangles/pairs, referenced-vertex containment, objects and planes queried. '
            'Each triangle pair uses all three vertices on each side, with one nonlinear minimum/maximum support gap on a fixed axis. '
            'Other witnesses retain their original forms. Local differences of nonsmooth support gaps can change proposal behavior; '
            'axes/extrema must be rebuilt/reevaluated and full decoded native/geometry checks remain authority. '
            'No subset, changed acceptance, self-collision, continuous-time, physical or animation-quality certification.')
    return CompactSurfaceRows(scene,rows,report)
