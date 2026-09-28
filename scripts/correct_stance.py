"""Periodic contact-velocity reduction, conserving bone lengths and ankle orientation."""
import argparse
import itertools
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from strep import ROOT, read, save, sha256, now, source_check
from correct_loops import assemble, repeat_motion, speed_p95
from evaluate_grid import loop_screen, rotation_angles
from inspect_motion import validate_motion, metrics


def load_motion(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def swing(a, b):
    """Proper shortest rotation mapping a direction to another; handles antipodes."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
    cross, dot = np.cross(a, b), float(np.clip(a @ b, -1, 1))
    norm = np.linalg.norm(cross)
    if norm < 1e-10:
        if dot > 0:
            return np.eye(3)
        axis = np.cross(a, np.eye(3)[np.argmin(abs(a))])
        return Rotation.from_rotvec(axis / np.linalg.norm(axis) * np.pi).as_matrix()
    return Rotation.from_rotvec(cross / norm * np.arctan2(norm, dot)).as_matrix()


def knee_target(hip, knee, ankle, target):
    """Preserve bend side and limb lengths; report unreachable target clamping."""
    upper, lower = np.linalg.norm(knee - hip), np.linalg.norm(ankle - knee)
    vector = target - hip
    distance = np.linalg.norm(vector)
    if distance < 1e-9:
        raise ValueError('Degenerate hip-to-ankle target')
    direction = vector / distance
    reachable = np.clip(distance, abs(upper - lower) + 1e-6, upper + lower - 1e-6)
    target = hip + direction * reachable
    projection = (upper * upper + reachable * reachable - lower * lower) / (2 * reachable)
    height = np.sqrt(max(0, upper * upper - projection * projection))
    pole = knee - hip - direction * ((knee - hip) @ direction)
    if np.linalg.norm(pole) < 1e-8:
        pole = np.cross(direction, np.eye(3)[np.argmin(abs(direction))])
    return hip + projection * direction + height * pole / np.linalg.norm(pole), target, abs(distance - reachable)


def periodic_offsets(points, contacts, displacement, velocity_weight, smoothness, regularization):
    """Solve a cyclic quadratic objective with the root displacement at the wrap."""
    frames = len(points)
    difference = np.roll(np.eye(frames), -1, axis=1) - np.eye(frames)
    # Explicit indexing avoids ambiguity of cyclic matrix direction.
    difference[:] = 0
    for frame in range(frames):
        difference[frame, frame] = -1
        difference[frame, (frame + 1) % frames] = 1
    second = np.roll(np.eye(frames), 1, axis=1) + np.roll(np.eye(frames), -1, axis=1) - 2 * np.eye(frames)
    support = contacts & np.roll(contacts, -1, axis=0)
    velocity = np.roll(points, -1, axis=0) - points
    velocity[-1] += displacement
    counts = support.sum(axis=1)
    matrix = velocity_weight * (difference.T @ (counts[:, None] * difference))
    matrix += smoothness * second.T @ second + regularization * np.eye(frames)
    rhs = -velocity_weight * difference.T @ (velocity[:, :, [0, 2]] * support[..., None]).sum(axis=1)
    horizontal = np.linalg.solve(matrix, rhs)
    result = np.zeros((frames, 3))
    result[:, [0, 2]] = horizontal
    return result


def apply_offsets(source, offsets, skeleton):
    names = skeleton.bone_order_names
    parents = skeleton.joint_parents.numpy()
    local = source['local_rot_mats'].astype(float).copy()
    global_rot, positions = source['global_rot_mats'], source['posed_joints']
    max_unreachable = 0.0
    for side, shifts in zip(('Left', 'Right'), offsets):
        hip, ankle = names.index(side + 'Leg'), names.index(side + 'Foot')
        knee = int(parents[ankle])
        for frame, shift in enumerate(shifts):
            h, k, a = positions[frame, [hip, knee, ankle]].astype(float)
            new_knee, new_ankle, clamped = knee_target(h, k, a, a + shift)
            max_unreachable = max(max_unreachable, clamped)
            hip_global = swing(k - h, new_knee - h) @ global_rot[frame, hip]
            knee_global = swing(a - k, new_ankle - new_knee) @ global_rot[frame, knee]
            local[frame, hip] = global_rot[frame, parents[hip]].T @ hip_global
            local[frame, knee] = hip_global.T @ knee_global
            local[frame, ankle] = knee_global.T @ global_rot[frame, ankle]
    corrected = assemble(local, source['root_positions'], source['foot_contacts'], skeleton)
    return corrected, max_unreachable


def main(output, baseline):
    from kimodo.skeleton import SOMASkeleton77
    from kimodo.exports.bvh import save_motion_bvh, bvh_to_kimodo_motion
    import torch
    root, baseline = Path(output).resolve(), Path(baseline).resolve()
    root.mkdir(parents=True, exist_ok=False)
    config = read(ROOT / 'benchmarks/stance-correction-v1.json')
    targets = read(ROOT / 'benchmarks/acceptance-v0.json')['targets']
    skeleton = SOMASkeleton77()
    summary = {'started_at': now(), 'config': config, 'baseline': str(baseline),
               'source_commit': source_check(), 'implementation_sha256': sha256(Path(__file__)),
               'config_sha256': sha256(ROOT / 'benchmarks/stance-correction-v1.json'),
               'acceptance_sha256': sha256(ROOT / 'benchmarks/acceptance-v0.json'),
               'baseline_summary_sha256': sha256(baseline / 'summary.json'), 'trials': []}
    for previous in read(baseline / 'summary.json')['trials']:
        seed = previous['seed']
        source_path = baseline / f'seed-{seed}/corrected.npz'
        if sha256(source_path) != previous['corrected_sha256']:
            raise RuntimeError('Frozen baseline source hash differs')
        source = load_motion(source_path)
        names, parents, feet = validate_motion(source, config['fps'])
        displacement = np.array(previous['cycle_displacement_m'])
        before = metrics(repeat_motion(source, displacement, 3), names, feet, config['fps'])
        candidates, best = [], None
        for velocity_weight, smoothness, strength in itertools.product(config['velocity_weights'], config['smoothness_weights'], config['strengths']):
            offsets = []
            for side in range(2):
                group = feet[side * 3:side * 3 + 3]
                offsets.append(strength * periodic_offsets(source['posed_joints'][:, [names.index(n) for n in group]],
                    source['foot_contacts'][:, side * 3:side * 3 + 3], displacement, velocity_weight, smoothness, config['offset_regularization']))
            corrected, reach_error = apply_offsets(source, offsets, skeleton)
            lift = max(0, -float(corrected['posed_joints'][..., 1].min()))
            corrected['posed_joints'][..., 1] += lift
            corrected['root_positions'][:, 1] += lift
            tiled = repeat_motion(corrected, displacement, 3)
            validate_motion(tiled, config['fps'])
            after = metrics(tiled, names, feet, config['fps'])
            screen = loop_screen(tiled, config['fps'], targets)
            distortion = np.linalg.norm(corrected['posed_joints'] - source['posed_joints'], axis=-1)
            rotation_change = rotation_angles(corrected['local_rot_mats'], source['local_rot_mats'])
            regression = []
            if speed_p95(after) is None or previous['allowed_contact_speed_p95_m_s'] is None:
                regression.append('contact_support_unassessed')
            elif speed_p95(after) > previous['allowed_contact_speed_p95_m_s']:
                regression.append('original_contact_speed_regression_limit')
            if lift > config['max_extra_ground_lift_m']:
                regression.append('extra_ground_lift')
            if distortion.max() > config['max_joint_displacement_m']:
                regression.append('joint_displacement_budget')
            if rotation_change.max() > config['max_local_rotation_change_degrees']:
                regression.append('rotation_distortion_budget')
            if after['max_joint_ground_penetration_m'] > before['max_joint_ground_penetration_m'] + 0.001:
                regression.append('ground_penetration_regression')
            improved = speed_p95(after) is not None and speed_p95(before) is not None and speed_p95(after) <= speed_p95(before) * (1 - config['minimum_relative_improvement'])
            accepted = screen['screen_status'] == 'within_provisional_screen' and not regression and improved
            record = {'velocity_weight': velocity_weight, 'smoothness': smoothness, 'strength': strength,
                      'screen': screen, 'before': before, 'after': after, 'improved': improved, 'accepted': accepted,
                      'regressions': regression, 'max_joint_displacement_m': float(distortion.max()),
                      'rms_joint_displacement_m': float(np.sqrt(np.mean(distortion ** 2))),
                      'max_local_rotation_change_degrees': float(rotation_change.max()),
                      'extra_constant_ground_lift_m': lift, 'max_unreachable_target_clamp_m': reach_error}
            score = (0 if accepted else 1000) + 100 * len(screen['screen_exceedances']) + 50 * len(regression) + 10 * (speed_p95(after) or 0) + float(distortion.max())
            candidates.append(record)
            if best is None or score < best[0]:
                best = score, record, corrected
        _, winner, corrected = best
        folder = root / f'seed-{seed}'
        folder.mkdir()
        np.savez(folder / 'corrected.npz', **corrected)
        np.savez(folder / 'repeated-four-cycles.npz', **repeat_motion(corrected, displacement, 4))
        save_motion_bvh(folder / 'corrected.bvh', torch.from_numpy(corrected['local_rot_mats']), torch.from_numpy(corrected['root_positions']), skeleton=skeleton, fps=30, standard_tpose=True)
        restored, fps = bvh_to_kimodo_motion(folder / 'corrected.bvh', skeleton=skeleton, standard_tpose=True)
        restored = {key: value.numpy() for key, value in restored.items()}
        error = float(np.linalg.norm(restored['posed_joints'] - corrected['posed_joints'], axis=-1).max())
        restored['foot_contacts'] = corrected['foot_contacts'].copy()
        export_screen = loop_screen(repeat_motion(restored, displacement, 3), fps, targets)
        if error > 1e-4 or (winner['accepted'] and export_screen['screen_status'] != 'within_provisional_screen'):
            raise RuntimeError('Export verification failed')
        if not np.array_equal(corrected['foot_contacts'], source['foot_contacts']):
            raise RuntimeError('Contact labels changed')
        winner.update(seed=seed, source=str(source_path), source_sha256=sha256(source_path),
                      corrected_sha256=sha256(folder / 'corrected.npz'), cycle_displacement_m=displacement.tolist(),
                      cycle_frames=len(corrected['posed_joints']), bvh_roundtrip_max_joint_error_m=error,
                      contact_labels_unchanged=True, old_regression_limit_m_s=previous['allowed_contact_speed_p95_m_s'])
        save(folder / 'report.json', winner)
        save(folder / 'candidates.json', candidates)
        summary['trials'].append(winner)
        save(root / 'summary.json', summary)
        print(json.dumps({'seed': seed, 'accepted': winner['accepted'], 'before': speed_p95(before), 'after': speed_p95(winner['after']), 'flags': winner['regressions'], 'seam': winner['screen']['screen_exceedances']}), flush=True)
    summary['finished_at'] = now()
    save(root / 'summary.json', summary)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, default=ROOT / 'reports/loop-correction-v1-reviewed')
    args = parser.parse_args()
    main(args.output, args.baseline)
