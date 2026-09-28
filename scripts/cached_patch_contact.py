"""Experimental exact last-pose surface cache for fixed contact-fitting problems."""
import copy
import numpy as np
from analytic_patch_contact import AnalyticPatchFitter


class CachedPatchFitter(AnalyticPatchFitter):
    """Reuse one FK/skin derivative result; rebuild the fitter if rig/spec changes."""
    def __init__(self,rig,spec,local):
        fixed=np.array(local,copy=True);fixed.setflags(write=False)
        super().__init__(rig,copy.deepcopy(spec),fixed)
        self._surface_frame=None;self._surface_x=None;self._surface_pair=None
        self.surface_hits=0;self.surface_misses=0

    def surface_jacobian(self,frame,values):
        if not isinstance(frame,(int,np.integer)) or isinstance(frame,(bool,np.bool_)):
            raise ValueError('Integer frame required')
        if self._surface_frame==frame and self._surface_x is not None and np.array_equal(self._surface_x,values):
            self.surface_hits+=1
            return self._surface_pair
        pair=super().surface_jacobian(frame,values)
        for array in pair:array.setflags(write=False)
        self._surface_frame=frame;self._surface_x=np.array(values,copy=True);self._surface_pair=pair
        self.surface_misses+=1
        return pair
