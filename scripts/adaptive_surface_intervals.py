"""Bounded interval subdivision with observed crossings and sampled containment.

Surface bounds do not establish absence of enclosed volume or self-collision.
No budget exhaustion, touching surface, or ambiguous case is labeled clear.
"""
from collections import Counter
import numpy as np
import trimesh
from triangle_crossing import audit as crossings
from convex_partner_surface import penetration
from swept_surface_boxes import audit as swept


def inspect_pose(left, right, left_faces, right_faces, tolerance_m=1e-8):
    meshes = [trimesh.Trimesh(vertices=v, faces=f, process=False)
              for v, f in [(left, left_faces), (right, right_faces)]]
    if not all(mesh.is_watertight and mesh.is_winding_consistent for mesh in meshes):
        raise ValueError('Closed consistently wound meshes required for containment')
    surface = crossings(left, left_faces, right, right_faces, tolerance_m)
    proper = [row for row in surface['records'] if row['kind'] == 'proper_crossing']
    base = dict(crossing_counts=surface['counts'], degenerate_faces=surface['degenerate_faces'])
    if proper:
        return dict(**base, outcome='crossing_observed', crossing_witness=proper[0], containment=None)
    contained = [penetration(left, right, right_faces, tolerance_m),
                 penetration(right, left, left_faces, tolerance_m)]
    if any(row['max_depth_m'] > tolerance_m for row in contained):
        return dict(**base, outcome='interior_vertex_observed', containment=contained)
    ambiguous = bool(surface['records'] or any(surface['degenerate_faces']))
    return dict(**base, outcome='ambiguous_contact' if ambiguous else 'no_intersection_observed', containment=contained)


def audit(left, right, start, end, *, max_depth=6, max_intervals=127, tolerance_m=1e-8, observe=None):
    """Actors supply faces, interval(a,b) bounds, and exact vertices(t)."""
    if not np.isfinite([start, end]).all() or not 0 <= start < end:
        raise ValueError('Finite increasing nonnegative interval required')
    if type(max_depth) is not int or not 0 <= max_depth <= 20:
        raise ValueError('Depth must be an integer from zero to twenty')
    if type(max_intervals) is not int or not 1 <= max_intervals <= 4095:
        raise ValueError('One to 4095 interval evaluations required')
    if not np.isfinite(tolerance_m) or tolerance_m <= 0:
        raise ValueError('Positive finite geometric tolerance required')
    pending = [(float(start), float(end), 0)]; leaves = []; nodes = []; poses = {}
    def pose(stamp, points=None):
        if stamp not in poses:
            if points is None: points = [actor['vertices'](stamp) for actor in [left, right]]
            value = inspect_pose(points[0], points[1],
                                 left['faces'], right['faces'], tolerance_m)
            poses[stamp] = dict(time_s=stamp, **value)
        return poses[stamp]
    while pending:
        a, b, depth = pending.pop(); center = (a+b)/2
        record = dict(start_s=a, end_s=b, depth=depth)
        if len(nodes) >= max_intervals or center == a or center == b:
            leaves.append(dict(**record, outcome='unresolved', reason='interval_budget' if len(nodes) >= max_intervals else 'time_resolution'))
            continue
        bounds = [actor['interval'](a, b) for actor in [left, right]]
        centers = [actor['vertices'](center) for actor in [left, right]]
        for bound, points in zip(bounds, centers):
            if bound['start_s'] != a or bound['end_s'] != b or bound['center_s'] != center:
                raise ValueError('Interval provider returned a different clock')
            if not np.array_equal(bound['center_vertices'], points):
                raise ValueError('Bound center differs from actual placed mesh')
        broad = swept(bounds[0], left['faces'], bounds[1], right['faces'], tolerance_m)
        record['candidate_pairs'] = broad['candidate_pairs']
        sampled = []
        for stamp in ([center] if broad['candidate_pairs'] == 0 else [center, a, b]):
            value = pose(stamp, centers if stamp == center else None); sampled.append(stamp)
            if value['outcome'] in ['crossing_observed', 'interior_vertex_observed']: break
        evidence = [poses[t] for t in sampled]
        observed = next((row for row in evidence if row['outcome'] in ['crossing_observed', 'interior_vertex_observed']), None)
        record['sampled_times_s'] = sampled
        if observed is not None:
            leaf = dict(**record, outcome=observed['outcome'], witness_time_s=observed['time_s'])
        elif broad['candidate_pairs'] == 0 and all(row['outcome'] == 'no_intersection_observed' for row in evidence):
            leaf = dict(**record, outcome='surface_separation_bound', reason='zero_swept_pairs_with_sampled_containment_check')
        elif depth >= max_depth:
            leaf = dict(**record, outcome='unresolved', reason='depth_budget')
        else:
            leaf = None
            pending.extend([(center, b, depth+1), (a, center, depth+1)])
        node = dict(**record, outcome='subdivided' if leaf is None else leaf['outcome'])
        nodes.append(node)
        if leaf is not None: leaves.append(leaf)
        if observe: observe(node)
    leaves.sort(key=lambda row: row['start_s'])
    # Every branch has an explicit terminal outcome, including unvisited budget
    # leaves. An intersection observation does not claim the whole leaf collides.
    if leaves[0]['start_s'] != start or leaves[-1]['end_s'] != end or any(
            a['end_s'] != b['start_s'] for a, b in zip(leaves[:-1], leaves[1:])):
        raise ValueError('Incomplete interval partition')
    counts = dict(Counter(row['outcome'] for row in leaves))
    observed = any(counts.get(kind, 0) for kind in ['crossing_observed', 'interior_vertex_observed'])
    return dict(start_s=float(start), end_s=float(end), evaluated_intervals=len(nodes),
        max_depth=max_depth, max_intervals=max_intervals, tolerance_m=tolerance_m,
        leaf_counts=counts, leaves=leaves, nodes=nodes, poses=[poses[t] for t in sorted(poses)],
        outcome='intersection_observed' if observed else ('unresolved' if counts.get('unresolved') else 'surface_separation_bound'),
        entire_partition_has_surface_bounds=all(row['outcome'] == 'surface_separation_bound' for row in leaves),
        collision_free_certified=False, quality_approved=False,
        scope='Observed intersections are discrete witnesses, not penetration severity or a quality decision. Separation leaves have swept surface bounds and a sampled containment check; unresolved leaves remain explicit. No exact-arithmetic, self-collision, force, anatomy or continuous volumetric clearance certification.')
