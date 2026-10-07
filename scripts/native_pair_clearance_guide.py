"""Fresh fixed-axis partner guidance alongside the complete native norm model.

Selected skin vertices define proposal guidance only. No original constraint,
clock, storage choice, export or geometry acceptance is replaced here.
"""
import copy
from dataclasses import dataclass
import numpy as np
from scipy import sparse
from native_scene_contacts import fields, scalar
from native_scene_norms import rows, linearize


@dataclass
class PairGuideModel:
    native: object
    native_jacobian: object
    guide_residual: np.ndarray
    guide_jacobian: object
    points: np.ndarray
    gaps_m: np.ndarray
    continuous_origin_points: np.ndarray
    identity: dict


def linearize_pair_guide(problem, value, base_worlds, guide, *, step=.001,
                         maximum_elements=60_000_000, stencil_sink=None):
    """Use the same full world stencils for native norms and every selected pair.

    Caller supplies freshly decoded base worlds and a suitable continuous
    problem, normally produced by stored-pair centering. This function does
    not authenticate those inputs or prove that an exported asset passes.
    A sink receives independent copies of each complete stencil observation.
    """
    guide = copy.deepcopy(guide)
    fields(guide, ('actor_a', 'vertices_a', 'actor_b', 'vertices_b', 'time_s',
                   'axis_world', 'clearance_m', 'scale_m'), 'pair clearance guide')
    actors = [guide['actor_a'], guide['actor_b']]
    if (any(not isinstance(n, str) or n not in problem.scene.actors for n in actors)
            or actors[0] == actors[1]):
        raise ValueError('Two distinct existing scene actors required')
    ids = []
    for name, key in zip(actors, ('vertices_a', 'vertices_b')):
        selection = guide[key]
        count = len(problem.scene.actors[name]['skin'].vertex_references)
        if (not isinstance(selection, list) or not selection or len(selection) > 4096
                or any(type(i) is not int or not 0 <= i < count for i in selection)
                or len(set(selection)) != len(selection)):
            raise ValueError('Explicit unique in-range skin vertex IDs required')
        ids.append(np.array(selection, dtype=int))
    if len(ids[0])*len(ids[1]) > 4096:
        raise ValueError('Pair guide exceeds the complete 4096-row guide budget')
    time_s = scalar(guide['time_s'], 0., float(problem.scene.duration), 'guide time')
    frames = np.flatnonzero(problem.times == time_s)
    if len(frames) != 1:
        raise ValueError('Guide time must already occur exactly once in the complete native clock')
    axis = guide['axis_world']
    if (not isinstance(axis, list) or len(axis) != 3
            or any(type(v) not in (int, float) for v in axis)):
        raise ValueError('Explicit finite unit world axis required')
    axis = np.asarray(axis, float)
    if not np.isfinite(axis).all() or abs(np.linalg.norm(axis)-1.) > 1e-12:
        raise ValueError('Explicit finite unit world axis required')
    clearance = scalar(guide['clearance_m'], 0., .1, 'guide clearance')
    scale = scalar(guide['scale_m'], 1e-6, 1., 'guide scale')
    x = problem.edits.controls(value).copy()
    if x.ndim != 1 or not 1 <= len(x) <= 96:
        raise ValueError('One to 96 complete native controls required')
    if stencil_sink is not None and not callable(stencil_sink):
        raise ValueError('Stencil sink must be callable')
    frame = int(frames[0]); counts = (len(ids[0]), len(ids[1]))

    def observe(worlds):
        points = []
        for name, vertices in zip(actors, ids):
            actor = problem.scene.actors[name]; p, r = actor['placement']
            points.append(actor['rig'].vertices(worlds[name][frame])[vertices] @ r.T+p)
        left, right = points[0] @ axis, points[1] @ axis
        gaps = (right[None, :]-left[:, None]).ravel()
        points = np.concatenate(points).ravel()
        if not np.isfinite(points).all() or not np.isfinite(gaps).all():
            raise ValueError('Nonfinite guide point or gap')
        return points, gaps

    wrapped = copy.copy(problem); original_worlds = problem.worlds; samples = {}
    origin_points, origin_gaps = observe(original_worlds(x, quantized=False))
    points, gaps = observe(base_worlds)

    def capture(other, quantized=True):
        worlds = original_worlds(other, quantized=quantized)
        changed = np.flatnonzero(other-x)
        if not quantized and len(changed) == 1:
            column = int(changed[0]); sign = 1 if other[column] > x[column] else -1
            if (column, sign) in samples:
                raise ValueError('Duplicate native stencil observation')
            pt, gap = observe(worlds); samples[column, sign] = gap
            if stencil_sink is not None:
                native = rows(wrapped, other, worlds)
                stencil_sink(column, sign, dict(controls=other.copy(),
                    vectors=native.vectors.copy(), caps=native.caps.copy(),
                    scales=native.scales.copy(), points=pt.copy(), gaps_m=gap.copy()))
        return worlds

    wrapped.worlds = capture
    native, jacobian, identity = linearize(wrapped, x, step=step,
        maximum_elements=maximum_elements, difference_source='continuous',
        difference_scheme='central', base_worlds=base_worlds)
    columns = []
    for c, offsets in enumerate(identity['actual_difference_offsets']):
        if len(offsets) == 2:
            columns.append((samples[c, 1]-samples[c, -1])/(offsets[0]-offsets[1])/scale)
        else:
            h = offsets[0]
            columns.append((samples[c, 1 if h > 0 else -1]-origin_gaps)/h/scale)
    if len(samples) != identity['column_proxy_evaluations']:
        raise ValueError('Incomplete native stencil population')
    guide_jacobian = np.column_stack(columns)
    if not np.isfinite(guide_jacobian).all():
        raise ValueError('Nonfinite guide derivative')
    identity.update(schema='strep-native-pair-clearance-guide-model-v1', guide=guide,
        guide_scalar_rows=counts[0]*counts[1], guide_point_counts=list(counts),
        pair_order='actor-a vertex outer, actor-b vertex inner',
        all_original_native_norm_rows_retained=True, all_original_caps_scales_unchanged=True,
        additional_world_stencils_for_guide=0, quality_approved=False, release_approved=False,
        scope='Fixed-axis selected partner skin-pair proposal guidance at one existing native time. '
              'All complete native controls and norm stencils are retained; central or recorded one-sided differences share the same worlds. '
              'No decoded asset, contact, geometry, optimality or quality acceptance.')
    return PairGuideModel(native, jacobian, (gaps-clearance)/scale,
        sparse.csc_matrix(guide_jacobian), points, gaps, origin_points, identity)
