"""Hard source-bound partner depth floors with original native norms.

Every existing partner witness uses the authored geometry penetration floor.
Complete surface reduction remains certified and all decoded checks remain.
"""
import numpy as np
from scipy import sparse
from native_scene_conic import solver_module
from native_partner_depth_guard import augment
from native_pair_surface_reduction import reduce, verify
from native_scene_geometry import policy_for


def depth_floor(policy, scene, digest, blocks):
    times, _, _ = policy_for(policy, scene, digest)
    scene.check_inputs()
    clock = set(times.tolist())
    if (not isinstance(blocks, list) or not blocks
            or any(not isinstance(r, dict) or type(r.get('time_s')) not in (int, float)
                or not np.isfinite(r['time_s']) or r['time_s'] not in clock for r in blocks)):
        raise ValueError('Every complete guide witness must belong to the source-bound geometry clock')
    return float(policy['limits']['penetration_m'])


def direction(native, native_jac, gaps, surface_jac, offsets, blocks, value, lower, upper, trust,
              *, policy, scene, digest, clearance=0., scale=.005):
    limit = depth_floor(policy, scene, digest, blocks)
    # Reuse complete witness validation; change guidance, never external acceptance.
    _, _, ids, guard = augment(native, native_jac, gaps, surface_jac, offsets, blocks,
        value, lower, upper, trust)
    guard = dict(guard, schema='strep-native-partner-depth-limit-v1', depth_limit_m=limit,
        local_condition='gap + J delta >= -original penetration limit',
        scope='Every existing partner witness uses the original authored depth floor. '
            'Local fixed-normal/barycentric guidance only; full decoded geometry remains authoritative.')
    guard.pop('local_gap_change_clearance_m', None)
    value, lower, upper, gaps = [np.asarray(a, float) for a in (value, lower, upper, gaps)]
    if (type(clearance) not in (int, float) or not np.isfinite(clearance) or not 0 <= clearance <= .005
            or type(scale) not in (int, float) or not np.isfinite(scale) or scale <= 0):
        raise ValueError('Finite scalar clearance and positive scale required')
    native_jac, surface_jac = sparse.csr_matrix(native_jac), sparse.csr_matrix(surface_jac)
    native_jac.eliminate_zeros(); surface_jac.eliminate_zeros()
    if native_jac.nnz+surface_jac.nnz+surface_jac[ids].nnz > 60000000:
        raise ValueError('Complete model exceeds resource budget; no subset returned')
    reduction = reduce(gaps, surface_jac, offsets, value, lower, upper, trust)
    certificate = verify(reduction, gaps, surface_jac, offsets, value, lower, upper, trust)
    retained = reduction.retained; solver = solver_module(); n = len(value)
    lo, hi = np.maximum(-1., (lower-value)/trust), np.minimum(1., (upper-value)/trust)
    counts = np.diff(native_jac.indptr).reshape(-1, 3).sum(axis=1); fixed = counts == 0
    info = dict(status='not-solved', protected_norm_rows=len(native.caps),
        complete_surface_rows=len(gaps), equivalent_encoded_surface_rows=len(retained),
        scalar_rows_encoded=len(retained), scalar_rows_omitted=0,
        hard_partner_scalar_rows=len(ids), guard_scalar_ids=ids.tolist(),
        trust_control_fraction=float(trust), clearance_m=float(clearance), scale_m=float(scale),
        solver_version=solver.__version__, reduction=reduction.report, certificate=certificate,
        partner_depth_guard=guard, depth_limit_m=limit, guard_representation='hard-scalar-depth-floor',
        original_native_caps_scales_unchanged=True, external_geometry_acceptance_unchanged=True,
        quality_approved=False, release_approved=False,
        scope='Every original native norm, complete equivalent soft surface representation and every '
            'hard affine partner depth floor. Decoded native and geometry checks remain authoritative.')
    if np.any(native.residual()[fixed] > 0):
        return None, dict(info, status='FixedProtectedConflict'), reduction
    maximum_step = np.maximum(abs(lo), abs(hi))*trust
    radius = np.asarray(abs(native_jac) @ maximum_step).reshape(native.vectors.shape)
    upper_norm = np.linalg.norm(abs(native.vectors)+radius, axis=1)
    reserve = 64*(n+4)*np.finfo(float).eps*np.maximum.reduce([upper_norm, abs(native.caps), np.ones(len(native.caps))])
    box_passing = (~fixed) & np.isfinite(upper_norm) & (upper_norm+reserve <= native.caps)
    active = np.flatnonzero(~fixed & ~box_passing)
    mats = [sparse.hstack([sparse.eye(n), sparse.csc_matrix((n, 1))]),
        sparse.hstack([-sparse.eye(n), sparse.csc_matrix((n, 1))]),
        sparse.csc_matrix(np.r_[np.zeros(n), -1.][None])]
    rhs = [hi, -lo, np.zeros(1)]; cones = [solver.NonnegativeConeT(2*n+1)]
    if len(active):
        selected = (3*active[:, None]+np.arange(3)).ravel()
        derivative = native_jac[selected].multiply((-trust/np.repeat(native.scales[active], 3))[:, None]).tocoo()
        mats.append(sparse.csc_matrix((derivative.data, (4*(derivative.row//3)+1+derivative.row%3,
            derivative.col)), shape=(4*len(active), n+1)))
        rhs.append((np.c_[native.caps[active], native.vectors[active]]/native.scales[active, None]).ravel())
        cones.extend(solver.SecondOrderConeT(4) for _ in active)
    if len(retained):
        mats.append(sparse.hstack([-trust/scale*surface_jac[retained], -np.ones((len(retained), 1))], format='csc'))
        rhs.append((gaps[retained]-clearance)/scale); cones.append(solver.NonnegativeConeT(len(retained)))
    if len(ids):
        # Zero t coefficient: the soft surface penalty cannot buy guard violations.
        mats.append(sparse.hstack([-trust/scale*surface_jac[ids], sparse.csc_matrix((len(ids), 1))], format='csc'))
        rhs.append((gaps[ids]+limit)/scale); cones.append(solver.NonnegativeConeT(len(ids)))
    matrix, bound = sparse.vstack(mats, format='csc'), np.concatenate(rhs)
    settings = solver.DefaultSettings(); settings.verbose = False
    settings.max_iter = 100; settings.time_limit = 30.
    settings.tol_gap_abs = settings.tol_gap_rel = settings.tol_feas = 1e-9
    if hasattr(settings, 'max_threads'):settings.max_threads = 1
    first = solver.DefaultSolver(sparse.csc_matrix((n+1, n+1)), np.r_[np.zeros(n), 1.],
        matrix, bound, cones, settings).solve()
    info.update(status=str(first.status), iterations=first.iterations, active_native_cones=len(active),
        omitted_fixed_passing_native_rows=int(fixed.sum()), omitted_affine_box_passing_native_rows=int(box_passing.sum()))
    if str(first.status) not in ('Solved', 'AlmostSolved'):return None, info, reduction
    point = np.asarray(first.x)
    if not np.isfinite(point).all():return None, dict(info, invalid_solution=True), reduction
    optimum = max(0., float(point[-1]))
    second_matrix = sparse.vstack([matrix, sparse.csc_matrix(np.r_[np.zeros(n), 1.][None])], format='csc')
    second = solver.DefaultSolver(sparse.diags(np.r_[np.ones(n), 0.], format='csc'), np.zeros(n+1),
        second_matrix, np.r_[bound, optimum+1e-9], cones+[solver.NonnegativeConeT(1)], settings).solve()
    info.update(affine_optimum=optimum, minimum_norm_phase_status=str(second.status))
    if str(second.status) in ('Solved', 'AlmostSolved') and np.isfinite(second.x).all():point = np.asarray(second.x)
    delta = point[:n]*trust
    if np.any(delta < lo*trust-1e-9) or np.any(delta > hi*trust+1e-9):
        return None, dict(info, invalid_solution=True), reduction
    delta = np.clip(value+delta, lower, upper)-value
    if np.any(delta < reduction.report['proof_delta_lower']) or np.any(delta > reduction.report['proof_delta_upper']):
        return None, dict(info, outside_certificate_box=True), reduction
    full = (clearance-gaps-surface_jac @ delta)/scale
    np.testing.assert_allclose(full.max(), full[retained].max(), atol=1e-10, rtol=1e-12)
    depth_residual = (-gaps[ids]-surface_jac[ids] @ delta-limit)/scale
    info.update(maximum_control_step=float(abs(delta).max()), predicted_native_excess=float(native.residual(native_jac, delta).max()),
        full_affine_surface_excess=float(max(0., full.max())), selected_affine_surface_excess=float(max(0., full[retained].max())),
        predicted_partner_depth_deficit=float(max(0., depth_residual.max())) if len(ids) else 0.,
        all_original_affine_surface_rows_evaluated=True, every_guarded_affine_gap_evaluated=True)
    return delta, info, reduction
