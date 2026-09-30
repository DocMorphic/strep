"""Isolate bounded finger shape and rigid hand placement for a native region.

All positive skin influences must lie in the hand subtree. Body reach, floor,
self-collision and time are relaxed; success still requires arm projection.
Failed local searches are not infeasibility certificates.
"""
import argparse
import copy
from pathlib import Path
import shutil
import time
import numpy as np
import psutil
import torch
from scipy.optimize import minimize
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from regional_pose_witness import RegionalPoseProblem
from regional_pose_full_residual import read_warm_start
from rigid_contact_placement import bounded,place,replay,placement_frame
from region_contact_objective import signed_distance
from scene_region_contact import measure_frame
from grasp_orientation import unit


def pure_hand_vertices(skin,parents,wrist):
    descendants=[]
    for joint in range(len(parents)):
        while joint>=0 and joint!=wrist:joint=parents[joint]
        descendants.append(joint==wrist)
    return np.flatnonzero(np.all(np.array(descendants)[skin['lbs_indices']] | (skin['lbs_weights']==0),axis=1))


def run(study,warm_start,output,seconds=30.,evaluations=240):
    if type(seconds) not in [int,float] or not np.isfinite(seconds) or not 0<seconds<=120:
        raise ValueError('Positive bounded time budget required')
    if type(evaluations) is not int or not 1<=evaluations<=500:raise ValueError('Bounded evaluation count required')
    torch.set_num_threads(2)
    study,warm_start,output=[Path(q).resolve() for q in (study,warm_start,output)]
    prior=read(study/'protocol.json');selected,inputs,descriptor=read_warm_start(warm_start,'best_cost',study,prior)
    p=RegionalPoseProblem(ROOT/prior['fit'],prior['frame']);seed=np.array(selected['parameters'])
    seed_audit,motion=p.independent(seed)
    if seed_audit!=selected['audit']:raise ValueError('Warm-start audit mismatch')
    archived=dict(np.load(warm_start/selected['pose'],allow_pickle=False))
    for key in motion:np.testing.assert_array_equal(motion[key],archived[key])
    scene=read(ROOT/prior['fit']/'authored-scene.json')
    output.mkdir(parents=True,exist_ok=False);snap=output/'implementation';snap.mkdir()
    for path in (ROOT/'scripts').glob('*.py'):shutil.copyfile(path,snap/path.name)
    protocol=dict(at=now(),study=study.relative_to(ROOT).as_posix(),warm_start=descriptor,inputs=inputs,
        methods={q.name:sha256(q) for q in snap.iterdir()},frame=p.frame,seed_parameters=seed.tolist(),
        starts_twist_degrees=[0,90,180,270],seconds_per_trial=seconds,maximum_evaluations=evaluations,
        maximum_rss_bytes=2*1024**3,minimum_available_bytes=int(1.25*1024**3),smooth_min_temperature_m=.00005,
        selection='Retain largest exact full-hand minimum clearance at all evaluated points, plus terminal; every region condition independently audited.',
        scope='Single-pose isolated rigid hand placement with original source-relative finger edit norms, anchor and normal limits. Original authored patches/binding unchanged. All positive skin influences must lie in hand subtree. Unrestricted wrist/body reach, no floor/body/self/partner collisions, temporal or anatomical approval. Clearance objective alone does not enforce distributed contact. No clip promotion.',
        quality_approved=False)
    save(output/'protocol.json',protocol);rows=[]
    for region in p.regions:
        contact=next(c for c in scene['contacts'] if c['id']==region['id']);hand=contact['region_contact']['hand']
        ids=pure_hand_vertices(p.skin,p.parents,p.names.index(hand));mapping={v:i for i,v in enumerate(ids)}
        if not set(region['ids']).issubset(mapping) or not set(region['faces'].ravel()).issubset(mapping):
            raise ValueError('Authored region is not wholly controlled by the hand subtree')
        slots=np.array([i for i,j in enumerate(p.editable) if p.names[j].startswith(hand) and p.names[j]!=hand])
        columns=np.array([3*i+k for i in slots for k in range(3)]);frozen=np.setdiff1d(np.arange(p.dim),columns)
        limits=p.limits[slots];scaled=seed[columns].reshape(-1,3)/limits[:,None]
        if np.any(np.sum(scaled**2,axis=1)>=1):raise ValueError('Interior source-relative finger seed required')
        initial_shape=(scaled/np.sqrt(1-np.sum(scaled**2,axis=1))[:,None]).ravel()
        hp=copy.copy(p);hp.indices=p.indices[ids];hp.bind=p.bind[ids];hp.weights=p.weights[ids]
        faces=np.array([[mapping[v] for v in tri] for tri in region['faces']]);anchor=mapping[region['anchor']]
        region_ids=np.array([mapping[v] for v in region['ids']])
        with torch.no_grad():_,_,_,v=hp.fk(p.t(seed))
        tri=v.numpy()[faces];normal=unit(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]).sum(0))
        frame=placement_frame(normal,region['normal']);tframe=[p.t(q) for q in frame]
        point_limit=region['anchor_tolerance']-1e-6;angle_limit=np.deg2rad(region['limits']['normal_degrees']-.001)
        if point_limit<=0 or angle_limit<=0:raise ValueError('Positive contact windows required')
        setup=dict(hand=hand,hand_vertices=ids.tolist(),region_vertices=region['ids'].tolist(),faces=region['faces'].tolist(),
            anchor_vertex=region['anchor'],variable_columns=columns.tolist(),variable_joints=[p.names[p.editable[i]] for i in slots],
            limits_radians=limits.tolist(),placement_frame=[q.tolist() for q in frame],point_limit_m=point_limit,angle_limit_radians=angle_limit,
            target=region['target'].tolist(),region_limits=region['limits'],anchor_tolerance_m=region['anchor_tolerance'])
        folder=output/hand;folder.mkdir();save(folder/'setup.json',setup)
        for degrees in protocol['starts_twist_degrees']:
            trial=folder/('twist-'+str(degrees));trial.mkdir();started=time.monotonic();history=[];peak=0;best=None;last=None
            def guard():
                nonlocal peak
                rss=psutil.Process().memory_info().rss;peak=max(peak,rss)
                if time.monotonic()-started>seconds or rss>protocol['maximum_rss_bytes'] or psutil.virtual_memory().available<protocol['minimum_available_bytes']:
                    raise TimeoutError('Isolated hand resource guard')
            def quantities(raw):
                theta=bounded(raw[:-6].reshape(-1,3),p.t(limits)[:,None]).reshape(-1)
                parameters=p.t(seed).index_copy(0,torch.as_tensor(columns),theta)
                _,_,_,vertices=hp.fk(parameters);tri=vertices[faces]
                normal=torch.linalg.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]).sum(0)
                normal=normal/torch.linalg.vector_norm(normal)
                positions,q,matrix=place(raw[-6:],vertices-vertices[anchor],normal,*tframe,p.t(region['target']),point_limit,angle_limit)
                gaps=signed_distance(positions,p.t(region['position']),p.t(region['rotation']),region['geometry'])
                tau=protocol['smooth_min_temperature_m'];loss=tau*torch.logsumexp(-gaps/tau,dim=0)/.01
                return loss,gaps,parameters,positions,q,matrix
            def pair(raw):
                nonlocal best,last
                guard();variable=p.t(raw).requires_grad_();loss,gaps,*_=quantities(variable)
                gradient=torch.autograd.grad(loss,variable)[0].detach().numpy();value=float(loss.detach());minimum=float(gaps.detach().min())
                if not np.isfinite(value) or not np.isfinite(gradient).all():raise ValueError('Nonfinite hand objective')
                last=raw.copy();history.append(dict(evaluation=len(history)+1,minimum_clearance_m=minimum,loss=value))
                if best is None or minimum>best[0]:best=minimum,raw.copy()
                if len(history)%50==0:save(output/'progress.json',dict(status='running',pid=psutil.Process().pid,hand=hand,twist_degrees=degrees,evaluation=len(history),best_clearance_m=best[0]))
                return value,gradient
            initial=np.r_[initial_shape,np.zeros(5),np.deg2rad(degrees)]
            value,gradient=pair(initial);direction=np.random.default_rng(191).normal(size=len(initial));direction/=np.linalg.norm(direction);h=1e-6
            with torch.no_grad():fd=float((quantities(p.t(initial+h*direction))[0]-quantities(p.t(initial-h*direction))[0])/(2*h))
            np.testing.assert_allclose(gradient@direction,fd,atol=2e-6,rtol=2e-4)
            derivative_error=abs(float(gradient@direction)-fd);status='complete'
            try:
                solved=minimize(pair,initial,jac=True,method='L-BFGS-B',options=dict(maxiter=evaluations,maxfun=evaluations,ftol=1e-12,gtol=1e-9))
                last=solved.x;solver=dict(success=bool(solved.success),message=str(solved.message),evaluations=int(solved.nfev))
            except TimeoutError as exc:status='interrupted_resource_guard';solver=dict(success=False,message=str(exc))
            variants={}
            for name,raw in [('best_clearance',best[1]),('terminal',last)]:
                with torch.no_grad():_,gaps,parameters,positions,_,_=quantities(p.t(raw))
                parameters=parameters.numpy();audit,motion=p.independent(parameters)
                np.testing.assert_array_equal(parameters[frozen],seed[frozen])
                if not audit['bounds_passed']:raise ValueError('Source-relative edit bounds failed')
                v=p.surface.vertices(motion['global_rot_mats'][0],motion['posed_joints'][0])[ids]
                tri=v[faces];normal=unit(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]).sum(0))
                placed,q,matrix=replay(raw[-6:],v-v[anchor],normal,*frame,region['target'],point_limit,angle_limit)
                exact=region['geometry'].distance_gradient(placed,region['position'],region['rotation'])[0]
                error=float(np.max(np.abs(placed-positions.numpy())));gap_error=float(np.max(np.abs(exact-gaps.numpy())))
                if max(error,gap_error)>2e-6:raise ValueError('Independent rigid hand replay failed')
                measured=measure_frame(placed,region_ids,faces,region['target'],region['normal'],region['geometry'],region['position'],region['rotation'],region['limits'])
                if measured['contact_triangle'] is not None:
                    measured['contact_triangle']['vertices']=ids[measured['contact_triangle']['vertices']].tolist()
                point_error=float(np.linalg.norm(placed[anchor]-region['target']));clearance=float(exact.min())
                local_pass=clearance>=p.config['object_clearance_m']-1e-6 and point_error<=region['anchor_tolerance'] and measured['passed']
                np.savez(trial/(name+'-unprojected.npz'),**motion)
                np.savez(trial/(name+'-placed-hand.npz'),vertices=placed,vertex_ids=ids)
                variants[name]=dict(raw=raw.tolist(),parameters=parameters.tolist(),unprojected_audit=audit,minimum_hand_clearance_m=clearance,
                    worst_vertex=int(ids[exact.argmin()]),anchor_error_m=point_error,region=measured,local_hand_passed=bool(local_pass),
                    desired_point=q.tolist(),rotation_from_unprojected=matrix.tolist(),independent_position_error_m=error,independent_gap_error_m=gap_error,
                    unprojected_pose_sha256=sha256(trial/(name+'-unprojected.npz')),placed_hand_sha256=sha256(trial/(name+'-placed-hand.npz')),quality_approved=False)
            result=dict(at=now(),status=status,solver=solver,seconds=time.monotonic()-started,peak_rss_bytes=peak,derivative_error=derivative_error,
                variants=variants,history=history,protocol_sha256=sha256(output/'protocol.json'),setup_sha256=sha256(folder/'setup.json'),quality_approved=False)
            save(trial/'result.json',result);row=dict(hand=hand,twist_degrees=degrees,status=status,seconds=result['seconds'],
                minimum_hand_clearance_m=variants['best_clearance']['minimum_hand_clearance_m'],local_hand_passed=variants['best_clearance']['local_hand_passed'],
                folder=trial.relative_to(ROOT).as_posix(),result_sha256=sha256(trial/'result.json'))
            rows.append(row);print(row,flush=True)
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Study input changed')
    for name,digest in protocol['methods'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Study method changed')
    save(output/'summary.json',dict(at=now(),status='complete',rows=rows,protocol_sha256=sha256(output/'protocol.json'),quality_approved=False))
    save(output/'progress.json',dict(status='complete',rows=rows))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study',type=Path);parser.add_argument('warm_start',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--seconds',type=float,default=30.);parser.add_argument('--evaluations',type=int,default=240)
    args=parser.parse_args()
    with threadpool_limits(limits=2):run(args.study,args.warm_start,args.output,args.seconds,args.evaluations)
