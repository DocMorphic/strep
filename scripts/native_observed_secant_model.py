"""Append an empirical vector guide without replacing original hard norm rows.

One authenticated exported sample supplies a rank-one secant, not a derivative
or an enclosure of quantization/nonlinear response. Actual decoded gates decide.
"""
import numpy as np
from scipy import sparse
from native_scene_norms import NormRows


def augment(native, jacobian, value, observed_value, observed_native, *,
            maximum_elements=60_000_000):
    """Keep the original affine model and append all sampled-secant norm rows.

    The caller binds both complete populations, source order and clocks to the
    same job. Matching arrays alone cannot authenticate those identities. The
    sample may fail its caps. Both models retain the exact original caps/scales.
    No rows are filtered by failure size, and no sample is promoted to an anchor.
    """
    x, other = [np.asarray(a, float) for a in (value, observed_value)]
    v, caps, scales = [np.asarray(a, float) for a in (native.vectors, native.caps, native.scales)]
    observed = np.asarray(observed_native.vectors, float)
    n = len(x) if x.ndim == 1 else 0
    j = sparse.csr_matrix(jacobian, copy=True)
    if (not 1 <= n <= 96 or other.shape != x.shape
            or v.ndim != 2 or v.shape[1:] != (3,) or not 1 <= len(v) <= 100_000
            or caps.shape != (len(v),) or scales.shape != caps.shape
            or observed.shape != v.shape or j.shape != (v.size, n)
            or not np.array_equal(observed_native.caps, caps)
            or not np.array_equal(observed_native.scales, scales)
            or any(not np.isfinite(a).all() for a in (x, other, v, caps, scales, observed, j.data))
            or np.any(caps < 0) or np.any(scales <= 0)
            or type(maximum_elements) is not int or not 1 <= maximum_elements <= 60_000_000):
        raise ValueError('Matching complete finite original/sample vector populations and bounded model required')
    step = other-x
    if not 1e-10 <= float(abs(step).max()) <= .02:
        raise ValueError('A nondegenerate sample within the supported control trust limit is required')
    # Budget before creating a dense rank-one update; never truncate dependencies.
    if 2*v.size*n > maximum_elements:
        raise ValueError('Complete augmented dense-dependency budget exceeded')
    if np.any((np.linalg.norm(v, axis=1)-caps)/scales > 0):
        raise ValueError('The original anchor must strictly pass its norm caps')
    j.sum_duplicates(); j.eliminate_zeros(); j.sort_indices()
    predicted = v+(j@step).reshape(v.shape)
    defect = observed-predicted
    weights = step/float(step@step)
    secant = j+sparse.csr_matrix(defect.reshape(-1, 1)*weights[None, :])
    secant.sum_duplicates(); secant.eliminate_zeros(); secant.sort_indices()
    stacked = sparse.vstack([j, secant], format='csr')
    if not np.isfinite(stacked.data).all():
        raise ValueError('Nonfinite empirical secant model')
    reconstructed = v+(secant@step).reshape(v.shape)
    error = float(abs(reconstructed-observed).max())
    allowance = float(128*np.finfo(float).eps*(1+max(abs(observed).max(), abs(predicted).max())))
    if not np.isfinite(allowance) or error > allowance:
        raise ValueError('The sampled secant does not reproduce its endpoint within arithmetic allowance')
    combined = NormRows(np.vstack([v, v]), np.tile(caps, 2), np.tile(scales, 2))
    report = dict(schema='strep-native-observed-secant-model-v1', controls=n,
        original_norm_rows=len(v), proposal_norm_rows=2*len(v), observed_samples=1,
        sample_control_step=step.tolist(), sample_norm_failures=int(np.count_nonzero(
            (np.linalg.norm(observed, axis=1)-caps)/scales > 0)),
        maximum_sample_vector_defect=float(np.linalg.norm(defect, axis=1).max()),
        sample_endpoint_maximum_component_error=error, sample_endpoint_arithmetic_allowance=allowance,
        original_native_rows_columns_retained=True, original_caps_scales_duplicated_exactly=True,
        maximum_nonzero_elements=maximum_elements, complete_dense_dependency_elements=2*v.size*n,
        stored_nonzero_elements=stacked.nnz, empirical_secant_is_derivative=False,
        nonlinear_or_storage_enclosure=False, acceptance_tolerance_changed=False,
        quality_approved=False, release_approved=False,
        scope='Original complete affine native rows followed by one complete rank-one sampled-vector '
              'secant at the same unchanged anchor. Both are proposal constraints under the original caps. '
              'Caller authenticates sample identities and clocks. Arithmetic endpoint allowance only; '
              'no allowance in actual acceptance, no pure-rounding attribution or generalization guarantee.')
    return combined, stacked, report
