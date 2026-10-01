"""Iterative rigid-wrist retraction proposal, without rig-limit or quality claims."""
import numpy as np
from oriented_two_bone import reach_pose


def retract(world, parents, chain, surface, midpoint, outward, rig_outward, *, clearance_m=.0005, reserve_m=.0001, steps=4):
    world = np.asarray(world, float)
    midpoint, outward, rig_outward = [np.asarray(v, float) for v in (midpoint, outward, rig_outward)]
    if (any(v.shape != (3,) or not np.isfinite(v).all() for v in (midpoint, outward, rig_outward))
            or any(abs(np.linalg.norm(v)-1.) > 1e-8 for v in (outward, rig_outward))
            or not np.isfinite([clearance_m, reserve_m]).all() or min(clearance_m, reserve_m) <= 0
            or type(steps) is not int or not 1 <= steps <= 8):
        raise ValueError('Finite midpoint, unit axes, positive clearance/reserve and bounded steps required')
    current = world.copy(); history = []
    def excess(value):
        points = np.asarray(surface(value), float)
        if points.ndim != 2 or points.shape[1:] != (3,) or not len(points) or not np.isfinite(points).all():
            raise ValueError('Finite nonempty actual hand surface required')
        return float(np.max((points-midpoint)@outward)+clearance_m)
    initial = excess(current); error = None; total = 0.
    for _ in range(steps):
        value = excess(current)
        if value <= 1e-8: break
        amount = value+reserve_m
        try:
            proposed, _ = reach_pose(current, parents, *chain,
                current[chain[-1], :3, 3]-rig_outward*amount, current[chain[-1], :3, :3])
        except ValueError as exc:
            error = str(exc); break
        after = excess(proposed); history.append(dict(retraction_m=amount, before_excess_m=value, after_excess_m=after))
        current = proposed; total += amount
    final = excess(current)
    return current, dict(initial_excess_m=initial, final_excess_m=final, total_retraction_m=total,
        iterations=history, error=error, selected_hand_plane_pass=bool(final <= 1e-8),
        original_joint_limits_verified=False, full_mesh_validation_required=True, quality_approved=False)
