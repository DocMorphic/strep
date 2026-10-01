"""Conservative rate-dependency masks for native rotation-only controls."""
import numpy as np
from dual_rate_peak_guard import DualRatePeakGuard


def rate_support(parents, joints, entries, times):
    parents, joints, times = np.asarray(parents), np.asarray(joints), np.asarray(times, float)
    if (parents.ndim != 1 or parents.dtype.kind not in 'iu' or not len(parents)
            or parents.min() < -1 or parents.max() >= len(parents)
            or joints.ndim != 1 or joints.dtype.kind not in 'iu' or not len(joints)
            or joints.min() < 0 or joints.max() >= len(parents) or len(np.unique(joints)) != len(joints)
            or times.ndim != 1 or len(times) < 3 or not np.isfinite(times).all() or np.any(np.diff(times) <= 0)):
        raise ValueError('Valid hierarchy, distinct joints and increasing sample times required')
    ancestors = []
    for node in range(len(parents)):
        chain = []; parent = int(parents[node]); seen = {node}
        while parent >= 0:
            if parent in seen: raise ValueError('Cyclic hierarchy')
            seen.add(parent); chain.append(parent); parent = int(parents[parent])
        ancestors.append(chain)
    local = np.zeros((len(times), len(parents)), bool)
    for entry in entries:
        node, clock, ids = entry['node'], np.asarray(entry['clock'], float), np.asarray(entry['ids'])
        if (not isinstance(node, (int, np.integer)) or not 0 <= node < len(parents)
                or clock.ndim != 1 or len(clock) < 3 or not np.isfinite(clock).all() or np.any(np.diff(clock) <= 0)
                or ids.ndim != 1 or ids.dtype.kind not in 'iu' or not len(ids) or ids.min() < 1 or ids.max() >= len(clock)-1):
            raise ValueError('Interior editable native keys required')
        # A native rotation key has open support between its two neighbors.
        # Using every editable key conservatively includes any key whose
        # particular control basis happens to vanish or whose contact is locked.
        local[:, node] |= np.any((times[:, None] > clock[ids-1]) & (times[:, None] < clock[ids+1]), axis=1)
    position = np.stack([local[:, ancestors[j]].any(axis=1) for j in joints], axis=1)
    rotation = np.stack([local[:, ancestors[j]+[int(j)]].any(axis=1) for j in joints], axis=1)
    def stencil(mask, order):
        return np.logical_or.reduce([mask[k:len(mask)-order+k] for k in range(order+1)])
    return [stencil(position, 1), stencil(position, 2), stencil(rotation, 1), stencil(rotation, 2)]


class SupportedDualRatePeakGuard(DualRatePeakGuard):
    def __init__(self, source, caps, columns, support, **kwargs):
        super().__init__(source, caps, columns, **kwargs)
        self.support = [np.asarray(m) for m in support]
        allowed = np.zeros(self.caps[0].shape[1], bool); allowed[self.columns] = True
        if len(self.support) != 4 or any(m.dtype != bool or m.shape != c.shape or np.any(m[:, ~allowed]) for m,c in zip(self.support,self.caps)):
            raise ValueError('Boolean matching rate support inside affected columns required')
        self.support = [m.copy() for m in self.support]
        if not any(m.any() for m in self.support): raise ValueError('No mutable rate rows')

    def sample_margins(self, values, *, proposal=False):
        self.peaks(values)
        return np.concatenate([((ceiling-value+self.guard_tolerance)/scale)[mask]
            for ceiling, value, scale, mask in zip(self.envelopes(proposal=proposal), values, self.scales, self.support)])
