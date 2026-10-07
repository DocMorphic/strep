"""Complete homogeneous rows for one parameter increment per native track.

Equal normalized control increments are proposal constraints, not a proof of
uniform world motion, preserved dynamics, contact, or stored-pose validity.
"""
import numpy as np
from native_scene_boundary_edit import BoundarySceneEdits
from native_rotation_storage_repair import StorageAdjustedEdits


def parameter_rows(edits, *, maximum_rows=96):
    base = edits.base if isinstance(edits, StorageAdjustedEdits) else edits
    if not isinstance(base, BoundarySceneEdits):
        raise ValueError('Original explicit native boundary editor required')
    size = base.size
    if type(size) is not int or not 1 <= size <= 96:
        raise ValueError('One to 96 complete native controls required')
    if type(maximum_rows) is not int or not 0 <= maximum_rows <= 96:
        raise ValueError('Explicit complete parameter-row budget required')
    groups, population = [], []
    for name, actor in base.actors.items():
        for track in actor['tracks']:
            ids = np.asarray(track['controls'])
            if (ids.ndim != 2 or ids.shape[1] != 3 or not len(ids) or ids.dtype.kind not in 'iu'
                    or np.any(ids < 0) or np.any(ids >= size) or track['path'] not in ('rotation', 'translation')):
                raise ValueError('Complete existing native track-control groups required')
            groups.append(dict(actor=name, node=track['node'], path=track['path'], controls=ids.tolist()))
            population.extend(ids.ravel().tolist())
    if sorted(population) != list(range(size)):
        raise ValueError('Every original control must occur exactly once; no subset or shared-index grouping')
    count = sum(3 * (len(g['controls']) - 1) for g in groups)
    if count > maximum_rows:
        raise ValueError('Complete uniform-increment population exceeds the declared row budget')
    rows = np.zeros((count, size))
    cursor = 0
    for group in groups:
        controls = group['controls']
        group['row_start'] = cursor
        for knot in controls[1:]:
            for first, other in zip(controls[0], knot):
                rows[cursor, first] = -1.
                rows[cursor, other] = 1.
                cursor += 1
        group['row_end'] = cursor
    assert cursor == count
    return rows, dict(schema='strep-native-uniform-control-increment-v1', controls=size, parameter_rows=count,
        groups=groups, all_original_controls_grouped_once=True,
        order='Original actor/track order, later control knot outer, component inner; compare to first knot.',
        quality_approved=False, release_approved=False,
        scope='One equal normalized increment across the control knots of every complete native track. '
              'Original native constraints and columns remain separate and unchanged. '
              'Protected/boundary basis weights, rotations, skinning and storage can produce nonuniform world effects. '
              'No rate, contact, geometry, physical or human-quality guarantee.')
