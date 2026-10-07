"""Explicit moving material witnesses on original indexed actor triangles.

A frozen world direction guides vertex-to-material-point separation. It is
not a signed-distance function, changing nearest-face query or collision gate.
"""
import copy
from dataclasses import dataclass
import numpy as np
from scipy import sparse
from native_scene_contacts import fields, scalar
from native_scene_geometry import faces_for
from native_scene_norms import rows, linearize


class MaterialWitnessGuides:
    """Validate the complete explicit population before querying any worlds."""
    def __init__(self, problem, guides, *, maximum_point_elements=60_000_000,
                 allow_duplicate_descriptors=False):
        if not isinstance(guides, list) or not 1 <= len(guides) <= 4096:
            raise ValueError('One to 4096 explicit material witness descriptors required')
        if (type(problem.size) is not int or not 1 <= problem.size <= 96
                or type(maximum_point_elements) is not int or not 1 <= maximum_point_elements <= 60_000_000
                or 12*len(guides)*problem.size > maximum_point_elements):
            raise ValueError('Complete material-point/control population exceeds its declared budget')
        if type(allow_duplicate_descriptors) is not bool:
            raise ValueError('Explicit boolean repeated-objective-row policy required')
        self.problem = problem
        self.guides = copy.deepcopy(guides)
        self.prepared = []
        topology = {}
        for guide in self.guides:
            fields(guide, ('actor_a', 'vertex_a', 'actor_b', 'face_b', 'barycentric_b',
                           'time_s', 'axis_world', 'clearance_m', 'scale_m'), 'material witness')
            a, b = guide['actor_a'], guide['actor_b']
            if any(type(n) is not str or n not in problem.scene.actors for n in (a, b)) or a == b:
                raise ValueError('Two distinct existing material-witness actors required')
            vertex = guide['vertex_a']
            if type(vertex) is not int or not 0 <= vertex < len(problem.scene.actors[a]['skin'].vertex_references):
                raise ValueError('Explicit original source skin vertex required')
            if b not in topology:
                topology[b] = faces_for(problem.scene.actors[b]['rig'])[0]
            face = guide['face_b']
            if type(face) is not int or not 0 <= face < len(topology[b]):
                raise ValueError('Explicit original target triangle index required')
            ids = topology[b][face].copy()
            if len(set(ids.tolist())) != 3:
                raise ValueError('Three distinct original target triangle vertices required')
            bary = guide['barycentric_b']
            if (not isinstance(bary, list) or len(bary) != 3
                    or any(type(v) not in (int, float) for v in bary)):
                raise ValueError('Explicit finite convex triangle barycentric coordinates required')
            bary = np.array(bary, float)
            if not np.isfinite(bary).all() or np.any(bary < 0) or np.any(bary > 1) or abs(bary.sum()-1.) > 1e-12:
                raise ValueError('Convex barycentric coordinates must sum to one; no clipping or renormalization')
            time = scalar(guide['time_s'], 0., float(problem.scene.duration), 'material witness time')
            frames = np.flatnonzero(problem.times == time)
            if len(frames) != 1:
                raise ValueError('Every witness time must occur exactly once in the original native clock')
            axis = guide['axis_world']
            if not isinstance(axis, list) or len(axis) != 3 or any(type(v) not in (int, float) for v in axis):
                raise ValueError('Explicit finite unit material-witness direction required')
            axis = np.array(axis, float)
            if not np.isfinite(axis).all() or abs(np.linalg.norm(axis)-1.) > 1e-12:
                raise ValueError('Explicit finite unit material-witness direction required')
            clearance = scalar(guide['clearance_m'], 0., .1, 'material clearance')
            scale = scalar(guide['scale_m'], 1e-6, 1., 'material scale')
            self.prepared.append((a, vertex, b, ids, bary, int(frames[0]), axis, clearance, scale))
        if not allow_duplicate_descriptors and any(g == earlier for i, g in enumerate(self.guides) for earlier in self.guides[:i]):
            raise ValueError('Duplicate complete material descriptors require an explicit weighting contract')
        self.scales = np.array([v[-1] for v in self.prepared])
        self.clearances = np.array([v[-2] for v in self.prepared])

    def observe(self, worlds):
        """Original deformed source vertex plus all three moving target corners."""
        vertices = {}
        def get(name, frame):
            key = name, frame
            if key not in vertices:
                actor = self.problem.scene.actors[name]
                p, r = actor['placement']
                vertices[key] = actor['rig'].vertices(worlds[name][frame]) @ r.T + p
            return vertices[key]
        points, gaps = [], []
        for a, vertex, b, ids, bary, frame, axis, _, _ in self.prepared:
            source, triangle = get(a, frame)[vertex], get(b, frame)[ids]
            target = bary @ triangle
            points.append(np.concatenate([source[None], triangle]).ravel())
            gaps.append(float((source-target) @ axis))
        points, gaps = np.concatenate(points), np.array(gaps)
        if not np.isfinite(points).all() or not np.isfinite(gaps).all():
            raise ValueError('Nonfinite complete material-witness points or gaps')
        return points, gaps


