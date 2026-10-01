"""Fit a separately authored meeting pose, then audit its whole edit interval."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.optimize import least_squares
from strep import ROOT,read,save,sha256,now


def run(source,output):
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from scene_pair_problem import load_actors
    from timed_rotation_edit import TimedRotationEdit,sampled_rotations
    from paired_guarded_temporal import world_from_local
    from paired_approach_basis import BoundSkin
    from native_finger_motion import palm_geometry
    from shared_palm_meeting import target,measure
    from sampled_motion_caps import SampledMotionCaps,features,measures
    from sampled_surface_guard import topology,snapshot,compare
    from triangle_crossing import audit
    from convex_partner_surface import penetration
    source,output=Path(source).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh shared-meeting study required')
    result=read(source/'result.json');request=read(source/'request.json')
    if result['status']!='complete':raise ValueError('Completed source required')
    files={str(source/'result.json'):sha256(source/'result.json')}
    for name,digest in result['outputs'].items():
        path=(source/name).resolve()
        if path.parent!=source or sha256(path)!=digest:raise ValueError('Source output changed')
        files[str(path)]=digest
    for path,digest in request['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Source input changed')
        files[path]=digest
    for name,digest in request['implementation'].items():
        path=source/'implementation'/name
        if sha256(path)!=digest:raise ValueError('Source method archive changed')
        files[str(path)]=digest
        if name!='study_coupled_window_repair.py' and sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Reference method changed')
    def bound(path):
        path=Path(path).resolve()
        if files.get(str(path))!=sha256(path):raise ValueError('Unbound source: '+str(path))
        return read(path)
    wr=bound(Path(request['window_audit'])/'request.json');fr=bound(Path(wr['study'])/'request.json')
    donor=bound(Path(fr['donor'])/'request.json');anchor=bound(Path(donor['study'])/'request.json')
    terminal=bound(Path(anchor['study'])/'request.json');plan=bound(Path(terminal['plan'])/'request.json')
    protocol=bound(Path(plan['source_plan'])/'request.json');baseline=Path(protocol['study']);br=bound(baseline/'result.json')
    original=bound(baseline/'request.json');prepared_folder=Path(original['prepared_request']).parent
    prepared,actors=load_actors(prepared_folder)
    scene=bound(prepared_folder/prepared['scene_snapshot']['path'])['scene']
    contact=next(c for c in scene['contacts'] if c['id'] in prepared['authored']['protected_contact_ids'])
    trial=next(v for v in bound(baseline/'trials.json') if v['folder']==br['selected'])
    window=np.asarray(fr['window_s']);event=float(fr['contact_time_s']);uniform=np.asarray(fr['uniform_times_s'])
    guard=np.asarray(request['guard_times_s'])
    if event not in guard:raise ValueError('Contact must be included in the complete guard clock')
    removed=[v for v in prepared['protected_seconds'] if v[0]<=event<=v[1]]
    protected=[v for v in prepared['protected_seconds'] if not v[0]<=event<=v[1]]
    if not removed:raise ValueError('Explicit frozen contact interval to replace required')
    rigs=[];references=[];fit_models=[];skins=[];patches=[];names=[];readers=[]
    for i,(actor,clip,entry) in enumerate(zip(actors,wr['clips'],trial['actors'])):
        path=Path(clip['path']);reference=baseline/br['selected']/entry['path']
        if files.get(str(path))!=clip['sha256'] or files.get(str(reference))!=entry['sha256']:raise ValueError('Bound donor and original rig required')
        rig=RigAsset.load(path);ref=RigAsset.load(reference);rigs.append(rig);references.append(ref)
        readers.append(AnimationSampler(rig.document,rig.binary,0));skins.append(BoundSkin(rig))
        joints=[rig.document['nodes'][n]['name'] for n in protocol['chains'][actor['name']]];names.append(joints)
        fit_models.append(TimedRotationEdit(rig.document,rig.binary,joints,[window[0],event,window[1]],window,protected,
            knots=[window[0],event,window[1]],limit_degrees=45.,reference=(ref.document,ref.binary)))
        item=contact['effector'] if i==0 else contact['target'];faces=actor['faces'][np.any(actor['faces']==item['surface_vertex'],axis=1)]
        ids,remap=np.unique(faces,return_inverse=True);patches.append((ids,remap.reshape(-1,3),int(np.flatnonzero(ids==item['surface_vertex'])[0])))
    def palms(worlds,frame):
        centers=[];normals=[]
        for world,skin,actor,(ids,faces,center) in zip(worlds,skins,actors,patches):
            points=skin.evaluate(world,np.full(len(ids),frame),ids)@actor['rotation'].T+actor['translation']
            c,n=palm_geometry(points,faces,center);centers.append(c);normals.append(n)
        return np.asarray(centers),np.asarray(normals)
    sizes=[m.size for m in fit_models]
    def split(x):return np.split(x,[sizes[0]])
    initial=palms([m.source_world for m in fit_models],1);spec=target(*initial)
    desired=np.asarray(spec['centers_m']);desired_normals=np.asarray(spec['normals'])
    def residual(x):
        centers,normals=palms([m.world(v) for m,v in zip(fit_models,split(x))],1)
        return np.r_[((centers-desired)/.001).ravel(),((normals-desired_normals)/.05).ravel(),x*.001]
    output.mkdir();(output/'implementation').mkdir();methods={}
    for name in sorted(set(request['implementation'])|{'study_shared_palm_meeting.py','shared_palm_meeting.py'}):
        path=ROOT/'scripts'/name;methods[name]=sha256(path);shutil.copyfile(path,output/'implementation'/name)
    save(output/'request.json',dict(at=now(),source=str(source),inputs=files,implementation=methods,
        window_s=window.tolist(),event_time_s=event,guard_times_s=guard.tolist(),target=spec,
        replaced_contact_id=contact['id'],replaced_protected_spans=removed,remaining_protected_spans=protected,
        original_reference_edit_limit_degrees=45.,additional_control_limit_degrees=15.,
        policy='New authored meeting condition. Geometric pose fit only; original motion caps and full interval geometry are independently audited, not relaxed.',
        quality_approved=False,accepted_for_publication=False))
    limit=np.deg2rad(15.)/np.sqrt(3)
    fit=least_squares(residual,np.zeros(sum(sizes)),bounds=(-limit,limit),max_nfev=150,ftol=1e-12,xtol=1e-12,gtol=1e-12)
    save(output/'fit.json',dict(controls=fit.x.tolist(),success=bool(fit.success),status=int(fit.status),message=fit.message,
        evaluations=int(fit.nfev),cost=float(fit.cost),initial=measure(*initial,spec),
        unrounded=measure(*palms([m.world(v) for m,v in zip(fit_models,split(fit.x))],1),spec),quality_approved=False))
    full=np.unique(np.r_[uniform,guard,window,0.,[r.duration for r in readers]])
    decoded=[];before=[];clips=[]
    for i,(rig,ref,reader,controls) in enumerate(zip(rigs,references,readers,split(fit.x))):
        model=TimedRotationEdit(rig.document,rig.binary,names[i],full,window,protected,knots=[window[0],event,window[1]],
            limit_degrees=45.,reference=(ref.document,ref.binary))
        path=output/f'authored-meeting-{i}.glb';model.export(controls,path)
        asset=RigAsset.load(path);current=AnimationSampler(asset.document,asset.binary,0)
        values=model.quaternions(controls,quantize=True);local=model.local.copy()
        for entry in model.entries:
            node=entry['node'];local[:,node,:3,:3]=sampled_rotations(entry['clock'],values[node],full)*model.scales[node][:,None,:]
        world=np.array([current.sample(t) for t in full]);prior=np.array([reader.sample(t) for t in full])
        np.testing.assert_allclose(world,world_from_local(local,model.parents),rtol=0,atol=2e-10)
        outside=(full<=window[0])|(full>=window[1]);np.testing.assert_array_equal(world[outside],prior[outside])
        if len(reader.channels)!=len(current.channels):raise ValueError('Animation channel population changed')
        for a,b in zip(reader.channels,current.channels):
            assert a[0:2]==b[0:2] and a[4]==b[4];np.testing.assert_array_equal(a[2],b[2])
            if a[1]!='rotation' or a[0] not in model.nodes:np.testing.assert_array_equal(a[3],b[3])
        decoded.append(world);before.append(prior)
        clips.append(dict(path=path.name,sha256=sha256(path),native_clocks_root_unselected_channels_and_outside_window_exact=True))
    selected=np.searchsorted(full,uniform)
    def payload(worlds):
        parts=[features(v,r.joints) for v,r in zip(worlds,references)]
        return {k:np.concatenate([p[k] for p in parts],axis=1) for k in ['positions','rotations']}
    reference_readers=[AnimationSampler(r.document,r.binary,0) for r in references]
    raw=[np.array([reader.sample(t) for t in uniform]) for reader in reference_readers]
    caps=SampledMotionCaps(payload(raw),uniform,fr['original_bins_s']);actual=payload([v[selected] for v in decoded])
    rates=[]
    for kind,unit,values,ceiling in zip(['position_speed','position_acceleration','angular_speed','angular_acceleration'],
            ['m/s','m/s^2','rad/s','rad/s^2'],measures(actual,caps.dt),caps.caps):
        excess=values-ceiling-caps.tolerance;rates.append(dict(kind=kind,unit=unit,failed_rows=int(np.count_nonzero(excess>0)),maximum_excess=float(excess.max())))
    decoded_contact=measure(*palms(decoded,int(np.searchsorted(full,event))),spec)
    save(output/'decoded.json',dict(clips=clips,contact=decoded_contact,motion_rates=rates,
        original_motion_caps_pass=bool(caps.check(dict(indices=np.arange(len(uniform)),**actual))),quality_approved=False))
    geometry_source=Path(request['mesh_repair_of']);gr=bound(geometry_source/'request.json')
    if gr['window_audit']!=request['window_audit'] or gr['arm_study']!=request['arm_study']:raise ValueError('Matching cached donor geometry required')
    baseline_snapshot=bound(geometry_source/'baseline-snapshot.json')
    meshes=topology([a['faces'] for a in actors],[len(r.vertices(r.reference)) for r in rigs])
    if baseline_snapshot['topology']!=meshes or [r['time_s'] for r in baseline_snapshot['samples']]!=guard.tolist():raise ValueError('Cached donor topology/clock changed')
    observations=[];floor=[]
    for i,t in enumerate(guard):
        frame=int(np.searchsorted(full,t))
        points=[r.vertices(w[frame])@a['rotation'].T+a['translation'] for r,w,a in zip(rigs,decoded,actors)]
        original_points=[r.vertices(w[frame])@a['rotation'].T+a['translation'] for r,w,a in zip(rigs,before,actors)]
        row=dict(time_s=float(t),surface=audit(points[0],actors[0]['faces'],points[1],actors[1]['faces']),
            depths=[penetration(points[a],points[b],actors[b]['faces']) for a,b in [(0,1),(1,0)]])
        observations.append(row);save(output/f'geometry-{i:02d}.json',row)
        floor.append(dict(time_s=float(t),before_m=[max(0.,-float(p[:,1].min())) for p in original_points],after_m=[max(0.,-float(p[:,1].min())) for p in points]))
        print(dict(phase='authored_meeting_geometry',completed=i+1,total=len(guard)),flush=True)
    current=snapshot(meshes,observations);decision=compare(baseline_snapshot,current)
    save(output/'mesh-comparison.json',decision);save(output/'floor.json',floor)
    for path,digest in files.items():
        if sha256(path)!=digest:raise ValueError('Meeting source changed')
    for name,digest in methods.items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Meeting method changed')
    save(output/'result.json',dict(at=now(),status='complete',outputs={p.name:sha256(p) for p in output.iterdir() if p.is_file()},
        contact_target_pass=decoded_contact['contact_target_pass'],original_motion_caps_pass=all(v['failed_rows']==0 for v in rates),
        sampled_mesh_regression_pass=decision['passed'],pair_time_crossings=sum(len(v['proper']) for v in current['samples']),
        maximum_vertex_depth_m=max(max(v['depths_m']) for v in current['samples']),
        diagnostic_only=True,new_authored_condition=True,selected_for_studio=False,accepted_for_publication=False,quality_approved=False))


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(args.source,args.output)
