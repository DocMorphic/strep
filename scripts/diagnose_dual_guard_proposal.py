"""Replay saved dual-guard proposals and attribute rejected constraints, without fitting."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now


def run(study, output):
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from scene_pair_problem import load_actors
    from contact_rate_path import ContactRatePath, ProjectedSkin
    from dual_rate_peak_guard import DualRatePeakGuard
    from elbow_swivel import descendants
    from paired_approach_basis import BoundSkin
    from sampled_motion_caps import SampledMotionCaps, features, measures
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh proposal diagnosis required')
    q, result = read(study/'request.json'), read(study/'result.json')
    if 'temporal_refinement' in q:
        from refined_contact_rate_path import RefinedContactRatePath as ContactRatePath
    if result['status'] != 'complete' or 'dual_peak_guards_pass' not in result:
        raise ValueError('Completed dual-guard fit required')
    files = dict(q['inputs']); files[str(study/'result.json')] = sha256(study/'result.json')
    for name, digest in result['outputs'].items():
        path = (study/name).resolve()
        if path.parent != study: raise ValueError('Escaping output')
        files[str(path)] = digest
    for name, digest in q['implementation'].items():
        path = (study/'implementation'/name).resolve()
        if path.parent != study/'implementation': raise ValueError('Escaping method')
        files[str(path)] = digest
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Changed evidence')
    def bound(path):
        if files.get(str(path)) != sha256(path): raise ValueError('Unbound evidence')
        return read(path)
    pose = q; seen = set()
    while 'baseline' not in pose:
        path = Path(pose['source'])/'request.json'
        if path in seen or len(seen) >= 32: raise ValueError('Invalid source chain')
        seen.add(path); pose = bound(path)
    region = bound(Path(pose['source'])/'request.json'); donor = bound(Path(region['source'])/'request.json')
    baseline = Path(pose['baseline']); br = bound(baseline/'result.json')
    trial = next(t for t in bound(baseline/'trials.json') if t['folder'] == br['selected'])
    _, actors = load_actors(region['prepared'])
    uniform = np.asarray(q['uniform_times_s']); planes = np.asarray(q['plane_times_s'])
    rows = []
    for i, entry in enumerate(trial['actors']):
        source = Path(q['source'])/f'candidate-{i}.glb'; reference = baseline/br['selected']/entry['path']
        for path in (source, reference):
            if files.get(str(path)) != sha256(path): raise ValueError('Unbound rig')
        rig, ref = RigAsset.load(source), RigAsset.load(reference)
        reader = AnimationSampler(rig.document, rig.binary, 0); rr = AnimationSampler(ref.document, ref.binary, 0)
        full = np.unique(np.r_[planes, q['guard_times_s'], uniform, q['event_time_s'], q['window_s'], 0., reader.duration])
        ids, plane_ids = np.searchsorted(full, uniform), np.searchsorted(full, planes)
        nodes = donor['actors'][i]['nodes'][:3]
        edit = ContactRatePath(rig.document, rig.binary, [rig.document['nodes'][n]['name'] for n in nodes], full, q['window_s'], q['protected_spans'], q['event_time_s'], (ref.document, ref.binary))
        caps = SampledMotionCaps(features(np.array([rr.sample(t) for t in uniform]), ref.joints), uniform, q['original_bins_s'])
        zero = np.zeros(edit.size); source_world = edit.world(zero, True)
        source_rates = measures(features(source_world[ids], rig.joints), caps.dt)
        affected = np.flatnonzero(descendants(rig.parents, nodes[0])[rig.joints])
        fit = bound(study/f'actor-{i}-fit.json')
        if 'control_dimension' in fit:
            if fit['control_dimension'] != edit.size: raise ValueError('Control dimension differs')
            np.testing.assert_array_equal(fit['temporal_knots_s'], edit.knots)
        if 'immutable_sample_rows' in fit:
            from rotation_rate_support import SupportedDualRatePeakGuard, rate_support
            support = rate_support(rig.parents, rig.joints, edit.model.entries, uniform)
            guard = SupportedDualRatePeakGuard(source_rates, caps.caps, affected, support, cap_tolerance=caps.tolerance)
            count = sum(int(m.sum()) for m in support)
        else:
            guard = DualRatePeakGuard(source_rates, caps.caps, affected, cap_tolerance=caps.tolerance)
            count = sum(c.shape[0]*len(affected) for c in caps.caps)
        if count != fit['proposal_sample_rows']: raise ValueError('Proposal row reconstruction differs')
        actor = actors[i]; target = q['target']; axis = np.asarray(target['normals'][i])
        projection = ProjectedSkin(BoundSkin(rig), np.asarray(region['region_vertices'][i]), actor['rotation'].T@axis, (actor['translation']-target['midpoint_m'])@axis)
        variants = []
        proposals = [('source', zero, True, None), ('double_proposal', np.asarray(fit['proposed_controls']), False, None)]
        proposals += [(f"serialized_{a['fraction']}", np.asarray(fit['proposed_controls'])*a['fraction'], True, a) for a in fit['serialized_attempts']]
        if 'selected_checkpoint' in fit:
            checkpoints = bound(study/f'actor-{i}-checkpoints.json')
            if checkpoints['status'] != 'selection_complete': raise ValueError('Completed checkpoint selection required')
            feasible_costs = [fit['initial_objective']]
            for record in checkpoints['records']:
                for attempt in record['serialized_attempts']:
                    feasible = attempt['minimum_constraint'] >= 0 and attempt['contact_matrix_drift'] <= 1e-6
                    if feasible != attempt['feasible']: raise ValueError('Checkpoint feasibility flag differs from margins')
                    if feasible: feasible_costs.append(attempt['objective'])
            if fit['selected_objective'] > min(feasible_costs)+1e-10:
                raise ValueError('Selected checkpoint is not lowest recorded feasible objective')
            if fit['selected_checkpoint'] == 'source': expected = zero
            else:
                recorded = next(r for r in checkpoints['records'] if r['label'] == fit['selected_checkpoint'])
                expected = np.asarray(recorded['proposed_controls'])*fit['selected_fraction']
            np.testing.assert_array_equal(expected, fit['controls'])
            np.testing.assert_array_equal(expected, checkpoints['selected_controls'])
            proposals.append(('selected_checkpoint', expected, True, None))
        for label, x, quantize, saved in proposals:
            world = edit.world(x, quantize); values = measures(features(world[ids], rig.joints), caps.dt)
            proposal = not quantize
            excess = projection.evaluate(world[plane_ids]).max(axis=1)+q['minimum_hand_plane_clearance_m']
            plane_margin = -(excess+(q['proposal_plane_reserve_m'] if proposal else 0))*1000
            angle_margin = (45-edit.original_angles(x, quantize))/45
            margins = guard.sample_margins(values, proposal=True) if proposal else guard.margins(values)
            minimum = float(min(plane_margin.min(), angle_margin.min(), margins.min()))
            cost = sum(float(np.mean((np.maximum(v-c-caps.tolerance, 0)/s)**2)) for v, c, s in zip(values, caps.caps, guard.scales))
            if label == 'selected_checkpoint' and (abs(cost-fit['selected_objective']) > 1e-10 or abs(minimum-fit['minimum_constraint']) > 1e-10):
                raise ValueError('Selected checkpoint replay differs from completed fit')
            if saved and (abs(cost-saved['objective']) > 1e-10 or abs(minimum-saved['minimum_constraint']) > 1e-10):
                raise ValueError('Replay differs from saved serialized attempt')
            rate_rows = []
            for k, (v, cap, scale, ceiling) in enumerate(zip(values, caps.caps, guard.scales, guard.envelopes(proposal=proposal))):
                eligible = np.ones(v.shape, bool)
                if proposal:
                    eligible[:] = False; eligible[:, affected] = True
                    if hasattr(guard, 'support'): eligible &= guard.support[k]
                deficits = (v-ceiling-guard.guard_tolerance)/scale
                frame, column = np.unravel_index(np.where(eligible, deficits, -np.inf).argmax(), v.shape)
                column = int(column); node = rig.joints[column]
                stamps = uniform[1:-1] if k == 3 else (uniform[:-(1 if k%2==0 else 2)]+uniform[(1 if k%2==0 else 2):])/2
                absolute_limit = guard.absolute[k][column]-(guard.absolute_reserve[k][column] if proposal else 0)
                relative_limit = cap[frame, column]+caps.tolerance+guard.allowed[k][column]-(guard.reserve[k][column] if proposal else 0)
                rate_rows.append(dict(kind=('position_speed','position_acceleration','angular_speed','angular_acceleration')[k],
                    failed_rows=int(np.count_nonzero(deficits[eligible] > 0)), maximum_scaled_deficit=float(deficits[frame, column]),
                    time_s=float(stamps[frame]), node=node, name=rig.document['nodes'][node]['name'], measured=float(v[frame, column]),
                    absolute_ceiling=float(absolute_limit), reference_excess_ceiling=float(relative_limit),
                    binding_guard='absolute' if absolute_limit < relative_limit else 'reference_excess'))
            variants.append(dict(label=label, objective=cost, minimum_constraint=minimum,
                minimum_plane_constraint=float(plane_margin.min()), minimum_angle_constraint=float(angle_margin.min()),
                rates=rate_rows, peak_report=guard.report(values), replayed_saved_attempt=saved is not None))
        rows.append(dict(actor=i, variants=variants))
    output.mkdir(); (output/'implementation').mkdir(); methods = {}
    for name in sorted(set(q['implementation']) | {Path(__file__).name}):
        methods[name] = sha256(ROOT/'scripts'/name); shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    save(output/'request.json', dict(at=now(), source=str(study), inputs=files, implementation=methods,
        policy='Read-only reproduction of saved controls and attempted serialized backoffs. Reports which fixed envelope rejects a sampled rate; no global infeasibility or quality claim.'))
    save(output/'diagnosis.json', dict(actors=rows, quality_approved=False))
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Evidence changed during replay')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Method changed during replay')
    save(output/'result.json', dict(at=now(), status='complete', outputs={p.name:sha256(p) for p in output.iterdir() if p.is_file()},
        animations_modified=False, quality_approved=False))


if __name__ == '__main__':
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('study', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with threadpool_limits(limits=1): run(args.study, args.output)
