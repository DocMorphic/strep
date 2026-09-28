"""Generate transparent numeric screens and an all-seed review gallery. Never certify realism."""
import html
import math
import json
from pathlib import Path

import numpy as np
from strep import ROOT, read, save, sha256, now
from inspect_motion import skeleton_metadata


def rms_vectors(values):
    return float(np.sqrt(np.mean(np.sum(values ** 2, axis=-1))))


def rotation_angles(a, b):
    delta = np.swapaxes(a, -1, -2) @ b
    cosine = np.clip((np.trace(delta, axis1=-2, axis2=-1) - 1) / 2, -1, 1)
    return np.degrees(np.arccos(cosine))


def loop_screen(data, fps, targets):
    pose = data['posed_joints'] - data['posed_joints'][:, :1]
    rotations = data['local_rot_mats']
    predicted = pose[-1] + (pose[-1] - pose[-2])
    next_rotation = rotations[-1] @ (np.swapaxes(rotations[-2], -1, -2) @ rotations[-1])
    root_velocity = np.diff(data['root_positions'], axis=0) * fps
    forward = data['global_rot_mats'][:, 0, :, 2]
    horizontal_norm = np.linalg.norm(forward[:, [0, 2]], axis=-1)
    valid_heading = bool(np.all(horizontal_norm > 0.5))
    yaw = np.unwrap(np.arctan2(forward[:, 0], forward[:, 2]))
    yaw_gap = float(abs(np.degrees(np.arctan2(np.sin(yaw[-1] - yaw[0]), np.cos(yaw[-1] - yaw[0]))))) if valid_heading else None
    next_yaw_delta = yaw[-1] + yaw[-1] - yaw[-2] - yaw[0]
    next_yaw_error = float(abs(np.degrees(np.arctan2(np.sin(next_yaw_delta), np.cos(next_yaw_delta))))) if valid_heading else None
    window = max(1, int(round(fps * 0.5)))
    trajectory = data['root_positions'][window:, [0, 2]] - data['root_positions'][:-window, [0, 2]]
    moving = np.linalg.norm(trajectory, axis=-1) / (window / fps) >= 0.2
    path_angles = np.abs(np.degrees(np.arctan2(trajectory[moving, 0], trajectory[moving, 1])))
    result = {
        'raw_root_relative_endpoint_joint_rms_m': rms_vectors(pose[-1] - pose[0]),
        'next_pose_prediction_rms_m': rms_vectors(predicted - pose[0]),
        'next_local_rotation_prediction_rms_degrees': float(np.sqrt(np.mean(rotation_angles(next_rotation, rotations[0]) ** 2))),
        'root_velocity_gap_m_s': float(np.linalg.norm(root_velocity[-1] - root_velocity[0])),
        'root_yaw_gap_degrees': yaw_gap,
        'next_root_yaw_prediction_error_degrees': next_yaw_error,
        'trajectory_heading_p95_degrees': float(np.percentile(path_angles, 95)) if len(path_angles) else None,
        'root_yaw_max_drift_degrees': float(np.max(np.abs(np.degrees(yaw - yaw[0])))) if valid_heading else None,
        'scope': 'All output joints, translation-normalized; one-frame constant-velocity extrapolation; local +Z projected root yaw. Path heading uses 0.5-second windows moving >=0.2 m/s relative to requested world +Z. Pelvis yaw oscillation is diagnostic only. No correction.'
    }
    pairs = {
        'next_pose_prediction_rms_m': 'root_translation_aligned_loop_next_pose_prediction_rms_m',
        'next_local_rotation_prediction_rms_degrees': 'loop_next_local_rotation_prediction_rms_degrees',
        'root_velocity_gap_m_s': 'loop_root_velocity_gap_m_s',
        'next_root_yaw_prediction_error_degrees': 'loop_next_root_yaw_prediction_error_degrees',
        'trajectory_heading_p95_degrees': 'run_trajectory_heading_p95_degrees',
    }
    result['screen_exceedances'] = [key for key, target in pairs.items() if result[key] is not None and result[key] > targets[target]]
    result['missing_screen_measures'] = [key for key in pairs if result[key] is None]
    result['screen_status'] = 'flagged' if result['screen_exceedances'] else 'unassessed' if result['missing_screen_measures'] else 'within_provisional_screen'
    return result


