"""Separate nonlinear proposal error from changing serialization error."""
import numpy as np
from hand_norm_proposal import validate


def compare(model, exact, smooth, delta, fractions, describe):
    base = validate(model['base']); point = np.asarray(model['point'], float)
    delta = np.asarray(delta, float); fractions = np.asarray(fractions, float)
    jac = np.asarray(model['jacobian']['vectors'], float)
    if (point.ndim != 1 or not len(point) or delta.shape != point.shape
            or not np.isfinite(point).all() or not np.isfinite(delta).all()
            or jac.shape != base['vectors'].shape+(len(point),) or not np.isfinite(jac).all()
            or fractions.ndim != 1 or not len(fractions) or not np.isfinite(fractions).all()
            or np.any(fractions <= 0) or np.any(fractions > 1) or len(np.unique(fractions)) != len(fractions)):
        raise ValueError('Finite matching saved proposal and unique positive fractions required')
    def checked(fn, x):
        value = validate(fn(x))
        if any(value[k].shape != base[k].shape for k in base) or any(
                not np.array_equal(value[k], base[k]) for k in ['caps', 'scales']):
            raise ValueError('Original populations, caps and scales required')
        return value
    seed = checked(exact, point)
    for k in base:
        np.testing.assert_allclose(seed[k], base[k], rtol=0, atol=1e-12)
    smooth_seed = checked(smooth, point)['vectors']; records = []
    for fraction in fractions:
        step = delta*fraction; candidate = point+step
        if np.any(abs(candidate) > 1): raise ValueError('Candidate exceeds original control bounds')
        serialized = checked(exact, candidate)['vectors']
        unrounded = checked(smooth, candidate)['vectors']
        # The proposal is centered at the exact serialized seed, not the
        # unrounded seed. Isolate curvature and the change in rounding error.
        affine = seed['vectors']+jac@step
        increment = seed['vectors']+unrounded-smooth_seed
        values = dict(affine=affine, unrounded=unrounded, smooth_increment=increment, serialized=serialized)
        norms = {k: np.linalg.norm(v, axis=1) for k, v in values.items()}
        margins = {k: (base['caps']-v)/base['scales'] for k, v in norms.items()}
        failures = {k: v < 0 for k, v in margins.items()}
        ids = np.flatnonzero(np.any(np.stack(list(failures.values())), axis=0))
        records.append(dict(fraction=float(fraction),
            groups={k: dict(failed_rows=int(v.sum()), minimum_margin=float(margins[k].min())) for k,v in failures.items()},
            curvature_only_failures=np.flatnonzero(~failures['affine'] & failures['smooth_increment']).tolist(),
            serialization_only_failures=np.flatnonzero(~failures['smooth_increment'] & failures['serialized']).tolist(),
            rows=[dict(index=int(i), **describe(int(i)), cap=float(base['caps'][i]), scale=float(base['scales'][i]),
                norms={k:float(v[i]) for k,v in norms.items()},
                seed_headroom=float(base['caps'][i]-np.linalg.norm(seed['vectors'][i])),
                curvature_vector_error=float(np.linalg.norm(increment[i]-affine[i])),
                serialization_change_error=float(np.linalg.norm(serialized[i]-increment[i]))) for i in ids]))
    return dict(method='motion_proposal_error_decomposition_v1', trials=records,
                diagnostic_only=True, accepted_for_publication=False, quality_approved=False)
