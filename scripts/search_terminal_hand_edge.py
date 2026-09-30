"""Search expanded terminal wrist/swivel states with motion-first hand rejection."""
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
    from sampled_motion_caps import SampledMotionCaps,features
    from decoded_motion_edges import DecodedEdges
    from hand_surface_screen import hand_vertices,screen
    from terminal_hand_search import population,candidates,terminal_motion_pass,reject_hand_edge
    plan,output=Path(plan).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh terminal hand search output required')
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
    required[str(study/'trials.json')]=result['trials_sha256'];sources=[];clocks=[];times=actors[0]['model'].times;reference=[]
    for actor,entry in zip(actors,selected[0]['actors']):
        path=(folder/entry['path']).resolve()
        if path.parent!=folder or sha256(path)!=entry['sha256']:raise ValueError('Source GLB changed')
        required[str(path)]=entry['sha256'];rig=RigAsset.load(path);chain=protocol['chains'][actor['name']]
        channels=rotation_channels(rig.document,rig.binary);clocks.extend(channels[n][1] for n in chain)
        reader=AnimationSampler(rig.document,rig.binary,0)
        reference.append(np.array([reader.sample(t) for t in times]))
        sources.append(dict(rig=rig,chain=chain,rotation=actor['rotation'],hand_ids=hand_vertices(rig,chain[-1])))
    guide,_,_,files=load_path(plan,source_plan,request['window_s'],required,native_clocks=clocks,protected=prepared['protected_seconds'],
        authored_window=prepared['authored']['window_s'],peak_time=float(times[protocol['sample']]))
    parts=[features(w,s['rig'].joints) for w,s in zip(reference,sources)]
    source={k:np.concatenate([p[k] for p in parts],axis=1) for k in ['positions','rotations']}
    caps=SampledMotionCaps(source,times,prepared['authored']['knots_s'])
    directions,states=population();dt=float(guide.times[-1]-guide.times[-2]);population_ids=candidates(directions,states,dt,request['guide_rate_limits'])
    zero=int(np.flatnonzero(np.all(states==0,axis=1))[0]);layer=len(guide.times)-2
    output.mkdir();(output/'implementation').mkdir();methods={}
    names=set(request['implementation'])|{'search_terminal_hand_edge.py','terminal_hand_search.py','hand_surface_screen.py',
        'decoded_motion_edges.py','sampled_motion_caps.py','waypoint_path_evidence.py','convex_partner_surface.py'}
    for name in sorted(names):
        shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name);methods[name]=sha256(output/'implementation'/name)
    save(output/'request.json',dict(at=now(),plan=str(plan),inputs=files,implementation=methods,axes=directions.tolist(),states=states.tolist(),
        candidates=[list(v) for v in population_ids],native_times_s=guide.times.tolist(),sample_times_s=times.tolist(),
        original_bins_s=prepared['authored']['knots_s'],guide_limits=request['guide_rate_limits'],terminal_edge_s=guide.times[-2:].tolist(),
        hand_vertex_ids=[s['hand_ids'].tolist() for s in sources],tolerance_m=.005,motion_tolerance=1e-5,
        scope='Necessary terminal-edge conditions only: exact float32 native pose replay, unchanged native edit budget and Euclidean fixed-direction guide limit, original-bin joint motion on edge interiors and two-sample frozen suffix, then both hands against full opposite meshes. Incoming-edge junction, earlier approach, other body surfaces and continuous time remain unverified. First hand failure rejects; observed partial maxima are lower bounds, not complete peaks.',quality_approved=False))
    records=[];geometry=[];passing=[];counts={};queries=0
    def query(worlds):
        points=[s['rig'].vertices(w)@a['rotation'].T+a['translation'] for s,w,a in zip(sources,worlds,actors)]
        return [screen(points[s],sources[s]['hand_ids'],points[t],actors[t]['faces']) for s,t in [(0,1),(1,0)]]
    for axis,direction in enumerate(directions):
        decoder=DecodedEdges(sources,guide.times,times,states,direction,caps)
        for ai,state in population_ids:
            if ai!=axis:continue
            decoded,reason=terminal_motion_pass(decoder,layer,state,zero)
            record=dict(id=len(records),axis=axis,state=state,reason=reason)
            if decoded is not None:
                ids,worlds=decoded
                # Center first is only a query-order heuristic. A passing result
                # must check every declared sample in both directions.
                priority=sorted(range(len(ids)),key=lambda i:(abs(i-(len(ids)-1)/2),i))
                audit=reject_hand_edge(ids,worlds,query,priority=priority)
                queries+=2*len(audit['rows']);geometry.append(dict(id=record['id'],**audit))
                record['reason']='terminal_pass' if audit['passed'] else 'hand_collision'
                if audit['passed']:passing.append(record['id'])
                save(output/'geometry.json',geometry)
            counts[record['reason']]=counts.get(record['reason'],0)+1;records.append(record)
            if len(records)%100==0:
                save(output/'candidates.json',records)
                print(dict(completed=len(records),total=len(population_ids),counts=counts,directional_queries=queries),flush=True)
        save(output/'candidates.json',records)
    save(output/'geometry.json',geometry)
    for path,digest in files.items():
        if sha256(path)!=digest:raise ValueError('Terminal search input changed')
    for name,digest in methods.items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Terminal search method changed')
    save(output/'result.json',dict(at=now(),status='complete',population=len(records),counts=counts,passing_candidate_ids=passing,
        directional_queries=queries,request_sha256=sha256(output/'request.json'),candidates_sha256=sha256(output/'candidates.json'),
        geometry_sha256=sha256(output/'geometry.json'),full_path_verified=False,full_mesh_clock_checked=False,
        accepted_for_publication=False,quality_approved=False))
    print(read(output/'result.json'),flush=True)


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('plan',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(args.plan,args.output)
