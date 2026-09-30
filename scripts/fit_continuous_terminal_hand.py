"""Fit terminal wrist/elbow controls to hand witnesses under decoded motion caps."""
import argparse,shutil
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now


def run(study,output,hand_orientation=False,witness_study=None):
    from bound_evidence import bind_inputs
    from diagnose_scene_pair_limits import load_bound_study
    from scene_pair_problem import load_actors
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from sampled_motion_caps import SampledMotionCaps,features,measures
    from hand_surface_screen import hand_vertices,screen
    from paired_approach_basis import BoundSkin
    from continuous_terminal_hand import VectorTerminalMotion,HandWitnessObjective,solve
    from oriented_terminal_hand import OrientedTerminalMotion,support_clock
    from hand_witness_reuse import load_queries,rebuild_witnesses
    from build_guarded_pair_witnesses import query
    from waypoint_path_evidence import load_path
    from paired_temporal_neighbor import rotation_channels
    from wrist_waypoint_motion import bake
    from waypoint_lattice import LinearGuide
    from verify_scene_pair_fit import rate_check
    from scalar_angular_replay import angular_replay
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh continuous terminal study required')
    result=read(study/'result.json');request=read(study/'request.json');files={str(study/'result.json'):sha256(study/'result.json')}
    if result['status']!='complete':raise ValueError('Completed terminal search required')
    for name,key in [('request.json','request_sha256'),('candidates.json','candidates_sha256'),('geometry.json','geometry_sha256')]:
        if sha256(study/name)!=result[key]:raise ValueError('Terminal search evidence changed')
        files[str(study/name)]=result[key]
    for name,digest in request['implementation'].items():
        path=(study/'implementation'/name).resolve()
        if path.parent!=study/'implementation' or sha256(path)!=digest:raise ValueError('Terminal snapshot changed')
        files[str(path)]=digest
    plan=Path(request['plan']);path_request=read(plan/'request.json');source_plan=Path(path_request['source_plan'])
    protocol=read(source_plan/'request.json');baseline=Path(protocol['study'])
    original,_,required=load_bound_study(baseline);files.update(bind_inputs(required,request['inputs']))
    prepared,actors=load_actors(Path(original['prepared_request']).parent)
    base_result=read(baseline/'result.json');trials=read(baseline/'trials.json')
    if sha256(baseline/'trials.json')!=base_result['trials_sha256']:raise ValueError('Baseline trials changed')
    selected=[r for r in trials if r['folder']==base_result['selected']]
    if len(selected)!=1 or not selected[0]['accepted_local_step'] or selected[0]['reasons']:raise ValueError('Accepted baseline required')
    trial=selected[0];folder=(baseline/trial['folder']).resolve()
    if not folder.is_relative_to(baseline):raise ValueError('Baseline escapes study')
    times=actors[0]['model'].times;np.testing.assert_array_equal(times,request['sample_times_s'])
    sources=[];reference=[];clocks=[]
    for actor,entry in zip(actors,trial['actors']):
        path=(folder/entry['path']).resolve()
        if path.parent!=folder or files.get(str(path))!=entry['sha256'] or sha256(path)!=entry['sha256']:raise ValueError('Bound baseline clip required')
        rig=RigAsset.load(path);chain=protocol['chains'][actor['name']];reader=AnimationSampler(rig.document,rig.binary,0)
        reference.append(np.array([reader.sample(t) for t in times]));channels=rotation_channels(rig.document,rig.binary)
        clocks.extend(channels[n][1] for n in chain)
        sources.append(dict(path=path,rig=rig,chain=chain,skin=BoundSkin(rig),hand=hand_vertices(rig,chain[-1])))
    guide,_,_,bound=load_path(plan,source_plan,path_request['window_s'],required,native_clocks=clocks,protected=prepared['protected_seconds'],
        authored_window=prepared['authored']['window_s'],peak_time=float(times[protocol['sample']]))
    files.update(bound);native=guide.times;np.testing.assert_array_equal(native,request['native_times_s'])
    edge=np.flatnonzero((times>=native[-2])&(times<native[-1]));suffix=np.flatnonzero(times>=native[-1])[:2]
    if len(edge)<2 or len(suffix)!=2:raise ValueError('Terminal edge and two frozen suffix samples required')
    ids=np.r_[edge,suffix];np.testing.assert_array_equal(np.diff(ids),1)
    if hand_orientation:edge,ids=support_clock(times,native[-3:])
    model_type=OrientedTerminalMotion if hand_orientation else VectorTerminalMotion
    models=[model_type(s['rig'],s['chain'],native[-3:],times[ids],prepared['protected_seconds'],a['rotation'],i)
            for i,(s,a) in enumerate(zip(sources,actors))]
    parts=[features(w,s['rig'].joints) for w,s in zip(reference,sources)]
    caps=SampledMotionCaps({k:np.concatenate([p[k] for p in parts],axis=1) for k in ['positions','rotations']},times,request['original_bins_s'])
    limits=np.asarray(path_request['guide_rate_limits']);dt=float(np.diff(native[-3:]).min())
    scale=np.r_[np.repeat(min(.06,limits[0]*dt),3),np.minimum(30.,limits[1:]*dt)]
    starts=[np.zeros(5),np.array([-.005,0,0,0,0]),np.array([0,0,-.02,0,0]),np.array([-.005,0,-.005,-1,-1])]
    if hand_orientation:
        scale=np.r_[scale,np.repeat(min(30.,300.*dt),6)]
        starts=[np.r_[v,np.zeros(6)] for v in starts]
        starts[2][5:]=[0,0,2.,0,0,-2.]
        starts[3][5:]=[0,2.,0,0,-2.,0]
    source_queries=[]
    if witness_study is not None:
        source_queries,reused_files=load_queries(witness_study,files,[s['hand'] for s in sources],edge);files.update(reused_files)
    output.mkdir();(output/'implementation').mkdir();methods={}
    names=set(request['implementation'])|{'fit_continuous_terminal_hand.py','continuous_terminal_hand.py','continuous_waypoint_motion.py',
        'build_guarded_pair_witnesses.py','paired_surface_witness.py','verify_scene_pair_fit.py','scalar_angular_replay.py','wrist_waypoint_motion.py',
        'oriented_terminal_hand.py','hand_witness_reuse.py'}
    for name in sorted(names):
        shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name);methods[name]=sha256(output/'implementation'/name)
    save(output/'request.json',dict(at=now(),study=str(study),inputs=files,implementation=methods,scale=scale.tolist(),starts=[v.tolist() for v in starts],
        sample_indices=ids.tolist(),hand_samples=edge.tolist(),native_times_s=native.tolist(),original_bins_s=request['original_bins_s'],
        hand_orientation=hand_orientation,witness_study=None if witness_study is None else str(Path(witness_study).resolve()),
        source_directional_queries_reused=len(source_queries),
        optimizer=dict(method='SLSQP',iterations_per_start=100,finite_difference_step=1e-4,ftol=1e-9),
        witness_maximum_per_direction_time=32,hand_tolerance_m=.005,motion_gate_tolerance=9e-6,export_tolerance=1e-5,
        scope=('Eleven continuous wrist/elbow/independent scene-hand rotation controls. Motion covers the entire edited-key support and two frozen halo samples on each side; hand witnesses and fresh hand audits cover both native intervals. ' if hand_orientation else
               'Five continuous symmetric wrist-vector/two-elbow controls at the final editable key. Motion is constrained on the final edge and two frozen suffix samples; incoming edge is not optimized. ')+
              'Fixed hand witnesses guide search only; exact baked GLBs, full-clock motion and fresh hand meshes are audited afterwards. No full-body/engine acceptance inferred.',quality_approved=False))
    reused_samples={q['sample'] for q in source_queries}
    for sample in edge:
        if int(sample) in reused_samples:continue
        frame=int(np.flatnonzero(ids==sample)[0])
        points=[s['rig'].vertices(w[sample])@a['rotation'].T+a['translation'] for s,w,a in zip(sources,reference,actors)]
        for source,target in [(0,1),(1,0)]:
            audit=query(points[source][sources[source]['hand']],points[target],actors[target]['faces'],maximum=32)
            source_queries.append(dict(frame=frame,sample=int(sample),source=source,target=target,**audit))
        print(dict(phase='source_queries',completed=len(source_queries),total=2*len(edge)),flush=True)
    source_queries=sorted(source_queries,key=lambda q:(q['sample'],q['source']))
    # Frames address this study's optimization clock, never the donor's clock.
    source_queries=[dict(q,frame=int(np.flatnonzero(ids==q['sample'])[0])) for q in source_queries]
    rows=rebuild_witnesses(source_queries,[s['hand'] for s in sources],ids)
    save(output/'witnesses.json',rows);save(output/'source-queries.json',source_queries)
    objective=HandWitnessObjective([s['skin'] for s in sources],actors,rows)
    motion_count=sum((len(ids)-o)*caps.joints for o in [1,2,1,2])
    def evaluate(control):
        domain=np.r_[1-np.linalg.norm(control[:3])/scale[0],1-np.abs(control[3:5])/scale[3:5]]
        if hand_orientation:domain=np.r_[domain,1-np.linalg.norm(control[5:8])/scale[5],1-np.linalg.norm(control[8:11])/scale[8]]
        try:
            evaluated=[m.evaluate_vector(control) for m in models];world=[r[0] for r in evaluated]
        except ValueError as error:
            if 'outside two-bone reach' not in str(error):raise
            return .2,np.r_[np.full(motion_count+1,-1.),domain]
        parts=[features(w,s['rig'].joints) for w,s in zip(world,sources)]
        payload=dict(indices=ids,**{k:np.concatenate([p[k] for p in parts],axis=1) for k in ['positions','rotations']})
        margins=[(bound[ids[0]:ids[0]+len(value)]+.9*caps.tolerance-value)/np.maximum(bound[ids[0]:ids[0]+len(value)],floor)
                 for value,bound,floor in zip(measures(payload,caps.dt),caps.caps,[.01,1.,.01,1.])]
        depth=max(0.,float(-objective.gaps(world).min()))
        return depth,np.r_[np.concatenate([v.ravel() for v in margins]),(45.+1e-4-max(r[1] for r in evaluated))/45.,domain]
    observed=[]
    def observe(record,best):
        observed.append(record)
        if len(observed)%100==0:
            save(output/'evaluations.json',observed)
            print(dict(phase='solve',evaluations=len(observed),best_depth_m=best['witness_peak_m'],feasible=record['motion_domain_feasible']),flush=True)
    best,solvers,records=solve(evaluate,scale,starts,observe=observe)
    save(output/'selected.json',best);save(output/'solvers.json',solvers);save(output/'evaluations.json',records)
    control=np.array(best['controls']);amount=float(np.linalg.norm(control[:3]));axis=control[:3]/amount if amount else np.array([1.,0.,0.])
    parameters=np.zeros((len(native),3));parameters[-2]=np.r_[amount,control[3:5]];fitted=LinearGuide(native,parameters,limits)
    decoded=[];worlds=[]
    for index,(s,a,m,old) in enumerate(zip(sources,actors,models,reference)):
        path=output/f'candidate-{index}.glb'
        def curve(t):
            v=fitted(t);return np.r_[axis*v[0]*(1 if index==0 else -1),v[index+1]]
        if hand_orientation:m.export_vector(control,path)
        else:bake(s['rig'],s['chain'],[0,0,0],a['rotation'],0,path_request['window_s'],prepared['protected_seconds'],path,control_curve=curve)
        rig=RigAsset.load(path);reader=AnimationSampler(rig.document,rig.binary,0);world=np.array([reader.sample(t) for t in times]);worlds.append(world)
        predicted,_=m.evaluate_vector(control);error=float(np.abs(world[ids]-predicted).max())
        if error>2e-10:raise ValueError('Baked GLB differs from continuous model')
        before=rotation_channels(s['rig'].document,s['rig'].binary);after=rotation_channels(rig.document,rig.binary)
        for node,(_,clock,q) in before.items():
            np.testing.assert_array_equal(after[node][1],clock)
            frozen=clock!=native[-2] if node in s['chain'] else np.ones(len(clock),bool)
            np.testing.assert_array_equal(after[node][2][frozen],q[frozen])
        outside=(times<=native[-3])|(times>=native[-1]);np.testing.assert_array_equal(world[outside],old[outside])
        decoded.append(dict(actor=a['name'],path=path.name,sha256=sha256(path),maximum_batch_error=error,native_clocks_and_frozen_keys_exact=True,
            positional=rate_check(a['rates'].positions(old),a['rates'].positions(world),times,request['original_bins_s']),
            angular=angular_replay(old[:,rig.joints,:3,:3],world[:,rig.joints,:3,:3],times,request['original_bins_s'])))
    parts=[features(w[ids],s['rig'].joints) for w,s in zip(worlds,sources)]
    if not caps.check(dict(indices=ids,**{k:np.concatenate([p[k] for p in parts],axis=1) for k in ['positions','rotations']})):
        raise ValueError('Actual GLB terminal motion fails independent gate')
    save(output/'decoded.json',decoded);geometry=[]
    for sample in edge:
        points=[s['rig'].vertices(w[sample])@a['rotation'].T+a['translation'] for s,w,a in zip(sources,worlds,actors)]
        directions=[screen(points[s],sources[s]['hand'],points[t],actors[t]['faces']) for s,t in [(0,1),(1,0)]]
        geometry.append(dict(sample=int(sample),time_s=float(times[sample]),directions=directions,hand_peak_m=max(d['max_depth_m'] for d in directions)))
        save(output/'geometry.json',geometry);print(dict(phase='fresh_geometry',completed=len(geometry),total=len(edge),peak_m=geometry[-1]['hand_peak_m']),flush=True)
    for path,digest in files.items():
        if sha256(path)!=digest:raise ValueError('Continuous hand input changed')
    for name,digest in methods.items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Continuous hand method changed')
    output_result=dict(at=now(),status='complete',nonzero_controls=bool(np.any(control)),terminal_motion_pass=True,
        hand_orientation=hand_orientation,whole_key_support_motion_constrained=hand_orientation,
        full_clock_motion_pass=all(not a['positional']['failures'] and not any(v['exceeding_observations'] for v in a['angular'].values()) for a in decoded),
        witness_peak_m=best['witness_peak_m'],fresh_hand_peak_m=max(r['hand_peak_m'] for r in geometry),
        failed_hand_samples=sum(r['hand_peak_m']>.005 for r in geometry),full_mesh_clock_checked=False,accepted_for_publication=False,quality_approved=False)
    for name in ['request','witnesses','source-queries','selected','solvers','evaluations','decoded','geometry']:
        output_result[name.replace('-','_')+'_sha256']=sha256(output/(name+'.json'))
    save(output/'result.json',output_result);print(output_result,flush=True)


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--hand-orientation',action='store_true');parser.add_argument('--witness-study',type=Path);args=parser.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(args.study,args.output,args.hand_orientation,args.witness_study)
