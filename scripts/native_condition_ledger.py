"""Locate native scalar/norm rows without evaluating or approving motion.

The complete population follows SceneProblem.constraints/native_scene_norms.
It includes all edited actors, native keys, skin joints and contact clocks.
Saved affine and decoded observations remain separate diagnostic evidence.
"""
from bisect import bisect_right
import copy
import numpy as np
from engine_contact_sampling import frame_populations


RATE_METRICS = (
    ('joint_linear_velocity', 1, 'm/s'),
    ('joint_linear_acceleration', 2, 'm/s^2'),
    ('joint_angular_velocity', 1, 'rad/s'),
    ('joint_angular_acceleration', 2, 'rad/s^2'),
)


class NativeConditionLedger:
    """Compact, complete row identities from validated scene/edit declarations.

    No world evaluation, rate cap recalibration, derivative or skin query occurs.
    Actor/track/joint/point order is preserved, including unavailable speed rows.
    Additional geometry times do not change this native row population.
    """
    def __init__(self, scene, edits):
        self.blocks = []
        self.total_rows = 0
        self.uniform = np.arange(int(np.floor(scene.duration * 120)) + 1) / 120
        if len(self.uniform) < 3:
            raise ValueError('At least three uniform native source samples required')
        native = [c[2] for a in scene.actors.values() for c in a['sampler'].channels]
        native += [o['times'] for o in scene.objects.values()]

        def add(kind, actor, times, order, items, unit, **details):
            times = np.asarray(times, float)
            if (times.ndim != 1 or not len(times) or not np.isfinite(times).all()
                    or np.any(np.diff(times) <= 0) or len(times) <= order or not items):
                raise ValueError('Complete increasing clock and row identities required')
            count = (len(times) - order) * len(items)
            block = dict(start=self.total_rows, stop=self.total_rows + count,
                kind=kind, actor=actor, unit=unit, order=order,
                times_s=times.tolist(), items=copy.deepcopy(items), **details)
            self.blocks.append(block)
            self.total_rows += count

        for name, actor_edit in edits.actors.items():
            actor = scene.actors[name]
            for track in actor_edit['tracks']:
                add('native_key_change', name, track['clock'][track['ids']], 0,
                    [dict(node=int(track['node']), path=track['path'])],
                    'normalized_control_vector',
                    native_key_indices=track['ids'].tolist(),
                    coordinate_frame='authored track edit coordinates')
            joints = [dict(joint_index=i, node=int(node),
                           node_name=actor['rig'].document['nodes'][node].get('name'))
                      for i, node in enumerate(actor['rig'].joints)]
            add('joint_displacement', name, self.uniform, 0, joints, 'm',
                coordinate_frame='rig world before actor placement')
            for kind, order, unit in RATE_METRICS:
                add(kind, name, self.uniform, order, joints, unit,
                    coordinate_frame='rig world before actor placement')
        self.edit_and_rate_rows = self.total_rows

        for entry in scene.rows:
            row = entry['authored']
            target = row['target']
            first, last = row['interval_s']
            populations = frame_populations([first, last]) if row['mode'] == 'hold' else []
            clock = np.unique(np.concatenate([np.array([first, last])] + native
                + [p['times_s'] for p in populations]))
            clock = clock[(clock >= first) & (clock <= last)]
            effectors = ([copy.deepcopy(row['vertices'])] if row['reduction'] == 'centroid'
                         else [[ref] for ref in row['vertices']])
            if target['space'] == 'actor':
                goals = ([copy.deepcopy(target['vertices'])] if target['reduction'] == 'centroid'
                         else [[ref] for ref in target['vertices']])
            else:
                goals = copy.deepcopy(target['points_m'])
            if len(effectors) != len(goals):
                raise ValueError('Complete corresponding native contact points required')
            points = [dict(point_index=i, effector_vertices=refs, target_point=goals[i])
                      for i, refs in enumerate(effectors)]
            details = dict(contact_id=row['id'], reduction=row['reduction'],
                target=copy.deepcopy(target), coordinate_frame=(
                    'object local' if target['space'] == 'object' else 'placed world'))
            add('contact_position', row['actor'], clock, 0, points, 'm', **details)
            for pop in populations:
                population = dict(id=pop['id'], rate_hz=pop['rate_hz'],
                    phase_offset_frames=pop['phase_offset_frames'],
                    tick_indices=pop['tick_indices'].tolist(), times_s=pop['times_s'].tolist())
                if len(pop['times_s']) < 2:
                    # One unavailable scalar row, even for an individual patch.
                    self.blocks.append(dict(start=self.total_rows, stop=self.total_rows + 1,
                        kind='contact_speed_unavailable', actor=row['actor'], unit=None,
                        order=None, times_s=population['times_s'], items=[],
                        population=population, available=False, **details))
                    self.total_rows += 1
                else:
                    add('contact_relative_speed', row['actor'], pop['times_s'], 1,
                        points, 'm/s', population=population, available=True, **details)
        self._starts = [b['start'] for b in self.blocks]

    def locate(self, index):
        if type(index) is not int or not 0 <= index < self.total_rows:
            raise ValueError('Existing integer native row index required')
        block = self.blocks[bisect_right(self._starts, index) - 1]
        result = {k: copy.deepcopy(v) for k, v in block.items()
                  if k not in ('start', 'stop', 'items', 'times_s', 'order', 'native_key_indices', 'population')}
        result['row_index'] = index
        if 'population' in block:
            result['population'] = {k: copy.deepcopy(v) for k, v in block['population'].items()
                                    if k not in ('times_s', 'tick_indices')}
        if block['kind'] == 'contact_speed_unavailable':
            result['sample_times_s'] = list(block['times_s'])
            return result
        sample, item = divmod(index - block['start'], len(block['items']))
        result.update(copy.deepcopy(block['items'][item]))
        result['sample_index'] = sample
        result['sample_times_s'] = block['times_s'][sample:sample + block['order'] + 1]
        if 'native_key_indices' in block:
            result['native_key_index'] = block['native_key_indices'][sample]
        if 'population' in block:
            result['tick_indices'] = block['population']['tick_indices'][sample:sample + 2]
        return result

    def manifest(self):
        return dict(schema='strep-native-condition-ledger-v1', native_rows=self.total_rows,
            edit_and_rate_rows=self.edit_and_rate_rows, blocks=copy.deepcopy(self.blocks),
            motion_evaluated=False, derivative_evaluated=False, quality_approved=False,
            release_approved=False)


