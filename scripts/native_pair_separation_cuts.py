"""Complete source-axis cuts for explicitly declared canonical triangle pairs.

New intersections can involve pairs absent from the initial crossing witnesses.
These local search bounds retain their source epoch, including source overlaps;
neither their affine satisfaction nor their input pair list certifies a mesh.
"""
import numpy as np
from native_scene_geometry import faces_for
from native_partner_surface_rows import SurfaceRows, separation_axis


def build(scene, pairs, *, clearance=.0001, maximum_rows=100000):
    if (not isinstance(pairs, list) or not pairs
            or type(maximum_rows) is not int or not 1 <= maximum_rows <= 100000
            or type(clearance) not in (int, float) or not np.isfinite(clearance)
            or not 0 <= clearance <= .005):
        raise ValueError('Explicit triangle pairs, 0-5mm clearance and bounded row budget required')
    if 9*len(pairs) > maximum_rows:
        raise ValueError('Complete nine-row triangle cuts exceed resource budget; no subset returned')
    faces = {name: faces_for(a['rig'])[0] for name, a in scene.actors.items()}
    seen = set(); cache = {}; rows = []; lower = []; gaps = []
    def vertices(name, time):
        key = (name, time)
        if key not in cache:
            actor = scene.actors[name]; p, r = actor['placement']
            value = actor['rig'].vertices(actor['sampler'].sample(time))@r.T+p
            if value.shape != (len(actor['skin'].nodes), 3) or not np.isfinite(value).all():
                raise ValueError('Complete finite original canonical vertices required')
            cache[key] = value
        return cache[key]
    for pair in pairs:
        if not isinstance(pair, dict) or set(pair) != {'time_s', 'left_actor', 'right_actor', 'left_triangle', 'right_triangle'}:
            raise ValueError('Exact explicit triangle-pair identity required')
        time = pair['time_s']; a = pair['left_actor']; b = pair['right_actor']
        i = pair['left_triangle']; j = pair['right_triangle']
        if (type(time) not in (int, float) or not np.isfinite(time) or not 0 <= time <= scene.duration
                or type(a) is not str or type(b) is not str or a not in faces or b not in faces or a == b
                or type(i) is not int or type(j) is not int or not 0 <= i < len(faces[a]) or not 0 <= j < len(faces[b])):
            raise ValueError('Existing distinct actors, native triangle IDs and finite scene time required')
        key = (time, *sorted(((a, i), (b, j))))
        if key in seen: raise ValueError('Duplicate canonical triangle-pair identity')
        seen.add(key); left = faces[a][i]; right = faces[b][j]
        normal, gap = separation_axis(vertices(a, time)[left], vertices(b, time)[right])
        # A source overlap remains explicitly unresolved. It is never relabelled
        # as a positive separation target merely because it was absent in a
        # previous tolerance-based crossing report.
        target = min(float(clearance), gap); gaps.append(gap)
        for av in left:
            for bv in right:
                rows.append(dict(kind='triangle-separation', time_s=float(time), normal_world=normal.tolist(),
                    constant_m=0., clearance_m=0.,
                    left=dict(actor=a, vertices=[int(av)], weights=[1.]),
                    right=dict(actor=b, vertices=[int(bv)], weights=[1.]),
                    left_triangle=i, right_triangle=j, source_axis_gap_m=gap, search_lower_bound_m=target))
                lower.append(target)
    scene.check_inputs()
    report = dict(pairs=len(pairs), rows=len(rows), rows_per_pair=9,
        positive_source_axis_pairs=sum(g > 0 for g in gaps), unresolved_source_axis_pairs=sum(g <= 0 for g in gaps),
        minimum_source_axis_gap_m=min(gaps), source_axis_gaps_m=gaps,
        source_vertices={name: len(actor['skin'].nodes) for name, actor in scene.actors.items()},
        clearance_m=float(clearance), maximum_rows=maximum_rows,
        quality_approved=False, release_approved=False,
        scope='All nine fixed source-axis vertex inequalities for every explicit pair. '
        'Lower bound is min(search clearance, original axis gap), retaining negative source gaps. '
        'No discovery completeness, nonlinear pose, mesh, continuous-time, engine or human certificate.')
    return SurfaceRows(scene, rows, report), np.asarray(lower)
