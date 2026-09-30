"""Attribute small terminal-control motion failures without relaxing their caps."""
import argparse,shutil
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now


def explain(payload,caps,names):
    from sampled_motion_caps import measures
    ids=np.asarray(payload['indices']);values=measures(payload,caps.dt);result={}
    if len(names)!=caps.joints:raise ValueError('One label per constrained joint required')
    # Validate the same clock, population and rotations as the actual gate.
    caps.check(payload)
    for metric,(name,unit,order,value,cap) in enumerate(zip(
            ['positional_speed','positional_acceleration','angular_speed','angular_acceleration'],
            ['m/s','m/s^2','rad/s','rad/s^2'],[1,2,1,2],values,caps.caps)):
        bound=cap[ids[0]:ids[0]+len(value)];excess=value-bound
        if not value.size:result[name]=dict(violations=0,worst=None);continue
        i,j=np.unravel_index(np.argmax(excess),excess.shape);sample=int(ids[0]+i)
        stamp=caps.times[sample+1] if metric==3 else (caps.times[sample]+caps.times[sample+order])/2
        result[name]=dict(violations=int((excess>caps.tolerance).sum()),unit=unit,
            worst=dict(joint=names[j],time_s=float(stamp),value=float(value[i,j]),cap=float(bound[i,j]),excess=float(excess[i,j])))
    return result


def run(study,output):
    from diagnose_scene_pair_limits import load_bound_study
    from bound_evidence import bind_inputs
    from scene_pair_problem import load_actors
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from sampled_motion_caps import SampledMotionCaps,features
    from decoded_motion_edges import DecodedEdges
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh terminal rate diagnosis required')
    result=read(study/'result.json');request=read(study/'request.json');files={str(study/'result.json'):sha256(study/'result.json')}
    if result['status']!='complete':raise ValueError('Completed terminal search required')
    for name,key in [('request.json','request_sha256'),('candidates.json','candidates_sha256'),('geometry.json','geometry_sha256')]:
        if sha256(study/name)!=result[key]:raise ValueError('Terminal search evidence changed')
        files[str(study/name)]=result[key]
    for name,digest in request['implementation'].items():
        path=(study/'implementation'/name).resolve()
        if path.parent!=study/'implementation' or sha256(path)!=digest or sha256(ROOT/'scripts'/name)!=digest:
            raise ValueError('Terminal method differs from the completed study')
        files[str(path)]=digest
    plan=read(Path(request['plan'])/'request.json');protocol=read(Path(plan['source_plan'])/'request.json');baseline=Path(protocol['study'])
    original,_,required=load_bound_study(baseline);files.update(bind_inputs(required,request['inputs']))
    prepared,actors=load_actors(Path(original['prepared_request']).parent)
    selected=read(baseline/'result.json')['selected'];trial=next(r for r in read(baseline/'trials.json') if r['folder']==selected)
    times=np.asarray(request['sample_times_s']);native=np.asarray(request['native_times_s']);sources=[];worlds=[];names=[]
    for actor,entry in zip(actors,trial['actors']):
        path=(baseline/selected/entry['path']).resolve()
        if files.get(str(path))!=entry['sha256'] or sha256(path)!=entry['sha256']:raise ValueError('Bound baseline clip required')
        rig=RigAsset.load(path);reader=AnimationSampler(rig.document,rig.binary,0)
        sources.append(dict(rig=rig,chain=protocol['chains'][actor['name']],rotation=actor['rotation']))
        worlds.append(np.array([reader.sample(t) for t in times]))
        names.extend(actor['name']+':'+rig.document['nodes'][n]['name'] for n in rig.joints)
    parts=[features(w,s['rig'].joints) for w,s in zip(worlds,sources)]
    caps=SampledMotionCaps({k:np.concatenate([p[k] for p in parts],axis=1) for k in ['positions','rotations']},times,request['original_bins_s'])
    states=np.asarray(request['states']);axes=np.asarray(request['axes']);zero=int(np.flatnonzero(np.all(states==0,axis=1))[0]);records=[]
    probes=[(a,s) for a,s in request['candidates'] if
            (np.count_nonzero(axes[a])==1 and np.array_equal(states[s],[.005,0,0])) or
            (states[s,0]==0 and np.sum(np.abs(states[s,1:])) in [0,7.5])]
    output.mkdir();(output/'implementation').mkdir();methods={}
    for name in sorted(set(request['implementation'])|{'diagnose_terminal_hand_rates.py'}):
        shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name);methods[name]=sha256(output/'implementation'/name)
    save(output/'request.json',dict(at=now(),study=str(study),inputs=files,implementation=methods,probes=probes,
        scope='Unchanged source, six 5-mm axial edits and four 7.5-degree single-elbow edits. Attribute necessary terminal-edge/frozen-suffix motion failures; no mesh queries or acceptance.',quality_approved=False))
    for axis,state in probes:
        decoder=DecodedEdges(sources,native,times,states,axes[axis],caps);decoded=decoder.decode(len(native)-2,state,zero)
        record=dict(axis=axes[axis].tolist(),control=states[state].tolist(),native_pose_valid=decoded is not None)
        if decoded is not None:
            ids,world=decoded;payload=decoder.combine(world,ids)
            record['edge']=explain(payload,caps,names)
            joined={k:np.concatenate([payload[k][-2:],decoder.suffix[k]]) for k in payload}
            record['frozen_junction']=explain(joined,caps,names)
        records.append(record)
    save(output/'probes.json',records)
    for path,digest in files.items():
        if sha256(path)!=digest:raise ValueError('Rate diagnosis input changed')
    for name,digest in methods.items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Rate diagnosis method changed')
    save(output/'result.json',dict(at=now(),status='complete',probes=len(records),request_sha256=sha256(output/'request.json'),
        probes_sha256=sha256(output/'probes.json'),accepted_for_publication=False,quality_approved=False))
    print(read(output/'result.json'),flush=True)


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(args.study,args.output)
