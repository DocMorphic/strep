"""Bake and audit paired wrist guides with native keys and protected contact."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT,read,save,sha256,now


def run(plan,output,path_plan=None):
    from diagnose_scene_pair_limits import load_bound_study
    from scene_pair_problem import load_actors
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from wrist_waypoint_motion import bake,peak_window,bump
    from paired_temporal_neighbor import rotation_channels
    from verify_scene_pair_fit import rate_check
    from scalar_angular_replay import angular_replay
    from convex_partner_surface import penetration
    from run_godot_rig_import import run as engine_run
    from scipy.spatial.transform import Rotation
    plan,output=Path(plan).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh temporal waypoint study required')
    result=read(plan/'result.json');protocol=read(plan/'request.json');files={str(plan/'result.json'):sha256(plan/'result.json')}
    if result['status']!='complete' or protocol.get('wrist_waypoints') is not True:raise ValueError('Completed wrist waypoint plan required')
    for name,key in [('request.json','request_sha256'),('audits.json','audits_sha256'),('proxy-candidates.json','proxy_sha256'),('rejected-candidates.json','rejected_sha256')]:
        if sha256(plan/name)!=result[key]:raise ValueError('Waypoint evidence changed')
        files[str(plan/name)]=result[key]
    for path,digest in protocol['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Waypoint input changed')
        files[path]=digest
    for name,digest in protocol['implementation'].items():
        path=(plan/'implementation'/name).resolve()
        if path.parent!=plan/'implementation' or sha256(path)!=digest:raise ValueError('Waypoint method snapshot changed')
        files[str(path)]=digest
    passing=[r for r in read(plan/'audits.json') if r['vertex_depth_screen_pass'] and r['floor_screen_pass'] and r['full_mesh_depth_m']<=.005 and max(r['floor_depth_m'])<=.005]
    if not passing:raise ValueError('A geometrically screened waypoint required')
    waypoint=min(passing,key=lambda r:(r['planning_cost'],r['id']))
    static_folder=(plan/waypoint['id']).resolve()
    if static_folder.parent!=plan:raise ValueError('Waypoint folder escapes plan')
    for name,digest in [('geometry.json',waypoint['geometry_sha256'])]+[(a['path'],a['sha256']) for a in waypoint['actors']]:
        path=(static_folder/name).resolve()
        if path.parent!=static_folder or sha256(path)!=digest:raise ValueError('Waypoint output changed')
        files[str(path)]=digest
    study=Path(protocol['study']);request,_,required=load_bound_study(study);files.update(required)
    baseline_result=read(study/'result.json');trials=read(study/'trials.json')
    if sha256(study/'trials.json')!=baseline_result['trials_sha256']:raise ValueError('Selected baseline changed')
    files[str(study/'trials.json')]=baseline_result['trials_sha256']
    matches=[r for r in trials if r['folder']==baseline_result['selected']]
    if len(matches)!=1 or not matches[0]['accepted_local_step'] or matches[0]['reasons']:raise ValueError('Accepted baseline required')
    baseline=matches[0];folder=(study/baseline['folder']).resolve()
    if not folder.is_relative_to(study):raise ValueError('Baseline escapes study')
    geometry=folder/'geometry.json'
    if sha256(geometry)!=baseline['geometry']['geometry_sha256']:raise ValueError('Baseline geometry changed')
    files[str(geometry)]=sha256(geometry);previous=read(geometry)
    prepared,actors=load_actors(Path(request['prepared_request']).parent)
    times=actors[0]['model'].times
    np.testing.assert_array_equal(times,[r['time_s'] for r in previous])
    window=peak_window(previous,protocol['sample'],prepared['authored']['window_s'])
    if path_plan is not None and read(Path(path_plan)/'request.json').get('planning_interval_policy')=='guarded_precontact':
        from native_waypoint_clock import guarded_approach_window
        window=guarded_approach_window(prepared['authored']['window_s'],float(times[protocol['sample']]),prepared['protected_seconds'])
    for span in prepared['protected_seconds']:
        if window[0]<span[1] and window[2]>span[0]:raise ValueError('Approach interval crosses a protected contact')
    guide=axis=route=None
    if path_plan is not None:
        from waypoint_path_evidence import load_path
        native_clocks=[]
        for actor,entry in zip(actors,baseline['actors']):
            source=(folder/entry['path']).resolve()
            if source.parent!=folder or sha256(source)!=entry['sha256']:raise ValueError('Baseline clip changed')
            files[str(source)]=entry['sha256'];native_rig=RigAsset.load(source)
            channels=rotation_channels(native_rig.document,native_rig.binary)
            native_clocks.extend(channels[node][1] for node in protocol['chains'][actor['name']])
        guide,axis,route,path_files=load_path(path_plan,plan,window,files,
            native_clocks=native_clocks,protected=prepared['protected_seconds'],authored_window=prepared['authored']['window_s'],
            peak_time=float(times[protocol['sample']]));files.update(path_files)
    if [a['name'] for a in actors]!=[a['actor'] for a in waypoint['actors']]:raise ValueError('Waypoint actor order differs')
    if sha256(ROOT/'scripts/convex_partner_surface.py')!=request['implementation']['convex_partner_surface.py']:
        raise ValueError('Reused geometry method differs')
    output.mkdir();(output/'implementation').mkdir();methods={}
    for name in sorted(set(protocol['implementation'])|{'fit_pair_wrist_waypoint.py','wrist_waypoint_motion.py',
            'timed_rotation_edit.py','paired_temporal_neighbor.py','verify_scene_pair_fit.py','scalar_angular_replay.py',
            'run_godot_rig_import.py','godot_import_audit.gd','waypoint_path_evidence.py','waypoint_lattice.py',
            'bound_evidence.py','native_waypoint_clock.py'}):
        shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name);methods[name]=sha256(output/'implementation'/name)
    records=[];worlds=[];originals=[];cases=[]
    for index,(actor,entry) in enumerate(zip(actors,baseline['actors'])):
        source=(folder/entry['path']).resolve()
        if source.parent!=folder or sha256(source)!=entry['sha256']:raise ValueError('Baseline clip changed')
        files[str(source)]=entry['sha256'];rig=RigAsset.load(source);sampler=AnimationSampler(rig.document,rig.binary,0)
        chain=protocol['chains'][actor['name']];candidate=output/f'candidate-{index}.glb'
        def curve(t):
            parameters=guide(t)
            return np.r_[axis*parameters[0]*(1 if index==0 else -1),parameters[index+1]]
        details=bake(rig,chain,waypoint['world_wrist_offsets_m'][index],actor['rotation'],waypoint['angles_degrees'][index],
            window,prepared['protected_seconds'],candidate,control_curve=None if guide is None else curve)
        decoded=RigAsset.load(candidate);reader=AnimationSampler(decoded.document,decoded.binary,0)
        before=rotation_channels(rig.document,rig.binary);after=rotation_channels(decoded.document,decoded.binary)
        maximum_edit=0.;frozen_keys=0
        for node,(_,clock,q) in before.items():
            np.testing.assert_array_equal(after[node][1],clock)
            frozen=np.setdiff1d(np.arange(len(clock)),details['nodes'].get(str(node),[]))
            np.testing.assert_array_equal(after[node][2][frozen],q[frozen]);frozen_keys+=len(frozen)
            maximum_edit=max(maximum_edit,float(np.rad2deg((Rotation.from_quat(q).inv()*Rotation.from_quat(after[node][2])).magnitude()).max()))
        if maximum_edit>45.+1e-4:raise ValueError('Decoded temporal native budget exceeded')
        old=np.array([sampler.sample(t) for t in times]);new=np.array([reader.sample(t) for t in times])
        frozen_clock=np.unique(np.r_[np.linspace(0,sampler.duration,int(np.ceil(sampler.duration*120))+1),np.asarray(prepared['protected_seconds']).ravel(),window[0],window[2]])
        frozen_clock=frozen_clock[(frozen_clock<=window[0])|(frozen_clock>=window[2])]
        preserved=max(float(np.abs(reader.sample(t)-sampler.sample(t)).max()) for t in frozen_clock)
        if preserved!=0:raise ValueError('Outside-window or protected poses changed')
        joints=rig.joints;pos=actor['rates'].positions
        positional=rate_check(pos(old),pos(new),times,actor['model'].knots)
        angular=angular_replay(old[:,joints,:3,:3],new[:,joints,:3,:3],times,actor['model'].knots)
        expected=old[:,chain[2],:3,3]@actor['rotation'].T+actor['translation']
        expected+=(np.array([bump(t,*window) for t in times])[:,None]*np.array(waypoint['world_wrist_offsets_m'][index])
                   if guide is None else np.array([curve(t)[:3] for t in times]))
        actual=new[:,chain[2],:3,3]@actor['rotation'].T+actor['translation']
        records.append(dict(actor=actor['name'],path=candidate.name,sha256=sha256(candidate),bake=details,
            maximum_joint_edit_degrees=maximum_edit,frozen_quaternion_keys=frozen_keys,protected_pose_samples=len(frozen_clock),
            maximum_protected_pose_error=preserved,maximum_wrist_target_error_m=float(np.linalg.norm(actual-expected,axis=1).max()),
            positional=positional,angular=angular))
        originals.append(old);worlds.append(new)
        shutil.copyfile(source,output/f'source-{index}.glb')
        for label in ['source','candidate']:
            path=output/f'{label}-{index}.glb'
            cases.append(dict(id=label+'-'+actor['name'],path=path.name,sha256=sha256(path),frames=int(round(sampler.duration*30))+1,fps=30,sample_by_time=True))
    save(output/'request.json',dict(at=now(),plan=str(plan),waypoint=waypoint['id'] if guide is None else None,
        path_plan=None if path_plan is None else str(Path(path_plan).resolve()),path_route=route,inputs=files,implementation=methods,
        window_s=list(window),protected_seconds=prepared['protected_seconds'],native_edit_budget_degrees=45.,
        scope='Experimental approach inside the recorded edit window. Native clocks, frozen keys, outside-window and protected contact poses remain exact. Original-relative rates are measured and may fail; no relaxed motion approval is inferred. Full local-clock vertex geometry and engine audit follow; all failures remain visible.',quality_approved=False))
    save(output/'decoded.json',records);save(output/'manifest.json',dict(cases=cases,quality_approved=False))
    print(dict(phase='decoded',window=window,waypoint=waypoint['id'] if guide is None else route['axis_name'],positional_failures=[r['positional']['failures'] for r in records]),flush=True)
    engine_run(output,output/'engine');rows=[];reused=0
    for i,prior in enumerate(previous):
        unchanged=all(np.array_equal(a[i],b[i]) for a,b in zip(worlds,originals))
        if unchanged:
            directions=prior['directions'];floor=prior['floor_depth_m'];reused+=1
        else:
            points=[a['rig'].vertices(w[i])@a['rotation'].T+a['translation'] for a,w in zip(actors,worlds)]
            directions=[penetration(points[s],points[t],actors[t]['faces']) for s,t in [(0,1),(1,0)]]
            floor=[max(0.,-float(p[:,1].min())) for p in points]
        depth=max(d['max_depth_m'] for d in directions)
        rows.append(dict(sample=i,time_s=prior['time_s'],directions=directions,baseline_depth_m=prior['candidate_depth_m'],
            candidate_depth_m=depth,floor_depth_m=floor,exact_unchanged_world_reuse=unchanged,
            floor_increase_m=max(f-s for f,s in zip(floor,prior['floor_depth_m']))))
        save(output/'geometry.json',rows)
        if (i+1)%10==0:print(dict(phase='geometry',completed=i+1,total=len(previous),reused=reused),flush=True)
    for path,digest in files.items():
        if sha256(path)!=digest:raise ValueError('Temporal waypoint input changed')
    for name,digest in methods.items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Temporal waypoint method changed')
    save(output/'result.json',dict(at=now(),status='complete',samples=len(rows),unchanged_samples_reused=reused,
        fresh_directional_queries=2*(len(rows)-reused),baseline_peak_m=max(r['baseline_depth_m'] for r in rows),
        candidate_peak_m=max(r['candidate_depth_m'] for r in rows),failed_samples=sum(r['candidate_depth_m']>.005 for r in rows),
        edited_window_peak_m=max(r['candidate_depth_m'] for r in rows if window[0]<=r['time_s']<=window[2]),
        maximum_floor_increase_m=max(r['floor_increase_m'] for r in rows),
        request_sha256=sha256(output/'request.json'),decoded_sha256=sha256(output/'decoded.json'),geometry_sha256=sha256(output/'geometry.json'),
        engine_sha256=sha256(output/'engine/verification.json'),accepted_for_publication=False,quality_approved=False))
    print(read(output/'result.json'),flush=True)


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--path-plan',type=Path);a=p.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(a.plan,a.output,a.path_plan)
