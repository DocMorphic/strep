"""Explicit sampled constraints for the same frozen per-joint peak envelopes."""
import numpy as np
from rate_peak_guard import RatePeakGuard


class SampleRatePeakGuard(RatePeakGuard):
    def __init__(self, source, caps, columns, **kwargs):
        super().__init__(source, caps, **kwargs)
        columns = np.asarray(columns)
        if (columns.ndim != 1 or not len(columns) or columns.dtype.kind not in 'iu'
                or len(np.unique(columns)) != len(columns) or columns.min() < 0 or columns.max() >= self.caps[0].shape[1]):
            raise ValueError('Distinct affected joint columns required')
        self.columns = columns

    def sample_margins(self, values, *, proposal=False):
        self.peaks(values)  # Validate all measured arrays, including omitted columns.
        ids = self.columns
        return np.concatenate([((limit[ids]-(reserve[ids] if proposal else 0))[None, :]
            -(np.asarray(value)[:, ids]-cap[:, ids]-self.cap_tolerance)+self.guard_tolerance).ravel()/scale
            for value, cap, limit, reserve, scale in zip(values, self.caps, self.allowed, self.reserve, self.scales)])
