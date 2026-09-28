"""Compare single-prompt and explicitly timed native kneel development trials."""
import argparse
from pathlib import Path

import numpy as np

from compare_kneel_origins import verified
from inspect_motion import skeleton_metadata
from strep import now, read, save, sha256


def pause_measures(trace, motion, start=60, end=90, fps=30):
    """Continuous diagnostics; no new semantic or release pass thresholds."""
    if len(trace['trace']) != len(motion['posed_joints']) or not 0 <= start < end <= len(trace['trace']):
        raise ValueError('Trace/window does not match native motion')
    coverage = sum(max(0, min(end, r['end_frame_exclusive']) - max(start, r['start_frame']))
                   for r in trace['kneeling_proxy_intervals'])
    names, _, _ = skeleton_metadata(motion['posed_joints'].shape[1])
    joints = motion['posed_joints'][start:end].astype(float)
    hip = joints[:, names.index('Hips')]
    torso = joints[:, names.index('Chest')] - hip
    lengths = np.linalg.norm(torso, axis=1)
    if np.any(lengths < 1e-8):
        raise ValueError('Degenerate torso direction')
    angles = np.degrees(np.arccos(np.clip(torso[:, 1] / lengths, -1., 1.)))
    speed = np.linalg.norm(np.diff(hip, axis=0), axis=1) * fps
    return dict(start_frame=start, end_frame_exclusive=end,
                sustained_kneeling_proxy_frames=coverage, sustained_kneeling_proxy_fraction=coverage/(end-start),
                torso_from_vertical_p95_degrees=float(np.percentile(angles, 95)),
                pelvis_speed_p95_m_s=float(np.percentile(speed, 95)),
                scope='Fixed 2–3s comparison window. Only timed requests explicitly demand this pause timing. '
                      'Knee posture, torso tilt and pelvis speed are proxies, not confirmed contact or action correctness.')


def run(single, timed, output):
    if output.exists():
        raise ValueError('Preserve previous comparisons')
    sc, sr = verified(single)
    tc, tr = verified(timed)
    if sc['model_and_sampling'] != tc['model_and_sampling']:
        raise ValueError('Checkpoint or sampling configuration changed')
    if [r['id'] for r in sr] != [r['id'] for r in tr] or len(sr) != 8:
        raise ValueError('Paired populations changed')
    rows, inputs = [], {}
    for condition, folder, source_rows in [('single', single, sr), ('timed', timed, tr)]:
        inputs[str(folder / 'completion.json')] = sha256(folder / 'completion.json')
        for row in source_rows:
            trace_path = folder / row['id'] / 'posture.json'
            trace = read(trace_path)
            path = Path(trace['source'])
            if sha256(path) != trace['source_sha256']:
                raise ValueError('Native source changed')
            with np.load(path, allow_pickle=False) as z:
                motion = dict(z)
            evidence_path = path.parent / 'evidence.json'
            evidence = read(evidence_path)
            timeline = read(path.parent / 'timeline.json')['segments']
            expected_bounds = [(0, 60), (60, 90), (90, 180)] if condition == 'timed' else [(0, 180)]
            if [(s['start_frame'], s['end_frame_exclusive']) for s in timeline] != expected_bounds:
                raise ValueError('Unexpected conditioning schedule')
            for p in [trace_path, path, evidence_path, path.parent / 'timeline.json']:
                inputs[str(p)] = sha256(p)
            rows.append(dict(experiment=condition, seed=row['seed'], guide=row['condition'],
                order_proxy=row['upright_kneel_upright_proxy_present'],
                starts_upright=row['sustained_upright_start'], ends_upright=row['sustained_upright_end'],
                pause=pause_measures(trace, motion), floor_max_m=row['mesh_floor_max_m'],
                foot_speed_proxies=row['foot_speed_proxies'], guide_audit=row['guide_audit'],
                requested_transition_diagnostics=evidence['sequence'], native_sha256=sha256(path)))
    output.mkdir(parents=True)
    summary = dict(at=now(), inputs=inputs, rows=rows, implementation_sha256=sha256(Path(__file__)),
                   quality_approved=False, human_review=None,
                   scope='Four-seed development comparison. Segmentation changes text conditioning and timing; '
                         'pose origin is canonical in both studies. Continuous diagnostics, no new acceptance threshold. '
                         'Complete engine proofs retained by both source audits; no held-out/visual/human approval.')
    save(output / 'comparison.json', summary)
    lines = ['# Single-prompt versus timed phases', '',
             '| Method | Seed | Ordered posture proxy | Kneeling coverage in 2–3s | Floor depth (mm) |',
             '|---|---:|---|---:|---:|']
    for row in rows:
        lines.append(f"| {row['experiment']} / {row['guide']} | {row['seed']} | {row['order_proxy']} | "
                     f"{row['pause']['sustained_kneeling_proxy_fraction']:.0%} | {row['floor_max_m']*1000:.2f} |")
    lines += ['', summary['scope'], '', 'The 2–3s pause is explicitly requested only in the timed condition. '
              'Matching pose intervals does not establish a believable lowering motion, forward step or natural pause.']
    (output / 'comparison.md').write_text('\n'.join(lines) + '\n', encoding='utf8')
    print({method: sum(r['order_proxy'] for r in rows if (r['experiment'], r['guide']) == method)
           for method in [('single', 'baseline'), ('single', 'upright-start'), ('timed', 'baseline'), ('timed', 'upright-start')]})


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('single', 'timed', 'output'):
        p.add_argument(name, type=Path)
    a = p.parse_args()
    run(a.single.resolve(), a.timed.resolve(), a.output.resolve())
