"""Exact-key native support sampling, separate from archived legacy experiments."""
import numpy as np
from rig_clip_import import AnimationSampler


class NativeSupportSampler(AnimationSampler):
    @staticmethod
    def value(path, times, values, mode, time):
        # Preserve the exact stored key values, but perform time arithmetic in
        # Float64. NumPy 2 weak-scalar promotion can otherwise round a Python
        # query to a Float32 endpoint before deciding whether to clamp it.
        # Float32 subtraction can also round a nonuniform key interval.
        times=np.asarray(times,dtype=np.float64)
        time=float(time)
        key = int(np.searchsorted(times, time, side='left'))
        if key < len(times) and float(times[key]) == float(time):
            result = values[3*key+1 if mode == 'CUBICSPLINE' else key].copy()
            if path == 'rotation':
                norm = np.linalg.norm(result)
                if norm < 1e-8: raise ValueError('Invalid exact-key quaternion')
                result = result/norm
            return result
        return AnimationSampler.value(path, times, values, mode, time)
