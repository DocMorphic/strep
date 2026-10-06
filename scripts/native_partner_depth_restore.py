"""Depth-first feasibility restoration with unchanged native norms.

Depth violations are minimized before complete surface excess and control norm.
Complete surface reduction remains certified and all decoded checks remain.
"""
import numpy as np
from scipy import sparse
from native_scene_conic import solver_module
from native_partner_depth_guard import augment
from native_pair_surface_reduction import reduce, verify
from native_partner_depth_limit import depth_floor


def direction(native, native_jac, gaps, surface_jac, offsets, blocks, value, lower, upper, trust,
              *, policy, scene, digest, clearance=0., scale=.005):
    limit = depth_floor(policy, scene, digest, blocks)
    # Reuse complete witness validation; change guidance, never external acceptance.
    _, _, ids, guard = augment(native, native_jac, gaps, surface_jac, offsets, blocks,
        value, lower, upper, trust)
    guard = dict(guard, schema='strep-native-partner-depth-restore-v1', depth_limit_m=limit,
        local_condition='minimize worst original depth-floor deficit before complete surface excess',
        scope='All existing partner depth-floor deficits remain explicit soft restoration conditions. '
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
        restored_partner_scalar_rows=len(ids), guard_scalar_ids=ids.tolist(),
        trust_control_fraction=float(trust), clearance_m=float(clearance), scale_m=float(scale),
        solver_version=solver.__version__, reduction=reduction.report, certificate=certificate,
        partner_depth_guard=guard, depth_limit_m=limit, guard_representation='lexicographic-depth-surface-restoration',
        original_native_caps_scales_unchanged=True, external_geometry_acceptance_unchanged=True,
        quality_approved=False, release_approved=False,
        scope='Every original native norm, complete equivalent soft surface representation and every '
            'soft affine partner depth deficit. Decoded native and geometry checks remain authoritative.')
    if np.any(native.residual()[fixed] > 0):
        return None, dict(info, status='FixedProtectedConflict'), reduction
    maximum_step = np.maximum(abs(lo), abs(hi))*trust
    radius = np.asarray(abs(native_jac) @ maximum_step).reshape(native.vectors.shape)
    upper_norm = np.linalg.norm(abs(native.vectors)+radius, axis=1)
    reserve = 64*(n+4)*np.finfo(float).eps*np.maximum.reduce([upper_norm, abs(native.caps), np.ones(len(native.caps))])
    box_passing = (~fixed) & np.isfinite(upper_norm) & (upper_norm+reserve <= native.caps)
    active = np.flatnonzero(~fixed & ~box_passing)
    mats = [sparse.hstack([sparse.eye(n), sparse.csc_matrix((n, 2))]),
        sparse.hstack([-sparse.eye(n), sparse.csc_matrix((n, 2))]),
        sparse.hstack([sparse.csc_matrix((2,n)), -sparse.eye(2)],format='csc')]
    rhs = [hi, -lo, np.zeros(2)]; cones = [solver.NonnegativeConeT(2*n+2)]
    if len(active):
        selected = (3*active[:, None]+np.arange(3)).ravel()
        derivative = native_jac[selected].multiply((-trust/np.repeat(native.scales[active], 3))[:, None]).tocoo()
        mats.append(sparse.csc_matrix((derivative.data, (4*(derivative.row//3)+1+derivative.row%3,
            derivative.col)), shape=(4*len(active), n+2)))
        rhs.append((np.c_[native.caps[active], native.vectors[active]]/native.scales[active, None]).ravel())
        cones.extend(solver.SecondOrderConeT(4) for _ in active)
    if len(retained):
        mats.append(sparse.hstack([-trust/scale*surface_jac[retained], sparse.csc_matrix((len(retained),1)), -np.ones((len(retained), 1))], format='csc'))
        rhs.append((gaps[retained]-clearance)/scale); cones.append(solver.NonnegativeConeT(len(retained)))
    if len(ids):
        # Depth has its own penalty; surface improvement cannot buy a worse depth optimum.
        mats.append(sparse.hstack([-trust/scale*surface_jac[ids], -np.ones((len(ids),1)), sparse.csc_matrix((len(ids),1))], format='csc'))
        rhs.append((gaps[ids]+limit)/scale); cones.append(solver.NonnegativeConeT(len(ids)))
    matrix, bound = sparse.vstack(mats, format='csc'), np.concatenate(rhs)
    settings = solver.DefaultSettings(); settings.verbose = False
    settings.max_iter = 100; settings.time_limit = 30.
    settings.tol_gap_abs = settings.tol_gap_rel = settings.tol_feas = 1e-9
    if hasattr(settings, 'max_threads'):settings.max_threads = 1
    zero = sparse.csc_matrix((n+2,n+2))
    first = solver.DefaultSolver(zero, np.r_[np.zeros(n), 1., 0.], matrix, bound, cones, settings).solve()
    info.update(status=str(first.status), iterations=first.iterations, active_native_cones=len(active),
        omitted_fixed_passing_native_rows=int(fixed.sum()), omitted_affine_box_passing_native_rows=int(box_passing.sum()),
        priority='depth deficit, then complete surface excess, then normalized control norm',
        phase_lock_tolerance=1e-9, phase_native_check_tolerance=settings.tol_feas,
        native_norms_always_hard=True, depth_phase_status=str(first.status),
        surface_phase_status='not-run', minimum_norm_phase_status='not-run', selected_phase=None, phase_checks=[])
    def checked(solution, name, *, depth_bound=None, surface_bound=None):
        record=dict(phase=name,status=str(solution.status),accepted=False,rejections=[])
        info['phase_checks'].append(record)
        if str(solution.status) not in ('Solved','AlmostSolved'):
            record['rejections'].append('solver_status');return None
        point=np.asarray(solution.x,float)
        if point.shape!=(n+2,) or not np.isfinite(point).all():
            record['rejections'].append('finite_complete_point');return None
        raw=point[:n]*trust
        if np.any(raw<lo*trust-1e-9) or np.any(raw>hi*trust+1e-9):
            record['rejections'].append('trust_box');return None
        # Check the exact projected step that will be exported, not solver slack.
        delta=np.clip(raw,lo*trust,hi*trust)
        projection=float(abs(delta-raw).max())
        delta=np.clip(value+delta,lower,upper)-value
        if np.any(delta<reduction.report['proof_delta_lower']) or np.any(delta>reduction.report['proof_delta_upper']):
            record['rejections'].append('certificate_box');return None
        full=(clearance-gaps-surface_jac@delta)/scale
        np.testing.assert_allclose(full.max(),full[retained].max(),atol=1e-10,rtol=1e-12)
        depth=float(max(0.,((-gaps[ids]-surface_jac[ids]@delta-limit)/scale).max())) if len(ids) else 0.
        surface=float(max(0.,full.max()));native_excess=float(native.residual(native_jac,delta).max())
        record.update(predicted_native_excess=native_excess,predicted_partner_depth_deficit=depth,
            full_affine_surface_excess=surface,reported_depth_epigraph=float(point[n]),reported_surface_epigraph=float(point[n+1]),
            trust_projection_maximum_change=projection)
        tolerance=info['phase_lock_tolerance']
        if native_excess>settings.tol_feas:record['rejections'].append('native_conditions')
        if np.any(point[n:] < -settings.tol_feas):record['rejections'].append('nonnegative_epigraphs')
        if depth>max(0.,float(point[n]))+tolerance:record['rejections'].append('depth_epigraph')
        if surface>max(0.,float(point[n+1]))+tolerance:record['rejections'].append('surface_epigraph')
        if depth_bound is not None and depth>depth_bound+tolerance:record['rejections'].append('depth_priority')
        if surface_bound is not None and surface>surface_bound+tolerance:record['rejections'].append('surface_priority')
        record['accepted']=not record['rejections']
        return (point,delta,record) if record['accepted'] else None
    candidate=checked(first,'depth')
    if candidate is None:
        return None,dict(info,status='UnverifiedDepthPhase',invalid_solution=True),reduction
    point,delta,selected=candidate;info['selected_phase']='depth'
    depth_optimum=max(0.,float(point[n]))
    depth_lock = sparse.csc_matrix(np.r_[np.zeros(n),1.,0.][None])
    second_matrix = sparse.vstack([matrix,depth_lock],format='csc')
    second_bound = np.r_[bound,depth_optimum+1e-9]
    second_cones = cones+[solver.NonnegativeConeT(1)]
    second = solver.DefaultSolver(zero,np.r_[np.zeros(n),0.,1.],second_matrix,second_bound,second_cones,settings).solve()
    info.update(depth_phase_optimum=depth_optimum,surface_phase_status=str(second.status),minimum_norm_phase_status='not-run')
    candidate=checked(second,'surface',depth_bound=depth_optimum)
    if candidate is not None:
        point,delta,selected=candidate;info['selected_phase']='surface';surface_optimum=max(0.,float(point[n+1]))
        surface_lock=sparse.csc_matrix(np.r_[np.zeros(n),0.,1.][None])
        third_matrix=sparse.vstack([second_matrix,surface_lock],format='csc')
        third=solver.DefaultSolver(sparse.diags(np.r_[np.ones(n),0.,0.],format='csc'),np.zeros(n+2),
            third_matrix,np.r_[second_bound,surface_optimum+1e-9],second_cones+[solver.NonnegativeConeT(1)],settings).solve()
        info.update(surface_phase_optimum=surface_optimum,minimum_norm_phase_status=str(third.status))
        candidate=checked(third,'minimum-norm',depth_bound=depth_optimum,surface_bound=surface_optimum)
        if candidate is not None:point,delta,selected=candidate;info['selected_phase']='minimum-norm'
    info.update(maximum_control_step=float(abs(delta).max()),predicted_native_excess=selected['predicted_native_excess'],
        trust_projection_maximum_change=selected['trust_projection_maximum_change'],
        full_affine_surface_excess=selected['full_affine_surface_excess'],selected_affine_surface_excess=selected['full_affine_surface_excess'],
        predicted_partner_depth_deficit=selected['predicted_partner_depth_deficit'],
        all_original_affine_surface_rows_evaluated=True, every_guarded_affine_gap_evaluated=True)
    return delta, info, reduction
