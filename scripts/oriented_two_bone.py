"""Rigid wrist pose reach with unchanged local translations and finger transforms."""
import numpy as np
from two_bone_waypoint import reach
from paired_guarded_temporal import world_from_local
from elbow_swivel import descendants


def reach_pose(world, parents, upper, elbow, wrist, position, rotation, swivel_radians=0.):
    rotation = np.asarray(rotation, float)
    if (rotation.shape != (3, 3) or not np.isfinite(rotation).all()
            or not np.allclose(rotation.T@rotation, np.eye(3), atol=1e-8, rtol=0)
            or abs(np.linalg.det(rotation)-1.) > 1e-8):
        raise ValueError('Proper desired wrist rotation required')
    reached, local = reach(world, parents, upper, elbow, wrist, position, swivel_radians)
    local[wrist, :3, :3] = reached[elbow, :3, :3].T@rotation
    result = world_from_local(local[None], parents)[0]
    hand = descendants(parents, wrist)
    delta = rotation@world[wrist, :3, :3].T
    expected = world[hand].copy()
    expected[:, :3, :3] = delta@world[hand, :3, :3]
    expected[:, :3, 3] = (world[hand, :3, 3]-world[wrist, :3, 3])@delta.T+position
    np.testing.assert_allclose(result[hand], expected, rtol=0, atol=1e-9)
    return result, local