def transition_screen(data, fps):
    # Pinned unprocessed source blends frames 85..89 and starts segment B at 90.
    root = data['root_positions']
    velocity = np.diff(root, axis=0) * fps
    joints = data['posed_joints']
    transitions = []
    for frame in range(85, 92):
        transitions.append({'arrival_frame': frame,
                            'root_step_m': float(np.linalg.norm(root[frame] - root[frame - 1])),
                            'root_velocity_change_m_s': float(np.linalg.norm(velocity[frame] - velocity[frame - 1])),
                            'joint_step_rms_m': rms_vectors(joints[frame] - joints[frame - 1])})
    return {'expected_frames': 210, 'actual_frames': len(root), 'blend_frames_inclusive': [85, 89],
            'second_segment_start_frame': 90, 'fps': fps, 'boundary_samples': transitions,
            'scope': 'Pinned unprocessed two-prompt 90+120 frame sequence; velocity-change diagnostic, not physical plausibility certification.'}


def paired_scenes(trials):
    scene = next(case['evaluation_targets'] for case in read(ROOT / 'benchmarks/v0.json')['cases'] if case['id'] == 'high_five')
    names, parents, feet = skeleton_metadata(77)
    wrist = names.index('RightHand')
    pairs = []
    for seed in read(ROOT / 'benchmarks/v0.json')['seeds']:
        actors = [next((trial for trial in trials if trial['case'] == 'high_five' and trial['seed'] == seed and trial['actor'] == actor and trial['generation_status'] == 'generated_validated'), None) for actor in ('A', 'B')]
        if any(actor is None for actor in actors):
            continue
        raw, world, hashes = [], [], []
        for actor, trial in zip(('A', 'B'), actors):
            source = read(trial['record'])['source_motion_file_and_hash']
            with np.load(source['path'], allow_pickle=False) as archive:
                positions = archive['posed_joints']
            raw.append(positions)
            theta = math.radians(scene['actor_' + actor]['yaw_degrees'])
            rotation = np.array([[math.cos(theta), 0, math.sin(theta)], [0, 1, 0], [-math.sin(theta), 0, math.cos(theta)]])
            world.append(positions @ rotation.T + np.array(scene['actor_' + actor]['origin_m']))
            hashes.append(source)
        if world[0].shape != world[1].shape:
            raise ValueError('Partner frame counts or skeletons differ')
        gap = np.linalg.norm(world[0][:, wrist] - world[1][:, wrist], axis=-1)
        closest = int(np.argmin(gap))
        target_frame = int(round(scene['contact_time_s'] * 30))
        diagnostics = {'seed': seed, 'status': 'provisional_uncalibrated_wrist_proxy_not_palm_contact',
                       'wrist_gap_at_target_m': float(gap[target_frame]), 'minimum_wrist_gap_m': float(gap[closest]),
                       'minimum_gap_frame': closest, 'minimum_gap_time_s': closest / 30,
                       'native_track_max_joint_difference_m': float(np.max(np.linalg.norm(raw[0] - raw[1], axis=-1))),
                       'scene': scene, 'sources': hashes,
                       'limitations': 'Fixed provisional transforms only; no time shift, spatial fitting, palm offsets, mesh collisions or acceptance claim. Same prompt and seed, independently run.'}
        folder = ROOT / f'reports/high-five-pairs/seed-{seed}'
        save(folder / 'diagnostics.json', diagnostics)
        positions = np.concatenate(world, axis=1)
        payload = {'report': {'provenance': 'PROVISIONAL SCENE · INDEPENDENT TRACKS · WRIST PROXY ONLY',
                             'frames': len(positions), 'fps': 30, 'joints': 154,
                             'contact_labels': [actor + ':' + foot for actor in ('A', 'B') for foot in feet],
                             'metrics': diagnostics},
                   'positions': positions.round(5).tolist(), 'names': [actor + ':' + name for actor in ('A', 'B') for name in names],
                   'parents': parents + [-1 if p < 0 else p + 77 for p in parents]}
        template = (ROOT / 'scripts/viewer.html').read_text(encoding='utf-8')
        (folder / 'preview.html').write_text(template.replace('__MOTION_DATA__', json.dumps(payload).replace('<', '\\u003c')), encoding='utf-8')
        diagnostics['preview'] = str((folder / 'preview.html').relative_to(ROOT).as_posix())
        pairs.append(diagnostics)
    return pairs


