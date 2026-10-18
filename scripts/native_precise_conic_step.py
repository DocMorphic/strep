"""Versioned precise hinge guidance with exact affine vector norm constraints.

The earlier native_conic_hinge_step kernel stays immutable for old evidence.
This version permits only tighter feasibility targets. It proposes a direction only. Every nonlinear/raw/saved motion gate remains
the caller's responsibility. Solver tolerances are not physical tolerances.
"""
import numpy as np
from scipy import sparse
from native_world_hinge_step import _real
from native_scene_conic import solver_module

MAXIMUM_BYTES = 64 * 1024**2


def conic_hinge_step(margins, jacobian, lower_delta, upper_delta, native_vectors,
                     native_matrix, native_radii, *, extra_matrix=None,
                     extra_upper=None, l1_penalty=1e-5,
                     maximum_model_violation=None,
                     solver_box_reserve=1e-9,
                     solver_feasibility_tolerance=1e-12,
                     proposal_fractions=(1.,),
                     maximum_matrix_bytes=MAXIMUM_BYTES,
                     time_limit_seconds=30., maximum_iterations=200):
    if (not isinstance(proposal_fractions, (tuple, list)) or not 1 <= len(proposal_fractions) <= 8
            or any(type(v) not in (int, float) or not np.isfinite(v) or not 1e-6 <= v <= 1 for v in proposal_fractions)
            or proposal_fractions[0] != 1 or any(a <= b for a, b in zip(proposal_fractions, proposal_fractions[1:]))):
        raise ValueError('Explicit descending bounded proposal fractions starting at1 required')
    if (type(solver_feasibility_tolerance) not in (int, float) or not np.isfinite(solver_feasibility_tolerance)
            or not 1e-14 <= solver_feasibility_tolerance <= 1e-10):
        raise ValueError('Feasibility target must tighten the earlier1e-10 target, never a physical tolerance')
    if type(maximum_matrix_bytes) is not int or not 1 <= maximum_matrix_bytes <= MAXIMUM_BYTES:
        raise ValueError('Complete storage budget up to64MiB required')
    if type(solver_box_reserve) not in (int, float) or not np.isfinite(solver_box_reserve) or not 0 <= solver_box_reserve <= 1e-5:
        raise ValueError('Explicit finite bounded interior solver box reserve required')
    if type(l1_penalty) not in (int, float) or not np.isfinite(l1_penalty) or not 1e-12 <= l1_penalty <= 1:
        raise ValueError('Finite bounded positive L1 penalty required')
    if (type(time_limit_seconds) not in (int, float) or not np.isfinite(time_limit_seconds)
            or not .01 <= time_limit_seconds <= 60 or type(maximum_iterations) is not int
            or not 1 <= maximum_iterations <= 10000):
        raise ValueError('Bounded solver time and iteration limits required')
    if maximum_model_violation is not None and (type(maximum_model_violation) not in (int, float)
            or not np.isfinite(maximum_model_violation) or not 0 <= maximum_model_violation <= 1e6):
        raise ValueError('Finite nonnegative bounded model peak ceiling required')
    raw = np.asarray(jacobian); values = np.asarray(native_vectors)
    if raw.ndim != 2 or not 1 <= raw.shape[0] <= 8192 or not 1 <= raw.shape[1] <= 768:
        raise ValueError('Complete bounded model rows and columns required')
    rows, columns = raw.shape
    if values.ndim != 2 or values.shape[1] != 3 or not 1 <= len(values) <= 65536:
        raise ValueError('Every native three-vector required')
    balls = len(values)
    if not sparse.issparse(native_matrix) or native_matrix.format not in ('csr', 'csc'):
        raise ValueError('Complete CSR or CSC native matrix required before allocation')
    if native_matrix.shape != (3 * balls, columns):
        raise ValueError('Complete native vector rows and matching columns required')
    if (extra_matrix is None) != (extra_upper is None):
        raise ValueError('Complete extra matrix and upper bound pair required')
    cuts = np.empty((0, columns)) if extra_matrix is None else np.asarray(extra_matrix)
    upper = np.empty(0) if extra_upper is None else np.asarray(extra_upper)
    if cuts.ndim != 2 or cuts.shape[1] != columns or len(cuts) > 8192 or upper.shape != (len(cuts),):
        raise ValueError('Complete matching extra rows and columns required')
    input_bytes = (raw.size + cuts.size + values.size + rows + balls + 2 * columns + len(cuts)) * 8
    input_bytes += native_matrix.data.nbytes + native_matrix.indices.nbytes + native_matrix.indptr.nbytes
    if input_bytes > maximum_matrix_bytes:
        raise ValueError('Complete model input exceeds budget; no truncation')
    margin, jac, lo, hi, vectors, radii, cuts, upper = [_real(v) for v in
        (margins, raw, lower_delta, upper_delta, values, native_radii, cuts, upper)]
    if margin.shape != (rows,) or np.any(abs(margin) > 1e6):
        raise ValueError('Complete bounded signed margins required')
    if (lo.shape != (columns,) or hi.shape != (columns,) or np.any(lo > 0)
            or np.any(hi < 0) or np.any(lo > hi) or np.any(lo < -2) or np.any(hi > 2)):
        raise ValueError('Complete boxes containing zero within [-2,2] required')
    if radii.shape != (balls,) or np.any(radii <= 0) or np.any(radii > 1e6):
        raise ValueError('Complete finite positive bounded native radii required')
    # Restrict the proposal solver inside the caller's unchanged boxes. This is
    # a documented search restriction, never output clipping or gate tolerance.
    solve_lo = np.minimum(0., lo + solver_box_reserve)
    solve_hi = np.maximum(0., hi - solver_box_reserve)
    _real(native_matrix.data)
    native_matrix.check_format(full_check=True)
    nonzeros = int(np.count_nonzero(jac) + 2 * rows + 8 * columns + np.count_nonzero(cuts) + native_matrix.nnz)
    linear_rows = 2 * rows + 6 * columns + len(cuts)
    if maximum_model_violation is not None:
        nonzeros += int(np.count_nonzero(jac)); linear_rows += rows
    variables = 2 * columns + rows
    estimated_bytes = 12 * nonzeros + 4 * (variables + 1)
    if estimated_bytes > maximum_matrix_bytes:
        raise ValueError('Complete sparse constraint matrix exceeds budget before allocation')
    transform = sparse.csr_matrix(native_matrix, dtype=float, copy=True)
    transform.sum_duplicates(); transform.eliminate_zeros()
    if not np.isfinite(transform.data).all():
        raise ValueError('Finite summed native matrix required')
    identity = sparse.eye(columns, format='csc'); zero = sparse.csc_matrix
    block = lambda a, b, c: sparse.hstack([a, b, c], format='csc')
    zcr = zero((columns, rows)); zrc = zero((rows, columns))
    matrices = [block(-sparse.csc_matrix(jac), zrc, -sparse.eye(rows, format='csc')),
        block(identity, -identity, zcr), block(-identity, -identity, zcr),
        block(identity, zero((columns, columns)), zcr),
        block(-identity, zero((columns, columns)), zcr),
        block(zero((columns, columns)), -identity, zcr),
        block(zero((columns, columns)), identity, zcr),
        block(zero((rows, columns)), zrc, -sparse.eye(rows, format='csc')),
        sparse.hstack([sparse.csc_matrix(cuts), zero((len(cuts), columns + rows))], format='csc')]
    rhs = [margin, np.zeros(2 * columns), solve_hi, -solve_lo, np.zeros(columns),
           np.maximum(-solve_lo, solve_hi), np.zeros(rows), upper]
    if maximum_model_violation is not None:
        matrices.append(block(-sparse.csc_matrix(jac), zrc, zero((rows, rows))))
        rhs.append(margin + maximum_model_violation)
    coo = transform.tocoo()
    mapped_rows = 4 * (coo.row // 3) + 1 + coo.row % 3
    native_block = sparse.csc_matrix((-coo.data, (mapped_rows, coo.col)), shape=(4 * balls, variables))
    matrices.append(native_block); rhs.append(np.c_[radii, vectors].ravel())
    matrix = sparse.vstack(matrices, format='csc'); bound = np.concatenate(rhs)
    matrix.sum_duplicates(); matrix.eliminate_zeros()
    actual_bytes = matrix.data.nbytes + matrix.indices.nbytes + matrix.indptr.nbytes
    if actual_bytes > maximum_matrix_bytes:
        raise ValueError('Complete sparse constraint matrix exceeds budget')
    assert matrix.shape == (linear_rows + 4 * balls, variables)
    solver = solver_module(); settings = solver.DefaultSettings()
    settings.verbose = False; settings.max_iter = maximum_iterations
    settings.time_limit = float(time_limit_seconds)
    settings.tol_gap_abs = settings.tol_gap_rel = 1e-10
    settings.tol_feas = float(solver_feasibility_tolerance)
    if hasattr(settings, 'max_threads'): settings.max_threads = 1
    cones = [solver.NonnegativeConeT(linear_rows)] + [solver.SecondOrderConeT(4) for _ in range(balls)]
    objective = np.r_[np.zeros(columns), np.full(columns, l1_penalty), np.ones(rows)]
    solution = solver.DefaultSolver(zero((variables, variables)), objective, matrix, bound, cones, settings).solve()
    direction = None; linear_residual = None; native_excess = None; box_excess = None; worst_norm = None; failed_norms = None
    trial_reports=[];chosen_fraction=None;raw_admission=None;raw_native_excess=None
    if str(solution.status) in ('Solved', 'AlmostSolved'):
        point = np.asarray(solution.x, float)
        if point.shape == (variables,) and np.isfinite(point).all():
            candidate = point[:columns]
            linear_residual = float(np.max(matrix[:linear_rows] @ point - bound[:linear_rows]))
            norm_excesses = np.linalg.norm(vectors + (transform @ candidate).reshape(-1, 3), axis=1) - radii
            worst_norm = int(np.argmax(norm_excesses)); native_excess = float(norm_excesses[worst_norm])
            failed_norms = int(np.count_nonzero(norm_excesses > 1e-8))
            box_excess = float(max(np.max(lo - candidate), np.max(candidate - hi)))
            raw_admission=bool(box_excess <= 0 and linear_residual <= 1e-7 and native_excess <= 1e-8)
            raw_native_excess=native_excess
            trial_reports.append(dict(fraction=1.,accepted=raw_admission,maximum_norm_excess=native_excess,maximum_linear_residual=linear_residual,maximum_box_excess=box_excess))
            if raw_admission:direction=candidate.copy();chosen_fraction=1.
            else:
                baseline_cost=float(np.maximum(-margin,0).sum())
                for fraction in proposal_fractions[1:]:
                    # A separately checked ray proposal, never coordinate clipping.
                    trial=float(fraction)*candidate;predicted_trial=margin+jac@trial
                    primal=np.r_[trial,np.abs(trial),np.maximum(-predicted_trial,0)]
                    trial_linear=float(np.max(matrix[:linear_rows]@primal-bound[:linear_rows]))
                    trial_norms=np.linalg.norm(vectors+(transform@trial).reshape(-1,3),axis=1)-radii
                    trial_native=float(np.max(trial_norms));trial_box=float(max(np.max(lo-trial),np.max(trial-hi)))
                    hard=float(np.max(cuts@trial-upper)) if len(cuts) else 0.
                    peak=float(np.max(-predicted_trial)-maximum_model_violation) if maximum_model_violation is not None else 0.
                    cost=float(np.maximum(-predicted_trial,0).sum())
                    accepted=bool(trial_box<=0 and trial_linear<=1e-7 and trial_native<=0 and hard<=0 and peak<=0 and cost<baseline_cost)
                    trial_reports.append(dict(fraction=float(fraction),accepted=accepted,maximum_norm_excess=trial_native,maximum_linear_residual=trial_linear,maximum_box_excess=trial_box,
                        maximum_extra_residual=hard,maximum_peak_residual=peak,predicted_sum_model_violation=cost,strict_norm_and_hard_rows=True))
                    if accepted:
                        direction=trial.copy();chosen_fraction=float(fraction);linear_residual=trial_linear;native_excess=trial_native;box_excess=trial_box
                        worst_norm=int(np.argmax(trial_norms));failed_norms=int(np.count_nonzero(trial_norms>1e-8));break
    predicted = None if direction is None else margin + jac @ direction
    report = dict(schema='strep-native-precise-conic-hinge-step-v1', solver_version=solver.__version__,
        solver_status=str(solution.status), iterations=solution.iterations,
        model_rows=rows, extra_proposal_rows=len(cuts), complete_columns=columns,
        native_cones=balls, omitted_native_cones=0,
        fixed_native_cones=int(np.count_nonzero(np.diff(transform.indptr).reshape(-1, 3).sum(axis=1) == 0)),
        linear_constraint_rows=linear_rows, sparse_matrix_bytes=actual_bytes,
        estimated_sparse_matrix_bytes=estimated_bytes, input_bytes=input_bytes,
        solver_box_reserve=float(solver_box_reserve),
        solver_feasibility_tolerance=float(solver_feasibility_tolerance),
        proposal_fractions=[float(v) for v in proposal_fractions],selected_fraction=chosen_fraction,proposal_trials=trial_reports,
        raw_solver_admission_pass=raw_admission,raw_solver_native_norm_excess=raw_native_excess,
        worst_norm_row=worst_norm, norms_exceeding_admission=failed_norms,
        usable_direction=direction is not None, maximum_linear_constraint_residual=linear_residual,
        maximum_native_norm_excess=native_excess, maximum_box_excess=box_excess,
        baseline_sum_model_violation=float(np.maximum(-margin, 0).sum()),
        predicted_sum_model_violation=None if predicted is None else float(np.maximum(-predicted, 0).sum()),
        maximum_model_violation=maximum_model_violation,
        original_selected=True, quality_approved=False, release_approved=False,
        scope='Optional predeclared ray fractions are separately checked with strict affine norm/extra/peak bounds and lower model cost; default full proposal only. No coordinate clipping. All supplied signed rows, columns and affine norm cones retained, including fixed cones. No clipping. Diagnostic solver tolerances never replace strict raw/saved motion acceptance; neither solver status proves nonlinear feasibility or infeasibility.')
    return direction, report
