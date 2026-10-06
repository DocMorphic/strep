"""Complete affine-equivalent pair reduction with original hard native norms."""
import numpy as np
from scipy import sparse
from native_pair_surface_reduction import reduce, verify
from native_pair_surface_conic import direction as mixed_direction


def direction(system, native_jac, gaps, surface_jac, offsets, value, lower, upper, trust,
              *, clearance=.0005, scale=.005):
    reduction = reduce(gaps, surface_jac, offsets, value, lower, upper, trust)
    certificate = verify(reduction, gaps, surface_jac, offsets, value, lower, upper, trust)
    retained = reduction.retained
    surface_jac = sparse.csr_matrix(surface_jac); gaps = np.asarray(gaps, float)
    delta, info = mixed_direction(system, native_jac, gaps[retained], surface_jac[retained],
        value, lower, upper, trust, clearance=clearance, scale=scale)
    info = dict(info, complete_surface_rows=len(gaps), equivalent_encoded_surface_rows=len(retained),
        reduction=reduction.report, certificate=certificate,
        scope='Certified equivalent affine surface encoding and every original hard native norm. '
            'Full nonlinear/native/export checks remain authoritative.')
    if delta is not None:
        lo, hi = reduction.report['proof_delta_lower'], reduction.report['proof_delta_upper']
        if np.any(delta < lo) or np.any(delta > hi):
            return None, dict(info, outside_certificate_box=True), reduction
        full = (clearance-gaps-surface_jac @ delta)/scale
        selected = full[retained]
        np.testing.assert_allclose(full.max(), selected.max(), atol=1e-10, rtol=1e-12)
        info.update(full_affine_surface_excess=float(max(0., full.max())),
            selected_affine_surface_excess=float(max(0., selected.max())),
            all_original_affine_surface_rows_evaluated=True)
    return delta, info, reduction
