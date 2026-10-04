"""Contact-protected pose proposals with complete declared triangle audits.

Witness planes guide the search; full geometry and every measured condition
decide retention. This single-pose relaxation never approves an animation.
"""
import copy
import time
import numpy as np
from scipy.optimize import minimize
from native_scene_contacts import scalar
from native_scene_geometry import evaluate, policy_for
from native_partner_surface_rows import build


class PosedScene:
    """Expose one hypothetical pose without changing source clips or requests."""
    def __init__(self, problem, worlds):
        self.source = problem.scene; self.duration = self.source.duration
        self.objects = self.source.objects; self.rows = self.source.rows
        self.object_poses = self.source.object_poses; self.actors = {}
        for name, actor in self.source.actors.items():
            sampler = actor['sampler']; pose = worlds[name]; stamp = problem.time
            class Reader:
                def __init__(self, original, matrix): self.original = original; self.matrix = matrix
                def sample(self, t): return self.matrix.copy() if t == stamp else self.original.sample(t)
                def __getattr__(self, field): return getattr(self.original, field)
            self.actors[name] = dict(actor, sampler=Reader(sampler, pose))
    def check_inputs(self): self.source.check_inputs()


def pose_policy(problem, original, digest):
    policy_for(original, problem.scene, digest)
    if not 0 < problem.time < problem.scene.duration:
        raise ValueError('An interior pose time is required for the three-snapshot diagnostic')
    result = copy.deepcopy(original)
    result['clock'] = dict(mode='explicit', times_s=[0., problem.time, problem.scene.duration])
    return result


def audit(problem, value, policy, digest):
    _, contacts, worlds, vertices = problem.measure(value)
    posed = PosedScene(problem, worlds)
    def observed(name, stamp):
        if stamp == problem.time: return vertices[name]
        actor = problem.scene.actors[name]; p,r = actor['placement']
        return actor['rig'].vertices(actor['sampler'].sample(stamp)) @ r.T+p
    geometry, arrays = evaluate(posed, policy, digest, actor_vertices=observed)
    return contacts, geometry, arrays


def score(residual):
    positive = np.maximum(np.asarray(residual, float), 0)
    if positive.ndim != 1 or not len(positive) or not np.isfinite(positive).all():
        raise ValueError('Complete finite condition residuals required')
    return float(positive.max()), float(positive @ positive)


def acceptable(before, after, geometry):
    before, after = np.asarray(before, float), np.asarray(after, float)
    if (before.ndim != 1 or not len(before) or after.shape != before.shape
            or not np.isfinite(np.r_[before,after]).all()):
        raise ValueError('Matching complete condition populations required')
    # No numerical acceptance allowance is added to a passing authored row.
    if not bool(np.all(after <= np.maximum(before, 0))) or geometry['sampled_conditions_pass'] is not True:
        return False
    old, new = score(before), score(after)
    return bool(new[0] <= old[0] and new[1] < old[1] - 1e-12)


