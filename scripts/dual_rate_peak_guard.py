"""Joint rate envelopes that retain both reference excess and absolute peaks."""
import numpy as np
from sample_rate_peak_guard import SampleRatePeakGuard
from absolute_rate_peaks import compare


class DualRatePeakGuard(SampleRatePeakGuard):
    def __init__(self, source, caps, columns, **kwargs):
        super().__init__(source, caps, columns, **kwargs)
        self.source = [np.asarray(v, float).copy() for v in source]
        self.absolute = [v.max(axis=0) for v in self.source]
        self.absolute_reserve = [np.minimum(.1*p, 1e-4*s) for p, s in zip(self.absolute, self.scales)]

    def envelopes(self, *, proposal=False):
        return [np.minimum(cap+self.cap_tolerance+limit-(reserve if proposal else 0),
                           absolute-(absolute_reserve if proposal else 0))
            for cap, limit, reserve, absolute, absolute_reserve in
            zip(self.caps, self.allowed, self.reserve, self.absolute, self.absolute_reserve)]

    def sample_margins(self, values, *, proposal=False):
        self.peaks(values)
        ids = self.columns
        return np.concatenate([((ceiling[:, ids]-np.asarray(value)[:, ids]+self.guard_tolerance)/scale).ravel()
            for ceiling, value, scale in zip(self.envelopes(proposal=proposal), values, self.scales)])

    def margins(self, values, *, proposal=False):
        self.peaks(values)
        return np.concatenate([((ceiling-value+self.guard_tolerance)/scale).min(axis=0)
            for ceiling, value, scale in zip(self.envelopes(proposal=proposal), values, self.scales)])

    def report(self, values):
        result = super().report(values)
        absolute = compare(self.source, values, tolerance=self.guard_tolerance)
        result.update(absolute_peak_guard=absolute,
            dual_peak_guard_pass=result['per_joint_peak_guard_pass'] and absolute['absolute_peak_guard_pass'])
        return result
