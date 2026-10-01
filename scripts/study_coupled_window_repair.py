"""Joint native arm/finger repair over the complete sampled crossing population."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now


def run(window_audit, arm_study, output, iterations=3, diagnostic_of=None, restoration_of=None, temporal_of=None, witness_of=None, ray_of=None, refine_of=None, continue_of=None, geometry_of=None, mesh_repair_of=None, mesh_ray_of=None, probe_motion=False, motion_headroom_of=None):
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
    if sum(v is not None for v in [diagnostic_of,restoration_of,temporal_of,witness_of,ray_of,refine_of,continue_of,geometry_of,mesh_repair_of,mesh_ray_of])>1:raise ValueError('Choose one study mode')
    expanded=any(v is not None for v in [temporal_of,witness_of,ray_of,refine_of,continue_of,geometry_of,mesh_repair_of,mesh_ray_of])
    if type(probe_motion) is not bool or probe_motion and mesh_ray_of is None:raise ValueError('Motion probe requires a saved mesh-repair direction')
    if motion_headroom_of is not None and (mesh_ray_of is None or probe_motion):raise ValueError('Headroom requires a saved mesh direction and separate diagnostic')
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
    mesh_ray_source=None;mesh_ray_request=None
    if mesh_ray_of is not None:
        mesh_ray_source=Path(mesh_ray_of).resolve();mesh_ray_request=bind_study(mesh_ray_source)
        if mesh_ray_request.get('mesh_repair_of') is None:raise ValueError('Completed mesh repair required')
        mesh_repair_of=Path(mesh_ray_request['mesh_repair_of'])
    headroom_source=None;headroom_request=None
    if motion_headroom_of is not None:
        headroom_source=Path(motion_headroom_of).resolve();headroom_request=bind_study(headroom_source)
        if headroom_request.get('probe_motion') is not True or headroom_request.get('mesh_ray_of')!=str(mesh_ray_source):
            raise ValueError('Matching completed motion diagnostic required')
        for name,digest in headroom_request['implementation'].items():
            archived=headroom_source/'implementation'/name
            if sha256(archived)!=digest:raise ValueError('Motion diagnostic archive changed')
            files[str(archived)]=digest
            if name!='study_coupled_window_repair.py' and sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Motion diagnostic method changed')
    mesh_source=None;mesh_request=None
    if mesh_repair_of is not None:
        mesh_source=Path(mesh_repair_of).resolve();mesh_request=bind_study(mesh_source)
        if mesh_request.get('geometry_of') is None:raise ValueError('Completed rejected-mesh diagnostic required')
        geometry_of=Path(mesh_request['geometry_of'])
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
    legacy_models=[];models=[];rigs=[];donors=[];reference=[];source_worlds=[];skins=[];neighborhoods=[];finger_sizes=[]
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
        legacy_models.append(CoupledHandFingerMotion(arm,finger))
        if expanded:
            from release_finger_motion import ReleaseFingerMotion, ReleaseCoupledHandFingerMotion, expand_controls
            finger=ReleaseFingerMotion(finger,fr['contact_time_s'],(fr['contact_time_s']+fr['window_s'][1])/2)
            models.append(ReleaseCoupledHandFingerMotion(arm,finger))
        else:models.append(legacy_models[-1])
        finger_sizes.append(finger.size);skins.append(BoundSkin(rig))
        faces=actor['faces'][np.any(actor['faces']==target['surface_vertex'],axis=1)];ids,remap=np.unique(faces,return_inverse=True)
        neighborhoods.append((ids,remap.reshape(-1,3),int(np.flatnonzero(ids==target['surface_vertex'])[0])))
    verify_scale(finger_scale,np.concatenate([np.repeat(m.finger.limits/np.sqrt(3),3) for m in legacy_models]))
    old_point=point.copy();old_scale=scale.copy();old_sizes=[m.finger.size for m in legacy_models]
    if expanded:
        point=expand_controls(point,len(arm_scale),old_sizes)
        blocks=[np.repeat(block.reshape(-1,1,3),2,axis=1).ravel() for block in np.split(finger_scale,[old_sizes[0]])]
        scale=np.r_[arm_scale,np.concatenate(blocks)]
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
    mesh_cuts=None
    def evaluate(x,quantize=True):
        values=evaluate_worlds(x,quantize);worlds=[v[0] for v in values];arm,fingers=split(x)
        temporal_margins=np.concatenate([m.finger.margins(f) for m,f in zip(models,fingers)]) if expanded else np.empty(0)
        vectors=np.concatenate([v.reshape(-1,3) for v in rate_vectors(payload([w[uniform] for w in worlds]),caps.dt)]+[palm_vectors(worlds)])
        return dict(vectors=vectors,caps=fixed_caps,scales=fixed_scales,
            margins=np.r_[(45.+1e-4-max(v[1] for v in values))/45.,arm_margins(arm,native,plan['guide_rate_limits']),(ceilings+old.gaps(worlds))/.02,(mesh_cuts.margins(worlds) if mesh_cuts is not None else np.empty(0)),temporal_margins],
            depths=objective.depths(worlds))
    exact=lambda x:evaluate(x);smooth=lambda x:evaluate(x,False);before=measurement(exact(point))
    if before['minimum_margin']<0:raise ValueError('Coupled donor must retain original feasibility')
    restoration_seed=None;seed_record=None;ray_delta=None;coarse_divisions=None
    if temporal_of is not None:
        prior=Path(temporal_of).resolve();pr=bind_study(prior)
        if pr['window_audit']!=str(window_audit) or pr['arm_study']!=str(arm_study):raise ValueError('Matching temporal source required')
        np.testing.assert_array_equal(pr['point'],old_point);np.testing.assert_array_equal(pr['scale'],old_scale)
        for name,digest in pr['implementation'].items():
            archived=prior/'implementation'/name
            if sha256(archived)!=digest:raise ValueError('Temporal source archive changed')
            files[str(archived)]=digest
            if name!='study_coupled_window_repair.py' and sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Temporal reference method changed')
        previous=bound(prior/'iteration-summary.json')
        if previous['method']!='serialized_feasibility_restoration_v1':raise ValueError('Restoration final state required')
        old_seed=np.asarray(previous['final_point']);restoration_seed=expand_controls(old_seed,len(arm_scale),old_sizes)
        values=old_seed*old_scale;old_fingers=np.split(values[len(arm_scale):],[old_sizes[0]])
        new_arm,new_fingers=split(restoration_seed)
        for legacy,model,old_f,new_f in zip(legacy_models,models,old_fingers,new_fingers):
            old_q,_=legacy.quaternions(values[:len(arm_scale)],old_f);new_q,_=model.quaternions(new_arm,new_f)
            for node in old_q:np.testing.assert_array_equal(old_q[node],new_q[node])
        actual=measurement(exact(restoration_seed))
        for key in ['witness_peak_m','minimum_margin']:np.testing.assert_allclose(actual[key],previous['final'][key],rtol=0,atol=1e-12)
        seed_record=dict(policy='exact_final_internal_state_with_zero_release_controls',prior=str(prior),metric=actual,
            serialized_keys_identical=True,release_peaks_s=[float(m.finger.release_knots[1]) for m in models])
    if any(v is not None for v in [witness_of,ray_of,refine_of,continue_of,geometry_of]):
        prior=Path(next(v for v in [witness_of,ray_of,refine_of,continue_of,geometry_of] if v is not None)).resolve();pr=bind_study(prior)
        source_key=('continue_of' if pr.get('continue_of') else 'refine_of') if continue_of is not None else ('ray_of' if refine_of is not None else ('witness_of' if ray_of is not None else 'temporal_of'))
        if geometry_of is not None:source_key='continue_of'
        if pr['window_audit']!=str(window_audit) or pr['arm_study']!=str(arm_study) or pr.get(source_key) is None:
            raise ValueError('Matching completed release-control study required')
        for key,value in [('point',point),('scale',scale),('uniform_times_s',times),('guard_times_s',guard_times)]:
            np.testing.assert_array_equal(pr[key],value)
        for name,digest in pr['implementation'].items():
            archived=prior/'implementation'/name
            if sha256(archived)!=digest:raise ValueError('Witness source archive changed')
            files[str(archived)]=digest
            if name!='study_coupled_window_repair.py' and sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Witness reference method changed')
        previous=bound(prior/'iteration-summary.json')
        expected_method='serialized_witness_ray_v1' if refine_of is not None else ('serialized_feasibility_restoration_v1' if ray_of is None else 'hard_motion_witness_restoration_v1')
        expected_methods=['refined_serialized_witness_ray_v1','iterated_serialized_witness_repair_v1'] if continue_of is not None else [expected_method]
        if geometry_of is not None:expected_methods=['iterated_serialized_witness_repair_v1']
        if previous['method'] not in expected_methods:raise ValueError('Prior restoration final state required')
        restoration_seed=np.asarray(previous['final_point']);actual=measurement(exact(restoration_seed))
        for key in ['witness_peak_m','minimum_margin']:np.testing.assert_allclose(actual[key],previous['final'][key],rtol=0,atol=1e-12)
        seed_record=dict(policy='exact_final_expanded_internal_state',prior=str(prior),metric=actual)
        if ray_of is not None:
            if len(previous['history'])!=1 or previous['history'][0]['internal_step']:raise ValueError('Single stopped proposal required for ray replay')
            attempt=previous['history'][0];np.testing.assert_array_equal(attempt['point_before'],restoration_seed)
            ray_delta=np.asarray(attempt['proposal']['delta'])
            seed_record['ray_from']='iteration-summary.json:history[0].proposal.delta'
        if refine_of is not None:
            ray_delta=np.asarray(previous['delta']);coarse_divisions=previous['divisions']
            seed_record['ray_from']='iteration-summary.json:delta';seed_record['coarse_divisions']=coarse_divisions
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
    mesh_cuts=None;mesh_cut_record=None;mesh_seed_metric=None
    if mesh_repair_of is not None:
        if mesh_request['window_audit']!=str(window_audit) or mesh_request['arm_study']!=str(arm_study):
            raise ValueError('Matching rejected-mesh source required')
        for key,value in [('point',point),('scale',scale),('uniform_times_s',times),('guard_times_s',guard_times)]:
            np.testing.assert_array_equal(mesh_request[key],value)
        for name,digest in mesh_request['implementation'].items():
            archived=mesh_source/'implementation'/name
            if sha256(archived)!=digest:raise ValueError('Mesh diagnostic archive changed')
            files[str(archived)]=digest
            if name!='study_coupled_window_repair.py' and sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Mesh diagnostic method changed')
        from mesh_regression_cuts import MeshRegressionCuts
        mesh_cuts=MeshRegressionCuts(skins,actors,combined,[a['faces'] for a in actors],
            bound(mesh_source/'baseline-snapshot.json'),bound(mesh_source/'rejected-snapshot.json'),initial)
        mesh_cut_record=mesh_cuts.record
        # Reproduce the diagnostic's exact rejected controls and serialized mesh
        # before adding new scalar rows; retain the original objective/caps.
        decoded=bound(mesh_source/'decoded-diagnostic.json')
        for i,entry in enumerate(decoded['clips']):
            path=mesh_source/entry['path']
            if files.get(str(path))!=entry['sha256']:raise ValueError('Bound rejected clip required')
            rig=RigAsset.load(path);reader=AnimationSampler(rig.document,rig.binary,0)
            np.testing.assert_allclose([reader.sample(t) for t in combined],evaluate_worlds(restoration_seed)[i][0],rtol=0,atol=2e-10)
        if mesh_ray_of is not None:
            if mesh_ray_request['window_audit']!=str(window_audit) or mesh_ray_request['arm_study']!=str(arm_study):
                raise ValueError('Matching completed mesh repair required')
            for key,value in [('point',point),('scale',scale),('uniform_times_s',times),('guard_times_s',guard_times)]:
                np.testing.assert_array_equal(mesh_ray_request[key],value)
            for name,digest in mesh_ray_request['implementation'].items():
                archived=mesh_ray_source/'implementation'/name
                if sha256(archived)!=digest:raise ValueError('Mesh repair archive changed')
                files[str(archived)]=digest
                if name!='study_coupled_window_repair.py' and sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Mesh repair method changed')
            saved_cuts=bound(mesh_ray_source/'mesh-cuts.json')
            if saved_cuts['rows']!=mesh_cut_record['rows']:raise ValueError('Frozen donor mesh cuts changed')
            previous=bound(mesh_ray_source/'iteration-summary.json')
            if previous['method']!='hard_motion_witness_restoration_v1' or not previous['history']:
                raise ValueError('Bound mesh proposal required')
            last=previous['history'][-1]
            if last['internal_step'] or 'delta' not in last['proposal']:raise ValueError('Stalled saved proposal required')
            restoration_seed=np.asarray(previous['final_point']);np.testing.assert_array_equal(restoration_seed,last['point_before'])
            actual=measurement(exact(restoration_seed))
            for key in ['witness_peak_m','minimum_margin']:np.testing.assert_allclose(actual[key],previous['final'][key],rtol=0,atol=1e-12)
            ray_delta=np.asarray(last['proposal']['delta'])
            seed_record=dict(policy='exact_stalled_mesh_repair_final_state',prior=str(mesh_ray_source),metric=actual)
        mesh_seed_metric=measurement(exact(restoration_seed))
        geometry_of=None
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
    solver=None if geometry_of is not None or probe_motion else solver_module();output.mkdir();(output/'implementation').mkdir();methods={}
    names=set(ar['implementation'])|set(fr['implementation'])|{'study_coupled_window_repair.py','coupled_hand_finger_motion.py',
        'window_triangle_objective.py','sampled_surface_guard.py','convex_partner_surface.py','replay_finger_proposal.py',
        'edit_interval_clock.py','restore_hand_feasibility.py'}
    if expanded:names|={'release_finger_motion.py','coupled_constraint_report.py'}
    if any(v is not None for v in [witness_of,ray_of,refine_of,continue_of,geometry_of]):names.add('restore_witness_feasibility.py')
    if ray_of is not None or refine_of is not None or continue_of is not None:names.add('scan_serialized_witness_ray.py')
    if continue_of is not None:names.add('iterated_witness_repair.py')
    if refine_of is not None:names.add('refine_serialized_witness_ray.py')
    if geometry_of is not None:names|=set(pr['implementation'])|{'diagnostic_mesh_comparison.py'}
    if mesh_repair_of is not None:names|=set(mesh_request['implementation'])|{'mesh_regression_cuts.py'}
    if mesh_ray_of is not None:names.add('scan_serialized_witness_ray.py')
    if probe_motion:names.add('motion_proposal_diagnostic.py')
    if headroom_source is not None:names|=set(headroom_request['implementation'])|{'motion_proposal_headroom.py'}
    for name in sorted(names):
        path=ROOT/'scripts'/name;methods[name]=sha256(path);shutil.copyfile(path,output/'implementation'/name)
    save(output/'request.json',dict(at=now(),inputs=files,implementation=methods,window_audit=str(window_audit),arm_study=str(arm_study),
        uniform_times_s=times.tolist(),audit_times_s=audit_times.tolist(),scale=scale.tolist(),point=point.tolist(),
        guard_times_s=guard_times.tolist(),guard_clock=guard_plan,restoration_of=None if restoration_of is None else str(Path(restoration_of).resolve()),restoration_seed=seed_record,
        temporal_of=None if temporal_of is None else str(Path(temporal_of).resolve()),
        witness_of=None if witness_of is None else str(Path(witness_of).resolve()),
        ray_of=None if ray_of is None else str(Path(ray_of).resolve()),
        refine_of=None if refine_of is None else str(Path(refine_of).resolve()),
        continue_of=None if continue_of is None else str(Path(continue_of).resolve()),
        geometry_of=None if geometry_of is None else str(Path(geometry_of).resolve()),
        mesh_repair_of=None if mesh_source is None else str(mesh_source),
        mesh_ray_of=None if mesh_ray_source is None else str(mesh_ray_source),probe_motion=probe_motion,
        motion_headroom_of=None if headroom_source is None else str(headroom_source),
        native_arm_times_s=native.tolist(),finger_window_s=fr['window_s'],before=before,iterations=iterations,
        all_crossing_pairs=len(rows),controls=len(point),trusts=[.1,.01,.001],quality_approved=False,
        scope='All observed crossing pairs across the window; original arm reference, guide limits, motion caps, palm geometry and old signed-witness ceilings retained. Full mesh guard before acceptance.'))
    if mesh_cut_record is not None:save(output/'mesh-cuts.json',dict(mesh_cut_record,seed_metric=mesh_seed_metric))
    if probe_motion:
        from motion_proposal_diagnostic import compare as compare_motion
        model_path=mesh_ray_source/f'iteration-{last["iteration"]:02d}.npz'
        if files.get(str(model_path))!=sha256(model_path):raise ValueError('Bound saved proposal required')
        with np.load(model_path,allow_pickle=False) as data:
            model=dict(point=data['point'],base={k:data[k] for k in ['vectors','caps','scales','margins','depths']},
                jacobian=dict(vectors=data['vectors_jacobian']))
        np.testing.assert_array_equal(model['point'],restoration_seed)
        labels=[a['name']+':'+r.document['nodes'][n]['name'] for a,r in zip(actors,rigs) for n in r.joints]
        sizes=[(len(times)-order)*len(labels) for order in [1,2,1,2]]+[3,2]
        kinds=['position_speed','position_acceleration','angular_speed','angular_acceleration','palm_points','palm_normals']
        units=['m/s','m/s^2','rad/s','rad/s^2','m','unit_vector']
        def describe(index):
            offset=0
            for group,(kind,size,unit) in enumerate(zip(kinds,sizes,units)):
                if index<offset+size:
                    local=index-offset;record=dict(kind=kind,unit=unit,row=local)
                    if group<4:
                        frame=local//len(labels);order=[1,2,1,2][group]
                        record.update(joint=labels[local%len(labels)],sample=frame,time_start_s=float(times[frame]),time_end_s=float(times[frame+order]))
                    return record
                offset+=size
            raise ValueError('Unknown motion row')
        fractions=[r['fraction'] for r in last['trials'] if 'minimum_margin' in r]
        for trial in last['trials']:
            metric=measurement(exact(restoration_seed+trial['fraction']*ray_delta))
            for key in ['witness_peak_m','minimum_margin']:np.testing.assert_allclose(metric[key],trial[key],rtol=0,atol=1e-12)
        diagnostic=compare_motion(model,exact,smooth,ray_delta,fractions,describe)
        save(output/'motion-proposal-diagnostic.json',diagnostic)
        for path,digest in files.items():
            if sha256(path)!=digest:raise ValueError('Motion diagnostic input changed')
        for name,digest in methods.items():
            if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Motion diagnostic method changed')
        save(output/'result.json',dict(at=now(),status='complete',outputs={p.name:sha256(p) for p in output.iterdir() if p.is_file()},
            diagnostic_only=True,trials=len(diagnostic['trials']),quality_approved=False,accepted_for_publication=False))
        return
    def observe(row):
        if row['phase'] not in ['jacobian','restoration_jacobian'] or row['coordinates']%19==0:print(row,flush=True)
    def mesh_points(worlds):
        return [[rig.vertices(w[int(np.searchsorted(combined,t))])@a['rotation'].T+a['translation'] for rig,w,a in zip(rigs,worlds,actors)] for t in guard_times]
    if geometry_of is not None:
        from diagnostic_mesh_comparison import run as inspect_meshes
        arm,fingers=split(restoration_seed);decoded=[];clips=[]
        for i,(model,finger,rig) in enumerate(zip(models,fingers,rigs)):
            path=output/f'rejected-diagnostic-{i}.glb';model.export(arm,finger,path)
            asset=RigAsset.load(path);reader=AnimationSampler(asset.document,asset.binary,0)
            world=np.array([reader.sample(t) for t in combined]);decoded.append(world)
            np.testing.assert_allclose(world,model.evaluate(arm,finger)[0],rtol=0,atol=2e-10)
            prior_channels=rotation_channels(rig.document,rig.binary);current_channels=rotation_channels(asset.document,asset.binary)
            for node,(_,clock,q) in prior_channels.items():
                np.testing.assert_array_equal(clock,current_channels[node][1])
                if node not in model.channels:np.testing.assert_array_equal(q,current_channels[node][2])
            outside=(combined<=fr['window_s'][0])|(combined>=fr['window_s'][1])
            np.testing.assert_array_equal(world[outside],source_worlds[i][outside])
            clips.append(dict(path=path.name,sha256=sha256(path),native_clocks_and_unselected_channels_exact=True,diagnostic_only=True))
        decoded_vectors=np.concatenate([v.reshape(-1,3) for v in rate_vectors(payload([w[uniform] for w in decoded]),caps.dt)]+[palm_vectors(decoded)])
        witness_margins=(ceilings+old.gaps(decoded))/.02
        save(output/'decoded-diagnostic.json',dict(clips=clips,
            original_export_motion_caps_pass=bool(caps.check(dict(indices=np.arange(len(times)),**payload([w[uniform] for w in decoded])))),
            proposal_motion_and_palm_pass=bool(np.all(np.linalg.norm(decoded_vectors,axis=1)<=fixed_caps)),
            failed_old_witnesses=int(np.count_nonzero(witness_margins<0)),minimum_old_witness_margin=float(witness_margins.min()),
            diagnostic_only=True,accepted_for_publication=False,quality_approved=False,selected_for_studio=False))
        def vertices(label,index):
            frame=int(np.searchsorted(combined,guard_times[index]));worlds=source_worlds if label=='baseline' else decoded
            return [rig.vertices(w[frame])@actor['rotation'].T+actor['translation'] for rig,w,actor in zip(rigs,worlds,actors)]
        geometry=inspect_meshes([a['faces'] for a in actors],[len(r.vertices(r.reference)) for r in rigs],guard_times,vertices,
            lambda name,value:save(output/name,value),observe)
        for path,digest in files.items():
            if sha256(path)!=digest:raise ValueError('Diagnostic source changed')
        for name,digest in methods.items():
            if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Diagnostic method changed')
        save(output/'result.json',dict(at=now(),status='complete',outputs={p.name:sha256(p) for p in output.iterdir() if p.is_file()},
            source_numeric_metric=measurement(exact(restoration_seed)),**geometry))
        return
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
        if any(v is not None for v in [witness_of,ray_of,refine_of,continue_of,geometry_of,mesh_repair_of]):
            from restore_witness_feasibility import restore
            settings=dict(witness_start=1+len(arm_margins(arm_start,native,plan['guide_rate_limits'])),witness_count=len(ceilings)+(mesh_cut_record['scalar_rows'] if mesh_cut_record else 0))
        else:
            from restore_hand_feasibility import restore
            settings={}
        if headroom_source is not None:
            from motion_proposal_headroom import solve as solve_headroom
            model_path=mesh_ray_source/f'iteration-{last["iteration"]:02d}.npz'
            if files.get(str(model_path))!=sha256(model_path):raise ValueError('Bound saved mesh proposal required')
            with np.load(model_path,allow_pickle=False) as data:
                model=dict(point=data['point'],base={k:data[k] for k in ['vectors','caps','scales','margins','depths']},
                    jacobian={k:data[k+'_jacobian'] for k in ['vectors','margins','depths']})
            candidate,report=solve_headroom(exact,point,restoration_seed,model,
                bound(headroom_source/'motion-proposal-diagnostic.json'),solver,
                witness_reserve=last['proposal']['reserve'],observe=observe,**settings)
        elif continue_of is not None:
            from iterated_witness_repair import solve as continue_repair
            candidate,report=continue_repair(exact,smooth,point,restoration_seed,solver,iterations=iterations,trust=.001,observe=observe,checkpoint=checkpoint,**settings)
        elif refine_of is not None:
            from refine_serialized_witness_ray import refine
            candidate,report=refine(exact,point,restoration_seed,ray_delta,coarse_divisions=coarse_divisions,observe=observe,**settings)
        elif ray_of is not None or mesh_ray_of is not None:
            from scan_serialized_witness_ray import scan
            candidate,report=scan(exact,point,restoration_seed,ray_delta,observe=observe,**settings)
        else:
            candidate,report=restore(exact,smooth,point,restoration_seed,solver,iterations=iterations,trust=.001,observe=observe,checkpoint=checkpoint,**settings)
        best=point.copy()
        if candidate is not None:
            guard=make_guard();decision=guard(candidate);save(output/'restored-candidate-surface.json',decision)
            if decision['passed']:best=candidate
        report['mesh_guard_run']=guard is not None
    if expanded:
        from coupled_constraint_report import breakdown
        final=exact(np.asarray(report['final_point']));guide_rows=len(arm_margins(arm_start,native,plan['guide_rate_limits']))
        original_rows=1+guide_rows+len(ceilings);labels=[a['name']+':'+r.document['nodes'][n]['name'] for a,r in zip(actors,rigs) for n in r.joints]
        cut_count=mesh_cut_record['scalar_rows'] if mesh_cut_record else 0
        cut_margins=final['margins'][original_rows:original_rows+cut_count]
        extra_margins=final['margins'][original_rows+cut_count:]
        save(output/'final-constraints.json',dict(original=breakdown(dict(final,margins=final['margins'][:original_rows]),labels,len(times),guide_rows,len(ceilings)),
            mesh_cuts=dict(rows=cut_count,failed_rows=int(np.count_nonzero(cut_margins<0)),minimum_margin=float(cut_margins.min()) if cut_count else None),
            temporal=dict(rows=len(extra_margins),failed_rows=int(np.count_nonzero(extra_margins<0)),minimum_margin=float(extra_margins.min()))))
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
    if mesh_cuts is not None and np.any(mesh_cuts.margins(decoded)<0):raise ValueError('Decoded new mesh cuts failed')
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
    parser.add_argument('--iterations',type=int,default=3);parser.add_argument('--diagnose-study',type=Path);parser.add_argument('--restore-study',type=Path);parser.add_argument('--temporal-study',type=Path);parser.add_argument('--witness-study',type=Path);parser.add_argument('--ray-study',type=Path);parser.add_argument('--refine-study',type=Path);parser.add_argument('--continue-study',type=Path);parser.add_argument('--geometry-study',type=Path);parser.add_argument('--mesh-repair-study',type=Path);parser.add_argument('--mesh-ray-study',type=Path);parser.add_argument('--probe-motion',action='store_true');parser.add_argument('--motion-headroom-study',type=Path);args=parser.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(args.window_audit,args.arm_study,args.output,args.iterations,args.diagnose_study,args.restore_study,args.temporal_study,args.witness_study,args.ray_study,args.refine_study,args.continue_study,args.geometry_study,args.mesh_repair_study,args.mesh_ray_study,args.probe_motion,args.motion_headroom_study)
