"""Reuse the frozen tail solver under a reversed clock to edit the clip start."""
import numpy as np
from relax_support_window import relax as relax_tail


class ReverseClock:
    def __init__(self,base):
        self.base=base;self.local=base.local[::-1];self.bounds=base.bounds;self.spec=base.spec

    def objective_pair(self,frame,values,neighbors):
        return self.base.objective_pair(len(self.local)-1-frame,values,neighbors)


def relax(fitter,initial,last=11,sweeps=6,progress=None):
    if type(last) is not int or not 0<=last<len(fitter.local)-1:
        raise ValueError('Start window must retain a fixed following frame')
    initial=np.asarray(initial,dtype=float)
    values,records,convergence=relax_tail(ReverseClock(fitter),initial[::-1].copy(),
        len(fitter.local)-1-last,sweeps=sweeps,progress=progress)
    result=values[::-1].copy()
    if not np.array_equal(result[last+1:],initial[last+1:]):raise ValueError('Motion after start window changed')
    for row in records:
        row['reversed_clock_frame']=row['frame'];row['frame']=len(initial)-1-row['frame']
    convergence.update(first_editable_frame=0,last_editable_frame=last,clock='reverse; original objective frames retained')
    return result,records,convergence
