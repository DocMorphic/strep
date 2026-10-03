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


def model(problem, value, decoded_scene, policy, digest, trust, *, step=.001, maximum_rows=20000, decoded_worlds=None, contact_model=None):
    """Rebuild all witnesses, then combine them with unchanged original norms."""
    value = problem.edits.controls(value)
    original, jac, identity = linearize(problem, value, step=step, difference_source='continuous')
    if decoded_worlds is not None:
        anchored=native_rows(problem,value,decoded_worlds)
        if not np.array_equal(original.caps,anchored.caps) or not np.array_equal(original.scales,anchored.scales):
            raise ValueError('Decoded anchoring changed original norm caps or ordering')
        original=anchored
    witnesses = build(decoded_scene, policy, digest, maximum_rows=maximum_rows)
    if not witnesses.rows:
        report=dict(differences=identity,surface_rows=0)
        if contact_model is None:return original,jac,None,report
        extra,extra_jac,contact_identity=contact_model.linearize(value,decoded_worlds if decoded_worlds is not None else problem.worlds(value),trust,step=step)
        combined=NormRows(np.r_[original.vectors,extra.vectors],np.r_[original.caps,extra.caps],np.r_[original.scales,extra.scales])
        report['contact_guidance']=contact_identity
        return combined,sparse.vstack([jac,extra_jac],format='csc'),None,report
    stored = witnesses.gaps()
    np.testing.assert_allclose(stored, witnesses.gaps(surface_points(problem,problem.worlds(value))),atol=2e-10,rtol=0)
    if decoded_worlds is not None:
        anchored=witnesses.gaps(surface_points(problem,decoded_worlds))
        np.testing.assert_allclose(stored,anchored,atol=2e-10,rtol=0)
        stored=anchored
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
    matrix=sparse.vstack([jac,vector_jac],format='csc')
    report=dict(
        differences=identity, surface_rows=len(stored), surface_query=witnesses.report,
        conversion=conversion, original_norm_rows=len(original.caps),
        scope='All original norms are protected. Witnesses only guide a local affine proposal; complete decoded audits decide acceptance.')
    if contact_model is not None:
        extra,extra_jac,contact_identity=contact_model.linearize(value,decoded_worlds if decoded_worlds is not None else problem.worlds(value),trust,step=step)
        combined=NormRows(np.r_[combined.vectors,extra.vectors],np.r_[combined.caps,extra.caps],np.r_[combined.scales,extra.scales])
        matrix=sparse.vstack([matrix,extra_jac],format='csc');report['contact_guidance']=contact_identity
    return combined,matrix,witnesses,report


