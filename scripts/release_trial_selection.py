"""Deterministic pre-fit joint and derivative-sample selection."""
import numpy as np
from scipy.spatial.transform import Rotation


def peak_joint(local, editable_nodes):
    local = np.asarray(local, float)
    if local.ndim != 4 or local.shape[2:] != (4, 4) or len(local) < 2 or not np.isfinite(local).all():
        raise ValueError('Finite frame/node local transforms required')
    delta = local[:-1, :, :3, :3].transpose(0, 1, 3, 2)@local[1:, :, :3, :3]
    angles = Rotation.from_matrix(delta.reshape(-1, 3, 3)).magnitude().reshape(delta.shape[:2])
    frame, node = np.unravel_index(angles.argmax(), angles.shape)
    return dict(node=int(node), step_end_frame=int(frame+1), degrees=float(np.degrees(angles[frame, node])),
        protected_nodes=[int(node)] if int(node) in set(editable_nodes) else [],
        policy='Retain the largest held local-rotation-step joint throughout the clip if editable; an uneditable peak already has fixed local rotation.')


def derivative_frames(dynamics, count):
    if type(count) is not int or count < 3: raise ValueError('At least three frames required')
    ranked = []
    for side in dynamics['candidate']['feet']:
        tracks = [dynamics[v]['feet'][side] for v in ['input', 'prior', 'candidate']]
        if len({len(t['releases']) for t in tracks}) != 1: raise ValueError('Release population differs')
        for raw, prior, held in zip(*(t['releases'] for t in tracks)):
            if len({r['release_frame'] for r in [raw, prior, held]}) != 1: raise ValueError('Release clocks differ')
            centers = np.asarray(held['acceleration_frames'], dtype=int)
            if not len(centers) or centers.min() < 1 or centers.max() > count-2: raise ValueError('Invalid release acceleration frames')
            acceleration = np.asarray(tracks[2]['acceleration_m_s2'])[centers-1]
            peak = int(centers[np.linalg.norm(acceleration, axis=1).argmax()])
            excess = held['acceleration_max_m_s2']-max(raw['acceleration_max_m_s2'], prior['acceleration_max_m_s2'])-1e-5
            ranked.append((excess, side, held['release_frame'], peak))
    worst = max(ranked) if ranked else (0., None, None, count//2)
    peak = worst[-1]
    return dict(frames=sorted({0, peak, min(peak+1, count-1), count//2, count-1}),
        selected_release_side=worst[1], selected_release_frame=worst[2], selected_peak_center=peak,
        policy='Before fitting, test endpoints, midpoint and the held acceleration peak of the largest release regression plus its next sample.')
