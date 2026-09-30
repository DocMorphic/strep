"""Empirical proposal margins; final decoded acceptance limits stay unchanged."""
import numpy as np


def empirical_reserve(predicted, exported, kinds, multiplier=2.):
    predicted, exported = np.asarray(predicted, float), np.asarray(exported, float)
    kinds = np.asarray(kinds)
    if predicted.ndim != 2 or not len(predicted) or exported.shape != predicted.shape or kinds.shape != predicted.shape[1:]:
        raise ValueError('Matching trial-by-constraint norm observations required')
    if not np.isfinite(predicted).all() or not np.isfinite(exported).all() or np.any(predicted < 0) or np.any(exported < 0):
        raise ValueError('Finite nonnegative norms required')
    if not np.isfinite(multiplier) or multiplier < 1 or not np.isin(kinds, ['edit', 'speed', 'acceleration']).all():
        raise ValueError('Declared kinds and multiplier at least one required')
    error = np.maximum(exported - predicted, 0).max(axis=0)
    reserve = multiplier * error
    reserve[kinds == 'edit'] = 0  # Exact affine edit cones keep their existing budget.
    return reserve, error


def tightened_radii(radii, reserve, kinds):
    radii, reserve, kinds = np.asarray(radii, float), np.asarray(reserve, float), np.asarray(kinds)
    if radii.ndim != 1 or reserve.shape != radii.shape or kinds.shape != radii.shape:
        raise ValueError('Matching constraint rows required')
    if not np.isfinite(radii).all() or not np.isfinite(reserve).all() or np.any(radii < 0) or np.any(reserve < 0):
        raise ValueError('Finite nonnegative radii and reserves required')
    if not np.isin(kinds, ['edit', 'speed', 'acceleration']).all() or np.any(reserve[kinds == 'edit'] != 0):
        raise ValueError('Native edit budgets must remain unchanged')
    if np.any(reserve > radii):
        raise ValueError('Empirical reserve exceeds a source cap; no silent clipping allowed')
    return radii - reserve


def conservative_refresh(previous,predicted,exported,kinds):
    """Retain prior margins while incorporating newly measured local error."""
    measured,error=empirical_reserve(predicted,exported,kinds)
    previous=np.asarray(previous,float);kinds=np.asarray(kinds)
    if previous.shape!=measured.shape or not np.isfinite(previous).all() or np.any(previous<0) or np.any(previous[kinds=='edit']!=0):
        raise ValueError('Matching finite prior motion margins required')
    return np.maximum(previous,measured),error
