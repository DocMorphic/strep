"""Per-joint rate-excess guards; original motion acceptance remains separate."""
import numpy as np


class RatePeakGuard:
    def __init__(self, source, caps, *, cap_tolerance=1e-5, guard_tolerance=1e-7, scales=(1., 10., 3., 100.)):
        self.caps = [np.asarray(c, float).copy() for c in caps]
        self.scales = np.asarray(scales, float)
        if (len(self.caps) != 4 or self.scales.shape != (4,) or not np.isfinite(self.scales).all()
                or np.any(self.scales <= 0) or not np.isfinite([cap_tolerance, guard_tolerance]).all()
                or min(cap_tolerance, guard_tolerance) < 0
                or any(c.ndim != 2 or not all(c.shape) or not np.isfinite(c).all() or np.any(c < 0) for c in self.caps)
                or len({c.shape[1] for c in self.caps}) != 1):
            raise ValueError('Four finite nonnegative joint-rate cap arrays and positive scales required')
        self.cap_tolerance, self.guard_tolerance = float(cap_tolerance), float(guard_tolerance)
        self.allowed = [np.maximum(p, 0) for p in self.peaks(source)]
        # Proposal-only inward reserve: never demand more than 10% of an
        # existing positive deficit, and leave already passing joints unchanged.
        self.reserve = [np.minimum(.1*p, 1e-4*s) for p, s in zip(self.allowed, self.scales)]

    def peaks(self, values):
        if len(values) != 4: raise ValueError('Four measured rate arrays required')
        result = []
        for value, cap in zip(values, self.caps):
            value = np.asarray(value, float)
            if value.shape != cap.shape or not np.isfinite(value).all() or np.any(value < 0):
                raise ValueError('Finite nonnegative measured rates matching original caps required')
            result.append((value-cap-self.cap_tolerance).max(axis=0))
        return result

    def margins(self, values, *, proposal=False):
        return np.concatenate([(limit-(reserve if proposal else 0)-peak+self.guard_tolerance)/scale
            for limit, reserve, peak, scale in zip(self.allowed, self.reserve, self.peaks(values), self.scales)])

    def report(self, values):
        peaks = self.peaks(values); rows = []
        for kind, limit, peak in zip(('position_speed', 'position_acceleration', 'angular_speed', 'angular_acceleration'), self.allowed, peaks):
            positive = np.maximum(peak, 0); change = positive-limit
            rows.append(dict(kind=kind, original_source_excess_peaks=limit.tolist(), candidate_excess_peaks=positive.tolist(),
                regressing_joints=int(np.count_nonzero(change > self.guard_tolerance)), maximum_increase=float(change.max())))
        return dict(guard_tolerance=self.guard_tolerance, per_joint_peak_guard_pass=all(r['regressing_joints'] == 0 for r in rows),
            original_motion_caps_pass=all(np.all(p <= 0) for p in peaks), rates=rows, quality_approved=False)
