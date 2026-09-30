"""Search the native waypoint lattice with full sampled joint motion constraints."""
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
    from motion_lattice import bounded_path
    from decoded_motion_edges import DecodedEdges
    plan,output=Path(plan).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh motion-bounded path output required')
    request=read(plan/'request.json')
    if request.get('clock_mode')!='native_shared':raise ValueError('Native-clock planning input required')
    source_plan=Path(request['source_plan']);protocol=read(source_plan/'request.json')
    study=Path(protocol['study']);original,_,required=load_bound_study(study)
    prepared,actors=load_actors(Path(original['prepared_request']).parent)
    base=read(study/'result.json');trials=read(study/'trials.json')
    if sha256(study/'trials.json')!=base['trials_sha256']:raise ValueError('Source trial binding changed')
    selected=[r for r in trials if r['folder']==base['selected']]
    if len(selected)!=1 or not selected[0]['accepted_local_step'] or selected[0]['reasons']:raise ValueError('Accepted source correction required')
    folder=(study/selected[0]['folder']).resolve()
    if not folder.is_relative_to(study):raise ValueError('Source correction escapes study')
    required[str(study/'trials.json')]=base['trials_sha256'];clocks=[];sources=[];worlds=[]
    times=actors[0]['model'].times
    for actor,entry in zip(actors,selected[0]['actors']):
        path=(folder/entry['path']).resolve()
        if path.parent!=folder or sha256(path)!=entry['sha256']:raise ValueError('Source clip changed')
        required[str(path)]=entry['sha256'];rig=RigAsset.load(path);chain=protocol['chains'][actor['name']]
        channels=rotation_channels(rig.document,rig.binary);clocks.extend(channels[n][1] for n in chain)
        sampler=AnimationSampler(rig.document,rig.binary,0)
        sources.append(dict(rig=rig,chain=chain,rotation=actor['rotation']))
        worlds.append(np.array([sampler.sample(t) for t in times]))
    guide,_,_,files=load_path(plan,source_plan,request['window_s'],required,native_clocks=clocks,protected=prepared['protected_seconds'],
        authored_window=prepared['authored']['window_s'],peak_time=float(times[protocol['sample']]))
    parts=[features(w,s['rig'].joints) for w,s in zip(worlds,sources)]
    source={k:np.concatenate([p[k] for p in parts],axis=1) for k in ['positions','rotations']}
    caps=SampledMotionCaps(source,times,prepared['authored']['knots_s'])
    with np.load(plan/'lattice.npz',allow_pickle=False) as archive:lattice=dict(archive)
    states=lattice['states'];output.mkdir();(output/'implementation').mkdir();methods={}
    names=set(request['implementation'])|{'plan_motion_bounded_path.py','motion_lattice.py','sampled_motion_caps.py',
        'decoded_motion_edges.py','waypoint_path_evidence.py'}
    for name in sorted(names):
        shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name);methods[name]=sha256(output/'implementation'/name)
    save(output/'request.json',dict(at=now(),plan=str(plan),inputs=files,implementation=methods,
        source_study=str(study),sample_times_s=times.tolist(),native_times_s=guide.times.tolist(),
        original_bins_s=prepared['authored']['knots_s'],tolerance=1e-5,
        scope='All source joints, positional and world-angular speed/acceleration on the original uniform clock; exact regular-decoder float32 native arm keys. Edge interiors, adjacent-edge junctions and two frozen halo samples on each side are checked. This finite lattice may return the unchanged source; no collision clearance or continuous-time certificate is inferred.',quality_approved=False))
    routes=[]
    for index,(name,axis) in enumerate(request['axes'].items()):
        decoder=DecodedEdges(sources,guide.times,times,states,np.asarray(axis),caps)
        parameters,report=bounded_path(guide.times,states,lattice['costs'][index],request['guide_rate_limits'],
            decoder,caps.join,decoder.prefix,decoder.suffix,request['transition_weight'])
        record=dict(axis_name=name,axis=axis,solver=report,parameters=None if parameters is None else parameters.tolist())
        if parameters is not None:
            ids=report['state_indices'];payloads=[decoder.prefix]
            for layer,(a,b) in enumerate(zip(ids[:-1],ids[1:])):
                payload=decoder(layer,a,b)
                if payload is None:raise ValueError('Selected edge failed repeated decode')
                payloads.append(payload)
            payloads.append(decoder.suffix)
            joined={k:np.concatenate([p[k] for p in payloads]) for k in ['indices','positions','rotations']}
            if not caps.check(joined):raise ValueError('Whole selected trajectory failed motion replay')
            record['selected_full_sample_replay']=True;record['nonzero_controls']=bool(np.any(parameters))
        routes.append(record);save(output/'routes.json',routes)
        print(dict(axis=name,**report),flush=True)
    passing=[r for r in routes if r['parameters'] is not None]
    selected=min(passing,key=lambda r:(r['solver']['total_cost'],r['axis_name'])) if passing else None
    for path,digest in files.items():
        if sha256(path)!=digest:raise ValueError('Motion path input changed')
    for name,digest in methods.items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Motion path method changed')
    save(output/'result.json',dict(at=now(),status='complete',selected=None if selected is None else selected['axis_name'],
        nonzero_controls=False if selected is None else selected['nonzero_controls'],
        request_sha256=sha256(output/'request.json'),routes_sha256=sha256(output/'routes.json'),
        full_mesh_checked=False,accepted_for_publication=False,quality_approved=False))
    print(read(output/'result.json'),flush=True)


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('plan',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(args.plan,args.output)
