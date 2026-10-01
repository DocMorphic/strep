"""Joint native arm/finger repair over the complete sampled crossing population."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now


def run(window_audit, arm_study, output, iterations=3, diagnostic_of=None, restoration_of=None):
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from scene_pair_problem import load_actors
    from independent_hand_motion import IndependentHandMotion, margins as arm_margins
    from native_finger_motion import NativeFingerMotion, palm_geometry
    from coupled_hand_finger_motion import CoupledHandFingerMotion
    from paired_approach_basis import BoundSkin
    from paired_temporal_neighbor import rotation_channels
    from continuous_terminal_hand import HandWitnessObjective
    from sampled_motion_caps import SampledMotionCaps, features
    from hand_norm_proposal import rate_vectors, measurement
    from triangle_separation_objective import TriangleSeparationObjective
    from sampled_surface_guard import SampledSurfaceGuard, snapshot, compare
    from triangle_crossing import audit
    from convex_partner_surface import penetration
    from iterated_hand_norm import solve
    from conic_root_descent import solver_module
    from replay_finger_proposal import verify_scale
    from edit_interval_clock import edit_interval_clock
    window_audit,arm_study,output=map(lambda p:Path(p).resolve(),[window_audit,arm_study,output])
    if output.exists():raise ValueError('Fresh coupled study required')
    if type(iterations) is not int or not 1<=iterations<=12:raise ValueError('One to twelve iterations required')
    if diagnostic_of is not None and restoration_of is not None:raise ValueError('Choose diagnostic or restoration mode')
    files={}
    def bind_study(folder):
        result=read(folder/'result.json')
        if result['status']!='complete':raise ValueError('Completed inputs required')
        files[str(folder/'result.json')]=sha256(folder/'result.json')
        for name,digest in result['outputs'].items():
            path=(folder/name).resolve()
            if path.parent!=folder or sha256(path)!=digest:raise ValueError('Study output changed')
            files[str(path)]=digest
        request=read(folder/'request.json')
        for path,digest in request['inputs'].items():
            if sha256(path)!=digest:raise ValueError('Study input changed')
            if path in files and files[path]!=digest:raise ValueError('Conflicting input bindings')
            files[path]=digest
        return request
    wr=bind_study(window_audit);ar=bind_study(arm_study);finger_folder=Path(wr['study']);fr=bind_study(finger_folder)
    def bound(path):
        path=Path(path).resolve()
        if files.get(str(path))!=sha256(path):raise ValueError('Unbound ancestry: '+str(path))
        return read(path)
    donor=Path(fr['donor']);dr=bound(donor/'request.json');anchor=Path(dr['study']);anchor_request=bound(anchor/'request.json')
    terminal=bound(Path(anchor_request['study'])/'request.json');plan=bound(Path(terminal['plan'])/'request.json')
    protocol=bound(Path(plan['source_plan'])/'request.json');baseline=Path(protocol['study']);original=bound(baseline/'request.json')
    prepared_folder=Path(original['prepared_request']).parent
    if str(prepared_folder)!=wr['prepared']:raise ValueError('Matching prepared scene required')
    prepared,actors=load_actors(prepared_folder);bound(prepared_folder/'request.json')
    scene=bound(prepared_folder/prepared['scene_snapshot']['path'])['scene']
    contact=next(c for c in scene['contacts'] if c['id'] in prepared['authored']['protected_contact_ids'])
    br=bound(baseline/'result.json');trial=next(r for r in bound(baseline/'trials.json') if r['folder']==br['selected'])
    times=np.asarray(fr['uniform_times_s']);audit_times=np.asarray(wr['audit_times_s'])
    guard_times=audit_times;guard_plan=None
    if diagnostic_of is None:
        clocks=[]
        for clip in wr['clips']:
            if files.get(clip['path'])!=clip['sha256']:raise ValueError('Bound donor clock required')
            asset=RigAsset.load(clip['path']);reader=AnimationSampler(asset.document,asset.binary,0)
            clocks.extend(channel[2] for channel in reader.channels)
        guard_times,guard_plan=edit_interval_clock(fr['window_s'],clocks,audit_times)
    combined=np.unique(np.r_[times,audit_times,guard_times])
    if not np.array_equal(audit_times,fr['audit_times_s']):raise ValueError('Complete original audit clock required')
    uniform=np.searchsorted(combined,times);event=int(np.searchsorted(combined,fr['contact_time_s']))
    native=np.asarray(ar['native_times_s']);arm_scale=np.asarray(ar['scale'])
    arm_start=np.asarray(bound(arm_study/'selected.json')['controls'])
    finger_scale=np.asarray(fr['scale']);scale=np.r_[arm_scale,finger_scale];point=np.r_[arm_start/arm_scale,np.zeros(len(finger_scale))]
    models=[];rigs=[];donors=[];reference=[];source_worlds=[];skins=[];neighborhoods=[];finger_sizes=[]
    for i,(actor,entry,clip) in enumerate(zip(actors,trial['actors'],bound(finger_folder/'decoded.json')['clips'])):
        path=(baseline/br['selected']/entry['path']).resolve()
        if files.get(str(path))!=entry['sha256']:raise ValueError('Original clip binding required')
        rig=RigAsset.load(path);rigs.append(rig);reader=AnimationSampler(rig.document,rig.binary,0)
        reference.append(np.array([reader.sample(t) for t in times]))
        donor_path=(finger_folder/clip['path']).resolve()
        if files.get(str(donor_path))!=clip['sha256'] or bound(arm_study/'decoded.json')['clips'][i]['sha256']!=clip['sha256']:
            raise ValueError('Both control studies must start from identical donors')
        donors.append(donor_path);donor_rig=RigAsset.load(donor_path);donor_reader=AnimationSampler(donor_rig.document,donor_rig.binary,0)
        source_worlds.append(np.array([donor_reader.sample(t) for t in combined]))
        arm=IndependentHandMotion(rig,protocol['chains'][actor['name']],native,combined,prepared['protected_seconds'],actor['rotation'],i)
        target=contact['effector'] if i==0 else contact['target'];hand=next(n for n,node in enumerate(rig.document['nodes']) if node.get('name')==target['joint'])
        finger=NativeFingerMotion(donor_rig,hand,fr['selected_nodes'][i],fr['edit_limits_degrees'][i],combined,fr['window_s'],fr['contact_time_s'])
        models.append(CoupledHandFingerMotion(arm,finger));finger_sizes.append(finger.size);skins.append(BoundSkin(rig))
        faces=actor['faces'][np.any(actor['faces']==target['surface_vertex'],axis=1)];ids,remap=np.unique(faces,return_inverse=True)
        neighborhoods.append((ids,remap.reshape(-1,3),int(np.flatnonzero(ids==target['surface_vertex'])[0])))
    verify_scale(finger_scale,np.concatenate([np.repeat(m.finger.limits/np.sqrt(3),3) for m in models]))
    def split(x):
        values=np.asarray(x)*scale
        return values[:len(arm_scale)],np.split(values[len(arm_scale):],[finger_sizes[0]])
    def evaluate_worlds(x,quantize=True):
        arm,fingers=split(x)
        return [m.evaluate(arm,f,quantize=quantize) for m,f in zip(models,fingers)]
    initial=[value[0] for value in evaluate_worlds(point)]
    for actual,expected in zip(initial,source_worlds):np.testing.assert_allclose(actual,expected,rtol=0,atol=2e-10)
    window_triangles=bound(window_audit/'triangles.json');rows=window_triangles['rows']
    if not rows or len(rows)!=window_triangles['all_crossing_pairs']:raise ValueError('Complete window population required')
    vertex_ids=np.array([r['vertices'] for r in rows]).transpose(1,0,2);frames=np.searchsorted(combined,[r['time_s'] for r in rows])
    objective=TriangleSeparationObjective(skins,actors,frames,vertex_ids,[r['axis'] for r in rows])
    old_rows=bound(anchor/'witnesses.json')
    for row in old_rows:row['frame']=int(uniform[anchor_request['sample_indices'][row['frame']]])
    old=HandWitnessObjective(skins,actors,old_rows);ceilings=np.asarray(fr['old_witness_ceilings_m'])
    def payload(worlds):
        parts=[features(w,r.joints) for w,r in zip(worlds,rigs)]
        return {k:np.concatenate([p[k] for p in parts],axis=1) for k in ['positions','rotations']}
    caps=SampledMotionCaps(payload(reference),times,fr['original_bins_s'])
    extra=np.r_[np.repeat(fr['point_drift_limit_m'],3),np.repeat(fr['normal_vector_drift_limit'],2)]
    fixed_caps=np.r_[np.concatenate([(c+.9*caps.tolerance).ravel() for c in caps.caps]),extra]
    fixed_scales=np.r_[np.concatenate([np.maximum(c,f).ravel() for c,f in zip(caps.caps,[.01,1.,.01,1.])]),extra]
    centers0=np.asarray(fr['initial_palm_centers_m']);normals0=np.asarray(fr['initial_palm_normals'])
    def palm_vectors(worlds):
        centers=[];normals=[]
        for world,skin,actor,(ids,faces,center) in zip(worlds,skins,actors,neighborhoods):
            p=skin.evaluate(world,np.full(len(ids),event),ids)@actor['rotation'].T+actor['translation']
            c,n=palm_geometry(p,faces,center);centers.append(c);normals.append(n)
        centers=np.array(centers);normals=np.array(normals)
        return np.vstack([centers-centers0,(centers[0]-centers[1])-(centers0[0]-centers0[1]),normals-normals0])
    def evaluate(x,quantize=True):
        values=evaluate_worlds(x,quantize);worlds=[v[0] for v in values];arm,_=split(x)
        vectors=np.concatenate([v.reshape(-1,3) for v in rate_vectors(payload([w[uniform] for w in worlds]),caps.dt)]+[palm_vectors(worlds)])
        return dict(vectors=vectors,caps=fixed_caps,scales=fixed_scales,
            margins=np.r_[(45.+1e-4-max(v[1] for v in values))/45.,arm_margins(arm,native,plan['guide_rate_limits']),(ceilings+old.gaps(worlds))/.02],
            depths=objective.depths(worlds))
    exact=lambda x:evaluate(x);smooth=lambda x:evaluate(x,False);before=measurement(exact(point))
    if before['minimum_margin']<0:raise ValueError('Coupled donor must retain original feasibility')
    restoration_seed=None;seed_record=None
    if restoration_of is not None:
        prior=Path(restoration_of).resolve();pr=bind_study(prior)
        if pr['window_audit']!=str(window_audit) or pr['arm_study']!=str(arm_study):raise ValueError('Matching restoration source required')
        np.testing.assert_array_equal(pr['point'],point);np.testing.assert_array_equal(pr['scale'],scale)
        for name,digest in pr['implementation'].items():
            archived=prior/'implementation'/name
            if sha256(archived)!=digest:raise ValueError('Restoration source archive changed')
            files[str(archived)]=digest
            if name!='study_coupled_window_repair.py' and sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Restoration decoder or constraint method changed')
        choices=[]
        for iteration in bound(prior/'proposals.json'):
            for attempt in iteration['attempts']:
                if 'delta' not in attempt:continue
                for trial in attempt.get('trials',[]):
                    if trial.get('minimum_margin',0)>=0 or trial.get('witness_peak_m',np.inf)>=before['witness_peak_m']-1e-9:continue
                    x=np.asarray(iteration['point_before'])+trial['fraction']*np.asarray(attempt['delta'])
                    choices.append((trial['witness_peak_m'],abs(trial['minimum_margin']),x,dict(iteration=iteration['iteration'],trust=attempt['trust'],fraction=trial['fraction'],metric=trial)))
        if not choices:raise ValueError('Rejected improving seed required')
        _,_,restoration_seed,seed_record=min(choices,key=lambda row:row[:2])
        actual=measurement(exact(restoration_seed))
        for key in ['witness_peak_m','minimum_margin']:np.testing.assert_allclose(actual[key],seed_record['metric'][key],rtol=0,atol=1e-12)
    if diagnostic_of is not None:
        from coupled_constraint_report import breakdown
        prior=Path(diagnostic_of).resolve();pr=bind_study(prior)
        if pr['window_audit']!=str(window_audit) or pr['arm_study']!=str(arm_study):raise ValueError('Matching prior experiment required')
        for key,value in [('point',point),('scale',scale),('uniform_times_s',times),('audit_times_s',audit_times)]:
            np.testing.assert_array_equal(pr[key],value)
        for name,digest in pr['implementation'].items():
            archived=prior/'implementation'/name
            if sha256(archived)!=digest:raise ValueError('Prior method archive changed')
            files[str(archived)]=digest
            if name!='study_coupled_window_repair.py' and sha256(ROOT/'scripts'/name)!=digest:
                raise ValueError('Diagnostic decoder or constraint method changed')
        labels=[a['name']+':'+r.document['nodes'][n]['name'] for a,r in zip(actors,rigs) for n in r.joints]
        guide_rows=len(arm_margins(arm_start,native,plan['guide_rate_limits']));records=[]
        baseline_precision={name:breakdown(fn(point),labels,len(times),guide_rows,len(ceilings)) for name,fn in [('serialized',exact),('unrounded',smooth)]}
        for iteration in bound(prior/'proposals.json'):
            start=np.asarray(iteration['point_before'])
            for attempt in iteration['attempts']:
                if 'delta' not in attempt:continue
                for trial in attempt['trials']:
                    if 'minimum_margin' not in trial:continue
                    candidate=start+trial['fraction']*np.asarray(attempt['delta']);actual=exact(candidate);predicted=smooth(candidate)
                    metric=measurement(actual)
                    for key in ['witness_peak_m','minimum_margin']:np.testing.assert_allclose(metric[key],trial[key],rtol=0,atol=1e-12)
                    records.append(dict(iteration=iteration['iteration'],trust=attempt['trust'],fraction=trial['fraction'],metric=metric,
                        serialized=breakdown(actual,labels,len(times),guide_rows,len(ceilings)),
                        unrounded=breakdown(predicted,labels,len(times),guide_rows,len(ceilings))))
                    print(dict(phase='constraint_replay',completed=len(records)),flush=True)
        if not records:raise ValueError('Recorded exact trials required')
        output.mkdir();(output/'implementation').mkdir();methods={}
        for name in sorted(set(pr['implementation'])|{'coupled_constraint_report.py'}):
            path=ROOT/'scripts'/name;methods[name]=sha256(path);shutil.copyfile(path,output/'implementation'/name)
        save(output/'request.json',dict(at=now(),inputs=files,implementation=methods,prior=str(prior),labels=labels,frame_count=len(times),
            guide_rows=guide_rows,witness_rows=len(ceilings),scope='Exact saved-trial failure localization and unrounded nonlinear comparison. Thresholds unchanged; no exports or approval.'))
        save(output/'trials.json',records);save(output/'baseline-precision.json',baseline_precision)
        for path,digest in files.items():
            if sha256(path)!=digest:raise ValueError('Diagnostic input changed')
        save(output/'result.json',dict(at=now(),status='complete',outputs={p.name:sha256(p) for p in output.iterdir() if p.is_file()},
            trials=len(records),serialized_passes=sum(r['serialized']['passed'] for r in records),
            unrounded_passes=sum(r['unrounded']['passed'] for r in records),quality_approved=False,accepted_for_publication=False))
        return
    solver=solver_module();output.mkdir();(output/'implementation').mkdir();methods={}
    names=set(ar['implementation'])|set(fr['implementation'])|{'study_coupled_window_repair.py','coupled_hand_finger_motion.py',
        'window_triangle_objective.py','sampled_surface_guard.py','convex_partner_surface.py','replay_finger_proposal.py',
        'edit_interval_clock.py','restore_hand_feasibility.py'}
    for name in sorted(names):
        path=ROOT/'scripts'/name;methods[name]=sha256(path);shutil.copyfile(path,output/'implementation'/name)
    save(output/'request.json',dict(at=now(),inputs=files,implementation=methods,window_audit=str(window_audit),arm_study=str(arm_study),
        uniform_times_s=times.tolist(),audit_times_s=audit_times.tolist(),scale=scale.tolist(),point=point.tolist(),
        guard_times_s=guard_times.tolist(),guard_clock=guard_plan,restoration_of=None if restoration_of is None else str(Path(restoration_of).resolve()),restoration_seed=seed_record,
        native_arm_times_s=native.tolist(),finger_window_s=fr['window_s'],before=before,iterations=iterations,
        all_crossing_pairs=len(rows),controls=len(point),trusts=[.1,.01,.001],quality_approved=False,
        scope='All observed crossing pairs across the window; original arm reference, guide limits, motion caps, palm geometry and old signed-witness ceilings retained. Full mesh guard before acceptance.'))
    def observe(row):
        if row['phase'] not in ['jacobian','restoration_jacobian'] or row['coordinates']%19==0:print(row,flush=True)
    def mesh_points(worlds):
        return [[rig.vertices(w[int(np.searchsorted(combined,t))])@a['rotation'].T+a['translation'] for rig,w,a in zip(rigs,worlds,actors)] for t in guard_times]
    def make_guard():
        guard=SampledSurfaceGuard([a['faces'] for a in actors],[len(r.vertices(r.reference)) for r in rigs],guard_times,
            lambda x:mesh_points(source_worlds if np.array_equal(x,point) else [v[0] for v in evaluate_worlds(x)]),point,observe=observe)
        save(output/'surface-baseline.json',guard.original);return guard
    guard=None;history=[]
    def checkpoint(model,row):
        np.savez_compressed(output/f'iteration-{row["iteration"]:02d}.npz',point=model['point'],**model['base'],**{k+'_jacobian':v for k,v in model['jacobian'].items()})
        if 'proposal' in row:row=dict(row,attempts=[dict(row['proposal'],trials=row['trials'])])
        history.append(row);save(output/'proposals.json',history)
    if restoration_seed is None:
        guard=make_guard()
        best,report=solve(exact,smooth,point,solver,iterations=iterations,trusts=(.1,.01,.001),observe=observe,checkpoint=checkpoint,acceptance_guard=guard)
    else:
        from restore_hand_feasibility import restore
        candidate,report=restore(exact,smooth,point,restoration_seed,solver,iterations=iterations,trust=.001,observe=observe,checkpoint=checkpoint)
        best=point.copy()
        if candidate is not None:
            guard=make_guard();decision=guard(candidate);save(output/'restored-candidate-surface.json',decision)
            if decision['passed']:best=candidate
        report['mesh_guard_run']=guard is not None
    save(output/'iteration-summary.json',report);save(output/'selected.json',dict(controls=(best*scale).tolist(),**measurement(exact(best))))
    arm,fingers=split(best);decoded=[];clips=[]
    for i,(model,finger,rig) in enumerate(zip(models,fingers,rigs)):
        path=output/f'candidate-{i}.glb'
        if np.array_equal(best,point):shutil.copyfile(donors[i],path)
        else:model.export(arm,finger,path)
        asset=RigAsset.load(path);reader=AnimationSampler(asset.document,asset.binary,0);world=np.array([reader.sample(t) for t in combined]);decoded.append(world)
        np.testing.assert_allclose(world,model.evaluate(arm,finger)[0],rtol=0,atol=2e-10)
        before_channels=rotation_channels(rig.document,rig.binary);after_channels=rotation_channels(asset.document,asset.binary)
        for node,(_,clock,q) in before_channels.items():
            np.testing.assert_array_equal(clock,after_channels[node][1])
            if node not in model.channels:np.testing.assert_array_equal(q,after_channels[node][2])
        outside=(combined<=fr['window_s'][0])|(combined>=fr['window_s'][1]);np.testing.assert_array_equal(world[outside],source_worlds[i][outside])
        clips.append(dict(path=path.name,sha256=sha256(path),native_clocks_and_unselected_channels_exact=True))
    if not caps.check(dict(indices=np.arange(len(times)),**payload([w[uniform] for w in decoded]))):raise ValueError('Decoded original motion caps failed')
    if np.any(np.linalg.norm(palm_vectors(decoded),axis=1)>extra):raise ValueError('Decoded palm bounds failed')
    if np.any(-old.gaps(decoded)>ceilings):raise ValueError('Decoded old witness ceilings failed')
    save(output/'decoded.json',dict(clips=clips,motion_caps_pass=True,palm_bounds_pass=True,old_witness_pass=True,quality_approved=False))
    observations=[]
    for t,points in ([] if restoration_seed is not None and np.array_equal(best,point) else zip(guard_times,mesh_points(decoded))):
        surface=audit(points[0],actors[0]['faces'],points[1],actors[1]['faces'])
        depths=[penetration(points[a],points[b],actors[b]['faces']) for a,b in [(0,1),(1,0)]]
        name=f'geometry-{len(observations):02d}.json';save(output/name,dict(time_s=float(t),surface=surface,depths=depths))
        observations.append(dict(time_s=float(t),surface=surface,depths=depths));print(dict(phase='decoded_geometry',completed=len(observations),total=len(guard_times)),flush=True)
    decision=compare(guard.original,snapshot(guard.meshes,observations)) if observations else dict(passed=None,reason='Unchanged donor retained; no new decoded mesh audit claimed')
    save(output/'decoded-surface-guard.json',decision)
    if decision['passed'] is False:raise ValueError('Decoded mesh guard failed')
    for path,digest in files.items():
        if sha256(path)!=digest:raise ValueError('Coupled input changed')
    for name,digest in methods.items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Coupled implementation changed')
    save(output/'result.json',dict(at=now(),status='complete',outputs={p.name:sha256(p) for p in output.iterdir() if p.is_file()},
        before=before,after=measurement(exact(best)),sampled_surface_guard_pass=decision['passed'],donor_retained=bool(np.array_equal(best,point)),
        total_pair_time_crossings=sum(r['surface']['counts'].get('proper_crossing',0) for r in observations) if observations else None,
        historical_pair_time_crossings=len(rows),guard_sample_count=len(guard_times),
        collision_free_certified=False,accepted_for_publication=False,quality_approved=False))


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('window_audit',type=Path);parser.add_argument('arm_study',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--iterations',type=int,default=3);parser.add_argument('--diagnose-study',type=Path);parser.add_argument('--restore-study',type=Path);args=parser.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(args.window_audit,args.arm_study,args.output,args.iterations,args.diagnose_study,args.restore_study)
