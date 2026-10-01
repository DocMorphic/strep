"""Exact-key native support sampling, separate from archived legacy experiments."""
import numpy as np
from rig_clip_import import AnimationSampler


class NativeSupportSampler(AnimationSampler):
    @staticmethod
    def value(path, times, values, mode, time):
        key = int(np.searchsorted(times, time, side='left'))
        if key < len(times) and float(times[key]) == float(time):
            result = values[3*key+1 if mode == 'CUBICSPLINE' else key].copy()
            if path == 'rotation':
                norm = np.linalg.norm(result)
                if norm < 1e-8: raise ValueError('Invalid exact-key quaternion')
                result = result/norm
            return result
        return AnimationSampler.value(path, times, values, mode, time)
