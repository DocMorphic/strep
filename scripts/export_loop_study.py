"""Export and verify loop candidates; preserve failed quality screens in the gallery."""
import argparse
import contextlib
import io
import json
from pathlib import Path

import numpy as np
import torch

from strep import ROOT, read, save, sha256, now
from correct_loops import repeat_motion
from evaluate_grid import loop_screen
from inspect_motion import skeleton_metadata, inspect_motion, validate_motion


def main(folder):
    from kimodo.skeleton import SOMASkeleton77
    from kimodo.exports.bvh import save_motion_bvh, bvh_to_kimodo_motion
    folder = Path(folder).resolve()
    summary = read(folder / 'summary.json')
    skeleton = SOMASkeleton77()
    names, parents, feet = skeleton_metadata(77)
    targets = read(ROOT / 'benchmarks/acceptance-v0.json')['targets']
    viewer = {'fps': 30, 'parents': parents, 'names': names, 'trials': []}
    for trial in summary['trials']:
        path = folder / f'seed-{trial["seed"]}'
        with np.load(path / 'corrected.npz', allow_pickle=False) as archive:
            corrected = {key: archive[key] for key in archive.files}
        validate_motion(corrected, 30)
        if sha256(trial['source']) != trial['source_sha256']:
            raise RuntimeError('Raw source changed')
        with np.load(trial['source'], allow_pickle=False) as archive:
            raw = {key: archive[key] for key in archive.files}
        start, length = trial['source_start_frame'], trial['cycle_frames']
        crop = {key: value[start:start + length].copy() for key, value in raw.items()}
        raw_displacement = raw['root_positions'][start + length] - raw['root_positions'][start]
        raw_displacement[1] = 0
        repeated_raw = repeat_motion(crop, raw_displacement, 4)
        repeated_corrected = repeat_motion(corrected, np.array(trial['cycle_displacement_m']), 4)
        # Full-joint FK agreement protects against a wrong skeleton/rest-pose assumption.
        with torch.no_grad():
            _, source_fk, _ = skeleton.fk(torch.from_numpy(raw['local_rot_mats']), torch.from_numpy(raw['root_positions']))
        source_fk_error = float(np.linalg.norm(source_fk.numpy() - raw['posed_joints'], axis=-1).max())
        if source_fk_error > 1e-4:
            raise RuntimeError('Source motion disagrees with the assumed skeleton')
        bvh_path = path / 'corrected.bvh'
        save_motion_bvh(bvh_path, torch.from_numpy(corrected['local_rot_mats']),
                        torch.from_numpy(corrected['root_positions']), skeleton=skeleton, fps=30, standard_tpose=True)
        restored, fps = bvh_to_kimodo_motion(bvh_path, skeleton=skeleton, standard_tpose=True)
        restored_np = {key: value.detach().cpu().numpy() for key, value in restored.items()}
        error = float(np.linalg.norm(restored_np['posed_joints'] - corrected['posed_joints'], axis=-1).max())
        root_error = float(np.abs(restored_np['root_positions'] - corrected['root_positions']).max())
        if len(restored_np['posed_joints']) != length or abs(fps - 30) > 0.001 or error > 1e-4:
            raise RuntimeError('BVH round-trip failed')
        # BVH has no contact channels. Do not use re-inferred labels for improvement claims.
        restored_np['foot_contacts'] = corrected['foot_contacts'].copy()
        export_screen = loop_screen(repeat_motion(restored_np, np.array(trial['cycle_displacement_m']), 3), 30, targets)
        if trial['numerically_accepted'] and export_screen['screen_status'] != 'within_provisional_screen':
            raise RuntimeError('Accepted candidate lost loop-screen validity after export')
        exported = {'checked_at': now(), 'bvh_sha256': sha256(bvh_path), 'source_fk_max_joint_error_m': source_fk_error,
                    'roundtrip_max_joint_error_m': error, 'roundtrip_max_root_coordinate_error_m': root_error,
                    'frames': length, 'fps': fps, 'loop_screen_after_bvh_roundtrip': export_screen,
                    'root_cycle_displacement_m': trial['cycle_displacement_m'],
                    'contact_provenance': 'Inherited source predictions, union of source intervals during blend. Not independently verified.'}
        save(path / 'export-validation.json', exported)
        with contextlib.redirect_stdout(io.StringIO()):
            inspect_motion(path / 'repeated-four-cycles.npz', path / 'inspection', 30, 'deterministically_corrected_four_cycles_source_contacts_inherited')
        events = read(path / 'inspection/contacts.json')
        for event in events:
            event['provenance'] = exported['contact_provenance']
        save(path / 'inspection/contacts.json', events)
        trial['export_validation'] = exported
        trial['selected_raw_loop_screen'] = loop_screen(repeated_raw, 30, targets)
        # Diagnostic attribution for material sliding regressions.
        foot_index = [names.index(name) for name in feet]
        speed = np.linalg.norm(np.diff(repeated_corrected['posed_joints'][:, foot_index][:, :, [0, 2]], axis=0), axis=-1) * 30
        contact = repeated_corrected['foot_contacts'][:-1] & repeated_corrected['foot_contacts'][1:]
        near_blend = np.arange(len(speed)) % length < trial['blend_frames']
        def p95(mask):
            values = speed[contact & mask[:, None]]
            return None if not len(values) else float(np.percentile(values, 95))
        trial['sliding_attribution'] = {'blend_interval_contact_speed_p95_m_s': p95(near_blend),
                                        'outside_blend_contact_speed_p95_m_s': p95(~near_blend),
                                        'interpretation': 'Crossfade changes stance geometry; constant-speed root also changes world foot velocity. No stance IK is applied in this pass.'}
        save(path / 'report.json', trial)
        viewer['trials'].append({'seed': trial['seed'], 'frames_per_cycle': length, 'source_start_frame': start,
                                'root_mode': trial['root_mode'], 'accepted': trial['numerically_accepted'],
                                'regressions': trial['regressions'],
                                'raw_positions': repeated_raw['posed_joints'].round(5).tolist(),
                                'corrected_positions': repeated_corrected['posed_joints'].round(5).tolist(),
                                'raw_seam_cm': trial['selected_raw_loop_screen']['next_pose_prediction_rms_m'] * 100,
                                'corrected_seam_cm': trial['loop_screen_repeated']['next_pose_prediction_rms_m'] * 100,
                                'raw_speed_cm_s': trial['raw_selected_metrics']['foot_horizontal_speed_predicted_contact_m_s']['p95'] * 100,
                                'corrected_speed_cm_s': trial['corrected_repeated_metrics']['foot_horizontal_speed_predicted_contact_m_s']['p95'] * 100})
        print(f'Seed {trial["seed"]}: BVH verified, max joint error {error:.8f} m; candidate accepted={trial["numerically_accepted"]}', flush=True)
    summary['exporter_sha256'] = sha256(Path(__file__))
    summary['export_finished_at'] = now()
    save(folder / 'summary.json', summary)
    template = (ROOT / 'scripts/loop-comparison.html').read_text(encoding='utf-8')
    (folder / 'comparison.html').write_text(template.replace('__LOOP_STUDY__', json.dumps(viewer).replace('<', '\\u003c')), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    main(parser.parse_args().folder)
