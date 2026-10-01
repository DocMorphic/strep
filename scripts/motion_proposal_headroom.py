"""Measured-error proposal headroom with unchanged real acceptance caps."""
import numpy as np
from hand_norm_proposal import validate, measurement
from restore_witness_feasibility import direction
from scan_serialized_witness_ray import scan


def tighten(model, diagnostic):
    base = validate(model['base']); reserve = np.zeros(len(base['caps']))
    if diagnostic.get('method') != 'motion_proposal_error_decomposition_v1' or not diagnostic.get('trials'):
        raise ValueError('Measured motion error diagnostic required')
    for trial in diagnostic['trials']:
        seen = set()
        for row in trial['rows']:
            i = row['index']
            if (type(i) is not int or not 0 <= i < len(reserve) or i in seen
                    or row['cap'] != base['caps'][i] or row['scale'] != base['scales'][i]):
                raise ValueError('Unique original motion rows required')
            seen.add(i)
            errors = np.array([row['curvature_vector_error'], row['serialization_change_error']], float)
            norms = np.array(list(row['norms'].values()), float)
            if not np.isfinite(errors).all() or np.any(errors < 0) or not np.isfinite(norms).all():
                raise ValueError('Finite nonnegative observed errors required')
            if row['norms']['serialized'] > row['cap']:
                reserve[i] = max(reserve[i], 2*float(errors.sum())+1e-9*base['scales'][i])
    if not np.any(reserve): raise ValueError('Observed serialized motion failures required')
    caps = base['caps']-reserve
    if np.any(caps < 0): raise ValueError('Headroom exceeds original motion cap')
    proposal = dict(model, base=dict(base, caps=caps))
    return proposal, dict(policy='twice_observed_error_plus_1e-9_normalized',
        rows=[dict(index=int(i), original_cap=float(base['caps'][i]), proposal_cap=float(caps[i]),
                   reserve=float(reserve[i])) for i in np.flatnonzero(reserve)],
        empirical_proposal_target=True, certified_error_bound=False, acceptance_caps_changed=False)


def solve(exact, original, seed, model, diagnostic, solver, *, witness_start, witness_count,
          witness_reserve, observe=None):
    seed = np.asarray(seed, float); np.testing.assert_array_equal(seed, model['point'])
    actual = validate(exact(seed)); base = validate(model['base'])
    for key in base: np.testing.assert_allclose(actual[key], base[key], rtol=0, atol=1e-12)
    reference = validate(exact(original))
    for key in ['caps', 'scales']: np.testing.assert_array_equal(reference[key], base[key])
    before = measurement(reference); ceiling = before['witness_peak_m']-1e-9
    if before['minimum_margin'] < 0: raise ValueError('Feasible original required')
    rows = np.arange(witness_start, witness_start+witness_count)
    proposal, headroom = tighten(model, diagnostic)
    delta, record = direction(proposal, .001, ceiling, rows, witness_reserve, solver)
    if delta is None:
        return None, dict(method='motion_headroom_replay_v1', original=before, seed=measurement(actual),
            final=measurement(actual), final_point=seed.tolist(), proposal=record, headroom=headroom,
            numerically_feasible=False, stop_reason='no_proposal', mesh_validation_required=True,
            accepted_for_publication=False, quality_approved=False)
    # Exact replay continues to use the original caps, not the smaller proposal
    # caps. Every sample is recorded, including motion and geometry failures.
    selected, report = scan(exact, original, seed, delta, witness_start=witness_start,
                            witness_count=witness_count, observe=observe)
    report.update(method='motion_headroom_replay_v1', proposal=record, headroom=headroom)
    return selected, report
