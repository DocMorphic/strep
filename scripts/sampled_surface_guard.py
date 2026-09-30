"""Fixed-baseline mesh regression checks at declared times, never certification."""
from copy import deepcopy
import hashlib
import numpy as np


def topology(faces, vertex_counts):
    if len(faces) != 2 or len(vertex_counts) != 2:
        raise ValueError('Two fixed mesh topologies required')
    result = []
    for f, count in zip(faces, vertex_counts):
        f = np.asarray(f)
        if (type(count) is not int or count <= 0 or f.ndim != 2 or f.shape[1:] != (3,)
                or not len(f) or not np.issubdtype(f.dtype, np.integer) or f.min() < 0 or f.max() >= count):
            raise ValueError('Valid indexed mesh required')
        result.append(dict(vertices=count, faces=len(f), sha256=hashlib.sha256(f.astype('<i8').tobytes()).hexdigest()))
    return result


def snapshot(meshes, observations):
    """Normalize full audit records; reject incomplete or inconsistent populations."""
    rows = []
    for observation in observations:
        stamp, surface, depths = observation['time_s'], observation['surface'], observation['depths']
        if not np.isfinite(stamp) or stamp < 0 or (rows and stamp <= rows[-1]['time_s']):
            raise ValueError('Finite strictly increasing sample times required')
        if [surface['left_faces'], surface['right_faces']] != [m['faces'] for m in meshes]:
            raise ValueError('Surface topology changed')
        pairs = {}; counts = {}
        for record in surface['records']:
            pair = (record['left_triangle'], record['right_triangle']); kind = record['kind']
            if (kind not in ['proper_crossing', 'boundary_or_near_contact', 'coplanar_or_near_parallel_overlap', 'degenerate']
                    or pair in pairs or any(type(p) is not int or not 0 <= p < m['faces'] for p,m in zip(pair,meshes))):
                raise ValueError('Unique classified triangle records required')
            pairs[pair] = kind; counts[kind] = counts.get(kind, 0)+1
        if any(surface['counts'].get(k, 0) != counts.get(k, 0) for k in set(counts)|set(surface['counts']) if k != 'disjoint'):
            raise ValueError('Surface counts and records disagree')
        if sum(surface['counts'].values()) != surface['candidate_pairs']:
            raise ValueError('Incomplete surface candidate population')
        if len(depths) != 2 or any(d['vertices_checked'] != m['vertices'] or not np.isfinite(d['max_depth_m']) or d['max_depth_m'] < 0 for d,m in zip(depths,meshes)):
            raise ValueError('Two complete finite vertex-depth queries required')
        degenerate = surface['degenerate_faces']
        if len(degenerate) != 2 or any(len(set(ids)) != len(ids) or any(type(i) is not int or not 0 <= i < m['faces'] for i in ids) for ids,m in zip(degenerate,meshes)):
            raise ValueError('Invalid degenerate face population')
        rows.append(dict(time_s=float(stamp), proper=[list(p) for p in sorted(pairs) if pairs[p]=='proper_crossing'],
            uncertain=[list(p) for p in sorted(pairs) if pairs[p]!='proper_crossing'], degenerate=deepcopy(degenerate),
            depths_m=[float(d['max_depth_m']) for d in depths], tolerance_m=surface['tolerance_m']))
    if not rows or any(r['tolerance_m'] != rows[0]['tolerance_m'] for r in rows) or not np.isfinite(rows[0]['tolerance_m']) or rows[0]['tolerance_m'] <= 0:
        raise ValueError('Nonempty fixed-tolerance surface population required')
    return dict(topology=deepcopy(meshes), samples=rows)


