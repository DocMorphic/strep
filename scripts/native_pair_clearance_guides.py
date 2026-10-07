"""Explicit partner guides at multiple native times, sharing complete stencils.

These are proposal objectives. Original clocks, conditions, stored exports and
full scene geometry remain the acceptance authority.
"""
import copy
from dataclasses import dataclass
import numpy as np
from scipy import sparse
from native_scene_contacts import fields, scalar
from native_scene_norms import rows, linearize


@dataclass
class PairGuidesModel:
    native: object
    native_jacobian: object
    guide_residual: np.ndarray
    guide_jacobian: object
    points: np.ndarray
    gaps_m: np.ndarray
    continuous_origin_points: np.ndarray
    identity: dict


def linearize_pair_guides(problem, value, base_worlds, guides, *, step=.001,
                          maximum_elements=60_000_000,
                          maximum_point_elements=60_000_000, stencil_sink=None):
    """Retain every declared guide and original norm on the same full worlds.

    Caller must authenticate decoded worlds and the continuous problem. All
    descriptors and total resource budgets validate before any world query.
    Guide order, pair order and per-guide units are preserved explicitly.
    """
    if not isinstance(guides, list) or not 1 <= len(guides) <= 64:
        raise ValueError('One to 64 explicit pair guide descriptors required')
    guides = copy.deepcopy(guides); prepared = []; row_offsets = [0]; point_offsets = [0]
    for guide in guides:
        fields(guide, ('actor_a', 'vertices_a', 'actor_b', 'vertices_b', 'time_s',
                       'axis_world', 'clearance_m', 'scale_m'), 'pair clearance guide')
        actors = [guide['actor_a'], guide['actor_b']]
        if (any(not isinstance(n, str) or n not in problem.scene.actors for n in actors)
                or actors[0] == actors[1]):
            raise ValueError('Two distinct existing scene actors required')
        ids = []
        for name, key in zip(actors, ('vertices_a', 'vertices_b')):
            selection = guide[key]; count = len(problem.scene.actors[name]['skin'].vertex_references)
            if (not isinstance(selection, list) or not selection or len(selection) > 4096
                    or any(type(i) is not int or not 0 <= i < count for i in selection)
                    or len(set(selection)) != len(selection)):
                raise ValueError('Explicit unique in-range skin vertex IDs required')
            ids.append(np.array(selection, dtype=int))
        time = scalar(guide['time_s'], 0., float(problem.scene.duration), 'guide time')
        frames = np.flatnonzero(problem.times == time)
        if len(frames) != 1:
            raise ValueError('Every guide time must occur exactly once in the original native clock')
        axis = guide['axis_world']
        if (not isinstance(axis, list) or len(axis) != 3
                or any(type(v) not in (int, float) for v in axis)):
            raise ValueError('Explicit finite unit world axis required')
        axis = np.asarray(axis, float)
        if not np.isfinite(axis).all() or abs(np.linalg.norm(axis)-1.) > 1e-12:
            raise ValueError('Explicit finite unit world axis required')
        clearance = scalar(guide['clearance_m'], 0., .1, 'guide clearance')
        scale = scalar(guide['scale_m'], 1e-6, 1., 'guide scale')
        count = len(ids[0])*len(ids[1]); row_offsets.append(row_offsets[-1]+count)
        point_offsets.append(point_offsets[-1]+3*(len(ids[0])+len(ids[1])))
        prepared.append((actors, ids, int(frames[0]), axis, clearance, scale))
    if any(g == earlier for i,g in enumerate(guides) for earlier in guides[:i]):
        raise ValueError('Duplicate complete guide descriptors require an explicit weighting contract')
    if row_offsets[-1] > 4096:
        raise ValueError('Complete guide population exceeds the total 4096-row budget')
    x = problem.edits.controls(value).copy()
    if x.ndim != 1 or not 1 <= len(x) <= 96:
        raise ValueError('One to 96 complete native controls required')
    if (type(maximum_point_elements) is not int or not 1 <= maximum_point_elements <= 60_000_000
            or point_offsets[-1]*len(x) > maximum_point_elements):
        raise ValueError('Complete guide point/control population exceeds its declared budget')
    if (type(maximum_elements) is not int or not 1 <= maximum_elements <= 60_000_000
            or type(step) not in (int, float) or not np.isfinite(step) or not 1e-6 <= step <= .01):
        raise ValueError('Bounded complete native difference settings required')
    if stencil_sink is not None and not callable(stencil_sink):
        raise ValueError('Stencil sink must be callable')
    scales = np.concatenate([np.full(len(ids[0])*len(ids[1]), scale) for _,ids,_,_,_,scale in prepared])
    clearances = np.concatenate([np.full(len(ids[0])*len(ids[1]), clearance) for _,ids,_,_,clearance,_ in prepared])

    def observe(worlds):
        points = []; gaps = []
        for actors, ids, frame, axis, _, _ in prepared:
            pair = []
            for name, vertices in zip(actors, ids):
                actor = problem.scene.actors[name]; p,r = actor['placement']
                pair.append(actor['rig'].vertices(worlds[name][frame])[vertices]@r.T+p)
            points.append(np.concatenate(pair).ravel())
            gaps.append(((pair[1]@axis)[None,:]-(pair[0]@axis)[:,None]).ravel())
        points,gaps = np.concatenate(points),np.concatenate(gaps)
        if not np.isfinite(points).all() or not np.isfinite(gaps).all():
            raise ValueError('Nonfinite complete guide point or gap')
        return points,gaps

    wrapped = copy.copy(problem); original_worlds = problem.worlds; samples = {}
    origin_points,origin_gaps = observe(original_worlds(x,quantized=False))
    points,gaps = observe(base_worlds)
    def capture(other,quantized=True):
        worlds = original_worlds(other,quantized=quantized); changed = np.flatnonzero(other-x)
        if not quantized and len(changed) == 1:
            column = int(changed[0]); sign = 1 if other[column] > x[column] else -1
            if (column,sign) in samples:raise ValueError('Duplicate native stencil observation')
            pt,gap = observe(worlds); samples[column,sign] = gap
            if stencil_sink is not None:
                native = rows(wrapped,other,worlds)
                stencil_sink(column,sign,dict(controls=other.copy(),vectors=native.vectors.copy(),
                    caps=native.caps.copy(),scales=native.scales.copy(),points=pt.copy(),gaps_m=gap.copy()))
        return worlds
    wrapped.worlds = capture
    native,jacobian,identity = linearize(wrapped,x,step=step,maximum_elements=maximum_elements,
        difference_source='continuous',difference_scheme='central',base_worlds=base_worlds)
    columns = []
    for c,offsets in enumerate(identity['actual_difference_offsets']):
        if len(offsets) == 2:
            column = (samples[c,1]-samples[c,-1])/(offsets[0]-offsets[1])/scales
        else:
            h = offsets[0]; column = (samples[c,1 if h > 0 else -1]-origin_gaps)/h/scales
        columns.append(column)
    if len(samples) != identity['column_proxy_evaluations']:
        raise ValueError('Incomplete native stencil population')
    guide_jacobian = np.column_stack(columns)
    if not np.isfinite(guide_jacobian).all():raise ValueError('Nonfinite complete guide derivative')
    identity.update(schema='strep-native-pair-clearance-guides-model-v1',guides=guides,
        guide_scalar_rows=row_offsets[-1],guide_row_offsets=row_offsets,point_coordinate_offsets=point_offsets,
        guide_point_counts=[[len(ids[0]),len(ids[1])] for _,ids,_,_,_,_ in prepared],
        pair_order='descriptor order; actor-a vertex outer, actor-b vertex inner',
        point_derivative_elements=point_offsets[-1]*len(x),all_original_native_norm_rows_retained=True,
        all_original_caps_scales_unchanged=True,additional_world_stencils_for_guide=0,
        quality_approved=False,release_approved=False,
        scope='Every explicit actor/skin-pair/fixed-axis descriptor at existing native times shares complete native perturbation worlds. '
              'Each guide retains its own units and recorded row/point offsets; no original row, column or clock is pruned or extended. '
              'Caller-supplied decoded anchors require authentication; no exported motion, scene geometry, physics or human-quality approval.')
    return PairGuidesModel(native,jacobian,(gaps-clearances)/scales,sparse.csc_matrix(guide_jacobian),
                           points,gaps,origin_points,identity)
