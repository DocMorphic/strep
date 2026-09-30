"""Search time-indexed two-bone approach guides against partner forearm geometry."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now


def run(previous,output,native_clock=False):
    from diagnose_scene_pair_limits import load_bound_study
    from bound_evidence import bind_inputs
    from scene_pair_problem import load_actors
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from paired_approach_basis import BoundSkin
    from two_bone_waypoint import reach
    from elbow_swivel import capsule_radius,segment_distance,local_transforms
    from waypoint_lattice import shortest_path,LinearGuide
    from native_waypoint_clock import guide_clock
    from paired_temporal_neighbor import rotation_channels
    previous,output=Path(previous).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh waypoint path study required')
    result=read(previous/'result.json');request=read(previous/'request.json')
    if result['status']!='complete':raise ValueError('Completed preceding temporal audit required')
    files={str(previous/'result.json'):sha256(previous/'result.json')}
    for name,key in [('request.json','request_sha256'),('geometry.json','geometry_sha256'),('decoded.json','decoded_sha256')]:
        if sha256(previous/name)!=result[key]:raise ValueError('Preceding motion evidence changed')
        files[str(previous/name)]=result[key]
    for name,digest in request['implementation'].items():
        path=(previous/'implementation'/name).resolve()
        if path.parent!=previous/'implementation' or sha256(path)!=digest:raise ValueError('Preceding method snapshot changed')
        files[str(path)]=digest
    for path,digest in request['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Preceding motion input changed')
        files[path]=digest
    plan=Path(request['plan']).resolve();protocol=read(plan/'request.json');study=Path(protocol['study']).resolve()
    if files.get(str(plan/'request.json'))!=sha256(plan/'request.json'):raise ValueError('Bound source waypoint plan required')
    original,_,required=load_bound_study(study);files.update(bind_inputs(required,request['inputs']))
    baseline=read(study/'result.json');trials=read(study/'trials.json')
    if files.get(str(study/'trials.json'))!=baseline['trials_sha256']:raise ValueError('Bound selected source trials required')
    rows=[r for r in trials if r['folder']==baseline['selected']]
    if len(rows)!=1 or not rows[0]['accepted_local_step'] or rows[0]['reasons']:raise ValueError('Accepted starting correction required')
    selected=rows[0];folder=(study/selected['folder']).resolve()
    if not folder.is_relative_to(study):raise ValueError('Source folder escapes study')
    prepared,actors=load_actors(Path(original['prepared_request']).parent)
    window=np.asarray(request['window_s'],float)
    if window.shape!=(3,) or not window[0]<window[1]<window[2]:raise ValueError('Valid prior approach window required')
    measured=read(previous/'geometry.json')
    returning=max((r for r in measured if window[0]<r['time_s']<window[2]),key=lambda r:r['candidate_depth_m'])
    times=np.unique(np.r_[np.linspace(window[0],window[2],9),window[1],returning['time_s']])
    # This second measured time is retained even if it already lies on the grid.
    amounts=[0.,.02,.04,.06];angles=[-30.,-15.,0.,15.,30.]
    states=np.array([[amount,a,b] for amount in amounts for a in angles for b in angles])
    axes=[(name+sign,axis*value) for name,axis in zip('XYZ',np.eye(3)) for sign,value in [('minus',-1),('plus',1)]]
    limits=np.array([.8,300.,300.]);sources=[];clocks=[]
    for actor,entry in zip(actors,selected['actors']):
        path=(folder/entry['path']).resolve()
        if path.parent!=folder or sha256(path)!=entry['sha256']:raise ValueError('Source clip changed')
        files[str(path)]=entry['sha256'];rig=RigAsset.load(path);skin=BoundSkin(rig)
        chain=protocol['chains'][actor['name']];forearm=np.flatnonzero(np.any((skin.nodes==chain[1])&(skin.weights>0),axis=1))
        channels=rotation_channels(rig.document,rig.binary)
        clocks.extend(channels[node][1] for node in chain)
        sources.append(dict(rig=rig,skin=skin,chain=chain,forearm=forearm,sampler=AnimationSampler(rig.document,rig.binary,0)))
    if native_clock:times=guide_clock(clocks,window,prepared['protected_seconds'])
    costs=np.full((len(axes),len(times),len(states)),np.inf)
    gaps=np.full_like(costs,np.nan);valid_counts=[]
    output.mkdir();(output/'implementation').mkdir();methods={}
    for name in ['plan_pair_waypoint_path.py','waypoint_lattice.py','two_bone_waypoint.py','elbow_swivel.py','strep.py',
            'diagnose_scene_pair_limits.py','bound_evidence.py','scene_pair_problem.py','rig_asset.py','rig_clip_import.py',
            'paired_approach_basis.py','paired_guarded_temporal.py','gltf_tools.py',
            'native_waypoint_clock.py','timed_rotation_edit.py','paired_temporal_neighbor.py']:
        shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name);methods[name]=sha256(output/'implementation'/name)
    save(output/'request.json',dict(at=now(),previous=str(previous),source_plan=str(plan),source_study=str(study),
        inputs=files,implementation=methods,window_s=window.tolist(),times_s=times.tolist(),
        clock_mode='native_shared' if native_clock else 'uniform_with_failure_times',
        states=states.tolist(),axes={name:axis.tolist() for name,axis in axes},guide_rate_limits=limits.tolist(),
        rates_units=['m/s','degrees/s','degrees/s'],native_pose_budget_degrees=45.,transition_weight=.1,
        scope='Finite time-indexed guide search. Per-node forearm capsules rank geometry; they do not certify full-mesh or between-node clearance. Piecewise-linear parameter rates are bounded, not actual character rates or acceleration. First collision cluster only; protected poses and later failures remain in subsequent baking.',quality_approved=False))
    for ti,stamp in enumerate(times):
        caches=[]
        for actor_index,(actor,source) in enumerate(zip(actors,sources)):
            world=source['sampler'].sample(float(stamp));before=local_transforms(world,source['rig'].parents)
            cache={};upper,elbow,wrist=source['chain']
            for axis_index,(_,axis) in enumerate(axes):
                for amount in amounts:
                    for angle in angles:
                        key=(axis_index,amount,angle);delta=axis*amount*(1 if actor_index==0 else -1)
                        try:
                            moved,local=reach(world,source['rig'].parents,*source['chain'],world[wrist,:3,3]+delta@actor['rotation'],np.deg2rad(angle))
                        except ValueError as error:
                            if 'outside two-bone reach' not in str(error):raise
                            cache[key]=None;continue
                        edit=Rotation.from_matrix(before[:,:3,:3]).inv()*Rotation.from_matrix(local[:,:3,:3])
                        if np.rad2deg(edit.magnitude()).max()>45.+1e-4:cache[key]=None;continue
                        points=source['skin'].evaluate(moved[None],np.zeros(len(source['forearm']),int),source['forearm'])@actor['rotation'].T+actor['translation']
                        ends=moved[[elbow,wrist],:3,3]@actor['rotation'].T+actor['translation']
                        cache[key]=(ends,capsule_radius(points,*ends))
            caches.append(cache)
        count=0
        for ai in range(len(axes)):
            for si,(amount,aa,ab) in enumerate(states):
                a=caches[0][ai,amount,aa];b=caches[1][ai,amount,ab]
                if a is None or b is None:continue
                clearance=segment_distance(*a[0],*b[0])-a[1]-b[1];gaps[ai,ti,si]=clearance
                costs[ai,ti,si]=(max(0.,-clearance)/.05)**2+.01*((amount/.06)**2+(aa/30)**2+(ab/30)**2)
                count+=1
        valid_counts.append(count);save(output/'progress.json',dict(completed=ti+1,total=len(times),valid_states=count))
        print(dict(phase='nodes',completed=ti+1,total=len(times),valid_states=count),flush=True)
    np.savez_compressed(output/'lattice.npz',costs=costs,proxy_gaps=gaps,states=states,times=times)
    routes=[]
    for ai,(name,axis) in enumerate(axes):
        parameters,report=shortest_path(times,states,costs[ai],limits,.1)
        if parameters is not None:LinearGuide(times,parameters,limits)
        routes.append(dict(axis_name=name,axis=axis.tolist(),solver=report,
            parameters=None if parameters is None else parameters.tolist(),quality_approved=False))
    passing=[r for r in routes if r['parameters'] is not None]
    selected_route=min(passing,key=lambda r:(r['solver']['total_cost'],r['axis_name'])) if passing else None
    save(output/'routes.json',routes)
    for path,digest in files.items():
        if sha256(path)!=digest:raise ValueError('Path input changed')
    for name,digest in methods.items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Path method changed')
    save(output/'result.json',dict(at=now(),status='complete',selected=None if selected_route is None else selected_route['axis_name'],
        request_sha256=sha256(output/'request.json'),lattice_sha256=sha256(output/'lattice.npz'),routes_sha256=sha256(output/'routes.json'),
        full_mesh_checked=False,accepted_for_publication=False,quality_approved=False))
    print(read(output/'result.json'),flush=True)


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('previous',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--native-clock',action='store_true');a=p.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(a.previous,a.output,a.native_clock)
