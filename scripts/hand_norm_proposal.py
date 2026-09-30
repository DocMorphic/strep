"""Local vector-norm proposals; only exact evaluations can accept a step."""
import numpy as np
from scipy import sparse
from scipy.spatial.transform import Rotation
from sampled_motion_caps import measures


def rate_vectors(payload, dt):
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError('Positive finite sample interval required')
    # Reuse the acceptance path's shape, rotation and angular-branch checks.
    measures(payload, dt)
    p = np.asarray(payload['positions'], float); r = np.asarray(payload['rotations'], float)
    angular = Rotation.from_matrix((r[1:] @ r[:-1].transpose(0, 1, 3, 2)).reshape(-1, 3, 3))
    angular = angular.as_rotvec().reshape(len(p)-1, p.shape[1], 3)/dt
    return [np.diff(p, axis=0)/dt, np.diff(p, n=2, axis=0)/dt**2,
            angular, np.diff(angular, axis=0)/dt]


def validate(sample):
    value = {key: np.asarray(sample[key], float) for key in ['vectors', 'caps', 'scales', 'margins', 'depths']}
    v, c, s, m, d = [value[k] for k in ['vectors', 'caps', 'scales', 'margins', 'depths']]
    if (v.ndim != 2 or v.shape[1] != 3 or not len(v) or c.shape != (len(v),) or s.shape != c.shape
            or m.ndim != 1 or not len(m) or d.ndim != 1 or not len(d)
            or any(not a.size or not np.isfinite(a).all() for a in value.values())
            or np.any(c < 0) or np.any(s <= 0)):
        raise ValueError('Matching finite vectors, nonnegative caps, positive scales and nonempty scalar rows required')
    return value


def measurement(sample):
    sample = validate(sample)
    return dict(witness_peak_m=max(0., float(sample['depths'].max())),
                minimum_margin=float(min(sample['margins'].min(),
                    ((sample['caps']-np.linalg.norm(sample['vectors'], axis=1))/sample['scales']).min())))


def linearize(exact, smooth, point, step=1e-4, observe=None):
    point = np.asarray(point, float)
    if (point.ndim != 1 or not len(point) or not np.isfinite(point).all()
            or not np.isfinite(step) or step <= 0 or np.any(np.abs(point)+step > 1)):
        raise ValueError('Interior normalized coordinates and positive central-difference step required')
    base = validate(exact(point)); jac = {k: np.empty(base[k].shape+(len(point),)) for k in ['vectors', 'margins', 'depths']}
    for column in range(len(point)):
        offset = np.zeros(len(point)); offset[column] = step
        samples = [validate(smooth(point+offset)), validate(smooth(point-offset))]
        for sample in samples:
            if any(sample[k].shape != base[k].shape for k in base):
                raise ValueError('Fixed derivative population required')
            for key in ['caps', 'scales']:
                if not np.array_equal(sample[key], base[key]):
                    raise ValueError('Original caps and scales must remain fixed')
        for key in jac: jac[key][..., column] = (samples[0][key]-samples[1][key])/(2*step)
        if observe: observe(column+1, len(point))
    return dict(base=base, jacobian=jac, point=point.copy(), step=float(step))


def assemble(model, trust):
    """Return A, b for A z + slack = b; z contains bounded step and epigraph.

    Omitted norms are certified inside their caps over this affine step box by
    the triangle inequality. This does not certify the nonlinear animation.
    """
    base = validate(model['base']); jac = model['jacobian']; point = np.asarray(model['point'])
    width = len(point)
    if not np.isfinite(trust) or trust <= 0 or np.any(np.abs(point) > 1):
        raise ValueError('Positive finite trust and bounded coordinates required')
    for key in ['vectors', 'margins', 'depths']:
        if jac[key].shape != base[key].shape+(width,) or not np.isfinite(jac[key]).all():
            raise ValueError('Matching finite proposal Jacobians required')
    lower = np.maximum(-1., (-1.-point)/trust); upper = np.minimum(1., (1.-point)/trust)
    def extra(matrix): return sparse.hstack([sparse.csc_matrix(matrix), sparse.csc_matrix((matrix.shape[0], 1))], format='csc')
    mats = [extra(-jac['margins']*trust), extra(np.eye(width)), extra(-np.eye(width)),
            sparse.csc_matrix(np.c_[jac['depths']*trust/.02, -np.ones(len(base['depths']))]),
            sparse.csc_matrix(np.r_[np.zeros(width), -1.][None, :])]
    rhs = [base['margins'], upper, -lower, -base['depths']/.02, np.zeros(1)]
    linear_count = sum(len(b) for b in rhs)
    magnitude = np.linalg.norm(base['vectors'], axis=1)
    reach = (np.linalg.norm(jac['vectors'], axis=1)*np.maximum(np.abs(lower), np.abs(upper))*trust).sum(axis=1)
    reserve = 4*(width+4)*np.finfo(float).eps*np.maximum(1., magnitude+reach+base['caps'])+1e-12
    keep = np.flatnonzero(magnitude+reach+reserve >= base['caps'])
    for row in keep:
        matrix = np.vstack([np.zeros(width), -jac['vectors'][row]*trust])/base['scales'][row]
        mats.append(extra(matrix)); rhs.append(np.r_[base['caps'][row], base['vectors'][row]]/base['scales'][row])
    return sparse.vstack(mats, format='csc'), np.concatenate(rhs), dict(
        linear_rows=linear_count, norm_rows=len(base['vectors']), retained_norm_rows=keep.tolist(),
        omitted_norm_rows=len(base['vectors'])-len(keep), trust=float(trust))


