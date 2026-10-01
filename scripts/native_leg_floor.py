"""Bounded two-bone floor lifts with retained foot orientation and root motion.

This removes sampled penetration; it does not establish balance, planted feet,
naturalness or between-key clearance. The caller must audit serialized motion.
"""
import copy
import numpy as np
from scipy.spatial.transform import Rotation
from elbow_swivel import descendants, local_transforms
from two_bone_waypoint import reach
from gltf_tools import append_accessor, write_glb


def foot_region(skin, parents, foot):
    """Only vertices whose positive influences all lie in this foot subtree."""
    inside = descendants(parents, foot)[skin.nodes]
    ids = np.flatnonzero(np.all(inside | (skin.weights == 0), axis=1))
    if not len(ids):
        raise ValueError('No fully foot-bound mesh region')
    return ids


def lift_pose(world, parents, chain, minimum_height, *, clearance=.00025,
              maximum_lift=.03, maximum_angle_degrees=45., up=(0.,1.,0.)):
    world = np.asarray(world, float); parents = np.asarray(parents)
    chain = list(chain); up = np.asarray(up, float)
    if len(chain) != 3 or len(set(chain)) != 3 or any(type(n) not in (int,np.int32,np.int64) or not 0 <= n < len(parents) for n in chain):
        raise ValueError('Distinct direct thigh/knee/foot chain required')
    upper, knee, foot = chain
    if parents[knee] != upper or parents[foot] != knee:
        raise ValueError('Direct thigh/knee/foot chain required')
    local = local_transforms(world, parents)
    parameters = [minimum_height, clearance, maximum_lift, maximum_angle_degrees]
    if not np.isfinite(parameters).all() or clearance < 0 or maximum_lift <= 0 or not 0 < maximum_angle_degrees <= 45:
        raise ValueError('Finite floor condition and bounded lift/angle required')
    if up.shape != (3,) or not np.isfinite(up).all() or abs(np.linalg.norm(up)-1) > 1e-8:
        raise ValueError('Unit floor normal required')
    amount = max(0., clearance-float(minimum_height))
    if amount > maximum_lift:
        raise ValueError('Floor lift exceeds authoring bound')
    if not amount:
        return world.copy(), local, dict(lift_m=0., angles_degrees=[0.,0.,0.])
    target = world[foot,:3,3]+up*amount
    changed, changed_local = reach(world, parents, upper, knee, foot, target)
    angles = np.rad2deg(Rotation.from_matrix(local[chain,:3,:3].transpose(0,2,1)@changed_local[chain,:3,:3]).magnitude())
    if angles.max() > maximum_angle_degrees:
        raise ValueError('Floor rotation exceeds authoring bound')
    return changed, changed_local, dict(lift_m=amount, angles_degrees=angles.tolist())


def export_rotations(document, binary, values, path):
    """Replace specified LINEAR rotation outputs; preserve original time inputs."""
    result = copy.deepcopy(document); data = bytearray(binary)
    if len(result.get('animations', [])) != 1:
        raise ValueError('One animation required')
    found = set()
    animation = result['animations'][0]
    for channel in animation['channels']:
        node = channel['target']['node']
        if channel['target']['path'] != 'rotation' or node not in values:
            continue
        if node in found:
            raise ValueError('Ambiguous rotation track')
        sampler = copy.deepcopy(animation['samplers'][channel['sampler']])
        if sampler.get('interpolation', 'LINEAR') != 'LINEAR':
            raise ValueError('LINEAR native rotations required')
        quats = np.asarray(values[node], np.float32)
        count = document['accessors'][sampler['input']]['count']
        if quats.shape != (count,4) or not np.isfinite(quats).all() or not np.allclose(np.linalg.norm(quats,axis=1),1.,atol=1e-6,rtol=0):
            raise ValueError('Matching unit native quaternion keys required')
        sampler['output'] = append_accessor(result, data, quats, 'VEC4')
        channel['sampler'] = len(animation['samplers']); animation['samplers'].append(sampler)
        found.add(node)
    if found != set(values):
        raise ValueError('Missing selected native rotation track')
    write_glb(path, result, data)
