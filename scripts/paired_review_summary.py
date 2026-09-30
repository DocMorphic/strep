"""Translate exact sampled pair evidence for the Studio scene viewer."""
import math


def partner_summary(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError('Completed sampled geometry rows required')
    frames = [r['frame'] for r in rows]
    if any(type(f) not in (int, float) or not math.isfinite(f) or f < 0 for f in frames) or any(b <= a for a, b in zip(frames, frames[1:])):
        raise ValueError('Distinct increasing sample times required')
    values = [r['candidate_depth_m'] for r in rows]
    if any(type(d) not in (int, float) or not math.isfinite(d) or d < 0 for d in values):
        raise ValueError('Finite nonnegative penetration depths required')
    samples = [dict(frame=f, max_depth_m=d) for f, d in zip(frames, values)]
    return dict(tolerance_m=.005, frames_checked=frames,
                pairs=[dict(actors=['A', 'B'], frames=samples, max_depth_m=max(values), frames_over_tolerance=sum(d > .005 for d in values))],
                quality_approved=False, scope='Complete skin vertex queries at these recorded times only; no continuous collision, full-clip or human quality approval.')