def main():
    grid = read(ROOT / 'reports/grid-v0.json')
    rubric_path = ROOT / 'benchmarks/acceptance-v0.json'
    rubric = read(rubric_path)
    report = {'created_at': now(), 'grid_status': grid['status'], 'rubric_sha256': sha256(rubric_path),
              'acceptance': 'No clips certified realistic; human, collision, rig and engine checks missing.', 'trials': []}
    rows = []
    for item in grid['jobs']:
        record_path = Path(item['record'])
        record = read(record_path)
        trial = {'id': item['id'], 'case': record['case_id'], 'seed': record['seed'], 'actor': record['actor'],
                 'generation_status': record['status'], 'record': str(record_path),
                 'realism_acceptance': 'unassessed', 'human_review': None, 'independent_foot_support': None,
                 'mesh_collision': None, 'rig_transfer': None, 'engine_import': None, 'cleanup_minutes': None}
        loop_text = '—'
        if record['status'] == 'generated_validated':
            source = record['source_motion_file_and_hash']
            if sha256(source['path']) != source['sha256']:
                raise ValueError('Raw motion changed since generation')
            with np.load(source['path'], allow_pickle=False) as archive:
                data = {k: archive[k] for k in archive.files}
            trial['frames'] = len(data['posed_joints'])
            trial['metrics'] = record['metrics']
            if trial['case'] == 'run_loop':
                trial['loop_screen'] = loop_screen(data, 30, rubric['targets'])
                loop_text = f'{trial["loop_screen"]["next_pose_prediction_rms_m"] * 100:.1f} cm — {trial["loop_screen"]["screen_status"]}'
            elif trial['case'] == 'run_to_roll':
                trial['transition_screen'] = transition_screen(data, 30)
            elif trial['case'] == 'lift_box':
                trial['interaction_status'] = 'unsupported_object_output: no predicted box trajectory or attachment'
            elif trial['case'] == 'high_five':
                trial['interaction_status'] = 'unassessed: independently sampled tracks; no calibrated palm contact or partner collision scoring'
            save(record_path.parent / 'inspection/quality-screen.json', trial)
            preview = Path(record['preview_file']).relative_to(ROOT).as_posix()
            speed = trial['metrics']['foot_horizontal_speed_predicted_contact_m_s']
            slide_text = f'{speed["p95"] * 100:.1f} cm/s' if speed else 'no predicted support'
            rows.append(f'<tr><td>{html.escape(trial["case"])}</td><td>{trial["seed"]}</td><td>{trial["actor"]}</td><td>{trial["frames"] / 30:.2f}s</td><td>{slide_text}</td><td>{loop_text}</td><td><a href="/{preview}">Preview</a></td><td>Unassessed</td></tr>')
        else:
            rows.append(f'<tr><td>{html.escape(item["id"])}</td><td colspan="7">{html.escape(record["status"])}</td></tr>')
        report['trials'].append(trial)
    report['counts'] = {'actor_jobs_recorded': len(report['trials']),
                        'generated': sum(t['generation_status'] == 'generated_validated' for t in report['trials']),
                        'certified_realistic': 0}
    report['high_five_pairs'] = paired_scenes(report['trials'])
    save(ROOT / 'reports/quality-v0.json', report)
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>strep · baseline review</title>
<style>body{background:#101821;color:#e6edf3;font:16px system-ui;margin:32px}main{max-width:1300px;margin:auto}h1{font-size:28px}p{line-height:1.6;max-width:1000px;color:#b9cbd8}a{color:#7ce0cb}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:13px 10px;border-bottom:1px solid #344354;text-align:left}th{color:#7ce0cb}strong{color:#ffcd87}.scroll{overflow:auto}</style>
<main><h1>strep / all-seed baseline review</h1><p>Four cases · five fixed seeds · unprocessed motion · original-precision streamed encoder. Every recorded result is retained. <strong>No clip is certified realistic yet.</strong> Successful generation means structurally valid data.</p>
<p>Foot speed uses the model's own predicted contacts; it is a screening proxy. Loop error predicts the next root-relative pose across the boundary. Object motion is absent, partner contacts are uncalibrated, and human/mesh/rig/engine checks are pending. High-five A/B use identical prompts and seeds, not joint inference. This is an exploratory review gallery, not a blind test.</p>
<p><a href="/docs/realism-rubric.md">Acceptance rubric</a> · <a href="/reports/quality-v0.json">Full numeric report</a></p><div class="scroll"><table><thead><tr><th>Case</th><th>Seed</th><th>Actor</th><th>Duration</th><th>Contact-speed p95</th><th>Loop next-pose error</th><th>Motion</th><th>Realism</th></tr></thead><tbody>'''
    pair_links = ' · '.join(f'<a href="/{pair["preview"]}">Pair seed {pair["seed"]}</a>' for pair in report['high_five_pairs'])
    (ROOT / 'reports/baseline-review.html').write_text(page + ''.join(rows) + '</tbody></table></div><h2>High-five pairs</h2><p>Fixed provisional layout; wrist distances are uncalibrated diagnostics, not contact acceptance.</p><p>' + pair_links + '</p></main></html>', encoding='utf-8')
    print(report['counts'])


if __name__ == '__main__':
    main()
