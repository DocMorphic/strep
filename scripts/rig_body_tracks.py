"""Explicit rig-node to rigid-body COM/axes sampling; no anatomy inference."""
import copy
import numpy as np
from scipy.spatial.transform import Rotation
from native_support_clock import NativeSupportSampler


def sample(rig, animation_index, bindings, sample_count, placement, *, rigid_tolerance):
    """Return a complete uniform body clock without modifying the supplied rig.

    Mass/inertia, body parents, joint anchors, reactions and capacities are
    separate explicit inputs to articulated_motion_dynamics.diagnose.
    """
    if (type(sample_count) is not int or not 3 <= sample_count <= 900
            or type(animation_index) is not int or animation_index < 0):
        raise ValueError('Explicit animation and 3–900 uniform samples required')
    if (type(rigid_tolerance) not in (int, float) or not np.isfinite(rigid_tolerance)
            or not 0 < rigid_tolerance <= 1e-6):
        raise ValueError('Explicit bounded rigid-transform numerical accuracy required')
    if not isinstance(bindings, list) or not 1 <= len(bindings) <= 128:
        raise ValueError('Explicit 1–128 body/node bindings required')
    bindings = copy.deepcopy(bindings)
    fields = {'id', 'node', 'com_from_node_local_m', 'body_rotation_from_node_xyzw', 'provenance'}
    ids, nodes, offsets, axes = [], [], [], []

    def vector(value, count, name):
        try:
            result = np.array(value, dtype=float, copy=True)
        except (TypeError, ValueError) as exc:
            raise ValueError('Invalid ' + name) from exc
        if result.shape != (count,) or not np.isfinite(result).all():
            raise ValueError('Explicit finite ' + name + ' required')
        return result

    def quaternion(value, name):
        result = vector(value, 4, name)
        if abs(np.linalg.norm(result) - 1) > rigid_tolerance:
            raise ValueError('Unit ' + name + ' required')
        return Rotation.from_quat(result).as_matrix()

    for entry in bindings:
        if not isinstance(entry, dict) or set(entry) != fields:
            raise ValueError('Complete explicit body/node binding required')
        name, node = entry['id'], entry['node']
        if not isinstance(name, str) or not 1 <= len(name) <= 128 or name in ids:
            raise ValueError('Distinct explicit body IDs required')
        if type(node) is not int or node not in rig.joints or node in nodes:
            raise ValueError('Distinct existing skin-joint nodes required')
        if not isinstance(entry['provenance'], str) or not 1 <= len(entry['provenance']) <= 2000:
            raise ValueError('Explicit COM/body-axis provenance required')
        offset = vector(entry['com_from_node_local_m'], 3, 'node-local COM')
        if np.max(abs(offset)) > 1000:
            raise ValueError('Bounded explicit COM offset required')
        ids.append(name); nodes.append(node); offsets.append(offset)
        axes.append(quaternion(entry['body_rotation_from_node_xyzw'], 'node-local body orientation'))
    if not isinstance(placement, dict) or set(placement) != {'translation_m', 'rotation_xyzw'}:
        raise ValueError('Complete explicit world placement required')
    translation = vector(placement['translation_m'], 3, 'world placement')
    rotation = quaternion(placement['rotation_xyzw'], 'world placement orientation')
    if np.max(abs(translation)) > 1000:
        raise ValueError('Bounded world placement required')
    sampler = NativeSupportSampler(rig.document, rig.binary, animation_index)
    if not 0 < sampler.duration <= 30:
        raise ValueError('Complete nonempty clip within thirty seconds required')
    fps = (sample_count - 1) / sampler.duration
    if not 1 <= fps <= 240:
        raise ValueError('Explicit uniform clock must be within 1–240 Hz')
    times = np.linspace(0, sampler.duration, sample_count)
    positions, rotations = [], []
    for time in times:
        world = sampler.sample(float(time))[nodes]
        if not np.isfinite(world).all() or not np.allclose(world[:, 3], [0, 0, 0, 1], rtol=0, atol=rigid_tolerance):
            raise ValueError('Finite affine node transforms required')
        linear = world[:, :3, :3]
        if (not np.allclose(linear @ linear.transpose(0, 2, 1), np.eye(3), rtol=0, atol=rigid_tolerance)
                or not np.allclose(np.linalg.det(linear), 1, rtol=0, atol=rigid_tolerance)):
            raise ValueError('Original body transforms must be rigid; scale/reflection/shear is not removed')
        com = world[:, :3, 3] + np.einsum('bij,bj->bi', linear, offsets)
        positions.append(com @ rotation.T + translation)
        rotations.append(rotation @ linear @ np.array(axes))
    positions = np.array(positions)
    if not np.isfinite(positions).all() or np.max(abs(positions)) > 1000:
        raise ValueError('Bounded complete world COM poses required')
    rotations = np.array(rotations)
    q = Rotation.from_matrix(rotations.reshape(-1, 3, 3)).as_quat().reshape(sample_count, len(nodes), 4)
    for frame in range(1, sample_count):
        flip = np.einsum('bi,bi->b', q[frame], q[frame-1]) < 0
        q[frame, flip] *= -1
    for entry, offset, axis in zip(bindings, offsets, axes):
        entry['com_from_node_local_m'] = offset.tolist()
        entry['body_rotation_from_node_xyzw'] = Rotation.from_matrix(axis).as_quat().tolist()
    return dict(schema='strep-rig-body-tracks-v1', animation_index=animation_index,
                body_ids=ids, bindings=bindings, duration_s=sampler.duration,
                sample_count=sample_count, fps=fps, uniform_times_s=times.tolist(),
                world_com_positions_m=positions.tolist(), body_rotations_xyzw=q.tolist(),
                placement=dict(translation_m=translation.tolist(), rotation_xyzw=Rotation.from_matrix(rotation).as_quat().tolist()),
                rigid_tolerance=rigid_tolerance, exact_clip_endpoints_preserved=True,
                body_properties_inferred=False, physical_approval=None, quality_approved=False,
                release_approved=False, training_admitted=False,
                scope='Complete supplied-rig joint transforms on an explicit uniform clock and declared COM/body-axis bindings. No skin-to-mass/anatomy inference, physical parent/anchor model, support/contact allocation, calibrated capacity, continuous dynamics, engine or human-quality certificate. Caller must bind original rig/profile bytes before claiming an immutable workflow.')
