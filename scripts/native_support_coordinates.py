"""Bounded coordinate screens with independently serialized step acceptance.

Rounded-key screens rank proposals. Only the separate export/decoder callback
can accept a step, and the native job still applies its full final audit.
"""
import numpy as np
from scipy.sparse import csr_matrix
from native_support_feasibility import constraint_model, merit


def improves(score, before):
    return (score[0] < before[0]-1e-12 or
            abs(score[0]-before[0]) <= 1e-12 and score[1] < before[1]-1e-15)


def restore(problem, start, evaluate, *, iterations=8, trust=.0002, observe=None):
    """Screen six bounded step sizes; independently decode up to three choices."""
    if (type(iterations) is not int or not 1 <= iterations <= 32 or
            type(trust) not in (int, float) or not np.isfinite(trust) or not 0 < trust <= .001):
        raise ValueError('Choose 1-32 coordinate iterations and up to .001 radians trust')
    x = np.asarray(start, float).copy()
    problem.rotations(x)
    current = np.asarray(evaluate(x, 'start'), float)
    initial = merit(current)
    pattern = csr_matrix(problem.sparsity())
    if pattern.shape != (len(current), len(x)) or not np.isfinite(pattern.data).all():
        raise ValueError('Matching finite coordinate dependency graph required')
    history = []
    radius = float(trust)
    reason = 'iteration_budget'
    fractions = (1., .5, .25, .1, .05, .025)

    def vector(g):
        g = np.asarray(g, float)
        if g.shape != current.shape:
            raise ValueError('Coordinate constraint population changed')
        merit(g)
        return g

    for iteration in range(1, iterations+1):
        before = merit(current)
        if before[0] == 0:
            reason = 'sampled_constraints_satisfied'
            break
        columns = np.flatnonzero(np.asarray(pattern[current > 0].getnnz(axis=0)).ravel())
        row = dict(iteration=iteration, before_merit=list(before),
                   starting_controls=x.tolist(), trust_radians=radius,
                   columns=columns.tolist(), numerical_screens=[], probes=[])
        candidates = []
        seen = set()
        for col in columns:
            for fraction in fractions:
                for sign in (-1, 1):
                    z = x.copy()
                    z[col] = np.clip(z[col]+sign*radius*fraction, problem.lower[col], problem.upper[col])
                    delta = float(z[col]-x[col])
                    identity = (int(col), delta)
                    if delta == 0 or identity in seen:
                        continue
                    seen.add(identity)
                    score = merit(vector(constraint_model(problem, z, quantized=True)))
                    index = len(row['numerical_screens'])
                    row['numerical_screens'].append(dict(column=int(col), delta=delta, proxy_merit=list(score)))
                    if improves(score, before):
                        candidates.append((score, index))
                    if (index+1) % 512 == 0:
                        print(dict(coordinate_iteration=iteration, screened_candidates=index+1,
                                   active_columns=len(columns)), flush=True)
        accepted = None
        # Keep rejected exported proposals as well as numerical screens. A
        # second/third screen can differ from the best proxy after decoding.
        for rank, (_, index) in enumerate(sorted(candidates)[:3]):
            screen = row['numerical_screens'][index]
            z = x.copy()
            z[screen['column']] += screen['delta']
            z = np.clip(z, problem.lower, problem.upper)
            label = f'coordinate-{iteration}-{rank}'
            g = vector(evaluate(z, label))
            score = merit(g)
            ok = improves(score, before)
            row['probes'].append(dict(label=label, screen_index=index,
                                      merit=list(score), accepted=bool(ok)))
            if ok:
                x, current, accepted = z, g, index
                break
        row.update(selected_screen_index=accepted, after_merit=list(merit(current)))
        history.append(row)
        if observe:
            observe(row)
        if accepted is None:
            radius *= .25
            if radius < 1e-9:
                reason = 'coordinate_search_stalled'
                break
    if merit(current)[0] == 0:
        reason = 'sampled_constraints_satisfied'
    return x, dict(initial_merit=list(initial), final_merit=list(merit(current)),
                   history=history, reason=reason, iterations=len(history),
                   maximum_iterations=iterations, trust_radians=trust,
                   step_fractions=list(fractions), maximum_decoded_choices_per_iteration=3,
                   minimum_trust_radians=1e-9, difference_model='float32_key_coordinate_screens',
                   numerical_screens=sum(len(r['numerical_screens']) for r in history),
                   sampled_proxy_feasible=merit(current)[0] == 0, quality_approved=False)
