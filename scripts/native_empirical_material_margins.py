"""Bounded, source-bound margins from complete saved endpoint observations.

These are empirical prediction errors, not nonlinear or continuous bounds.
The caller authenticates the material model and declared complete sample set.
"""
import copy
from dataclasses import dataclass
import hashlib
import json
import re
import numpy as np


@dataclass(frozen=True)
class EmpiricalMaterialMargins:
    margins_m: np.ndarray
    actual_gaps_m: np.ndarray
    affine_gaps_m: np.ndarray
    report: dict


def _sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def _digest(array):
    a = np.asarray(array, dtype='<f8', order='C')
    h = hashlib.sha256(json.dumps(a.shape).encode())
    h.update(a.tobytes())
    return h.hexdigest()


def build(actual_gaps_m, affine_gaps_m, *, material_model_sha256,
          sample_sha256, required_sample_sha256, row_indices, required_rows,
          extra_buffer_m=0., maximum_samples=32, maximum_rows=4096,
          maximum_elements=131072):
    """Use max(0, affine - actual) per row over every declared endpoint.

Reject incomplete or over-budget populations before Float64 copies. Never
clip measured errors or select a row/sample subset to fit a resource limit.
Model identity must bind frozen row descriptors, anchor and derivatives.
    """
    if (not _sha(material_model_sha256)
            or type(required_rows) is not int or not 1 <= required_rows <= 4096
            or type(maximum_samples) is not int or not 1 <= maximum_samples <= 32
            or type(maximum_rows) is not int or not 1 <= maximum_rows <= 4096
            or type(maximum_elements) is not int or not 1 <= maximum_elements <= 131072
            or not isinstance(sample_sha256, list) or not isinstance(required_sample_sha256, list)
            or not 1 <= len(sample_sha256) <= maximum_samples
            or sample_sha256 != required_sample_sha256
            or any(not _sha(s) for s in sample_sha256)
            or len(set(sample_sha256)) != len(sample_sha256)
            or not isinstance(row_indices, list) or len(row_indices) != required_rows
            or any(type(i) is not int for i in row_indices)
            or row_indices != list(range(required_rows))
            or required_rows > maximum_rows
            or len(sample_sha256)*required_rows > maximum_elements
            or type(extra_buffer_m) not in (int, float) or not np.isfinite(extra_buffer_m)
            or not 0. <= extra_buffer_m <= .001):
        raise ValueError('Complete declared source, endpoint/row identities and bounded empirical policy required')
    raw_actual, raw_affine = np.asarray(actual_gaps_m), np.asarray(affine_gaps_m)
    shape = (len(sample_sha256), required_rows)
    if (raw_actual.shape != shape or raw_affine.shape != shape
            or any(a.dtype.kind not in 'fiu' for a in (raw_actual, raw_affine))):
        raise ValueError('Every complete numeric actual and affine endpoint required')
    actual, affine = [np.array(a, dtype=float, copy=True) for a in (raw_actual, raw_affine)]
    if not np.isfinite(actual).all() or not np.isfinite(affine).all():
        raise ValueError('Finite complete endpoint observations required')
    with np.errstate(over='ignore', invalid='ignore'):
        loss = affine-actual
        worst = np.maximum(0., loss.max(axis=0))
        margins = worst+extra_buffer_m
    if not np.isfinite(loss).all() or not np.isfinite(margins).all() or np.any(margins > .1):
        raise ValueError('Finite bounded empirical error required; no clipping or subset returned')
    report = dict(schema='strep-native-empirical-material-margins-v1',
        material_model_sha256=material_model_sha256, sample_sha256=sample_sha256.copy(),
        required_sample_sha256=required_sample_sha256.copy(), row_indices=row_indices.copy(),
        required_rows=required_rows, samples=len(sample_sha256),
        maximum_samples=maximum_samples, maximum_rows=maximum_rows, maximum_elements=maximum_elements,
        extra_buffer_m=float(extra_buffer_m), maximum_margin_limit_m=.1,
        worst_observed_gap_loss_m=worst.tolist(), margins_m=margins.tolist(),
        actual_gaps_sha256=_digest(actual), affine_gaps_sha256=_digest(affine),
        margins_sha256=_digest(margins), complete_declared_endpoints=True,
        complete_declared_rows=True, nonlinear_certificate=False, continuous_certificate=False,
        quality_approved=False, release_approved=False,
        policy='Per-row maximum positive affine-minus-actual gap over every declared saved endpoint, plus explicit buffer.',
        scope='Empirical endpoint envelope only. Caller authenticates complete source/model/sample identities. '
              'Original actual stored motion, material and full-scene gates remain decisive; no guarantee for new poses.')
    report['policy_sha256'] = hashlib.sha256(json.dumps(report, sort_keys=True, allow_nan=False).encode()).hexdigest()
    for array in (actual, affine, margins):
        array.setflags(write=False)
    return EmpiricalMaterialMargins(margins, actual, affine, report)


def validate(policy, *, material_model_sha256, required_rows):
    """Recompute the complete policy and reject stale or mutated snapshots."""
    if (not isinstance(policy, EmpiricalMaterialMargins) or not isinstance(policy.report, dict)
            or not _sha(material_model_sha256) or type(required_rows) is not int
            or policy.report.get('material_model_sha256') != material_model_sha256
            or policy.report.get('required_rows') != required_rows):
        raise ValueError('Separately typed margins bound to this exact material model required')
    r = policy.report
    try:
        rebuilt = build(policy.actual_gaps_m, policy.affine_gaps_m,
            material_model_sha256=material_model_sha256,
            sample_sha256=r['sample_sha256'], required_sample_sha256=r['required_sample_sha256'],
            row_indices=r['row_indices'], required_rows=required_rows,
            extra_buffer_m=r['extra_buffer_m'], maximum_samples=r['maximum_samples'],
            maximum_rows=r['maximum_rows'], maximum_elements=r['maximum_elements'])
        same_report = json.dumps(r, sort_keys=True, allow_nan=False) == json.dumps(rebuilt.report, sort_keys=True, allow_nan=False)
        same_margins = (_digest(policy.margins_m) == rebuilt.report['margins_sha256']
                        and np.array_equal(policy.margins_m, rebuilt.margins_m))
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise ValueError('Intact complete empirical policy required') from error
    if not same_report or not same_margins:
        raise ValueError('Empirical observations, margins or metadata changed after calibration')
    return rebuilt.margins_m.copy(), copy.deepcopy(rebuilt.report)
