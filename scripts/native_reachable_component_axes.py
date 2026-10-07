"""Alternative fixed-axis proposals ranked by represented box potential.

This is a Float64 heuristic, not a reachability or collision certificate.
Keep every originally clear group's axis and all original model rows/clocks.
Caller binds same-pose complete derivatives and checks actual stored motion.
"""
from dataclasses import dataclass
import copy
import numpy as np
from scipy import sparse
from native_component_trajectory_model import build as original_build, ComponentTrajectoryModel


@dataclass
class ReachableAxisProposal:
    trajectory: ComponentTrajectoryModel
    report: dict
    screens: list


def _axes(points, faces):
    tri = points[faces]
    normals = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    edges = sorted({tuple(sorted((int(a), int(b))))
                    for face in faces for a, b in zip(face, np.roll(face, -1))})
    edges = np.array(edges, int)
    vectors = points[edges[:, 1]]-points[edges[:, 0]]
    vectors /= np.linalg.norm(vectors, axis=1)[:, None]
    return normals, edges, vectors


def build(vertices, point_jacobians, local_faces, source_vertex_ids, times_s,
          *, required_times_s, lower_delta, upper_delta, clearance_m=1e-8,
          maximum_groups=4096, maximum_rows=400000, maximum_elements=60000000,
          maximum_candidate_axes=4096, maximum_screen_elements=8000000):
    """Choose alternative axes for colliding samples without dropping any row.

Enumerate every original face normal and edge cross product with both signs.
Rank the minimum over all pair rows of their independently maximized affine
gap estimates. The same delta need not attain those independent maxima; the
ranking ignores native constraints and is deliberately not a pass condition.
Keep clear samples on their original axes. Reject oversized screens whole.
    """
    lower_raw, upper_raw = np.asarray(lower_delta), np.asarray(upper_delta)
    if (lower_raw.dtype.kind not in 'fiu' or upper_raw.dtype.kind not in 'fiu'
            or lower_raw.ndim != 1 or not 1 <= len(lower_raw) <= 96
            or upper_raw.shape != lower_raw.shape
            or type(maximum_candidate_axes) is not int or not 1 <= maximum_candidate_axes <= 4096
            or type(maximum_screen_elements) is not int or not 1 <= maximum_screen_elements <= 8000000):
        raise ValueError('Explicit real delta box and bounded complete axis screens required')
    lower, upper = lower_raw.astype(float), upper_raw.astype(float)
    if (not np.isfinite(lower).all() or not np.isfinite(upper).all()
            or np.any(lower > 0) or np.any(upper < 0) or np.any(lower > upper)):
        raise ValueError('Finite ordered delta box containing the unchanged anchor required')
    base = original_build(vertices, point_jacobians, local_faces, source_vertex_ids, times_s,
        required_times_s=required_times_s, clearance_m=clearance_m,
        maximum_groups=maximum_groups, maximum_rows=maximum_rows, maximum_elements=maximum_elements)
    if base.report['controls'] != len(lower):
        raise ValueError('Every original derivative column must have a delta bound')
    names = list(vertices); a, b = names
    faces = {n: np.asarray(local_faces[n]) for n in names}
    edges = {n: len({tuple(sorted((int(u), int(v))))
                    for face in faces[n] for u, v in zip(face, np.roll(face, -1))}) for n in names}
    raw_count = len(faces[a])+len(faces[b])+edges[a]*edges[b]
    pairs = len(source_vertex_ids[a])*len(source_vertex_ids[b])
    if 2*raw_count > maximum_candidate_axes or pairs*2*raw_count*len(lower) > maximum_screen_elements:
        raise ValueError('Complete signed axis screen exceeds budget; no subset returned')
    gaps = base.gaps_m.copy(); jacobian = base.jacobian.toarray()
    groups = copy.deepcopy(base.groups); screens = []; changed = []
    for frame, group in enumerate(groups):
        ap, bp = [np.asarray(vertices[n], float)[frame] for n in names]
        aj, bj = [np.asarray(point_jacobians[n], float)[frame] for n in names]
        an, ae, av = _axes(ap, faces[a]); bn, be, bv = _axes(bp, faces[b])
        raw = np.concatenate([an, bn, np.cross(av[:, None], bv[None, :]).reshape(-1, 3)])
        lengths = np.linalg.norm(raw, axis=1); available = np.flatnonzero(lengths > 1e-12)
        unit = raw[available]/lengths[available, None]
        axes = np.stack([unit, -unit], axis=1).reshape(-1, 3)
        positions = (ap[:, None]-bp[None, :]).reshape(pairs, 3)
        derivatives = (aj[:, None]-bj[None, :]).reshape(pairs, 3, len(lower))
        coefficients = np.einsum('pcn,ac->pan', derivatives, axes)
        candidate_gaps = positions @ axes.T
        with np.errstate(over='ignore', invalid='ignore'):
            potential = candidate_gaps + np.sum(coefficients*np.where(coefficients > 0, upper, lower), axis=-1)
        if not np.isfinite(potential).all():
            raise ValueError('Finite complete Float64 axis ranking required; no partial proposal')
        scores = potential.min(axis=0)
        old = group['support_report']
        current = 2*int(np.flatnonzero(available == old['selected_raw_axis_index'])[0]) + (old['selected_sign'] < 0)
        choice = int(np.argmax(scores))
        if (group['starts_positive'] or not np.any((lower != 0) | (upper != 0))
                or scores[choice] <= scores[current]):
            choice = current
        if choice != current:
            changed.append(frame); first, last = group['first_row'], group['stop_row']
            axis = axes[choice]; moved = ((ap[:, None]-bp[None, :])@axis).ravel()
            # Use the original projection arithmetic and pair order for model columns.
            columns = np.array([axis@(aj[i]-bj[k]) for i in range(len(ap)) for k in range(len(bp))])
            gaps[first:last] = moved; jacobian[first:last] = columns
            smallest = float(moved.min()); margin = min(clearance_m, smallest) if smallest > 0 else clearance_m
            group.update(axis_world=axis.tolist(), starting_minimum_support_gap_m=smallest,
                         starts_positive=smallest > 0, clearance_m=margin)
            group['support_report'] = dict(schema='strep-reachable-component-axis-selection-v1',
                original_support=copy.deepcopy(old), selected_raw_axis_index=int(available[choice//2]),
                selected_sign=1 if choice % 2 == 0 else -1, axis_world=axis.tolist(),
                minimum_complete_pair_gap_m=smallest, estimated_box_potential_m=float(scores[choice]),
                certified_collision_predicate=False, nonlinear_reachability_proven=False)
        screens.append(dict(time_s=group['time_s'], complete_raw_axis_count=raw_count,
            skipped_raw_axis_indices=np.setdiff1d(np.arange(raw_count), available).tolist(),
            tested_signed_axes=len(axes), original_signed_axis_index=int(current), selected_signed_axis_index=choice,
            original_clear_axis_preserved=base.groups[frame]['starts_positive'],
            axes_world=axes.copy(), estimated_box_potential_m=scores.copy()))
    margins = np.concatenate([np.full(pairs, g['clearance_m']) for g in groups])
    report = copy.deepcopy(base.report)
    report['positive_sample_indices'] = [i for i, g in enumerate(groups) if g['starts_positive']]
    report['proposal_axis_policy'] = 'Independent-row Float64 box-potential ranking; original clear axes retained'
    trajectory = ComponentTrajectoryModel(gaps, sparse.csr_matrix(jacobian), margins,
                                         base.weights_s.copy(), groups, report)
    summary = dict(schema='strep-reachable-component-axes-v1', controls=len(lower),
        complete_samples=len(groups), complete_pair_rows=len(gaps), lower_delta=lower.tolist(), upper_delta=upper.tolist(),
        changed_sample_indices=changed, original_positive_sample_indices=base.report['positive_sample_indices'].copy(),
        every_original_clear_axis_and_margin_preserved=True, all_candidate_axes_and_pair_rows_retained=True,
        ranking_is_float64_estimate=True, independent_row_maxima_not_proven_jointly_attainable=True,
        native_constraints_checked=False, nonlinear_reachability_proven=False, collision_certified=False,
        quality_approved=False, release_approved=False,
        scope='Complete signed original-pose axis inventory and same-pose projected columns. '
              'Finite box-potential heuristic only; native constraints ignored. Original clear axes stay hard. '
              'Caller authenticates source memberships, clock and derivatives; actual exports and full scene remain decisive.')
    return ReachableAxisProposal(trajectory, summary, screens)
