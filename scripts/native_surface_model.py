"""Surface-guided proposals with original decoded constraints and full mesh checks.

Fixed axes/barycentric witnesses guide a local solve. Full decoded geometry,
never those witnesses alone, decides whether to retain a motion proposal.
"""
import numpy as np
from scipy import sparse
from native_scene_norms import NormRows, linearize, rows as native_rows
from native_partner_surface_rows import build
from native_surface_lift import lift
from native_scene_conic import direction
from native_scene_restore import tighten


def include_times(problem, times):
    """Add explicit geometry clocks without rebuilding original motion caps."""
    times = np.asarray(times, float)
    if (times.ndim != 1 or not len(times) or not np.isfinite(times).all()
            or np.any(times < 0) or np.any(times > problem.scene.duration)):
        raise ValueError('Finite in-clip surface times required')
    problem.times = np.unique(np.r_[problem.times, times])
    problem.rate_ids = np.searchsorted(problem.times, problem.uniform)
    problem.source_world = {n: np.array([a['sampler'].sample(float(t)) for t in problem.times])
        for n, a in problem.scene.actors.items()}
    for row in problem.rows: row['ids'] = np.searchsorted(problem.times, row['times'])


def surface_points(problem, worlds):
    cache = {}
    def vertices(name, time):
        key = name, float(time)
        if key not in cache:
            i = int(np.searchsorted(problem.times, time))
            if i == len(problem.times) or problem.times[i] != time:
                raise ValueError('Surface clock missing from decoded pose population')
            ids = np.arange(len(problem.scene.actors[name]['skin'].nodes))
            cache[key] = problem.skin_points(name, ids, worlds, np.array([i]), 'vertices')[0]
        return cache[key]
    return vertices


def geometry_score(report):
    """Full audit depth first, then unresolved surface/containment populations."""
    limit = max(report['limits']['penetration_m'], 1e-12)
    depth, records, inside, failed = 0., 0, 0, 0
    for sample in report['samples']:
        if sample['actor_objects']: raise ValueError('Object surface correction is not implemented')
        if any(sample['degenerate_faces'].values()): raise ValueError('Degenerate decoded actor surface')
        for row in sample['world_planes']:
            depth = max(depth, row['maximum_depth_m'] / limit)
            failed += int(not row['passed'])
        for row in sample['actor_pairs']:
            records += len(row['surface']['records'])
            if any(row['surface']['degenerate_faces']): raise ValueError('Degenerate decoded partner surface')
            for measure in row['vertex_containment']:
                if not measure['available']: raise ValueError('Complete partner containment unavailable')
                depth = max(depth, measure['max_depth_m'] / limit)
                inside += measure['vertices_over_tolerance']
            failed += int(not row['passed'])
    return np.array([depth, records, inside, failed], float)


def improved(before, after):
    before, after = np.asarray(before, float), np.asarray(after, float)
    if before.shape != (4,) or after.shape != (4,) or not np.isfinite(np.r_[before,after]).all():
        raise ValueError('Complete finite geometry scores required')
    # A depth regression is never exchanged for fewer crossing records.
    for i, tolerance in enumerate((1e-9, 0., 0., 0.)):
        if after[i] < before[i] - tolerance: return True
        if after[i] > before[i] + tolerance: return False
    return False


def model(problem, value, decoded_scene, policy, digest, trust, *, step=.001, maximum_rows=20000, decoded_worlds=None):
    """Rebuild all witnesses, then combine them with unchanged original norms."""
    value = problem.edits.controls(value)
    original, jac, identity = linearize(problem, value, step=step, difference_source='continuous')
    if decoded_worlds is not None:
        anchored=native_rows(problem,value,decoded_worlds)
        if not np.array_equal(original.caps,anchored.caps) or not np.array_equal(original.scales,anchored.scales):
            raise ValueError('Decoded anchoring changed original norm caps or ordering')
        original=anchored
    witnesses = build(decoded_scene, policy, digest, maximum_rows=maximum_rows)
    if not witnesses.rows: return original, jac, None, dict(differences=identity, surface_rows=0)
    stored = witnesses.gaps()
    np.testing.assert_allclose(stored, witnesses.gaps(surface_points(problem,problem.worlds(value))),atol=2e-10,rtol=0)
    smooth = witnesses.gaps(surface_points(problem, problem.worlds(value, quantized=False)))
    columns = []
    for i in range(len(value)):
        room = problem.upper[i]-value[i] if problem.upper[i]-value[i] >= value[i]-problem.lower[i] else problem.lower[i]-value[i]
        h = np.copysign(min(step, abs(room)), room)
        if h == 0: raise ValueError('No finite-difference room for surface controls')
        other = value.copy(); other[i] += h
        columns.append((witnesses.gaps(surface_points(problem, problem.worlds(other, quantized=False)))-smooth)/h)
    scalar_jac = sparse.csr_matrix(np.stack(columns, axis=1))
    extra, vector_jac, conversion = lift(stored, scalar_jac, value, problem.lower, problem.upper, trust)
    combined = NormRows(np.r_[original.vectors,extra.vectors],np.r_[original.caps,extra.caps],np.r_[original.scales,extra.scales])
    return combined, sparse.vstack([jac,vector_jac],format='csc'), witnesses, dict(
        differences=identity, surface_rows=len(stored), surface_query=witnesses.report,
        conversion=conversion, original_norm_rows=len(original.caps),
        scope='All original norms are protected. Witnesses only guide a local affine proposal; complete decoded audits decide acceptance.')