def compare(original, candidate, depth_slack_m=1e-8):
    """No new crossing pairs, uncertain pairs or degenerate faces; no deeper peak.

    This deliberately conservative gate can reject migrating intersections. It
    does not prove that retained intersections, other vertices or other times
    improve, and it never grants animation or collision-free approval.
    """
    if not np.isfinite(depth_slack_m) or depth_slack_m < 0:
        raise ValueError('Finite nonnegative depth roundoff allowance required')
    a, b = original['samples'], candidate['samples']
    if (original['topology'] != candidate['topology'] or len(a) != len(b) or not a
            or [(r['time_s'],r['tolerance_m']) for r in a] != [(r['time_s'],r['tolerance_m']) for r in b]):
        raise ValueError('Fixed topology, sample clock and tolerance required')
    records = []
    for left, right in zip(a,b):
        proper = set(map(tuple,left['proper'])); known = proper | set(map(tuple,left['uncertain']))
        new_proper = set(map(tuple,right['proper']))-proper
        new_uncertain = set(map(tuple,right['uncertain']))-known
        new_degenerate = [sorted(set(y)-set(x)) for x,y in zip(left['degenerate'],right['degenerate'])]
        delta = np.asarray(right['depths_m'])-left['depths_m']
        if delta.shape != (2,) or not np.isfinite(delta).all(): raise ValueError('Finite paired depths required')
        passed = not new_proper and not new_uncertain and not any(new_degenerate) and np.all(delta<=depth_slack_m)
        records.append(dict(time_s=left['time_s'], passed=bool(passed), new_proper_pairs=sorted(new_proper),
            new_uncertain_pairs=sorted(new_uncertain), new_degenerate_faces=new_degenerate,
            depth_increases_m=delta.tolist(), proper_counts=[len(left['proper']),len(right['proper'])]))
    return dict(passed=all(r['passed'] for r in records), samples=records, depth_slack_m=float(depth_slack_m),
        collision_free_certified=False, quality_approved=False, scope='Fixed-baseline sampled mesh regression guard only')


class SampledSurfaceGuard:
    """Query complete meshes only for feasible improving solver candidates."""
    def __init__(self, faces, vertex_counts, times, vertices_for, initial, *, observe=None):
        self.faces = [np.array(f,copy=True) for f in faces]
        self.meshes = topology(self.faces,vertex_counts)
        self.times = np.array(times,float,copy=True)
        if self.times.ndim != 1 or not len(self.times) or not np.isfinite(self.times).all() or self.times[0]<0 or np.any(np.diff(self.times)<=0):
            raise ValueError('Increasing finite nonnegative audit times required')
        self.vertices_for = vertices_for; self.observe = observe; self.cache = {}
        self.original = self._snapshot(initial)

    def _snapshot(self, point):
        from triangle_crossing import audit
        from convex_partner_surface import penetration
        point = np.asarray(point,float)
        if point.ndim!=1 or not len(point) or not np.isfinite(point).all(): raise ValueError('Finite control vector required')
        key = (point.shape,point.tobytes())
        if key in self.cache: return deepcopy(self.cache[key])
        vertices = self.vertices_for(point.copy())
        if len(vertices)!=len(self.times): raise ValueError('Complete audit pose population required')
        rows = []
        for stamp, pair in zip(self.times,vertices):
            if len(pair)!=2 or any(np.asarray(v).shape!=(m['vertices'],3) or not np.isfinite(v).all() for v,m in zip(pair,self.meshes)):
                raise ValueError('Complete finite posed meshes required')
            rows.append(dict(time_s=float(stamp),surface=audit(pair[0],self.faces[0],pair[1],self.faces[1]),
                depths=[penetration(pair[a],pair[b],self.faces[b]) for a,b in [(0,1),(1,0)]]))
            if self.observe: self.observe(dict(phase='surface_guard',completed=len(rows),total=len(self.times)))
        result = snapshot(self.meshes,rows); self.cache[key]=deepcopy(result)
        return result

    def __call__(self, point):
        return compare(self.original,self._snapshot(point))

    def fresh(self, vertices):
        """Independently decoded meshes bypass the control cache."""
        other = SampledSurfaceGuard(self.faces,[m['vertices'] for m in self.meshes],self.times,lambda _:vertices,[0.],observe=self.observe)
        return compare(self.original,other.original)
