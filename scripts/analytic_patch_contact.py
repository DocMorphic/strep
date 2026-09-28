"""Exact authored-patch objective with the existing skin Jacobian and edit bounds.

Experimental solver option. No new contact inference or acceptance thresholds.
"""
import numpy as np
from scipy.optimize import least_squares
from rig_clearance_fit import ClearanceFitter


class AnalyticPatchFitter(ClearanceFitter):
    def __init__(self, rig, spec, local):
        super().__init__(rig, spec, local, {}, np.ones(len(local)))

    def residual_pair(self, frame, values, previous):
        points, jac = self.surface_jacobian(frame, values)
        obj = self.spec['objective']
        parts, rows = [], []
        for contact in self.active[frame]:
            ids = self.spec['patches'][contact['patch']]['vertices']
            parts.append((points[ids].mean(axis=0)-contact['target_position_m'])*obj['contact_weight'])
            rows.append(jac[ids].mean(axis=0)*obj['contact_weight'])
        identity = np.eye(len(values))
        parts += [np.minimum(points[:,1],0)*obj['floor_weight'],
                  values[:3]*obj['root_prior'], values[3:]*obj['rotation_prior_m_per_radian'],
                  (values[:3]-previous[:3])*obj['temporal_weight'],
                  (values[3:]-previous[3:])*obj['rotation_prior_m_per_radian']*obj['temporal_weight']]
        rows += [jac[:,1]*(points[:,1]<0)[:,None]*obj['floor_weight'],
                 identity[:3]*obj['root_prior'], identity[3:]*obj['rotation_prior_m_per_radian'],
                 identity[:3]*obj['temporal_weight'],
                 identity[3:]*obj['rotation_prior_m_per_radian']*obj['temporal_weight']]
        return np.concatenate(parts), np.vstack(rows)

    def fit_frame(self, frame, previous):
        lower, upper = -self.bounds, self.bounds
        if frame:
            lower, upper = np.maximum(lower,previous-self.steps), np.minimum(upper,previous+self.steps)
        last_x, last_pair = None, None
        def pair(x):
            nonlocal last_x,last_pair
            if last_x is None or not np.array_equal(x,last_x):
                last_x=x.copy();last_pair=self.residual_pair(frame,x,previous)
            return last_pair
        return least_squares(lambda x:pair(x)[0],np.clip(previous,lower+1e-10,upper-1e-10),
            jac=lambda x:pair(x)[1],bounds=(lower,upper),max_nfev=self.spec['max_nfev'],
            ftol=1e-5,xtol=1e-5,gtol=1e-5)
