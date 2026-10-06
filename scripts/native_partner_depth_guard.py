"""Local partner penetration-gap nonregression with unchanged acceptance.

Every currently contained partner vertex receives a hard affine gap-change
guard. All original native norms and surface conditions remain. These local
fixed-normal/barycentric guards do not prove nonlinear depth nonregression.
"""
import numpy as np
from scipy import sparse
from native_scene_norms import NormRows
from native_surface_lift import lift
from native_pair_surface_reduced_conic import direction as reduced_direction

SCHEMA = 'strep-native-partner-depth-guard-v1'


def augment(native, native_jac, gaps, surface_jac, offsets, blocks, value, lower, upper, trust):
    gaps = np.asarray(gaps, float); offsets = np.asarray(offsets)
    surface_jac, native_jac = sparse.csc_matrix(surface_jac), sparse.csc_matrix(native_jac)
    known = ('triangle-support-separation', 'penetrating-vertex', 'world-plane',
        'primitive-triangle', 'primitive-center-enclosure')
    if (gaps.ndim != 1 or not 1 <= len(gaps) <= 400000
            or not isinstance(blocks, list) or not blocks or len(blocks)+1 != len(offsets)
            or offsets.ndim != 1 or offsets.dtype.kind not in 'iu' or offsets[0] != 0 or offsets[-1] != len(gaps)
            or any(not isinstance(r, dict) or r.get('kind') not in known for r in blocks)
            or not np.array_equal(np.diff(offsets), [9 if r['kind']=='triangle-support-separation' else 1 for r in blocks])
            or surface_jac.shape != (len(gaps), len(value)) or native_jac.shape != (native.vectors.size, len(value))
            or any(not np.isfinite(a).all() for a in (gaps, surface_jac.data, native_jac.data))
            or type(trust) not in (int, float) or not np.isfinite(trust) or not 1e-6 <= trust <= .02):
        raise ValueError('Complete native/pair model, original blocks and bounded trust required')
    ids = np.array([offsets[i] for i,r in enumerate(blocks) if r['kind']=='penetrating-vertex'], int)
    if len(ids) and np.any(gaps[ids] > 0):
        raise ValueError('Partner penetration witnesses must have nonpositive anchor gaps')
    report = dict(schema=SCHEMA, original_native_norm_rows=len(native.caps), guarded_partner_rows=len(ids),
        guard_scalar_ids=ids.tolist(), local_gap_change_clearance_m=0.,
        all_partner_penetration_witnesses_guarded=True, original_native_caps_scales_unchanged=True,
        external_geometry_acceptance_unchanged=True, nonlinear_nonregression_verified=False,
        quality_approved=False, release_approved=False,
        scope='All contained partner-vertex affine gaps must not decrease from this decoded anchor. '
            'Original native norms and complete surface conditions remain. Local guidance only; '
            'fixed normals/barycentric targets do not prove signed-distance or full-scene nonregression.')
    if not len(ids):
        return native, native_jac, ids, report
    extra, extra_jac, conversion = lift(np.zeros(len(ids)), surface_jac[ids], value, lower, upper,
        trust, clearance=0., scale=.005)
    combined = NormRows(np.r_[native.vectors, extra.vectors], np.r_[native.caps, extra.caps], np.r_[native.scales, extra.scales])
    report['conversion'] = conversion
    return combined, sparse.vstack([native_jac, extra_jac], format='csc'), ids, report


def direction(native, native_jac, gaps, surface_jac, offsets, blocks, value, lower, upper, trust,
              *, clearance=0.):
    combined, jac, ids, guard = augment(native, native_jac, gaps, surface_jac, offsets, blocks,
        value, lower, upper, trust)
    delta, info, reduction = reduced_direction(combined, jac, gaps, surface_jac, offsets,
        value, lower, upper, trust, clearance=clearance)
    info = dict(info, partner_depth_guard=guard, original_native_norm_rows=len(native.caps),
        scope='Every original native norm and affine-equivalent surface condition, plus hard '
            'partner penetration-gap change guards. Full decoded native/geometry audits decide acceptance.')
    if delta is not None:
        change = np.asarray(sparse.csr_matrix(surface_jac)[ids] @ delta)
        info.update(predicted_partner_gap_deficit=float(max(0., (-change/.005).max())) if len(ids) else 0.,
            every_guarded_affine_gap_evaluated=True)
    return delta, info, reduction
