"""Measured decoded defects tighten proposal caps; actual limits never change."""
import numpy as np
from native_scene_norms import NormRows


def tighten(system, jacobian, delta, decoded, protected_rows, reserves=None):
    if type(protected_rows) is not int or not 0<protected_rows<=len(system.caps):
        raise ValueError('Nonempty protected norm prefix required')
    actual=np.asarray(decoded,float)
    if actual.shape!=system.caps.shape or not np.isfinite(actual).all():
        raise ValueError('Complete finite decoded residual population required')
    reserve=np.zeros(len(actual)) if reserves is None else np.asarray(reserves,float).copy()
    if reserve.shape!=actual.shape or not np.isfinite(reserve).all() or np.any(reserve<0) or np.any(reserve[protected_rows:]):
        raise ValueError('Finite nonnegative protected-only reserve population required')
    predicted=system.residual(jacobian,delta)
    failed=np.flatnonzero(actual[:protected_rows]>0)
    # Include underpredictions that have not yet violated their cap: repairing
    # only failed rows can expose another nearly active row on the next solve.
    defect=np.maximum(0.,actual[:protected_rows]-predicted[:protected_rows])
    # Double the measured affine underprediction or the actual overrun. This
    # reserve is a heuristic proposal margin, not a numerical error certificate.
    extra=2*np.maximum(np.maximum(0.,actual[:protected_rows]),defect)*system.scales[:protected_rows]
    reserve[:protected_rows]+=extra
    if not np.isfinite(reserve).all():raise ValueError('Finite proposal reserve required')
    modified=NormRows(system.vectors,system.caps-reserve,system.scales)
    return modified,reserve,dict(failed_protected_rows=len(failed),tightened_rows=int(np.count_nonzero(reserve)),
        underpredicted_protected_rows=int(np.count_nonzero(defect)),
        maximum_normalized_reserve=float((reserve/system.scales).max()),
        original_caps_unchanged=True,contact_caps_unchanged=True,
        maximum_measured_normalized_underprediction=float(max(0.,(actual-predicted)[:protected_rows].max())),
        scope='Measured decoded defect heuristic; proposal caps only. Complete unchanged decoded constraints decide acceptance.')
