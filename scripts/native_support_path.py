"""Signed native ankle proposals inside explicit edit windows, with fixed ends."""
import numpy as np
from scipy.spatial.transform import Rotation
from native_leg_floor import foot_region, export_rotations
from native_leg_smoothing import smooth, lifts
from native_support_skin import NativeSupportSkin as BoundSkin
from contact_rate_path import ProjectedSkin
from paired_temporal_neighbor import rotation_channels
from elbow_swivel import local_transforms
from two_bone_waypoint import reach


def bend_box(worlds, parents, chain, heights, times, condition):
    """Intersect authored signed heights with exact per-key reachability."""
    for world in worlds: local_transforms(world, parents)
    points = worlds[:, :, :3, 3][:, chain]
    lengths = np.linalg.norm(np.diff(points, axis=1), axis=2)
    if np.any(lengths <= 1e-8): raise ValueError('Positive source segment lengths required')
    a, b = lengths.T; delta = points[:, 2]-points[:, 0]; up = condition['up']
    vertical = delta@up; horizontal = np.sum((delta-vertical[:, None]*up)**2, axis=1)
    if np.any(vertical >= -1e-8) or np.any(horizontal >= (a+b)**2):
        raise ValueError('Support edit requires ankle below hip along its plane normal')
    low = np.full(len(times), -condition['displacement']); high = -low
    # Include the keys bracketing fractional stance boundaries. Otherwise the
    # boundary pose interpolates toward an unconstrained, possibly buried foot.
    first = max(0, int(np.searchsorted(times, condition['stance_s'][0], side='right'))-1)
    last = min(len(times)-1, int(np.searchsorted(times, condition['stance_s'][1], side='left')))
    stance = np.zeros(len(times), bool); stance[first:last+1] = True
    low[stance] = np.maximum(low[stance], condition['clearance']-heights[stance])
    high[stance] = np.minimum(high[stance], condition['maximum_height']-.00025-heights[stance])
    # Restrict the permitted box to attainable distances; never widen it.
    low = np.maximum(low, -np.sqrt((a+b)**2-horizontal)-vertical)
    high = np.minimum(high, -np.sqrt(np.maximum(0., (a-b)**2-horizontal))-vertical)
    if any(low[k] > 1e-10 or high[k] < -1e-10 for k in (0, len(times)-1)):
        raise ValueError('Frozen edit boundary cannot satisfy the authored stance')
    low[[0, -1]] = 0.; high[[0, -1]] = 0.
    if np.any(low > high): raise ValueError('Authored stance is unreachable within displacement bounds')
    bend = lambda lift: np.arccos(np.clip((horizontal+(vertical+lift)**2-a*a-b*b)/(2*a*b), -1., 1.))
    lower, upper, original = bend(low), bend(high), bend(np.zeros(len(times)))
    return dict(lower=lower, upper=upper, lower_lift=low, upper_lift=high,
                vertical=vertical, horizontal_squared=horizontal, lengths=lengths,
                reference=np.clip(original, lower, upper))


def restrict_box(box, low, high):
    """Intersect an existing lift corridor; never widen authored key bounds."""
    low,high=map(lambda x:np.asarray(x,float),(low,high))
    if (low.shape!=box['lower_lift'].shape or high.shape!=low.shape
            or not np.isfinite([low,high]).all() or np.any(low>high)
            or np.any(low<box['lower_lift']) or np.any(high>box['upper_lift'])
            or any(low[k]!=0 or high[k]!=0 for k in (0,len(low)-1))):
        raise ValueError('Tightened lift corridor must preserve original bounds and frozen ends')
    a,b=box['lengths'].T
    def bend(lift):return np.arccos(np.clip((box['horizontal_squared']+(box['vertical']+lift)**2-a*a-b*b)/(2*a*b),-1.,1.))
    lower,upper=bend(low),bend(high)
    return dict(box,lower=lower,upper=upper,lower_lift=low.copy(),upper_lift=high.copy(),
                reference=np.clip(box['reference'],lower,upper))


def propose(rig, reader, rows, path, acceleration_time=.05, reference_weight=.5, *, lift_limits=None):
    if lift_limits is not None and set(lift_limits)!={r['id'] for r in rows}:
        raise ValueError('One tightening corridor per authored support required')
    channels = rotation_channels(rig.document, rig.binary); skin = BoundSkin(rig)
    nodes = sorted({n for row in rows for n in row['chain']})
    values = {n: channels[n][2].copy() for n in nodes}; reports = []
    for row in rows:
        chain = row['chain']; first, last = row['edit_keys']; times = row['clock'][first:last+1]
        worlds = np.array([reader.sample(float(t)) for t in times])
        region = foot_region(skin, rig.parents, chain[-1])
        projection = ProjectedSkin(skin, region, row['up'], row['offset'])
        heights = projection.evaluate(worlds).min(axis=1)
        box = bend_box(worlds, rig.parents, chain, heights, times, row)
        if lift_limits is not None:box=restrict_box(box,*lift_limits[row['id']])
        bend, optimizer = smooth(times, box['lower'], box['upper'],
            acceleration_time=acceleration_time, reference_weight=reference_weight, reference=box['reference'])
        amounts = lifts(box, bend); edits = []
        for key, (world, amount) in enumerate(zip(worlds, amounts)):
            if key in (0, len(times)-1): continue
            if abs(amount) <= 1e-12: continue
            local = local_transforms(world, rig.parents)
            _, changed = reach(world, rig.parents, *chain, world[chain[-1], :3, 3]+row['up']*amount)
            angles = np.rad2deg(Rotation.from_matrix(local[chain, :3, :3].transpose(0, 2, 1)@changed[chain, :3, :3]).magnitude())
            if angles.max() > row['angle']: raise ValueError('Source-relative support rotation exceeds authoring bound')
            for node, q in zip(chain, Rotation.from_matrix(changed[chain, :3, :3]).as_quat()):
                values[node][first+key] = q if q@channels[node][2][first+key] >= 0 else -q
            edits.append(dict(time_s=float(times[key]), displacement_m=float(amount), angles_degrees=angles.tolist()))
        reports.append(dict(id=row['id'], vertices=len(region), optimizer=optimizer, edits=edits))
    export_rotations(rig.document, rig.binary, values, path)
    return reports
