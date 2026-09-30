"""Audit every replayed route's hands on the final native approach edge."""
import argparse,shutil
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now


def run(plan,output):
    from diagnose_scene_pair_limits import load_bound_study
    from scene_pair_problem import load_actors
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from paired_temporal_neighbor import rotation_channels
    from waypoint_path_evidence import load_path
    from wrist_waypoint_motion import bake
    from verify_scene_pair_fit import rate_check
    from scalar_angular_replay import angular_replay
    from hand_surface_screen import hand_vertices,screen
    plan,output=Path(plan).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh hand-route screen output required')
    request=read(plan/'request.json')
    if request.get('clock_mode')!='native_shared':raise ValueError('Native guide required')
    source_plan=Path(request['source_plan']);protocol=read(source_plan/'request.json');study=Path(protocol['study'])
    original,_,required=load_bound_study(study);prepared,actors=load_actors(Path(original['prepared_request']).parent)
    result=read(study/'result.json');trials=read(study/'trials.json')
    if sha256(study/'trials.json')!=result['trials_sha256']:raise ValueError('Selected source trial changed')
    selected=[r for r in trials if r['folder']==result['selected']]
    if len(selected)!=1 or not selected[0]['accepted_local_step'] or selected[0]['reasons']:raise ValueError('Accepted starting source required')
    folder=(study/selected[0]['folder']).resolve()
    if not folder.is_relative_to(study):raise ValueError('Source folder escapes study')
    required[str(study/'trials.json')]=result['trials_sha256'];sources=[];clocks=[];times=actors[0]['model'].times
    for actor,entry in zip(actors,selected[0]['actors']):
        path=(folder/entry['path']).resolve()
        if path.parent!=folder or sha256(path)!=entry['sha256']:raise ValueError('Source GLB changed')
        required[str(path)]=entry['sha256'];rig=RigAsset.load(path);chain=protocol['chains'][actor['name']]
        channels=rotation_channels(rig.document,rig.binary);clocks.extend(channels[n][1] for n in chain)
        reader=AnimationSampler(rig.document,rig.binary,0)
        sources.append(dict(path=path,rig=rig,chain=chain,hand_ids=hand_vertices(rig,chain[-1]),
                            world=np.array([reader.sample(t) for t in times])))
    kwargs=dict(native_clocks=clocks,protected=prepared['protected_seconds'],
                authored_window=prepared['authored']['window_s'],peak_time=float(times[protocol['sample']]))
    guide,_,original_route,files=load_path(plan,source_plan,request['window_s'],required,**kwargs)
    sample_ids=np.flatnonzero((times>=guide.times[-2])&(times<guide.times[-1]))
    if len(sample_ids)<2:raise ValueError('At least two samples in the final native edge required')
    # Select only from the entire independently replayed historical population.
    routes=[r for r in read(plan/'routes.json') if r['parameters'] is not None]
    output.mkdir();(output/'implementation').mkdir();methods={}
    names=set(request['implementation'])|{'screen_pair_hand_routes.py','hand_surface_screen.py','waypoint_path_evidence.py',
        'wrist_waypoint_motion.py','verify_scene_pair_fit.py','scalar_angular_replay.py','convex_partner_surface.py'}
    for name in sorted(names):
        shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name);methods[name]=sha256(output/'implementation'/name)
    save(output/'request.json',dict(at=now(),plan=str(plan),inputs=files,implementation=methods,
        original_proxy_selected=original_route['axis_name'],route_names=[r['axis_name'] for r in routes],
        sample_indices=sample_ids.tolist(),sample_times_s=times[sample_ids].tolist(),native_edge_s=guide.times[-2:].tolist(),
        hand_vertex_ids=[s['hand_ids'].tolist() for s in sources],tolerance_m=.005,
        selection_policy='Rank all replayed routes by final-edge hand peak depth, failing samples, proxy cost, then name; no acceptance inferred.',
        scope='Actual baked GLBs decoded on the original clock. All positive hand-subtree skin influences queried against the full opposite mesh, both directions, final native edge only. Whole-clock original-relative motion rates measured separately. No other-surface, whole-clock mesh, engine or continuous-time clearance claim.',quality_approved=False))
    records=[]
    for route in routes:
        name=route['axis_name'];guide,axis,chosen,bound=load_path(plan,source_plan,request['window_s'],required,route_name=name,**kwargs)
        if bound!=files or chosen!=route:raise ValueError('Route population changed')
        subfolder=output/name;subfolder.mkdir();worlds=[];decoded=[]
        for index,(actor,source) in enumerate(zip(actors,sources)):
            def curve(t):
                control=guide(t)
                return np.r_[axis*control[0]*(1 if index==0 else -1),control[index+1]]
            path=subfolder/f'candidate-{index}.glb'
            details=bake(source['rig'],source['chain'],[0,0,0],actor['rotation'],0,request['window_s'],
                         prepared['protected_seconds'],path,control_curve=curve)
            rig=RigAsset.load(path);reader=AnimationSampler(rig.document,rig.binary,0)
            world=np.array([reader.sample(t) for t in times]);worlds.append(world)
            before=rotation_channels(source['rig'].document,source['rig'].binary);after=rotation_channels(rig.document,rig.binary)
            for node,(_,clock,q) in before.items():
                np.testing.assert_array_equal(after[node][1],clock)
                frozen=np.setdiff1d(np.arange(len(clock)),details['nodes'].get(str(node),[]))
                np.testing.assert_array_equal(after[node][2][frozen],q[frozen])
            position=actor['rates'].positions
            decoded.append(dict(actor=actor['name'],path=str(path.relative_to(output)),sha256=sha256(path),
                positional=rate_check(position(source['world']),position(world),times,prepared['authored']['knots_s']),
                angular=angular_replay(source['world'][:,rig.joints,:3,:3],world[:,rig.joints,:3,:3],times,prepared['authored']['knots_s']),
                native_clocks_and_frozen_keys_exact=True))
        save(subfolder/'decoded.json',decoded);rows=[]
        for sample in sample_ids:
            points=[s['rig'].vertices(w[sample])@a['rotation'].T+a['translation'] for s,w,a in zip(sources,worlds,actors)]
            directions=[screen(points[s],sources[s]['hand_ids'],points[t],actors[t]['faces']) for s,t in [(0,1),(1,0)]]
            rows.append(dict(sample=int(sample),time_s=float(times[sample]),directions=directions,
                             hand_peak_m=max(d['max_depth_m'] for d in directions)))
            save(subfolder/'geometry.json',rows)
            print(dict(route=name,sample=int(sample),hand_peak_m=rows[-1]['hand_peak_m']),flush=True)
        records.append(dict(axis_name=name,proxy_cost=route['solver']['total_cost'],hand_peak_m=max(r['hand_peak_m'] for r in rows),
            failed_samples=sum(r['hand_peak_m']>.005 for r in rows),samples=len(rows),
            positional_failures=[d['positional']['failures'] for d in decoded],
            angular_failures=[{k:v['exceeding_observations'] for k,v in d['angular'].items()} for d in decoded],
            decoded_sha256=sha256(subfolder/'decoded.json'),geometry_sha256=sha256(subfolder/'geometry.json')))
        save(output/'routes.json',records)
    ranking=sorted(records,key=lambda r:(r['hand_peak_m'],r['failed_samples'],r['proxy_cost'],r['axis_name']))
    for path,digest in files.items():
        if sha256(path)!=digest:raise ValueError('Hand screen input changed')
    for name,digest in methods.items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Hand screen method changed')
    save(output/'result.json',dict(at=now(),status='complete',request_sha256=sha256(output/'request.json'),
        routes_sha256=sha256(output/'routes.json'),ranking=[r['axis_name'] for r in ranking],
        final_edge_hand_passing=[r['axis_name'] for r in records if not r['failed_samples']],
        directional_queries=2*len(routes)*len(sample_ids),full_mesh_clock_checked=False,accepted_for_publication=False,quality_approved=False))
    print(read(output/'result.json'),flush=True)


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('plan',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(args.plan,args.output)
