"""Small native wrist translations with frozen contact interpolation support."""
import numpy as np
from scipy.spatial.transform import Rotation
from contact_locked_native import NativeRotationEdit
from oriented_two_bone import reach_pose
from rig_clip_import import AnimationSampler
from timed_rotation_edit import sampled_rotations
from paired_guarded_temporal import world_from_local


def key_influence(clock, ids, times):
    clock, ids, times = np.asarray(clock), np.asarray(ids, int), np.asarray(times, float)
    left = np.clip(np.searchsorted(clock, times, side='right')-1, 0, len(clock)-2)
    fraction = np.clip((times-clock[left].astype(float))/(clock[left+1]-clock[left]).astype(float), 0, 1)
    return ((left[:, None] == ids)*((1-fraction)[:, None])
            + (left[:, None]+1 == ids)*fraction[:, None])


class NativeWristRetraction:
    def __init__(self, document, binary, names, times, window, protected, event, reference, direction):
        self.direction = np.asarray(direction, float)
        if self.direction.shape != (3,) or not np.isfinite(self.direction).all() or abs(np.linalg.norm(self.direction)-1) > 1e-8:
            raise ValueError('Unit rig-space retraction direction required')
        if not np.isfinite(event) or not window[0] < event < window[1]:
            raise ValueError('Interior contact time required')
        self.exporter = NativeRotationEdit(document, binary, names, times, window, [*protected, [event, event]], reference)
        self.model = self.exporter.model
        if len(self.model.nodes) != 3:
            raise ValueError('Three consecutive arm joints required')
        self.chain = self.model.nodes
        if [self.model.parents[n] for n in self.chain[1:]] != self.chain[:2]:
            raise ValueError('Three consecutive arm joints required')
        first = self.model.entries[0]; self.clock = first['clock']; self.ids = first['ids']
        for entry in self.model.entries[1:]:
            np.testing.assert_array_equal(entry['clock'], self.clock)
            np.testing.assert_array_equal(entry['ids'], self.ids)
        reader = AnimationSampler(document, binary, 0)
        self.key_worlds = [reader.sample(float(self.clock[k])) for k in self.ids]
        self.influence = key_influence(self.clock, self.ids, self.model.times)

    def quaternions(self, amounts, quantize=True):
        amounts = np.asarray(amounts, float)
        if amounts.shape != self.ids.shape or not np.isfinite(amounts).all() or np.any(amounts < 0):
            raise ValueError('Finite nonnegative retractions for every editable key required')
        result = {e['node']: e['source'].astype(float).copy() for e in self.model.entries}
        for k, amount, world in zip(self.ids, amounts, self.key_worlds):
            if amount == 0: continue
            wrist = self.chain[-1]
            _, local = reach_pose(world, self.model.parents, *self.chain,
                world[wrist, :3, 3]+amount*self.direction, world[wrist, :3, :3])
            rotations = Rotation.from_matrix(local[self.chain, :3, :3]).as_quat()
            for node, q in zip(self.chain, rotations):
                q *= -1 if q@result[node][k] < 0 else 1
                result[node][k] = q.astype(np.float32) if quantize else q
        # Check cumulative angles against the same original reference, before use.
        for entry in self.model.entries:
            maximum = np.rad2deg((Rotation.from_quat(entry['original']).inv()*Rotation.from_quat(result[entry['node']])).magnitude()).max()
            if maximum > 45.+1e-4: raise ValueError('Original native rotation budget exceeded')
        return result

    def world(self, amounts):
        local = self.model.local.copy(); q = self.quaternions(amounts)
        for entry in self.model.entries:
            n = entry['node']
            local[:, n, :3, :3] = sampled_rotations(entry['clock'], q[n], self.model.times)*self.model.scales[n][:, None, :]
        return world_from_local(local, self.model.parents)

    def export(self, amounts, path):
        return self.exporter.export(self.quaternions(amounts), path)


def repair(evaluate, influence, *, maximum_m=.02, reserve_m=.0001, iterations=8):
    """Refresh serialized skin after bounded corrections; never infer mesh success."""
    influence = np.asarray(influence, float)
    if (influence.ndim != 2 or not all(influence.shape) or not np.isfinite(influence).all()
            or np.any(influence < 0) or np.any(influence.sum(axis=1) > 1+1e-8)
            or not np.isfinite([maximum_m, reserve_m]).all() or not 0 < reserve_m < maximum_m
            or type(iterations) is not int or not 1 <= iterations <= 16):
        raise ValueError('Valid interpolation influences and bounded repair settings required')
    amounts = np.zeros(influence.shape[1]); history = []; error = None
    active = influence.sum(axis=1) > 1e-10
    def observed(value):
        result = np.asarray(evaluate(value), float)
        if result.shape != (len(influence),) or not np.isfinite(result).all():
            raise ValueError('Finite signed plane excess per declared sample required')
        return result
    excess = observed(amounts)
    for _ in range(iterations):
        bad = active & (excess > 1e-8)
        if not np.any(bad): break
        # Each influencing key gets the same extra wrist translation. Refresh
        # actual skin because SLERP and arm reach are not linear in this offset.
        needed = (excess[bad]+reserve_m)/influence[bad].sum(axis=1)
        increment = np.max(np.where(influence[bad] > 0, needed[:, None], 0), axis=0)
        proposed = np.minimum(amounts+increment, maximum_m)
        if np.array_equal(proposed, amounts): error = 'Retraction proposal cap exhausted'; break
        accepted = False
        for backoff in range(9):
            candidate = amounts+(proposed-amounts)*2.**(-backoff)
            try: next_excess = observed(candidate)
            except ValueError as exc:
                error = str(exc); continue
            if np.maximum(next_excess[active], 0).max(initial=0) >= np.maximum(excess[active], 0).max(initial=0):
                continue
            history.append(dict(maximum_excess_before_m=float(excess[active].max()),
                maximum_excess_after_m=float(next_excess[active].max()), fraction=2.**(-backoff)))
            amounts, excess, accepted, error = candidate, next_excess, True, None
            break
        if not accepted:
            error = error or 'No bounded decrease in refreshed plane violation'; break
    return amounts, dict(iterations=history, error=error, active_samples=int(active.sum()),
        inactive_samples=int((~active).sum()), active_plane_pass=bool(np.all(excess[active] <= 1e-8)),
        all_planes_pass=bool(np.all(excess <= 1e-8)), final_excess_m=excess.tolist(),
        maximum_retraction_m=float(amounts.max()), quality_approved=False)
