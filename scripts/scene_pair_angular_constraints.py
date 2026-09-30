"""Append rotation-rate cones without altering existing paired constraints."""
import numpy as np


def append_rows(linear, parts):
    width = linear['gap_jacobian'].shape[1]
    vectors = [linear['vectors']]; jacobians = [linear['jacobians']]
    radii = [linear['radii']]; kinds = [linear['kinds']]
    for offset, value, derivative, caps, labels in parts:
        value, derivative, caps, labels = map(np.asarray, [value, derivative, caps, labels])
        if value.shape != (len(caps), 3) or derivative.ndim != 3 or derivative.shape[:2] != value.shape or labels.shape != caps.shape:
            raise ValueError('Matching angular vectors, derivatives, caps and labels required')
        if type(offset) is not int or offset < 0 or offset+derivative.shape[2] > width:
            raise ValueError('Angular derivative columns outside paired controls')
        if not all(np.isfinite(x).all() for x in [value, derivative, caps]) or np.any(caps < 0):
            raise ValueError('Finite angular rows with nonnegative radii required')
        if not np.isin(labels, ['angular_speed', 'angular_acceleration']).all():
            raise ValueError('Explicit angular norm kind required')
        full = np.zeros((len(caps), 3, width)); full[:, :, offset:offset+derivative.shape[2]] = derivative
        vectors.append(value); jacobians.append(full); radii.append(caps); kinds.append(labels)
    return dict(linear, vectors=np.concatenate(vectors), jacobians=np.concatenate(jacobians),
        radii=np.concatenate(radii), kinds=np.concatenate(kinds))


def linearize_angular(actors, policies, linear):
    if len(actors) != len(policies): raise ValueError('One original angular policy per actor required')
    parts = []; offset = 0; proofs = []
    for actor, policy in zip(actors, policies):
        model = actor['model']; world, derivative = model.world_pair(np.zeros(model.size))
        value, jacobian = policy.values(world, derivative)
        direction = np.random.default_rng(2309+offset).normal(size=model.size)*1e-7
        actual, _ = policy.values(model.world(direction))
        residual = np.linalg.norm(actual-value-np.einsum('nid,d->ni', jacobian, direction), axis=1)
        errors = {kind: float(residual[policy.kinds == kind].max(initial=0)) for kind in ['angular_speed', 'angular_acceleration']}
        if max(errors.values()) > 1e-5: raise ValueError('Independent angular direction failed')
        source_excess = float(np.maximum(np.linalg.norm(value, axis=1)-policy.radii, 0).max(initial=0))
        if source_excess > 1e-8: raise ValueError('Zero edit already violates original angular rows')
        proofs.append(dict(actor=actor['name'], rows=len(value), source_maximum_excess=source_excess, directional_errors=errors))
        parts.append((offset, value, jacobian, policy.radii, policy.kinds)); offset += model.size
    if offset != linear['gap_jacobian'].shape[1]: raise ValueError('Angular actors do not span paired controls')
    return append_rows(linear, parts), proofs
