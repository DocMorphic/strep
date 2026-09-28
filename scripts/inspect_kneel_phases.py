"""Native SOMA posture diagnostics; deliberately not an action/realism classifier."""
import argparse
from pathlib import Path

import numpy as np

from inspect_motion import validate_motion
from strep import now, save, sha256


# Fixed before running the paired guide experiment. These are development
# proxies for the native SOMA scale, not transferable release thresholds.
RULES = dict(standing_pelvis_min_m=.8, standing_knee_flexion_max_deg=35.,
             kneeling_knee_height_max_m=.15, kneeling_knee_flexion_min_deg=85.,
             minimum_dwell_s=.3)


def intervals(mask, minimum_frames):
    changes = np.diff(np.r_[False, mask, False].astype(int))
    return [{'start_frame': int(a), 'end_frame_exclusive': int(b)}
            for a, b in zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1))
            if b - a >= minimum_frames]


def summarize_trace(pelvis, knees, flexion, fps):
    pelvis, knees, flexion = map(lambda x: np.asarray(x, dtype=float), (pelvis, knees, flexion))
    if (not np.isfinite(fps) or fps <= 0 or pelvis.ndim != 1 or len(pelvis) < 2
            or knees.shape != (len(pelvis), 2) or flexion.shape != knees.shape
            or not all(np.isfinite(v).all() for v in (pelvis, knees, flexion))):
        raise ValueError('Invalid posture trace')
    dwell = max(1, int(np.ceil(RULES['minimum_dwell_s'] * fps)))
    standing = ((pelvis >= RULES['standing_pelvis_min_m'])
                & (flexion <= RULES['standing_knee_flexion_max_deg']).all(axis=1))
    kneeling = ((knees <= RULES['kneeling_knee_height_max_m']).all(axis=1)
                & (flexion >= RULES['kneeling_knee_flexion_min_deg']).all(axis=1))
    upright_runs, kneel_runs = intervals(standing, dwell), intervals(kneeling, dwell)
    start = next((r for r in upright_runs if r['start_frame'] == 0), None)
    end = next((r for r in upright_runs if r['end_frame_exclusive'] == len(pelvis)), None)
    middle = [r for r in kneel_runs if start and end
              and r['start_frame'] >= start['end_frame_exclusive']
              and r['end_frame_exclusive'] <= end['start_frame']]
    return dict(rules=RULES.copy(), minimum_dwell_frames=dwell,
                standing_proxy_intervals=upright_runs, kneeling_proxy_intervals=kneel_runs,
                sustained_upright_start=start is not None, sustained_upright_end=end is not None,
                upright_kneel_upright_proxy_present=bool(middle),
                matched_middle_intervals=middle, action_correctness=None,
                scope='Native SOMA Y-up posture proxies only. A matching order does not establish '
                      'continuous lowering, upright torso, a forward step, naturalness or contact. '
                      'Fast or stylized correct actions can miss these fixed development proxies.')


def inspect(source, output, fps=30.):
    if output.exists():
        raise ValueError('Preserve earlier diagnostics; choose a fresh output')
    digest = sha256(source)
    with np.load(source, allow_pickle=False) as archive:
        motion = dict(archive)
    names, _, _ = validate_motion(motion, fps)
    if len(names) != 77:
        raise ValueError('This development diagnostic is calibrated only for SOMA77')
    joints = motion['posed_joints'].astype(float)
    knees, flexions = [], []
    for side in ('Left', 'Right'):
        hip, knee, ankle = [joints[:, names.index(side + suffix)] for suffix in ('Leg', 'Shin', 'Foot')]
        thigh, shin = hip - knee, ankle - knee
        denom = np.linalg.norm(thigh, axis=1) * np.linalg.norm(shin, axis=1)
        if np.any(denom < 1e-10):
            raise ValueError('Degenerate leg; knee angle is undefined')
        flexions.append(180. - np.degrees(np.arccos(np.clip(np.sum(thigh * shin, axis=1) / denom, -1., 1.))))
        knees.append(knee[:, 1])
    pelvis = joints[:, names.index('Hips'), 1]
    knees, flexions = np.stack(knees, axis=1), np.stack(flexions, axis=1)
    result = summarize_trace(pelvis, knees, flexions, fps)
    if sha256(source) != digest:
        raise ValueError('Source changed during inspection')
    result.update(at=now(), source=str(source.resolve()), source_sha256=digest, fps=fps,
                  frames=len(joints), implementation_sha256=sha256(Path(__file__)),
                  quality_approved=False, human_review=None,
                  trace=[dict(frame=i, time_s=i / fps, pelvis_y_m=float(pelvis[i]),
                              knee_y_m=dict(zip(('Left', 'Right'), knees[i].tolist())),
                              knee_flexion_degrees=dict(zip(('Left', 'Right'), flexions[i].tolist())))
                         for i in range(len(joints))])
    save(output, result)
    print({k: result[k] for k in ('frames', 'sustained_upright_start', 'sustained_upright_end',
                                 'upright_kneel_upright_proxy_present')})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--fps', type=float, default=30.)
    args = parser.parse_args()
    inspect(args.source, args.output, args.fps)
