"""Isolate one skin joint's contribution without authoring or approving motion.

The probe moves an explicitly selected ancestor with the pelvis while holding
every other joint's world transform fixed. Local child compensation makes this
an isolation experiment, not ordinary hierarchical root motion or retargeting.
"""
import numpy as np


def diagnose(rig, reader, root, anchor, times):
    count = len(rig.parents)
    if (type(root) is not int or type(anchor) is not int or root == anchor
            or not 0 <= root < count or not 0 <= anchor < count or root not in rig.joints):
        raise ValueError('Distinct skin root and descendant anchor required')
    parent = rig.parents[anchor]
    while parent >= 0 and parent != root:
        parent = rig.parents[parent]
    if parent != root:
        raise ValueError('Selected root must be an ancestor of the anchor')
    if any(p['node'] == root for p in rig.primitives):
        raise ValueError('Root mesh nodes are outside this skin-only diagnostic')
    times = np.asarray(times, dtype=float)
    if (times.ndim != 1 or len(times) < 2 or not np.isfinite(times).all()
            or times[0] != 0 or times[-1] != reader.duration or np.any(np.diff(times) <= 0)):
        raise ValueError('Increasing finite clock including both clip endpoints required')
    slot = rig.joints.index(root)
    responses, weights = [], []
    for primitive in rig.primitives:
        points = np.c_[primitive['positions'], np.ones(len(primitive['positions']))]
        weight = (np.zeros(len(points)) if primitive['joints'] is None else
                  np.sum(np.where(primitive['joints'] == slot, primitive['weights'], 0), axis=1))
        # Retain raw weights and homogeneous inverse-bind coordinates. No
        # normalization or near-zero cutoff may change the unaffected set.
        weights.append(weight)
        responses.append(weight[:, None] * (rig.inverse[slot] @ points.T).T)
    weights = np.concatenate(weights)
    response = np.concatenate(responses)
    unaffected = np.flatnonzero(weights == 0)
    inverse_anchor = np.linalg.inv(rig.reference[anchor])
    rows = []
    first_root = None
    for time in times:
        world = reader.sample(float(time))
        original = rig.vertices(world)
        probe = world.copy()
        probe[root] = world[anchor] @ inverse_anchor @ rig.reference[root]
        moved = rig.vertices(probe)
        expected_delta = (response @ (probe[root] - world[root]).T)[:, :3]
        delta_error = float(np.max(np.abs(moved - original - expected_delta)))
        if delta_error > 1e-10:
            raise ValueError('Independent skin delta identity failed')
        if len(unaffected) and not np.array_equal(moved[unaffected], original[unaffected]):
            raise ValueError('Zero-weight vertices changed')
        # Reconstruct the probe through local transforms to check that fixed
        # descendant worlds are realizable by compensating immediate children.
        local = [matrix.copy() for matrix in probe]
        for node, parent in enumerate(rig.parents):
            if parent >= 0:
                local[node] = np.linalg.solve(probe[parent], probe[node])
        rebuilt = {}
        def visit(node):
            if node not in rebuilt:
                parent = rig.parents[node]
                rebuilt[node] = local[node] if parent < 0 else visit(parent) @ local[node]
            return rebuilt[node]
        reconstruction_error = float(np.max(np.abs(np.array([visit(n) for n in range(count)]) - probe)))
        if reconstruction_error > 1e-10:
            raise ValueError('Compensated hierarchy reconstruction failed')
        if first_root is None:
            first_root = world[root].copy()
        worst = int(np.argmin(original[:, 1]))
        fixed_worst = int(unaffected[np.argmin(original[unaffected, 1])]) if len(unaffected) else None
        rows.append(dict(time_s=float(time), original_floor_depth_m=max(0., -float(original[:, 1].min())),
            probe_floor_depth_m=max(0., -float(moved[:, 1].min())), worst_original_vertex=worst,
            worst_original_root_weight=float(weights[worst]),
            unaffected_floor_lower_bound_m=max(0., -float(original[fixed_worst, 1])) if fixed_worst is not None else 0.,
            unaffected_witness_vertex=fixed_worst,
            maximum_vertex_change_m=float(np.linalg.norm(moved - original, axis=1).max()),
            independent_delta_error_m=delta_error, hierarchy_reconstruction_error=reconstruction_error,
            original_root_translation_from_start_m=float(np.linalg.norm(world[root, :3, 3] - first_root[:3, 3])),
            original_root_rotation_element_change=float(np.max(np.abs(world[root, :3, :3] - first_root[:3, :3])))))
    peak = lambda key: max(row[key] for row in rows)
    return dict(schema='strep-auxiliary-root-diagnostic-v1', root_node=root, anchor_node=anchor,
        samples=len(rows), vertices=len(weights), affected_vertices=int(np.count_nonzero(weights)),
        unaffected_vertices=len(unaffected), maximum_root_weight=float(weights.max()), rows=rows,
        original_floor_depth_max_m=peak('original_floor_depth_m'),
        probe_floor_depth_max_m=peak('probe_floor_depth_m'),
        unaffected_floor_lower_bound_max_m=peak('unaffected_floor_lower_bound_m'),
        maximum_vertex_change_m=peak('maximum_vertex_change_m'),
        maximum_delta_error_m=peak('independent_delta_error_m'),
        maximum_hierarchy_reconstruction_error=peak('hierarchy_reconstruction_error'),
        original_root_translation_from_start_max_m=peak('original_root_translation_from_start_m'),
        original_root_rotation_element_change_max=peak('original_root_rotation_element_change'),
        scope='Sampled isolation probe only. Every other node world transform is held fixed, including mapped joints. '
              'Unaffected vertices bound any edit restricted to this root skin contribution, not general retargeting. '
              'No exported candidate, source-body surface, continuous collision, contacts, engine or human assessment.',
        quality_approved=False, release_approved=False)