def optimize(problem, evaluate, iterations=4, trust=.02, *, step=.001, restoration_steps=3):
    """evaluate returns native residuals, worlds, decoded scene/policy and geometry.

    Every candidate must be independently exported/decoded by the caller. Full
    geometry and unchanged native conditions are mandatory, including rejected
    candidates. Originals remain retained; this function grants no approval.
    """
    if (type(iterations) is not int or not 1 <= iterations <= 16
            or type(trust) not in (int,float) or not np.isfinite(trust) or not 1e-6 <= trust <= .02
            or type(step) not in (int,float) or not np.isfinite(step) or not 1e-6 <= step <= .01
            or type(restoration_steps) is not int or not 0 <= restoration_steps <= 4):
        raise ValueError('Bounded surface proposal settings required')
    value = problem.initial.copy(); current = evaluate(value,'start'); history=[]; radius=trust
    initial=np.asarray(current['native'],float)
    if initial.ndim!=1 or not len(initial) or not np.isfinite(initial).all() or np.any(initial > 0):
        raise ValueError('Surface correction requires an originally feasible native/contact start')
    for iteration in range(1, iterations+1):
        if current['geometry']['sampled_conditions_pass']: break
        system,jac,witnesses,identity=model(problem,value,current['scene'],current['policy'],current['digest'],radius,step=step,decoded_worlds=current['worlds'])
        hard = len(current['native'])
        if hard > len(system.caps): raise ValueError('Original norm population changed')
        np.testing.assert_allclose(system.residual()[:hard],current['native'],atol=1e-9,rtol=1e-12)
        delta,info=direction(system,jac,value,problem.lower,problem.upper,radius,hard_rows=hard)
        probes=[]; accepted=None; before=geometry_score(current['geometry']); reserve=None
        def observe(other,label):
            result=evaluate(other,label); native=np.asarray(result['native'],float)
            if native.shape!=(hard,) or not np.isfinite(native).all(): raise ValueError('Complete original decoded native population required')
            score=geometry_score(result['geometry']); safe=bool(np.all(native<=0))
            good=bool(safe and improved(before,score))
            probes.append(dict(label=label,native_pass=safe,geometry_score=score.tolist(),accepted=good))
            return result,good
        if delta is not None:
            for backoff in range(10):
                fraction=.5**backoff; other=np.clip(value+fraction*delta,problem.lower,problem.upper)
                candidate,good=observe(other,f'{iteration}-{backoff}')
                if good: value=other;current=candidate;accepted=fraction;break
                if backoff==0 and np.any(candidate['native']>0):
                    repair_delta=delta
                    for repair in range(restoration_steps):
                        actual=system.residual().copy();actual[:hard]=candidate['native']
                        if witnesses is not None:
                            gaps=witnesses.gaps(surface_points(problem,candidate['worlds']))
                            actual[hard:]=(.0005-gaps)/.005
                        tightened,reserve,_=tighten(system,jac,repair_delta,actual,hard,reserve)
                        repaired,repair_info=direction(tightened,jac,value,problem.lower,problem.upper,radius,hard_rows=hard)
                        if repaired is None: break
                        other=np.clip(value+repaired,problem.lower,problem.upper)
                        candidate,good=observe(other,f'{iteration}-restore-{repair}')
                        probes[-1]['restoration_step']=repair_info
                        if good: value=other;current=candidate;accepted=1.;break
                        if np.all(candidate['native']<=0): break
                        repair_delta=repaired
                    if accepted is not None: break
        history.append(dict(iteration=iteration,before_geometry_score=before.tolist(),
            after_geometry_score=geometry_score(current['geometry']).tolist(),selected_fraction=accepted,
            probes=probes,conic_step=info,model=identity))
        print(iteration,history[-1]['after_geometry_score'],accepted,flush=True)
        if accepted is None:
            radius *= .25
            if radius < 1e-6: break
    return value,dict(history=history,geometry_score=geometry_score(current['geometry']).tolist(),
        maximum_iterations=iterations,trust=trust,all_original_norms_protected=True,
        quality_approved=False,release_approved=False)
