"""Validate source motion and export an offline skeleton viewer and measured proxies."""
from __future__ import annotations

import argparse
import ast
import csv
import json
from pathlib import Path
import numpy as np

from strep import ROOT, save, sha256


def skeleton_metadata(joint_count):
    cls = {30: 'SOMASkeleton30', 77: 'SOMASkeleton77'}.get(joint_count)
    if cls is None:
        raise ValueError(f'Unsupported baseline skeleton: {joint_count} joints')
    tree = ast.parse((ROOT / 'vendor/kimodo/kimodo/skeleton/definitions.py').read_text())
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls)
    fields = {}
    for field in node.body:
        if isinstance(field, ast.Assign) and isinstance(field.targets[0], ast.Name):
            try:
                fields[field.targets[0].id] = ast.literal_eval(field.value)
            except (ValueError, TypeError):
                pass
    pairs = fields['bone_order_names_with_parents']
    names = [p[0] for p in pairs]
    parents = [-1 if p is None else names.index(p) for _, p in pairs]
    feet = fields['left_foot_joint_names'] + fields['right_foot_joint_names']
    return names, parents, feet


def validate_motion(data, fps):
    if not np.isfinite(fps) or fps <= 0:
        raise ValueError('FPS must be positive and finite')
    for key in ('posed_joints', 'local_rot_mats', 'global_rot_mats', 'root_positions', 'foot_contacts'):
        if key not in data:
            raise ValueError(f'Missing motion array: {key}')
        if not np.issubdtype(data[key].dtype, np.number) and data[key].dtype != bool:
            raise ValueError(f'Non-numeric array: {key}')
        if not np.isfinite(data[key]).all():
            raise ValueError(f'Non-finite array: {key}')
    joints = data['posed_joints']
    if joints.ndim != 3 or joints.shape[-1] != 3 or len(joints) < 2:
        raise ValueError('Expected at least two frames of [T,J,3] joints')
    frames, count, _ = joints.shape
    names, parents, feet = skeleton_metadata(count)
    if data['root_positions'].shape != (frames, 3):
        raise ValueError('Root trajectory frame/shape mismatch')
    contacts = data['foot_contacts']
    if contacts.shape not in ((frames, 4), (frames, len(feet))):
        raise ValueError('Unknown contact layout')
    if np.any((contacts < 0) | (contacts > 1)):
        raise ValueError('Foot contacts outside [0,1]')
    for key in ('local_rot_mats', 'global_rot_mats'):
        matrices = data[key]
        if matrices.shape != (frames, count, 3, 3):
            raise ValueError(f'Rotation frame/shape mismatch: {key}')
        if np.max(np.abs(matrices @ matrices.swapaxes(-1, -2) - np.eye(3))) > 0.01:
            raise ValueError(f'Non-orthogonal rotations: {key}')
        if np.max(np.abs(np.linalg.det(matrices) - 1)) > 0.01:
            raise ValueError(f'Improper rotations: {key}')
    if contacts.shape[1] == 4:
        feet = ['LeftFoot', 'LeftToeBase', 'RightFoot', 'RightToeBase']
    return names, parents, feet


def summarize(values):
    return None if not len(values) else {'mean': float(np.mean(values)), 'p95': float(np.percentile(values, 95)), 'max': float(np.max(values))}


def contact_events(contacts, labels, fps):
    result = []
    for channel, name in enumerate(labels):
        flags = np.r_[False, contacts[:, channel] >= 0.5, False].astype(int)
        starts = np.flatnonzero(np.diff(flags) == 1)
        ends = np.flatnonzero(np.diff(flags) == -1)
        result.extend({'joint': name, 'start_frame': int(a), 'end_frame_exclusive': int(b),
                       'start_seconds': float(a / fps), 'end_seconds_exclusive': float(b / fps),
                       'provenance': 'model_contact_channel_not_independent_annotation'} for a, b in zip(starts, ends))
    return result