def compare(ledger, decoded_residuals, affine_vectors, caps, scales, *, baseline_residuals):
    """Report every decoded failure and affine false negative with its identity.

    Scalar decoded residuals decide failure strictly at zero. Physical excess is
    their unscaled signed excess, not a fresh physical measurement. No tolerance
    is added; differences between scalar/vector floating arithmetic stay visible.
    """
    decoded, vectors, caps, scales, baseline = [np.asarray(v, float) for v in
        (decoded_residuals, affine_vectors, caps, scales, baseline_residuals)]
    count = ledger.total_rows
    if (decoded.shape != (count,) or baseline.shape != (count,)
            or vectors.shape != (count, 3) or caps.shape != (count,) or scales.shape != (count,)
            or any(not np.isfinite(a).all() for a in (decoded, vectors, caps, scales, baseline))
            or np.any(scales <= 0)):
        raise ValueError('Complete matching finite native observations and positive scales required')
    affine = (np.linalg.norm(vectors, axis=1) - caps) / scales
    if not np.isfinite(affine).all():
        raise ValueError('Nonfinite native affine arithmetic')
    failed = np.flatnonzero(decoded > 0)
    with np.errstate(over='ignore', invalid='ignore'):
        excess = decoded[failed] * scales[failed]
        difference = decoded[failed] - affine[failed]
    if not np.isfinite(excess).all() or not np.isfinite(difference).all():
        raise ValueError('Nonfinite native diagnostic excess arithmetic')
    records = []
    for position, index in enumerate(failed):
        i = int(index)
        identity = ledger.locate(i)
        physical = identity['unit'] is not None
        records.append(dict(**identity, decoded_residual=float(decoded[i]),
            baseline_residual=float(baseline[i]), affine_residual=float(affine[i]),
            affine_false_negative=bool(affine[i] <= 0),
            decoded_minus_affine_residual=float(difference[position]),
            cap_with_existing_tolerance=float(caps[i]), normalization_scale=float(scales[i]),
            unscaled_decoded_excess=float(excess[position]) if physical else None))
    return dict(schema='strep-native-affine-decoded-diagnostic-v1', native_rows=count,
        baseline_failed_rows=int(np.count_nonzero(baseline > 0)),
        decoded_failed_rows=len(records), affine_failed_rows=int(np.count_nonzero(affine > 0)),
        affine_false_negative_rows=sum(r['affine_false_negative'] for r in records),
        maximum_decoded_excess=float(decoded.max()), failures=records,
        all_decoded_failures_reported=True, tolerance_added=False,
        physical_measurements_recomputed=False, derivative_columns_recomputed=False,
        geometry_checked=False, quality_approved=False, release_approved=False)
