"""Deterministic cycle extraction and crossfade, with explicit regression screening."""
import json
import argparse
import math
from pathlib import Path

import numpy as np
import torch
from scipy.spatial.transform import Rotation

from strep import ROOT, read, save, sha256, now, source_check
from evaluate_grid import loop_screen, rotation_angles, rms_vectors
from inspect_motion import skeleton_metadata, metrics, validate_motion, inspect_motion


def yaw_rotation(angle):
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def geodesic_blend(a, b, weight):
    shape = a.shape
    delta = np.swapaxes(a, -1, -2) @ b
    vectors = Rotation.from_matrix(delta.reshape(-1, 3, 3)).as_rotvec().reshape(shape[:-2] + (3,))
    vectors *= weight.reshape((-1,) + (1,) * (vectors.ndim - 1))
    return a @ Rotation.from_rotvec(vectors.reshape(-1, 3)).as_matrix().reshape(shape)


def crossfade_cycle(source, start, length, blend, root_mode):
    """Frame zero continues the retained tail; blend returns to the earlier stride."""
    stop = start + length
    rotation = source['local_rot_mats'][start:stop + blend].astype(np.float64).copy()
    root = source['root_positions'][start:stop + blend].astype(np.float64).copy()
    displacement = root[length] - root[0]
    displacement[1] = 0
    if np.linalg.norm(displacement[[0, 2]]) < 0.1:
        raise ValueError('Not a traveling run cycle')
    alignment = yaw_rotation(-math.atan2(displacement[0], displacement[2]))
    root = (root - np.array([root[0, 0], 0, root[0, 2]])) @ alignment.T
    rotation[:, 0] = alignment @ rotation[:, 0]
    displacement = alignment @ displacement
    # Two unchanged continuation samples protect the boundary derivatives.
    u = np.clip((np.arange(blend) - 1) / (blend - 2), 0, 1)
    weight = u * u * (3 - 2 * u)
    out_rotation = rotation[:length].copy()
    out_root = root[:length].copy()
    out_rotation[:blend] = geodesic_blend(rotation[length:length + blend], rotation[:blend], weight)
    out_root[:blend] = (root[length:length + blend] - displacement) * (1 - weight[:, None]) + root[:blend] * weight[:, None]
    if root_mode == 'constant_forward_speed':
        out_root[:, 0] = 0
        out_root[:, 2] = np.arange(length) / length * displacement[2]
    elif root_mode != 'aligned':
        raise ValueError('Unknown root mode')
    contacts = source['foot_contacts'][start:stop].copy()
    contacts[:blend] |= source['foot_contacts'][stop:stop + blend]
    return out_rotation, out_root, contacts, displacement


def assemble(rotation, root, contacts, skeleton):
    rotation_tensor = torch.from_numpy(rotation.astype(np.float32))
    root_tensor = torch.from_numpy(root.astype(np.float32))
    with torch.no_grad():
        global_rot, positions, _ = skeleton.fk(rotation_tensor, root_tensor)
    return {'local_rot_mats': rotation_tensor.numpy(), 'global_rot_mats': global_rot.numpy(),
            'posed_joints': positions.numpy(), 'root_positions': root_tensor.numpy(),
            'foot_contacts': contacts.astype(bool)}


def repeat_motion(data, displacement, repeats):
    out = {}
    for name, array in data.items():
        if name in ('posed_joints', 'root_positions'):
            out[name] = np.concatenate([array + displacement * i for i in range(repeats)])
        else:
            out[name] = np.concatenate([array] * repeats)
    return out


def shortlist(source, blend, config):
    names, _, _ = skeleton_metadata(77)
    core_names, _, _ = skeleton_metadata(30)
    core = [names.index(name) for name in core_names if name in names]
    local = source['local_rot_mats'][:, core]
    pose = source['posed_joints'][:, core] - source['root_positions'][:, None]
    ranked = []
    for length in range(config['cycle_frames_min'], config['cycle_frames_max'] + 1):
        for start in range(config['source_start_margin_frames'], len(local) - length - blend + 1):
            end = start + length
            position_gap = rms_vectors(pose[end] - pose[start])
            rotation_gap = float(np.sqrt(np.mean(rotation_angles(local[end], local[start]) ** 2)))
            # Match full body phase, not just a repeated root height or half stride.
            score = position_gap / 0.05 + rotation_gap / 10
            ranked.append((score, start, length))
    return sorted(ranked)[:config['shortlist_per_blend']]


def speed_p95(metric):
    value = metric['foot_horizontal_speed_predicted_contact_m_s']
    return None if value is None else value['p95']


