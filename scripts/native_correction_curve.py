"""Complete sampled source-relative rotation bounds on native LINEAR curves.

Batch interpolation follows NativeSupportSampler's scalar quaternion rules.
Rows cover every supplied time and neighbor, not continuous-time extrema.
The caller owns immutable asset bindings, permissions and serialized acceptance.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from native_support_clock import NativeSupportSampler


def _numeric(value):
    a = np.asarray(value)
    if a.dtype.kind not in 'fiu' or not np.isfinite(a).all():
        raise ValueError('Finite real arrays required')
    return a.astype(float, copy=True)


class CorrectionCurve:
    def __init__(self, clock, reference, times, *, maximum_working_bytes=64*1024**2):
        clock = _numeric(clock); reference = _numeric(reference); times = _numeric(times)
        if (clock.ndim != 1 or not 2 <= len(clock) <= 4096 or clock[0] < 0
                or np.any(np.diff(clock) <= 0)
                or reference.ndim != 3 or reference.shape[0] != len(clock)
                or not 1 <= reference.shape[1] <= 64 or reference.shape[2] != 4
                or times.ndim != 1 or not 2 <= len(times) <= 16384
                or np.any(np.diff(times) <= 0) or times[0] < clock[0] or times[-1] > clock[-1]):
            raise ValueError('Complete matching native keys, joint quaternions and increasing in-range times required')
        # Conservative array budget; caller-owned control Jacobians are separate.
        required = 8*reference.shape[1]*(24*len(clock)+160*len(times))
        if (type(maximum_working_bytes) is not int or not 1 <= maximum_working_bytes <= 64*1024**2
                or required > maximum_working_bytes):
            raise ValueError('Complete curve workspace exhausted; no times or joints discarded')
        self.clock = clock; self.times = times; self.reference = reference
        self._quaternions(reference)
        right = np.searchsorted(clock, times, side='left')
        self.right = right
        self.left = np.maximum(right-1, 0)
        self.exact = clock[right] == times
        self.left[self.exact] = right[self.exact]
        dt = clock[right]-clock[self.left]
        self.alpha = np.divide(times-clock[self.left], dt, out=np.zeros_like(times), where=dt > 0)
        # Very short differences amplify harmless batch/scalar rounding into
        # rate errors. Retain these neighbors and use the authoritative scalar
        # sampler at both ends; do not merge clocks or relax acceptance limits.
        short = np.diff(times) < 1e-5
        self.scalar_samples = np.flatnonzero(np.r_[short, False] | np.r_[False, short])
        self.original_inverse = Rotation.from_quat(self.sample(reference).reshape(-1,4)).inv()
        for a in (self.clock, self.times, self.reference, self.left, self.right, self.exact, self.alpha, self.scalar_samples):
            a.setflags(write=False)
        self.report = dict(schema='strep-native-correction-curve-v1', native_keys=len(clock),
            joints=reference.shape[1], samples=len(times), rate_neighbors=len(times)-1,
            estimated_working_bytes=required, all_supplied_times_retained=True,
            scalar_short_interval_samples=len(self.scalar_samples),
            continuous_time_verified=False, quality_approved=False, release_approved=False)

    def _quaternions(self, value):
        q = _numeric(value)
        if q.shape != self.reference.shape or np.any(np.abs(np.linalg.norm(q, axis=-1)-1.) > 1e-5):
            raise ValueError('Complete matching near-unit XYZW native rotation keys required')
        return q

    def sample(self, candidate):
        raw = self._quaternions(candidate); q = raw.copy()
        q /= np.linalg.norm(q, axis=-1, keepdims=True)
        a, b = q[self.left], q[self.right]
        dot = np.sum(a*b, axis=-1)
        b = np.where((dot < 0)[...,None], -b, b)
        angle = np.arccos(np.clip(np.abs(dot), 0., 1.))
        t = self.alpha[:,None]
        small = angle < 1e-6
        denominator = np.where(small, 1., np.sin(angle))
        wa = np.where(small, 1.-t, np.sin((1.-t)*angle)/denominator)
        wb = np.where(small, t, np.sin(t*angle)/denominator)
        result = wa[...,None]*a+wb[...,None]*b
        result /= np.linalg.norm(result, axis=-1, keepdims=True)
        result[self.exact] = q[self.right[self.exact]]
        for i in self.scalar_samples:
            result[i] = [NativeSupportSampler.value('rotation', self.clock, raw[:,j], 'LINEAR', float(self.times[i]))
                         for j in range(raw.shape[1])]
        return result

    def evaluate(self, candidate, caps_degrees, speed_limits_degrees_s):
        joints = self.reference.shape[1]
        caps = _numeric(caps_degrees); limits = _numeric(speed_limits_degrees_s)
        if (caps.shape != (joints,) or limits.shape != (joints,)
                or np.any(caps <= 0) or np.any(caps > 180)
                or np.any(limits <= 0) or np.any(limits > 1e6)):
            raise ValueError('Explicit positive bounded original caps and speed limits for every joint required')
        correction = self.original_inverse*Rotation.from_quat(self.sample(candidate).reshape(-1,4))
        angles = np.rad2deg(correction.magnitude()).reshape(len(self.times), joints)
        # Keep the already-normalized Rotation objects, as the scalar audit
        # does. A second as_quat/from_quat normalization perturbs differences
        # across very short native/uniform-clock neighbors.
        previous = correction[:-joints]
        following = correction[joints:]
        with np.errstate(over='raise', divide='raise', invalid='raise'):
            try:
                rates = np.rad2deg((previous.inv()*following).magnitude()).reshape(-1,joints)/np.diff(self.times)[:,None]
                angular_rows = 1.-(angles/caps)**2
                speed_rows = 1.-(rates/limits)**2
            except FloatingPointError as error:
                raise ValueError('Finite representable complete curve rows required') from error
        if not all(np.isfinite(v).all() for v in (angles, rates, angular_rows, speed_rows)):
            raise ValueError('Finite complete correction values required')
        return dict(angles_degrees=angles, rates_degrees_s=rates,
                    angular_rows=angular_rows, speed_rows=speed_rows,
                    report={**self.report, 'row_sign': 'nonnegative passes supplied sampled limit'})