@dataclass
class MaterialWitnessModel:
    native: object
    native_jacobian: object
    guide_residual: np.ndarray
    guide_jacobian: object
    points: np.ndarray
    gaps_m: np.ndarray
    continuous_origin_points: np.ndarray
    identity: dict


def linearize_material_guides(problem, value, base_worlds, guides, *, step=.001,
                              maximum_elements=60_000_000, maximum_point_elements=60_000_000,
                              stencil_sink=None, allow_duplicate_descriptors=False):
    """Share every original native stencil with every declared material guide.

    Caller authenticates the decoded starting worlds and continuous problem.
    Face IDs, barycentric weights and world directions remain fixed in this
    local proposal model. Actual decoded scene geometry remains authoritative.
    """
    prepared = MaterialWitnessGuides(problem, guides, maximum_point_elements=maximum_point_elements,
                                    allow_duplicate_descriptors=allow_duplicate_descriptors)
    x = problem.edits.controls(value).copy()
    if x.ndim != 1 or len(x) != problem.size:
        raise ValueError('Complete existing native controls required')
    if (type(maximum_elements) is not int or not 1 <= maximum_elements <= 60_000_000
            or type(step) not in (int, float) or not np.isfinite(step) or not 1e-6 <= step <= .01):
        raise ValueError('Bounded complete native difference settings required')
    if stencil_sink is not None and not callable(stencil_sink):
        raise ValueError('Material stencil sink must be callable')
    wrapped, original_worlds, samples = copy.copy(problem), problem.worlds, {}
    origin_points, origin_gaps = prepared.observe(original_worlds(x, quantized=False))
    points, gaps = prepared.observe(base_worlds)
    def capture(other, quantized=True):
        worlds = original_worlds(other, quantized=quantized)
        changed = np.flatnonzero(other-x)
        if not quantized and len(changed) == 1:
            c = int(changed[0]); sign = 1 if other[c] > x[c] else -1
            if (c, sign) in samples:
                raise ValueError('Duplicate complete material stencil observation')
            pt, gap = prepared.observe(worlds)
            samples[c, sign] = gap
            if stencil_sink is not None:
                native = rows(wrapped, other, worlds)
                stencil_sink(c, sign, dict(controls=other.copy(), vectors=native.vectors.copy(),
                    caps=native.caps.copy(), scales=native.scales.copy(), points=pt.copy(), gaps_m=gap.copy()))
        return worlds
    wrapped.worlds = capture
    native, jacobian, identity = linearize(wrapped, x, step=step, maximum_elements=maximum_elements,
        difference_source='continuous', difference_scheme='central', base_worlds=base_worlds)
    columns = []
    for c, offsets in enumerate(identity['actual_difference_offsets']):
        if len(offsets) == 2:
            column = (samples[c, 1]-samples[c, -1])/(offsets[0]-offsets[1])/prepared.scales
        else:
            h = offsets[0]
            column = (samples[c, 1 if h > 0 else -1]-origin_gaps)/h/prepared.scales
        columns.append(column)
    if len(samples) != identity['column_proxy_evaluations']:
        raise ValueError('Incomplete native/material stencil population')
    guide_jacobian = np.column_stack(columns)
    if not np.isfinite(guide_jacobian).all():
        raise ValueError('Nonfinite complete material derivative')
    identity.update(schema='strep-native-material-witness-model-v1', guides=prepared.guides,
        duplicate_policy='explicit repeated objective rows' if allow_duplicate_descriptors else 'reject',
        guide_scalar_rows=len(guides), point_coordinate_offsets=list(range(0, 12*len(guides)+1, 12)),
        target_triangle_vertices=[v[3].tolist() for v in prepared.prepared],
        point_order='Descriptor order: source vertex, then the three original ordered target triangle vertices.',
        gap_convention='(source vertex - barycentric target material point) dot fixed world direction',
        point_derivative_elements=12*len(guides)*len(x), all_original_native_norm_rows_retained=True,
        all_original_caps_scales_unchanged=True, additional_world_stencils_for_guide=0,
        quality_approved=False, release_approved=False,
        scope='Explicit original actor vertex-to-triangle material witnesses at existing native times. '
              'All complete original native perturbations, rows, columns, caps, scales and clocks are retained. '
              'Fixed barycentric points deform with the target; directions and face identities are local proposal choices. '
              'No nearest-face update, signed-distance equivalence, surface intersection, exported motion, '
              'scene geometry, physics, engine or human-quality approval.')
    return MaterialWitnessModel(native, jacobian, (gaps-prepared.clearances)/prepared.scales,
        sparse.csc_matrix(guide_jacobian), points, gaps, origin_points, identity)
