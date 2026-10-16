"""Source-epoch surface derivatives at exact existing quaternion keys.

All canonical vertices are checked against the unchanged native decoder. This
is a local proposal model, not a collision or decoded-motion certificate.
"""
import numpy as np
from scipy import sparse
from native_affine_key_pose import AffineKeyPose


def linearize(surface, layouts, *, maximum_nonzeros=6000000):
    if (not isinstance(layouts, dict) or set(layouts) != set(surface.scene.actors)
            or type(maximum_nonzeros) is not int or maximum_nonzeros <= 0):
        raise ValueError('Complete explicit actor layouts and positive sparse budget required')
    offsets = {}; width = 0; clocks = {}; active = {}
    for name, layout in layouts.items():
        if not isinstance(layout, dict) or set(layout) != {'nodes', 'degrees', 'active_keys'}:
            raise ValueError('Explicit nodes, degrees and active_keys required')
        actor = surface.scene.actors[name]; nodes = layout['nodes']; keys = layout['active_keys']
        if (not isinstance(nodes, list) or not nodes or any(type(n) is not int for n in nodes)
                or not isinstance(keys, list) or not keys or any(type(k) is not int for k in keys)
                or keys != sorted(set(keys))):
            raise ValueError('Distinct ordered existing nodes and active integer keys required')
        channels = []
        for node in nodes:
            tracks = [c for c in actor['sampler'].channels if c[:2] == (node, 'rotation')]
            if len(tracks) != 1 or tracks[0][4] != 'LINEAR':
                raise ValueError('Existing LINEAR quaternion channels required')
            channels.append(tracks[0])
        clock = np.asarray(channels[0][2])
        if (any(not np.array_equal(clock, c[2]) for c in channels)
                or not np.isfinite(clock).all() or np.any(np.diff(clock) <= 0)
                or keys[0] <= 0 or keys[-1] >= len(clock)-1):
            raise ValueError('Common native clock and strictly interior active keys required')
        # Validate affine joint/cap rules even when no surface row uses an actor.
        AffineKeyPose(actor, float(clock[keys[0]]), nodes, layout['degrees'])
        offsets[name] = width; clocks[name] = clock
        active[name] = {float(clock[k]): i for i, k in enumerate(keys)}
        width += len(keys)*3*len(nodes)
    if width > 768:
        raise ValueError('Explicit 768-component proposal budget exceeded')
    vertices = {}; derivatives = {}; maximum_error = 0.
    for row in surface.rows:
        if row.get('plane_guidance') == 'minimum-envelope':
            raise ValueError('Frozen material rows required; minimum envelopes need separate derivatives')
        normal = np.asarray(row['normal_world'], float); time = row['time_s']
        if (normal.shape != (3,) or not np.isfinite(normal).all()
                or abs(np.linalg.norm(normal)-1) > 1e-10
                or type(time) not in (int, float) or not np.isfinite(time)
                or not np.isfinite(row['constant_m'])):
            raise ValueError('Finite exact native times, constants and unit normals required')
        for entry in (row['left'], row['right']):
            if entry is None: continue
            name = entry['actor']
            if name not in layouts or np.count_nonzero(clocks[name] == time) != 1:
                raise ValueError('Every material point must use an exact existing native key')
            ids = entry['vertices']; weights = np.asarray(entry['weights'], float)
            if (not isinstance(ids, list) or not ids or any(type(i) is not int for i in ids)
                    or min(ids) < 0 or max(ids) >= len(surface.scene.actors[name]['skin'].nodes)
                    or weights.shape != (len(ids),) or not np.isfinite(weights).all()
                    or np.any(weights < 0) or abs(weights.sum()-1) > 1e-10):
                raise ValueError('Complete convex canonical material points required')
            key = (name, time)
            if key in vertices: continue
            actor = surface.scene.actors[name]; layout = layouts[name]
            graph = AffineKeyPose(actor, time, layout['nodes'], layout['degrees'])
            _, posed, jac, _ = graph.evaluate(np.zeros(graph.size))
            actual = actor['rig'].vertices(actor['sampler'].sample(time))
            error = float(np.max(np.abs(posed-actual))); maximum_error = max(maximum_error, error)
            if error > 1e-12:
                raise ValueError('Affine canonical vertices disagree with unchanged native source')
            p, r = actor['placement']; vertices[key] = posed@r.T+p
            derivatives[key] = np.einsum('ij,vjc->vic', r, jac)
    gaps = surface.gaps(lambda name, time: vertices[name, time])
    rr = []; cc = []; vv = []
    for index, row in enumerate(surface.rows):
        for entry, sign in ((row['left'], 1.), (row['right'], -1.)):
            if entry is None: continue
            name = entry['actor']; time = row['time_s']
            if time not in active[name]: continue
            count = 3*len(layouts[name]['nodes'])
            local = sign*np.einsum('v,vic,i->c', entry['weights'],
                derivatives[name, time][entry['vertices']], row['normal_world'])
            used = np.flatnonzero(local); start = offsets[name]+active[name][time]*count
            if len(vv)+len(used) > maximum_nonzeros:
                raise ValueError('Complete surface Jacobian exceeds sparse budget; no subset returned')
            rr.extend([index]*len(used)); cc.extend(start+used); vv.extend(local[used])
    matrix = sparse.csr_matrix((vv, (rr, cc)), shape=(len(gaps), width))
    matrix.eliminate_zeros(); surface.scene.check_inputs()
    return gaps, matrix, dict(controls=width, rows=len(gaps), nonzero_entries=matrix.nnz,
        native_pose_vertex_maximum_error_m=maximum_error, actor_offsets=offsets,
        source_epoch='original zero controls', exact_native_keys_only=True,
        quality_approved=False, release_approved=False)