def evaluate_candidate(source, start, length, blend, mode, skeleton, config, targets, full_raw_metrics):
    rotation, root, contacts, displacement = crossfade_cycle(source, start, length, blend, mode)
    corrected = assemble(rotation, root, contacts, skeleton)
    lift = max(0, -float(corrected['posed_joints'][..., 1].min()))
    corrected['posed_joints'][..., 1] += lift
    corrected['root_positions'][..., 1] += lift
    tiled = repeat_motion(corrected, displacement, config['evaluation_repeats'])
    names, _, feet = validate_motion(tiled, config['fps'])
    screen = loop_screen(tiled, config['fps'], targets)
    after = metrics(tiled, names, feet, config['fps'])
    selected = {key: value[start:start + length].copy() for key, value in source.items()}
    before = metrics(selected, names, feet, config['fps'])
    # Fixed-mask comparison exposes effects that would be hidden by relabeling contact.
    selected['foot_contacts'] = contacts.copy()
    fixed_before = metrics(selected, names, feet, config['fps'])
    reference_speeds = {'matched_source_own_contacts': speed_p95(before),
                        'matched_source_fixed_contacts': speed_p95(fixed_before),
                        'full_source_own_contacts': speed_p95(full_raw_metrics)}
    new_speed = speed_p95(after)
    speed_limits = {key: max(value + config['foot_speed_p95_allowed_absolute_increase_m_s'], value * (1 + config['foot_speed_p95_allowed_relative_increase']))
                    for key, value in reference_speeds.items() if value is not None}
    allowed_speed = min(speed_limits.values()) if len(speed_limits) == len(reference_speeds) else None
    regression = []
    if new_speed is None or allowed_speed is None:
        regression.append('contact_support_unassessed')
    elif new_speed > allowed_speed:
        regression.append('contact_speed_materially_worse')
    if after['max_joint_ground_penetration_m'] > before['max_joint_ground_penetration_m'] + config['ground_depth_allowed_increase_m']:
        regression.append('joint_ground_penetration_worse')
    accepted = screen['screen_status'] == 'within_provisional_screen' and not regression
    # Feasibility first, then minimize skating and matching distortion.
    score = (0 if accepted else 1000) + 100 * len(screen['screen_exceedances']) + 50 * len(regression) + (new_speed if new_speed is not None else 10) * 10 + screen['next_pose_prediction_rms_m']
    record = {'source_start_frame': start, 'cycle_frames': length, 'blend_frames': blend, 'root_mode': mode,
              'cycle_displacement_m': displacement.tolist(), 'constant_ground_lift_m': lift,
              'loop_screen_repeated': screen, 'raw_selected_metrics': before, 'fixed_mask_raw_selected_metrics': fixed_before,
              'corrected_repeated_metrics': after, 'allowed_contact_speed_p95_m_s': allowed_speed,
              'contact_speed_reference_limits_m_s': speed_limits,
              'regressions': regression, 'numerically_accepted': accepted, 'selection_score': score}
    return record, corrected


def main(output):
    from kimodo.skeleton import SOMASkeleton77
    config = read(ROOT / 'benchmarks/loop-correction-v1.json')
    targets = read(ROOT / 'benchmarks/acceptance-v0.json')['targets']
    skeleton = SOMASkeleton77()
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    result = {'started_at': now(), 'source_commit': source_check(), 'config': config,
              'config_sha256': sha256(ROOT / 'benchmarks/loop-correction-v1.json'),
              'implementation_sha256': sha256(Path(__file__)),
              'acceptance_rubric_sha256': sha256(ROOT / 'benchmarks/acceptance-v0.json'), 'trials': []}
    for trial in read(ROOT / 'reports/quality-v0.json')['trials']:
        if trial['case'] != 'run_loop':
            continue
        record = read(trial['record'])
        source_path = Path(record['source_motion_file_and_hash']['path'])
        original_hash = sha256(source_path)
        with np.load(source_path, allow_pickle=False) as archive:
            source = {key: archive[key] for key in archive.files}
        candidates = []
        best = None
        for blend in config['blend_frames']:
            for phase_score, start, length in shortlist(source, blend, config):
                for mode in config['root_modes']:
                    candidate, corrected = evaluate_candidate(source, start, length, blend, mode, skeleton, config, targets, record['metrics'])
                    candidate['phase_match_score'] = phase_score
                    candidates.append(candidate)
                    if best is None or candidate['selection_score'] < best[0]['selection_score']:
                        best = candidate, corrected
        winner, corrected = best
        folder = root / f'seed-{trial["seed"]}'
        folder.mkdir(exist_ok=True)
        np.savez(folder / 'corrected.npz', **corrected)
        tiled = repeat_motion(corrected, np.array(winner['cycle_displacement_m']), 4)
        np.savez(folder / 'repeated-four-cycles.npz', **tiled)
        save(folder / 'candidates.json', candidates)
        winner.update(seed=trial['seed'], source=str(source_path), source_sha256=original_hash,
                      corrected_sha256=sha256(folder / 'corrected.npz'), full_raw_metrics=record['metrics'])
        save(folder / 'report.json', winner)
        if sha256(source_path) != original_hash:
            raise RuntimeError('Raw source changed')
        result['trials'].append(winner)
        save(root / 'summary.json', result)
        print(json.dumps({k: winner[k] for k in ('seed', 'source_start_frame', 'cycle_frames', 'root_mode', 'numerically_accepted', 'regressions')}), flush=True)
        print(winner['loop_screen_repeated'], flush=True)
    result['finished_at'] = now()
    save(root / 'summary.json', result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New directory; existing studies are never overwritten')
    main(parser.parse_args().output)
