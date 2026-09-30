"""Fixed original-reference acceptance gates for sequential research proposals."""
import numpy as np


def acceptance(previous_peak,candidate_peak,cap_excess,rate_failures,original_edits,finger_passed):
    values=np.array([previous_peak,candidate_peak,cap_excess,*original_edits],float)
    if len(original_edits)!=2 or len(rate_failures)!=2 or len(finger_passed)!=2 or not np.isfinite(values).all() or np.any(values<0):
        raise ValueError('Finite two-actor evidence required')
    reasons=[]
    if any(n!=0 for n in rate_failures):reasons.append('exported_motion')
    if any(angle>5.0001 for angle in original_edits):reasons.append('original_total_edit')
    if not all(finger_passed):reasons.append('original_finger_bounds')
    if cap_excess>1e-6:reasons.append('retained_surface_allowance')
    if previous_peak-candidate_peak<1e-6:reasons.append('insufficient_retained_distance_improvement')
    return dict(accepted=not reasons,reasons=reasons,improvement_m=float(previous_peak-candidate_peak))