def metrics(data, names, feet, fps):
    positions = data['posed_joints'][:, [names.index(n) for n in feet], :]
    speed = np.linalg.norm(np.diff(positions[:, :, [0, 2]], axis=0), axis=-1) * fps
    height_mask = (positions[:-1, :, 1] < 0.05) & (positions[1:, :, 1] < 0.05)
    predicted = (data['foot_contacts'][:-1] >= 0.5) & (data['foot_contacts'][1:] >= 0.5)
    depth = np.maximum(-data['posed_joints'][:, :, 1], 0)
    return {
        'foot_horizontal_speed_height_proxy_m_s': summarize(speed[height_mask]),
        'height_proxy_foot_intervals': int(height_mask.sum()),
        'foot_horizontal_speed_predicted_contact_m_s': summarize(speed[predicted]),
        'predicted_contact_foot_intervals': int(predicted.sum()),
        'max_joint_ground_penetration_m': float(depth.max()),
        'max_joint_depth_integral_m_s': float(np.trapezoid(depth.max(axis=1), dx=1/fps)),
        'root_displacement_xyz_m': (data['root_positions'][-1] - data['root_positions'][0]).tolist(),
        'mesh_penetration': None, 'action_correctness': None, 'rig_transfer': None,
        'limitations': 'Height and predicted-contact masks are proxies; joint penetration is not mesh collision; no scene, interaction, import, or animator scores.'
    }


def inspect_motion(source, destination, fps, provenance):
    source, destination = Path(source), Path(destination)
    if destination.resolve() == source.parent.resolve():
        raise ValueError('Inspection must go into a separate derived directory')
    with np.load(source, allow_pickle=False) as archive:
        data = {k: archive[k] for k in archive.files}
    derivations = []
    if provenance == 'upstream_example_not_generated_here':
        # Old bundled examples omit local rotations and root positions. Derive
        # only for explicitly labeled legacy inspection, never fix generated output silently.
        if 'local_rot_mats' not in data and 'global_rot_mats' in data:
            _, parents, _ = skeleton_metadata(data['posed_joints'].shape[1])
            global_rots = data['global_rot_mats']
            local = global_rots.copy()
            for joint, parent in enumerate(parents):
                if parent >= 0:
                    local[:, joint] = global_rots[:, parent].swapaxes(-1, -2) @ global_rots[:, joint]
            data['local_rot_mats'] = local
            derivations.append('local rotations derived from global rotations and pinned joint hierarchy')
        if 'root_positions' not in data:
            data['root_positions'] = data['posed_joints'][:, 0].copy()
            derivations.append('pelvis trajectory derived from joint zero Hips')
    names, parents, feet = validate_motion(data, fps)
    destination.mkdir(parents=True, exist_ok=True)
    if derivations:
        np.savez(destination / 'legacy-derived.npz', **data)
    report = {'source': str(source.resolve()), 'source_sha256': sha256(source), 'provenance': provenance,
              'frames': len(data['posed_joints']), 'fps': fps, 'fps_source': 'explicit_argument_not_inferred_from_NPZ',
              'joints': len(names), 'contact_labels': feet, 'derivations': derivations,
              'metrics': metrics(data, names, feet, fps)}
    save(destination / 'report.json', report)
    save(destination / 'contacts.json', contact_events(data['foot_contacts'], feet, fps))
    with (destination / 'root-motion.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f); writer.writerow(['frame', 'seconds', 'pelvis_x_m', 'pelvis_y_m', 'pelvis_z_m'])
        for frame, position in enumerate(data['root_positions']):
            writer.writerow([frame, frame / fps, *position])
    payload = {'report': report, 'names': names, 'parents': parents,
               'positions': np.round(data['posed_joints'], 5).tolist()}
    template = (ROOT / 'scripts' / 'viewer.html').read_text(encoding='utf-8')
    encoded = json.dumps(payload, allow_nan=False).replace('<', '\\u003c')
    (destination / 'preview.html').write_text(template.replace('__MOTION_DATA__', encoded), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fps', type=float, required=True)
    parser.add_argument('--provenance', required=True, choices=['upstream_example_not_generated_here', 'generated_baseline', 'generated_original_precision_offload_experiment', 'synthetic_test'])
    args = parser.parse_args()
    inspect_motion(args.source, args.output, args.fps, args.provenance)