def optimize(problem, evaluate, iterations=4, trust=.02, *, step=.001, restoration_steps=3, contact_model=None):
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
    value = problem.initial.copy(); current = evaluate(value,'start'); history=[]; radius=trust;geometry_guard_used=False
    initial=np.asarray(current['native'],float)
    if initial.ndim!=1 or not len(initial) or not np.isfinite(initial).all() or np.any(initial > 0):
        raise ValueError('Surface correction requires an originally feasible native/contact start')
    for iteration in range(1, iterations+1):
        if current['geometry']['sampled_conditions_pass'] and (contact_model is None or current['surface_contact']['surface_contacts_pass']): break
        system,jac,witnesses,identity=model(problem,value,current['scene'],current['policy'],current['digest'],radius,step=step,decoded_worlds=current['worlds'],contact_model=contact_model)
        hard = len(current['native'])
        if hard > len(system.caps): raise ValueError('Original norm population changed')
        np.testing.assert_allclose(system.residual()[:hard],current['native'],atol=1e-9,rtol=1e-12)
        probes=[]; accepted=None; before=geometry_score(current['geometry']); reserve=None
        contact_before=None if contact_model is None else contact_model.residual(current['worlds'])
        protected=hard
        if contact_model is not None:
            from native_contact_norms import protect_rows
            system,jac,guard_identity=protect_rows(system,jac,hard,contact_before)
            protected=guard_identity['hard_rows'];identity['contact_protection']=guard_identity
        contact_end=protected;geometry_rows=0 if witnesses is None else len(witnesses.rows)
        if geometry_rows:
            from native_geometry_norms import protect_worst
            system,jac,geometry_identity=protect_worst(system,jac,protected,geometry_rows)
            protected=geometry_identity['hard_rows'];identity['geometry_protection']=geometry_identity
            geometry_guard_used=True
        delta,info=direction(system,jac,value,problem.lower,problem.upper,radius,hard_rows=protected)
        def observe(other,label):
            result=evaluate(other,label); native=np.asarray(result['native'],float)
            if native.shape!=(hard,) or not np.isfinite(native).all(): raise ValueError('Complete original decoded native population required')
            score=geometry_score(result['geometry']); safe=bool(np.all(native<=0))
            good=bool(safe and improved(before,score));contact_score=None
            if contact_model is not None:
                from native_contact_norms import score as contact_merit,improved as contact_improved,nonregressing,row_regression
                contact_actual=contact_model.residual(result['worlds']);contact_score=contact_merit(contact_actual).tolist()
                regression=row_regression(contact_before,contact_actual)
                good=bool(safe and np.all(regression<=0) and not improved(score,before) and nonregressing(contact_before,contact_actual)
                    and (improved(before,score) or contact_improved(contact_before,contact_actual)))
            probes.append(dict(label=label,native_pass=safe,geometry_score=score.tolist(),surface_contact_merit=contact_score,accepted=good))
            if contact_model is not None:
                probes[-1].update(contact_rows_nonregressing=bool(np.all(regression<=0)),
                    maximum_contact_row_regression=float(max(0.,regression.max())))
            if geometry_rows:
                probes[-1]['maximum_geometry_proxy_guard_excess']=float(max(0.,actual_rows(result)[contact_end:protected].max()))
            return result,good
        def actual_rows(candidate):
            actual=system.residual().copy();actual[:hard]=candidate['native']
            if witnesses is not None:
                gaps=witnesses.gaps(surface_points(problem,candidate['worlds']))
                actual[protected:protected+geometry_rows]=(.0005-gaps)/.005
                offsets=np.asarray(identity['conversion']['offset_m'])
                actual[contact_end:protected]=NormRows(np.c_[offsets-gaps,np.zeros((len(gaps),2))],
                    system.caps[contact_end:protected],system.scales[contact_end:protected]).residual()
            if contact_model is not None:
                from native_contact_norms import row_regression
                contact_actual=contact_model.residual(candidate['worlds'])
                actual[hard:contact_end]=row_regression(contact_before,contact_actual)
                actual[protected+geometry_rows:]=contact_actual
            return actual
        if delta is not None:
            for backoff in range(10):
                fraction=.5**backoff; other=np.clip(value+fraction*delta,problem.lower,problem.upper)
                candidate,good=observe(other,f'{iteration}-{backoff}')
                if good: value=other;current=candidate;accepted=fraction;break
                if backoff==0 and np.any(actual_rows(candidate)[:protected]>0):
                    repair_delta=delta
                    for repair in range(restoration_steps):
                        actual=actual_rows(candidate)
                        tightened,reserve,_=tighten(system,jac,repair_delta,actual,protected,reserve)
                        repaired,repair_info=direction(tightened,jac,value,problem.lower,problem.upper,radius,hard_rows=protected)
                        if repaired is None: break
                        other=np.clip(value+repaired,problem.lower,problem.upper)
                        candidate,good=observe(other,f'{iteration}-restore-{repair}')
                        probes[-1]['restoration_step']=repair_info
                        if good: value=other;current=candidate;accepted=1.;break
                        if np.all(actual_rows(candidate)[:protected]<=0): break
                        repair_delta=repaired
                    if accepted is not None: break
        history.append(dict(iteration=iteration,before_geometry_score=before.tolist(),
            after_geometry_score=geometry_score(current['geometry']).tolist(),selected_fraction=accepted,
            probes=probes,conic_step=info,model=identity))
        if contact_model is not None:
            from native_contact_norms import score as contact_merit
            history[-1].update(before_surface_contact_merit=contact_merit(contact_before).tolist(),
                after_surface_contact_merit=contact_merit(contact_model.residual(current['worlds'])).tolist())
        print(iteration,history[-1]['after_geometry_score'],accepted,flush=True)
        if accepted is None:
            radius *= .25
            if radius < 1e-6: break
    return value,dict(history=history,geometry_score=geometry_score(current['geometry']).tolist(),
        maximum_iterations=iterations,trust=trust,all_original_norms_protected=True,
        individual_contact_rows_protected=contact_model is not None,
        worst_geometry_proxy_bounded_in_proposal=geometry_guard_used,
        quality_approved=False,release_approved=False)