def direction(model, trust, solver):
    a, b, record = assemble(model, trust); width = len(model['point'])
    cones = [solver.NonnegativeConeT(record['linear_rows'])]
    cones.extend(solver.SecondOrderConeT(4) for _ in record['retained_norm_rows'])
    settings = solver.DefaultSettings(); settings.verbose = False
    settings.max_iter = 100; settings.time_limit = 30.
    settings.tol_gap_abs = settings.tol_gap_rel = settings.tol_feas = 1e-10
    if hasattr(settings, 'max_threads'): settings.max_threads = 1
    p = sparse.diags(np.r_[np.repeat(1e-8, width), 0.], format='csc')
    result = solver.DefaultSolver(p, np.r_[np.zeros(width), 1.], a, b, cones, settings).solve()
    z = np.asarray(result.x); record.update(status=str(result.status), iterations=result.iterations)
    # Avoid putting thousands of row IDs in every summary; their count suffices.
    record['retained_norm_count'] = len(record.pop('retained_norm_rows'))
    if str(result.status) not in ['Solved', 'AlmostSolved'] or z.shape != (width+1,) or not np.isfinite(z).all():
        return None, record
    delta = z[:-1]*trust; point = model['point']; base = model['base']; jac = model['jacobian']
    if np.any(np.abs(delta) > trust+1e-12) or np.any(np.abs(point+delta) > 1):
        return None, dict(record, rejected='step bounds')
    predicted = dict(base, vectors=base['vectors']+jac['vectors']@delta,
                     margins=base['margins']+jac['margins']@delta, depths=base['depths']+jac['depths']@delta)
    record.update(predicted=measurement(predicted), epigraph_m=float(z[-1]*.02), delta=delta.tolist())
    return delta, record


def backtrack(exact, point, delta, base, fractions=(1., .5, .25, .125, .0625, .03125, .015625, .0078125)):
    point, delta = np.asarray(point, float), np.asarray(delta, float)
    fractions = np.asarray(fractions, float)
    if (point.ndim != 1 or delta.shape != point.shape or not np.isfinite(point).all() or not np.isfinite(delta).all()
            or np.any(np.abs(point) > 1) or fractions.ndim != 1 or not len(fractions)
            or not np.isfinite(fractions).all() or np.any(fractions <= 0) or np.any(fractions > 1)):
        raise ValueError('Finite matching steps and fractions in (0, 1] required')
    before = measurement(base)
    if before['minimum_margin'] < 0: raise ValueError('Motion-feasible starting point required')
    records = []
    for fraction in fractions:
        candidate = point+fraction*delta
        if np.any(np.abs(candidate) > 1):
            records.append(dict(fraction=float(fraction), accepted=False, reason='control bounds')); continue
        try: value = validate(exact(candidate))
        except ValueError as error:
            if 'outside two-bone reach' not in str(error): raise
            records.append(dict(fraction=float(fraction), accepted=False, reason='outside two-bone reach')); continue
        if any(value[k].shape != base[k].shape for k in base) or any(not np.array_equal(value[k], base[k]) for k in ['caps', 'scales']):
            raise ValueError('Acceptance population and caps changed')
        metric = measurement(value)
        accepted = metric['minimum_margin'] >= 0 and metric['witness_peak_m'] < before['witness_peak_m']-1e-9
        records.append(dict(fraction=float(fraction), accepted=bool(accepted), **metric))
        if accepted: return candidate, records
    return None, records
