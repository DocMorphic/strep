"""Project a planned wrist guide toward original decoded motion limits."""
import argparse,shutil
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now


def run(plan,output,method='COBYLA',start='source'):
    from diagnose_scene_pair_limits import load_bound_study
    from scene_pair_problem import load_actors
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from paired_temporal_neighbor import rotation_channels
    from waypoint_path_evidence import load_path
    from sampled_motion_caps import SampledMotionCaps,features
    from continuous_waypoint_motion import ContinuousWaypointMotion
    from waypoint_projection import project
    from waypoint_lattice import LinearGuide
    from wrist_waypoint_motion import bake
    from verify_scene_pair_fit import rate_check
    from scalar_angular_replay import angular_replay
    from run_godot_rig_import import run as engine_run
    from convex_partner_surface import penetration
    plan,output=Path(plan).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh continuous projection output required')
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
        sources.append(dict(path=path,rig=rig,chain=chain))
    guide,axis,route,files=load_path(plan,source_plan,request['window_s'],required,native_clocks=clocks,protected=prepared['protected_seconds'],
        authored_window=prepared['authored']['window_s'],peak_time=float(times[protocol['sample']]))
    models=[ContinuousWaypointMotion(s['rig'],s['chain'],guide.times,times,prepared['protected_seconds'],a['rotation'],axis,i)
            for i,(s,a) in enumerate(zip(sources,actors))]
    parts=[features(m.model.source_world,m.rig.joints) for m in models]
    source={k:np.concatenate([p[k] for p in parts],axis=1) for k in ['positions','rotations']}
    caps=SampledMotionCaps(source,times,prepared['authored']['knots_s'])
    output.mkdir();(output/'implementation').mkdir();methods={}
    names=set(request['implementation'])|{'project_native_waypoint_path.py','continuous_waypoint_motion.py','waypoint_projection.py',
        'sampled_motion_caps.py','waypoint_path_evidence.py','wrist_waypoint_motion.py','verify_scene_pair_fit.py',
        'scalar_angular_replay.py','run_godot_rig_import.py','godot_import_audit.gd','convex_partner_surface.py'}
    for name in sorted(names):
        shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name);methods[name]=sha256(output/'implementation'/name)
    import scipy
    save(output/'request.json',dict(at=now(),plan=str(plan),inputs=files,implementation=methods,numpy_version=np.__version__,scipy_version=scipy.__version__,
        axis=axis.tolist(),native_times_s=guide.times.tolist(),sample_times_s=times.tolist(),target=route['parameters'],
        original_bins_s=prepared['authored']['knots_s'],guide_rate_limits=request['guide_rate_limits'],
        projection_gate_tolerance=9e-6,independent_export_tolerance=1e-5,
        initialization=start,
        optimizer=(dict(method='COBYLA',max_evaluations=1200,rhobeg=.1,tol=1e-5,catol=1e-9) if method=='COBYLA'
                   else dict(method='SLSQP',max_iterations=100,ftol=1e-9,finite_difference_step=1e-4)),
        scope='Nearest normalized wrist/swivel controls to the selected planned guide under unchanged sampled motion, guide-rate, domain and native-edit bounds. Feasible incumbents are independently gated, not inferred from optimizer success. Proximity to the target does not establish collision clearance.',quality_approved=False))
    observed=[]
    def observe(record,best):
        observed.append(record)
        if record['evaluation']%25==0:
            save(output/'evaluations.json',observed)
            save(output/'progress.json',dict(evaluations=len(observed),best=best,current=record))
            print(dict(evaluations=len(observed),feasible=record['feasible'],best_objective=None if best is None else best['objective']),flush=True)
    best,solver,records=project(models,caps,guide.times,route['parameters'],request['guide_rate_limits'],observe=observe,
        method=method,start=start,max_evaluations=1200 if method=='COBYLA' else 100)
    save(output/'evaluations.json',records);save(output/'solver.json',solver);save(output/'selected.json',best)
    parameters=np.asarray(best['parameters']);changed=bool(np.any(parameters));decoded=[];engine=None;geometry=None
    if changed:
        fitted=LinearGuide(guide.times,parameters,request['guide_rate_limits']);cases=[];peak_world=[]
        for index,(actor,source,model) in enumerate(zip(actors,sources,models)):
            curve=lambda t:np.r_[axis*fitted(t)[0]*(1 if index==0 else -1),fitted(t)[index+1]]
            path=output/f'candidate-{index}.glb'
            details=bake(source['rig'],source['chain'],[0,0,0],actor['rotation'],0,request['window_s'],prepared['protected_seconds'],path,control_curve=curve)
            rig=RigAsset.load(path);reader=AnimationSampler(rig.document,rig.binary,0);world=np.array([reader.sample(t) for t in times])
            predicted,_=model.evaluate(parameters);error=float(np.abs(world-predicted).max())
            if error>2e-10:raise ValueError('Continuous replay differs from actual GLB')
            reference=model.model.source_world;position=actor['rates'].positions
            positional=rate_check(position(reference),position(world),times,prepared['authored']['knots_s'])
            angular=angular_replay(reference[:,rig.joints,:3,:3],world[:,rig.joints,:3,:3],times,prepared['authored']['knots_s'])
            if positional['failures'] or any(v['exceeding_observations'] for v in angular.values()):raise ValueError('Independent export motion check failed')
            before=rotation_channels(source['rig'].document,source['rig'].binary);after=rotation_channels(rig.document,rig.binary)
            for node,(_,clock,q) in before.items():
                np.testing.assert_array_equal(after[node][1],clock)
                frozen=np.setdiff1d(np.arange(len(clock)),details['nodes'].get(str(node),[]))
                np.testing.assert_array_equal(after[node][2][frozen],q[frozen])
            outside=(times<=guide.times[0])|(times>=guide.times[-1]);np.testing.assert_array_equal(world[outside],reference[outside])
            decoded.append(dict(actor=actor['name'],path=path.name,sha256=sha256(path),maximum_batch_replay_error=error,
                positional=positional,angular=angular,frozen_keys_exact=True,outside_world_exact=True))
            shutil.copyfile(source['path'],output/f'source-{index}.glb')
            for kind in ['source','candidate']:
                clip=output/f'{kind}-{index}.glb';cases.append(dict(id=kind+'-'+actor['name'],path=clip.name,sha256=sha256(clip),frames=int(round(reader.duration*30))+1,fps=30,sample_by_time=True))
            peak_world.append(world[protocol['sample']])
        save(output/'decoded.json',decoded);save(output/'manifest.json',dict(cases=cases,quality_approved=False))
        engine_run(output,output/'engine');engine=sha256(output/'engine/verification.json')
        points=[s['rig'].vertices(w)@a['rotation'].T+a['translation'] for s,w,a in zip(sources,peak_world,actors)]
        directions=[penetration(points[s],points[t],actors[t]['faces']) for s,t in [(0,1),(1,0)]]
        geometry=dict(sample=protocol['sample'],time_s=float(times[protocol['sample']]),directions=directions,
            maximum_depth_m=max(d['max_depth_m'] for d in directions),floor_depth_m=[max(0.,-float(p[:,1].min())) for p in points],
            scope='Only the original peak time; no full-clock clearance claim.',quality_approved=False)
        save(output/'peak-geometry.json',geometry)
    for path,digest in files.items():
        if sha256(path)!=digest:raise ValueError('Projection input changed')
    for name,digest in methods.items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Projection method changed')
    save(output/'result.json',dict(at=now(),status='complete',nonzero_controls=changed,selected_objective=best['objective'],
        request_sha256=sha256(output/'request.json'),selected_sha256=sha256(output/'selected.json'),solver_sha256=sha256(output/'solver.json'),
        evaluations_sha256=sha256(output/'evaluations.json'),decoded_sha256=sha256(output/'decoded.json') if changed else None,
        peak_geometry_sha256=sha256(output/'peak-geometry.json') if geometry else None,engine_sha256=engine,
        full_mesh_clock_checked=False,accepted_for_publication=False,quality_approved=False))
    print(read(output/'result.json'),flush=True)


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('plan',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--method',choices=['COBYLA','SLSQP'],default='COBYLA')
    parser.add_argument('--start',choices=['source','target'],default='source');args=parser.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(args.plan,args.output,args.method,args.start)
