"""Prepare an unapproved developer-review packet from a completed target audit."""
from __future__ import annotations

import argparse
from pathlib import Path

from strep import ROOT, read, save, sha256, now


def prepare(result_path, output):
    import numpy as np
    from safetensors.torch import load_file
    from inspect_motion import skeleton_metadata
    result_path, output = Path(result_path), Path(output)
    result = read(result_path)
    if result.get('schema') != 'strep-denoising-target-audit-result-v1' or result.get('status') != 'complete' or not result.get('base_unchanged') or not result.get('input_files_unchanged'):
        raise ValueError('A completed, unchanged-base target audit is required')
    if output.exists():
        raise ValueError('Retain earlier packets and reviews; choose a fresh path')
    protocol_path = result_path.parent / 'protocol.json'
    if sha256(protocol_path) != result['protocol_sha256']:
        raise ValueError('Protocol changed')
    protocol = read(protocol_path)
    for name, expected in result['inputs_sha256'].items():
        if sha256(name) != expected:
            raise ValueError('Original audit input changed')
    folder = (ROOT / 'reports/action-jobs' / protocol['job']).resolve()
    if folder.parent != (ROOT / 'reports/action-jobs').resolve():
        raise ValueError('Invalid source action job')
    checkpoint = ROOT / 'models/checkpoints/Kimodo-SOMA-RP-v1.1/stats/motion/body'
    mean, std = np.load(checkpoint / 'mean.npy'), np.load(checkpoint / 'std.npy')
    names, _, _ = skeleton_metadata(77)
    labels = ['LeftFoot', 'LeftToeBase', 'RightFoot', 'RightToeBase']
    packet = {'schema': 'strep-native-target-review-draft-v1', 'created_at': now(),
              'audit_result': str(result_path.resolve()), 'audit_result_sha256': sha256(result_path),
              'review_type': 'developer review first; not blind animator release review',
              'reviewer': None, 'rights_evidence': None, 'training_admitted': False, 'quality_approved': False,
              'instructions': 'Review each original clip at the listed segment and disagreement times. Numerical reconstruction is not quality approval. Supply reviewed corrections, contact labels, rights evidence and measured cleanup time before training admission.',
              'items': []}
    for target in result['targets']:
        path = Path(target['target_file'])
        if sha256(path) != target['target_sha256']:
            raise ValueError('Encoded target changed')
        features = load_file(str(path))['clean_features'][0].numpy()
        derived = (features[:, -4:] * np.sqrt(std[-4:] ** 2 + 1e-5) + mean[-4:]) > .5
        take = (folder / 'takes' / f"{target['case']}-seed-{target['source_seed']}").resolve()
        if take.parent != folder / 'takes':
            raise ValueError('Invalid source take')
        start, end = target['source_start_frame'], target['source_end_frame_exclusive']
        source = take / 'motion.npz'
        with np.load(source, allow_pickle=False) as archive:
            predicted = archive['foot_contacts'][start:end][:, [0, 1, 3, 4]] > .5
            positions = archive['posed_joints'][start:end]
        if derived.shape != predicted.shape:
            raise ValueError('Contact clock/layout mismatch')
        differences = []
        for frame, channel in np.argwhere(derived != predicted):
            differences.append({'source_frame': int(start + frame), 'source_seconds': float((start + frame) / 30),
                                'joint': labels[channel], 'model_contact': bool(predicted[frame, channel]),
                                'pose_velocity_contact': bool(derived[frame, channel]),
                                'source_joint_position_m': positions[frame, names.index(labels[channel])].tolist(),
                                'reviewed_contact': None})
        if len(differences) != target['original_contact_difference_count']:
            raise ValueError('Contact comparison differs from archived audit')
        preview = take / 'soma.glb'
        if not preview.is_file():
            raise ValueError('Original native preview is unavailable')
        packet['items'].append({'id': target['id'], 'prompt': target['prompt'],
                                'source_start_frame': start, 'source_end_frame_exclusive': end, 'fps': 30,
                                'source_motion': str(source), 'source_motion_sha256': sha256(source),
                                'source_preview': str(preview), 'source_preview_sha256': sha256(preview),
                                'encoded_target': str(path.resolve()), 'encoded_target_sha256': sha256(path),
                                'contact_disagreements': differences,
                                'semantic_review': None, 'motion_quality_review': None, 'contact_schedule_review': None,
                                'correction_file': None, 'correction_sha256': None, 'cleanup_seconds': None,
                                'decision': 'unreviewed', 'notes': ''})
    save(output, packet)
    return packet


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('result', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    packet = prepare(args.result, args.output)
    print(f"Prepared {len(packet['items'])} unreviewed segments; training admission remains false")
