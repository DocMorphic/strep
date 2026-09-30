"""Refresh paired surface models without rebasing original animation limits."""
import numpy as np
from scene_pair_angular_constraints import append_rows


def angular_at(actors, policies, linear, controls):
    sizes = [a['model'].size for a in actors]
    controls = np.asarray(controls, float)
    if len(actors) != len(policies) or controls.shape != (sum(sizes),) or not np.isfinite(controls).all():
        raise ValueError('Matching finite cumulative controls and original angular policies required')
    parts = []; proofs = []; offset = 0
    for actor, policy, size in zip(actors, policies, sizes):
        model = actor['model']; current = controls[offset:offset+size]
        world, derivative = model.world_pair(current)
        value, jacobian = policy.values(world, derivative)
        direction = np.random.default_rng(2309+offset).normal(size=size)*1e-7
        actual, _ = policy.values(model.world(current+direction))
        residual = np.linalg.norm(actual-value-np.einsum('nid,d->ni', jacobian, direction), axis=1)
        errors = {kind: float(residual[policy.kinds == kind].max(initial=0))
                  for kind in ['angular_speed', 'angular_acceleration']}
        if max(errors.values()) > 1e-5:
            raise ValueError('Nonzero angular directional derivative failed')
        # Infeasible iterates must be diagnosed, not silently become new caps.
        excess = float(np.maximum(np.linalg.norm(value, axis=1)-policy.radii, 0).max(initial=0))
        proofs.append(dict(actor=actor['name'], current_maximum_excess=excess, directional_errors=errors))
        parts.append((offset, value, jacobian, policy.radii, policy.kinds)); offset += size
    return append_rows(linear, parts), proofs


def refreshed_problem(actors, original_samples, current_samples):
    from scene_pair_problem import ScenePairProblem
    # Validate both clocks/populations before preserving the original ceilings.
    original = ScenePairProblem(actors, original_samples)
    current = ScenePairProblem(actors, current_samples)
    caps = np.array([max(.005, max(d['maximum_depth_m'] for d in row['directions'])) for row in original_samples])
    if not np.isfinite(caps).all(): raise ValueError('Finite original depth caps required')
    for group in current.groups:
        group['caps'] = caps[group['frames']].copy()
    return original, current


def retain_original_surfaces(current, original):
    """Keep original surface bounds alongside refreshed proposal witnesses."""
    for name in ['vectors', 'jacobians', 'radii', 'kinds']:
        np.testing.assert_array_equal(current[name], original[name])
    result = dict(current)
    for name in ['gaps', 'gap_jacobian', 'depth_caps', 'surface_vectors', 'surface_jacobians']:
        result[name] = np.concatenate([current[name], original[name]])
    return result
