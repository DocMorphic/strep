"""Decode a diagnostic finger proposal and audit real geometry without approval."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now


def verify_scale(saved, reconstructed):
    """Permit degree/radian roundtrip noise; use the bound saved scale unchanged."""
    a,b=np.asarray(saved,float),np.asarray(reconstructed,float)
    if a.ndim!=1 or not len(a) or b.shape!=a.shape or not np.isfinite(a).all() or not np.isfinite(b).all() or np.any(a<=0) or np.any(b<=0):
        raise ValueError('Matching finite positive parameter scales required')
    np.testing.assert_allclose(a,b,rtol=4*np.finfo(float).eps,atol=0)
    return float(np.max(abs(a-b)))


def select_diagnostic(rows):
    """Predeclared largest feasible backoff; full step if all remaining gates fail."""
    if not rows or [r['fraction'] for r in rows] != [1., .5, .25, .125, .0625, .03125, .015625, .0078125]:
        raise ValueError('Complete ordered deterministic backoff population required')
    for i, row in enumerate(rows):
        if row['proposal_motion_pass'] and row['palm_pass']: return i, 'largest_motion_and_palm_feasible_backoff'
    return 0, 'full_step_rejected_diagnostic'


def run(study, diagnostic, output):
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from scene_pair_problem import load_actors
    from native_finger_motion import NativeFingerMotion, palm_geometry
    from sampled_motion_caps import SampledMotionCaps, features, measures
    from continuous_terminal_hand import HandWitnessObjective
    from paired_approach_basis import BoundSkin
    from triangle_separation_objective import TriangleSeparationObjective
    from paired_temporal_neighbor import rotation_channels
    from triangle_crossing import audit
    from convex_partner_surface import penetration
    study, diagnostic, output = map(lambda p: Path(p).resolve(), [study, diagnostic, output])
    if output.exists(): raise ValueError('Fresh diagnostic replay required')
    result, request = read(study/'result.json'), read(study/'request.json')
    dresult, drequest = read(diagnostic/'result.json'), read(diagnostic/'request.json')
    if result['status'] != 'complete' or dresult['status'] != 'complete': raise ValueError('Completed studies required')
    inputs = {str(study/'result.json'): sha256(study/'result.json'), str(diagnostic/'result.json'): sha256(diagnostic/'result.json')}
    for name, digest in result['outputs'].items():
        path = (study/name).resolve()
        if path.parent != study or sha256(path) != digest: raise ValueError('Finger output changed')
        inputs[str(path)] = digest
    for name, key in [('request.json','request_sha256'), ('proposals.json','proposals_sha256')]:
        if sha256(diagnostic/name) != dresult[key]: raise ValueError('Group diagnostic changed')
        inputs[str(diagnostic/name)] = dresult[key]
    for declared in (request['inputs'], drequest['inputs']):
        for path, digest in declared.items():
            if sha256(path) != digest: raise ValueError('Bound source changed: '+path)
            inputs[path] = digest
    if drequest['inputs'].get(str(study/'request.json')) != sha256(study/'request.json'):
        raise ValueError('Diagnostic belongs to another study')
    core = ['native_finger_motion.py','timed_rotation_edit.py','rig_asset.py','rig_clip_import.py','gltf_tools.py',
        'sampled_motion_caps.py','triangle_crossing.py','triangle_separation_objective.py','paired_approach_basis.py','continuous_terminal_hand.py']
    for name in core:
        if sha256(ROOT/'scripts'/name) != request['implementation'][name]: raise ValueError('Bound replay method changed')
    def bound_read(path):
        path = Path(path).resolve()
        if inputs.get(str(path)) != sha256(path): raise ValueError('Undeclared ancestor: '+str(path))
        return read(path)
    donor = Path(request['donor']); donor_request = bound_read(donor/'request.json'); anchor = Path(donor_request['study'])
    anchor_request = bound_read(anchor/'request.json'); terminal = bound_read(Path(anchor_request['study'])/'request.json')
    plan = bound_read(Path(terminal['plan'])/'request.json'); protocol = bound_read(Path(plan['source_plan'])/'request.json')
    baseline = Path(protocol['study']); original = bound_read(baseline/'request.json')
    folder = Path(original['prepared_request']).parent; prepared, actors = load_actors(folder)
    if prepared != bound_read(folder/'request.json'): raise ValueError('Prepared request changed')
    scene_path = (folder/prepared['scene_snapshot']['path']).resolve()
    if not scene_path.is_relative_to(folder) or sha256(scene_path) != prepared['scene_snapshot']['sha256']:
        raise ValueError('Prepared scene snapshot changed')
    inputs[str(scene_path)] = prepared['scene_snapshot']['sha256']
    scene = bound_read(folder/prepared['scene_snapshot']['path'])['scene']
    contact = next(c for c in scene['contacts'] if c['id'] in prepared['authored']['protected_contact_ids'])
    original_result = bound_read(baseline/'result.json'); trials = bound_read(baseline/'trials.json')
    trial = next(t for t in trials if t['folder'] == original_result['selected'])
    times = np.asarray(request['uniform_times_s']); audit_times = np.asarray(request['audit_times_s'])
    combined = np.unique(np.r_[times, audit_times]); uniform = np.searchsorted(combined, times); event = int(np.searchsorted(combined, request['contact_time_s']))
    rigs = []; models = []; source_worlds = []; originals = []; neighborhoods = []; paths = []
    for i, (actor, entry, clip) in enumerate(zip(actors, trial['actors'], bound_read(donor/'decoded.json')['clips'])):
        path = (baseline/original_result['selected']/entry['path']).resolve()
        if inputs.get(str(path)) != entry['sha256'] or sha256(path) != entry['sha256']: raise ValueError('Original clip changed')
        rig = RigAsset.load(path); reader = AnimationSampler(rig.document, rig.binary, 0); originals.append(np.array([reader.sample(t) for t in times]))
        path = (donor/clip['path']).resolve()
        if inputs.get(str(path)) != clip['sha256'] or sha256(path) != clip['sha256']: raise ValueError('Donor clip changed')
        paths.append(path); rig = RigAsset.load(path); rigs.append(rig); reader = AnimationSampler(rig.document, rig.binary, 0)
        source_worlds.append(np.array([reader.sample(t) for t in combined]))
        target = contact['effector'] if i == 0 else contact['target']; root = next(n for n, node in enumerate(rig.document['nodes']) if node.get('name') == target['joint'])
        models.append(NativeFingerMotion(rig, root, request['selected_nodes'][i], request['edit_limits_degrees'][i], combined, request['window_s'], request['contact_time_s']))
        vertex = target['surface_vertex']; faces = actor['faces'][np.any(actor['faces'] == vertex, axis=1)]
        ids, remap = np.unique(faces, return_inverse=True); neighborhoods.append((ids, remap.reshape(-1,3), int(np.flatnonzero(ids == vertex)[0])))
    skins = [BoundSkin(r) for r in rigs]; scale = np.asarray(request['scale']); sizes = [m.size for m in models]
    scale_roundtrip_error=verify_scale(scale, np.concatenate([np.repeat(m.limits/np.sqrt(3),3) for m in models]))
    records = read(diagnostic/'proposals.json'); chosen = next(r for r in records if r['omitted'] == 'old_witnesses')
    delta = np.asarray(chosen['delta'])
    with np.load(study/'iteration-01.npz', allow_pickle=False) as archive: point = archive['point']
    if delta.shape != point.shape or point.shape != scale.shape or not np.isfinite(delta).all() or np.any(abs(point+delta)>1):
        raise ValueError('Finite bound diagnostic coordinates required')
    rows = bound_read(anchor/'witnesses.json')
    for row in rows: row['frame'] = int(uniform[anchor_request['sample_indices'][row['frame']]])
    old_objective = HandWitnessObjective(skins, actors, rows); ceilings = np.asarray(request['old_witness_ceilings_m'])
    crossing = [r for r in read(study/'baseline-geometry.json')['records'] if r['kind']=='proper_crossing']
    vertices = np.array([[a['faces'][r['left_triangle' if i==0 else 'right_triangle']] for r in crossing] for i,a in enumerate(actors)])
    triangle_objective = TriangleSeparationObjective(skins, actors, np.full(len(crossing),event), vertices, request['axes'])
    def payload(worlds):
        parts = [features(w,r.joints) for w,r in zip(worlds,rigs)]
        return {k:np.concatenate([p[k] for p in parts],axis=1) for k in ['positions','rotations']}
    caps = SampledMotionCaps(payload(originals), times, request['original_bins_s'])
    def evaluate(worlds):
        actual = measures(payload([w[uniform] for w in worlds]), caps.dt)
        motions = []
        for kind, values, cap, floor in zip(['positional_speed','positional_acceleration','angular_speed','angular_acceleration'], actual, caps.caps, [.01,1.,.01,1.]):
            excess = values-cap; margins = (cap+.9*caps.tolerance-values)/np.maximum(cap,floor); index = np.unravel_index(int(margins.argmin()), margins.shape)
            actor_index, joint_index = divmod(index[1], len(rigs[0].joints)); node = rigs[actor_index].joints[joint_index]
            motions.append(dict(kind=kind, proposal_pass=bool(np.all(excess<=.9*caps.tolerance)), export_pass=bool(np.all(excess<=caps.tolerance)),
                maximum_excess=float(excess.max()), minimum_proposal_margin=float(margins.min()), worst_sample=int(index[0]), actor=actors[actor_index]['name'], joint=rigs[actor_index].document['nodes'][node]['name']))
        centers = []; normals = []
        for world, skin, a, (ids, faces, center) in zip(worlds, skins, actors, neighborhoods):
            p = skin.evaluate(world, np.full(len(ids),event), ids)@a['rotation'].T+a['translation']; c,n = palm_geometry(p,faces,center); centers.append(c); normals.append(n)
        centers, normals = np.array(centers), np.array(normals); old_centers = np.asarray(request['initial_palm_centers_m'])
        position_error = np.linalg.norm(centers-old_centers,axis=1); normal_error = np.linalg.norm(normals-request['initial_palm_normals'],axis=1)
        relative_error = float(np.linalg.norm((centers[0]-centers[1])-(old_centers[0]-old_centers[1])))
        old_depths = -old_objective.gaps(worlds); excess = old_depths-ceilings
        palm_pass = position_error.max()<=request['point_drift_limit_m'] and relative_error<=request['point_drift_limit_m'] and normal_error.max()<=request['normal_vector_drift_limit']
        return dict(proposal_motion_pass=all(r['proposal_pass'] for r in motions), export_motion_pass=all(r['export_pass'] for r in motions), motion=motions,
            palm_pass=bool(palm_pass), palm_position_errors_m=position_error.tolist(), relative_palm_error_m=relative_error, palm_normal_errors=normal_error.tolist(),
            old_witness_pass=bool(np.all(excess<=0)), old_witness_violations=int((excess>0).sum()), maximum_old_witness_excess_m=float(max(0.,excess.max())),
            fixed_triangle_violation_m=float(max(0.,triangle_objective.depths(worlds).max())), accepted_for_publication=False)
    before = evaluate(source_worlds)
    if not before['proposal_motion_pass'] or not before['palm_pass'] or not before['old_witness_pass']: raise ValueError('Donor gates no longer reproduce')
    output.mkdir(); (output/'implementation').mkdir(); methods = {}
    names = set(request['implementation']) | {'replay_finger_proposal.py','convex_partner_surface.py'}
    for name in sorted(names):
        source = ROOT/'scripts'/name; methods[name] = sha256(source); shutil.copyfile(source, output/'implementation'/name)
    save(output/'request.json', dict(at=now(), inputs=inputs, implementation=methods, donor=str(donor), finger_study=str(study), diagnostic=str(diagnostic),
        omitted_for_proposal_only='old_witnesses', fractions=[1.,.5,.25,.125,.0625,.03125,.015625,.0078125],
        selection='Largest backoff passing unchanged proposal-motion and palm gates; otherwise full rejected step. Old-witness failures stay explicit. No approval.',
        point=point.tolist(), delta=delta.tolist(), scale=scale.tolist(), scale_roundtrip_max_error=scale_roundtrip_error,
        before=before, quality_approved=False))
    comparisons = []; poses = []
    for fraction in [1.,.5,.25,.125,.0625,.03125,.015625,.0078125]:
        controls = np.split((point+fraction*delta)*scale,[sizes[0]])
        worlds = [m.world(c) for m,c in zip(models,controls)]; poses.append(worlds)
        comparisons.append(dict(fraction=fraction, **evaluate(worlds))); save(output/'backoffs.json',comparisons)
        print({k:comparisons[-1][k] for k in ['fraction','proposal_motion_pass','export_motion_pass','palm_pass','old_witness_violations','fixed_triangle_violation_m']},flush=True)
    selected, reason = select_diagnostic(comparisons); fraction = comparisons[selected]['fraction']; controls = np.split((point+fraction*delta)*scale,[sizes[0]])
    decoded_worlds = []; clips = []
    for i,(model,control,rig) in enumerate(zip(models,controls,rigs)):
        dest = output/f'diagnostic-rejected-{i}.glb'; model.export(control,dest)
        decoded = RigAsset.load(dest); reader = AnimationSampler(decoded.document,decoded.binary,0); world = np.array([reader.sample(t) for t in combined]); decoded_worlds.append(world)
        np.testing.assert_allclose(world,poses[selected][i],rtol=0,atol=2e-10)
        np.testing.assert_array_equal(world[:,model.body],source_worlds[i][:,model.body])
        frozen=(combined<=request['window_s'][0])|(combined>=request['window_s'][1]); np.testing.assert_array_equal(world[frozen],source_worlds[i][frozen])
        old,new=rotation_channels(rig.document,rig.binary),rotation_channels(decoded.document,decoded.binary)
        for node,(_,clock,q) in old.items():
            np.testing.assert_array_equal(new[node][1],clock)
            if node not in model.nodes:np.testing.assert_array_equal(new[node][2],q)
        clips.append(dict(path=dest.name,sha256=sha256(dest),unchanged_body_and_clocks=True,accepted_for_publication=False))
    decoded_gates=evaluate(decoded_worlds); save(output/'decoded.json',dict(clips=clips,selected_backoff=selected,selection_reason=reason,gates=decoded_gates))
    geometry=[]
    baseline_rows={r['time_s']:r for r in read(study/'geometry.json')}
    for stamp in audit_times:
        frame=int(np.searchsorted(combined,stamp)); pair=[]
        for version,worlds in [('donor',source_worlds),('diagnostic',decoded_worlds)]:
            points=[rig.vertices(w[frame])@a['rotation'].T+a['translation'] for rig,w,a in zip(rigs,worlds,actors)]
            depths=[penetration(points[a],points[b],actors[b]['faces']) for a,b in [(0,1),(1,0)]]
            if version=='donor':
                row=baseline_rows[float(stamp)]
                if sha256(study/row['path'])!=row['sha256']:raise ValueError('Baseline geometry changed')
                counts=row['counts']; path=None
            else:
                value=audit(points[0],actors[0]['faces'],points[1],actors[1]['faces']); path=f'geometry-{len(geometry):02d}.json';save(output/path,value);counts=value['counts']
            pair.append(dict(version=version,counts=counts,full_vertex_depths=depths,path=path,sha256=None if path is None else sha256(output/path)))
        geometry.append(dict(time_s=float(stamp),versions=pair));save(output/'geometry.json',geometry)
        print(dict(phase='geometry',completed=len(geometry),total=len(audit_times),crossings=[p['counts'].get('proper_crossing',0) for p in pair],depths=[[d['max_depth_m'] for d in p['full_vertex_depths']] for p in pair]),flush=True)
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Replay input changed')
    for name,digest in methods.items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Replay method changed')
    outputs={p.name:sha256(p) for p in output.iterdir() if p.is_file()}
    save(output/'result.json',dict(at=now(),status='complete',outputs=outputs,selected_fraction=fraction,selection_reason=reason,decoded_gates=decoded_gates,
        diagnostic_only=True,collision_free_certified=False,accepted_for_publication=False,quality_approved=False))


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('diagnostic',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(args.study,args.diagnostic,args.output)
