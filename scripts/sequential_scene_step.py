"""Strict nonlinear retention of complete named signed scene rows.

Search reserves tighten the original zero boundary. This numerical guard does
not create geometry observations or establish full motion/release approval.
"""
import copy
import numpy as np


def _vector(value,length):
    raw=np.asarray(value)
    if raw.dtype.kind not in 'fiu' or raw.shape!=(length,) or not np.isfinite(raw).all() or np.any(abs(raw)>1e6):
        raise ValueError('Every complete finite signed numeric row/control required')
    return raw.astype(float,copy=True)


class SceneStepGuard:
    def __init__(self,names,margins,controls,search_reserves):
        if (not isinstance(names,(list,tuple)) or not 1<=len(names)<=8192 or len(set(names))!=len(names)
                or any(not isinstance(n,str) or not n or len(n)>160 for n in names)):
            raise ValueError('Complete distinct original row identities required')
        self.names=tuple(names);self._margins=_vector(margins,len(names));self._reserves=_vector(search_reserves,len(names))
        raw=np.asarray(controls)
        if raw.ndim!=1 or not 3<=len(raw)<=384 or len(raw)%3:raise ValueError('Complete normalized three-vector control groups required')
        self._controls=_vector(controls,len(raw))
        if np.any(self._reserves<0) or np.any(self._reserves>1) or np.any(np.linalg.norm(self._controls.reshape(-1,3),axis=1)>1):
            raise ValueError('Nonnegative bounded search reserves and valid original control balls required')
        self._protected=self._margins>=0;self.steps=0

    @property
    def protected_rows(self):return self._protected.copy()

    @property
    def controls(self):return self._controls.copy()

    @property
    def margins(self):return self._margins.copy()

    @property
    def search_reserves(self):return self._reserves.copy()

    def assess(self,names,margins,controls):
        if tuple(names)!=self.names:raise ValueError('Original complete row identities and order must remain unchanged')
        after=_vector(margins,len(self.names));point=_vector(controls,len(self._controls))
        before_peak=float(np.maximum(self._reserves-self._margins,0).max());after_peak=float(np.maximum(self._reserves-after,0).max())
        lost=np.flatnonzero(self._protected&(after<0));bounds=bool(np.all(np.linalg.norm(point.reshape(-1,3),axis=1)<=1))
        return dict(schema='strep-sequential-scene-step-v1',accepted=bool(bounds and not len(lost) and after_peak<before_peak),
            original_row_names=list(self.names),complete_rows=len(self.names),protected_row_indices=np.flatnonzero(self._protected).tolist(),lost_protected_row_indices=lost.tolist(),
            baseline_maximum_working_violation=before_peak,candidate_maximum_working_violation=after_peak,all_original_control_balls_pass=bounds,
            failed_original_row_indices=np.flatnonzero(after<0).tolist(),all_original_numeric_rows_pass=bool(np.all(after>=0)),all_search_targets_pass=bool(np.all(after>=self._reserves)),
            added_physical_tolerance=0.,quality_approved=False,release_approved=False,
            scope='Exact complete caller-bound signed row comparison at original zero boundary, strictly decreasing peak toward tighter declared search targets. Every previously passing row stays nonnegative. Not source binding, geometry, motion, full clock, exported-asset or release approval.')

    def advance(self,names,margins,controls):
        report=self.assess(names,margins,controls)
        if not report['accepted']:raise ValueError('Nonlinear step rejected; current state retained')
        self._margins=_vector(margins,len(self.names));self._controls=_vector(controls,len(self._controls));self._protected|=self._margins>=0;self.steps+=1
        return copy.deepcopy(report)
