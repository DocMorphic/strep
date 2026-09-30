"""Reconcile complete sampled geometry before reusing a reserve-study result."""
import numpy as np


def checked_summary(source, candidate, summary):
    if not source or len(source) != len(candidate): raise ValueError('Complete matching geometry population required')
    for index,(before,after) in enumerate(zip(source,candidate)):
        if before['sample'] != index or after['sample'] != index or before['time_s'] != after['time_s']:
            raise ValueError('Original geometry clock required')
        if len(before['directions']) != 2 or len(after['directions']) != 2:
            raise ValueError('Both directional mesh queries required')
        start = max(d['maximum_depth_m'] for d in before['directions'])
        end = max(d['max_depth_m'] for d in after['directions'])
        original_floor, floor = np.asarray(before['floor_depth_m']), np.asarray(after['floor_depth_m'])
        depths = [d['maximum_depth_m'] for d in before['directions']]+[d['max_depth_m'] for d in after['directions']]
        if original_floor.shape != (2,) or floor.shape != (2,) or not np.isfinite(np.r_[depths,original_floor,floor]).all() or min(np.r_[depths,original_floor,floor]) < 0:
            raise ValueError('Finite nonnegative measured depths required')
        expected = [start,end,max(0.,end-max(.005,start)),float((floor-original_floor).max())]
        found = [after[k] for k in ['source_depth_m','candidate_depth_m','cap_excess_m','floor_increase_m']]
        if not np.isfinite(found).all() or not np.allclose(found,expected,atol=1e-12,rtol=0):
            raise ValueError('Geometry arithmetic differs')
    values = dict(samples=len(candidate),fresh_directional_queries=2*len(candidate),
        source_peak_m=max(r['source_depth_m'] for r in candidate),candidate_peak_m=max(r['candidate_depth_m'] for r in candidate),
        source_failed_times=sum(r['source_depth_m']>.005 for r in candidate),candidate_failed_times=sum(r['candidate_depth_m']>.005 for r in candidate),
        maximum_cap_excess_m=max(r['cap_excess_m'] for r in candidate),maximum_floor_increase_m=max(r['floor_increase_m'] for r in candidate))
    for key,value in values.items():
        if not np.isfinite(summary[key]) or abs(summary[key]-value)>1e-12: raise ValueError('Geometry summary differs: '+key)
    reasons=[]
    if values['maximum_cap_excess_m']>1e-6: reasons.append('fresh_surface_caps')
    if values['maximum_floor_increase_m']>1e-6: reasons.append('floor_regression')
    if values['source_peak_m']-values['candidate_peak_m']<1e-6: reasons.append('no_peak_improvement')
    return reasons