def fit(problem, original_geometry_policy, digest, *, iterations=6, trust=.15, solve_iterations=30,
        maximum_seconds=240., maximum_calls=3000, maximum_surface_rows=20000, observer=None):
    """Only audited nonregressing backoffs can replace the initially valid pose."""
    if type(iterations) is not int or not 1 <= iterations <= 16:
        raise ValueError('Choose 1-16 explicit protected pose iterations')
    if type(solve_iterations) is not int or not 1 <= solve_iterations <= 100:
        raise ValueError('Choose 1-100 explicit local solve iterations')
    trust = scalar(trust, 1e-4, 1., 'raw-coordinate trust box')
    maximum_seconds = scalar(maximum_seconds, 1., 3600., 'protected pose time budget')
    if type(maximum_calls) is not int or not 1 <= maximum_calls <= 50000:
        raise ValueError('Explicit pose measurement budget required')
    if type(maximum_surface_rows) is not int or not 1 <= maximum_surface_rows <= 100000:
        raise ValueError('Explicit complete witness-row budget required')
    policy = pose_policy(problem, original_geometry_policy, digest)
    value = np.zeros(problem.size); baseline, baseline_contacts, _, _ = problem.measure(value)
    if any(not all(c['normals_available']) for c in baseline_contacts['contacts']):
        raise ValueError('All active source contact normals must be available')
    started = time.monotonic(); calls = 0; history = []; trials = []; witness_rows = []
    _, initial_geometry, initial_arrays = audit(problem, value, policy, digest)
    if not initial_geometry['sampled_conditions_pass']:
        raise ValueError('Full declared three-pose geometry must pass at the source start')
    if observer: observer('seed', value.copy(), baseline_contacts, initial_geometry, initial_arrays)
    class BudgetExhausted(Exception): pass
    def check():
        if calls >= maximum_calls or time.monotonic()-started >= maximum_seconds: raise BudgetExhausted()
    def add_guides(candidate):
        check(); _,_,worlds,_ = problem.measure(candidate)
        rows = build(PosedScene(problem, worlds), policy, digest, maximum_rows=maximum_surface_rows)
        if len(witness_rows) + len(rows.rows) > maximum_surface_rows:
            raise ValueError('Complete accumulated witness population exceeds budget; no truncation')
        witness_rows.extend(rows.rows)
        return rows.report
    from native_partner_surface_rows import SurfaceRows
    def vertices_at(vertices):
        def query(name, stamp):
            if stamp == problem.time: return vertices[name]
            actor = problem.scene.actors[name]; p,r = actor['placement']
            return actor['rig'].vertices(actor['sampler'].sample(stamp)) @ r.T+p
        return query
    exhausted = False; stop = 'iteration_limit'
    try:
        source_guides = add_guides(value)
        for iteration in range(iterations):
            check(); base = value.copy(); reference = problem.measure(base)[0]; caps = np.maximum(reference, 0)
            surface = SurfaceRows(problem.scene, list(witness_rows), {})
            base_vertices = problem.measure(base)[3]
            guide_caps = np.minimum(surface.gaps(vertices_at(base_vertices)), -policy['limits']['penetration_m'])
            cache = {}
            def measured(candidate):
                nonlocal calls
                key = np.asarray(candidate, float).tobytes()
                if key not in cache:
                    check(); calls += 1
                    residual, _, _, vertices = problem.measure(candidate)
                    gaps = surface.gaps(vertices_at(vertices))
                    cache[key] = residual, gaps
                return cache[key]
            def objective(candidate):
                positive = np.maximum(measured(candidate)[0], 0)
                return float(positive @ positive + 1e-8 * np.sum((candidate-base)**2))
            def protected(candidate):
                residual, gaps = measured(candidate)
                return np.r_[caps-residual, (gaps-guide_caps)/.005]
            result = minimize(objective, base, method='SLSQP', bounds=list(zip(np.maximum(-20.,base-trust), np.minimum(20.,base+trust))),
                constraints=[dict(type='ineq', fun=protected)], options=dict(maxiter=solve_iterations, ftol=1e-10))
            direction = np.asarray(result.x)-base; accepted = False; rejected_geometry = []
            for fraction in (1., .5, .25, .125, .0625, .03125):
                check(); candidate = base+fraction*direction
                residual, contacts, _, _ = problem.measure(candidate)
                # Always inspect full geometry for every actual backoff trial,
                # including candidates that fail the contact guard.
                _, full, arrays = audit(problem, candidate, policy, digest)
                keep = acceptable(reference, residual, full)
                label = f'iteration-{iteration+1}-backoff-{len(trials)+1}'
                if observer: observer(label, candidate.copy(), contacts, full, arrays)
                trials.append(dict(label=label, iteration=iteration+1, fraction=fraction, controls=candidate.tolist(),
                    row_guard_pass=bool(np.all(residual<=caps)), full_geometry_pass=bool(full['sampled_conditions_pass']),
                    score=list(score(residual)), accepted=keep))
                if keep: value=candidate.copy(); accepted=True; break
                if not full['sampled_conditions_pass']: rejected_geometry.append(candidate.copy())
            history.append(dict(iteration=iteration+1, solver_success=bool(result.success), solver_message=str(result.message),
                solver_iterations=int(result.nit), accepted=accepted, accumulated_witness_rows=len(witness_rows)))
            # Rebuild from the retained full mesh; failed geometry can add new
            # witnesses to a later proposal, without becoming the source epoch.
            add_guides(value)
            for rejected in rejected_geometry: add_guides(rejected)
            if np.all(problem.measure(value)[0] <= 0): stop='pose_conditions_satisfied'; break
    except BudgetExhausted:
        exhausted=True; stop='time_or_measurement_budget'
    final_residual, final_contacts, _, _ = problem.measure(value)
    _, final_geometry, final_arrays = audit(problem, value, policy, digest)
    if observer: observer('final', value.copy(), final_contacts, final_geometry, final_arrays)
    return value, dict(stop=stop, budget_exhausted=bool(exhausted or stop=='iteration_limit'),
        iteration_budget_exhausted=bool(stop=='iteration_limit'), time_or_measurement_budget_exhausted=exhausted,
        elapsed_s=time.monotonic()-started,
        proposal_measurement_calls=calls, iterations=history, trials=trials, accumulated_witness_rows=len(witness_rows),
        initial_score=list(score(baseline)), final_score=list(score(final_residual)),
        original_condition_rows_preserved=bool(np.all(final_residual<=np.maximum(baseline,0))),
        full_declared_three_pose_geometry_pass=bool(final_geometry['sampled_conditions_pass']),
        pose_witness_found=bool(np.all(final_residual<=0) and final_geometry['sampled_conditions_pass']),
        temporal_constraints_checked=False, imported_skin_checked=False, self_collision_checked=False,
        original_selected=True, quality_approved=False, release_approved=False)
