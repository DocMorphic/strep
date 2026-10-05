"""Bounded whole-clip reference calibration for explicit transferred contacts.

Separate target profiles/candidates; authored scene targets and old clips remain.
This can change boundary poses. Transition and human approval remain separate.
"""
import argparse
import copy
from pathlib import Path
import shutil
import time

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits

import native_transfer_scene as scene_bridge
import native_rig_transfer as transfer
from native_scene_contacts import SceneContacts,fields,scalar
from native_contact_pose import rotation_ball
from contact_pose_reachability import point_bound
from contact_pose_sphere_bound import sphere_bound
from retarget_rig import calibration
from gltf_tools import local_matrix
from sampled_motion_caps import features,measures,SampledMotionCaps
from strep import read,save,sha256,now
from action_worker_lock import worker_lock
from engine_contact_sampling import frame_populations

SCHEMA='strep-native-transfer-calibration-v1'
SCRIPT_ROOT=Path(__file__).resolve().parent
POSE_TRANSFORM_LIMIT=1000000
# Search slightly inside contact limits to survive serialized FP32 readback.
# Acceptance always replays the original authored limits without this reserve.
SEARCH_CONTACT_FRACTION=.999
METHODS=tuple(dict.fromkeys(scene_bridge.METHODS+('native_transfer_calibration.py','native_contact_pose.py',
    'contact_pose_reachability.py','contact_pose_sphere_bound.py','sampled_motion_caps.py')))


def require(value,message):
    if not value:raise ValueError(message)


class CalibrationProblem:
    def __init__(self,folder,permissions):
        fields(permissions,('schema','comparison','actors','search'),'calibration recipe')
        require(permissions['schema']==SCHEMA,'Explicit native transfer calibration schema required')
        fields(permissions['comparison'],('path','sha256'),'comparison binding')
        self.folder=Path(folder).resolve();self.comparison=scene_bridge.verify(folder,permissions['comparison']['sha256'])
        self.spec=read(self.folder/'contacts.json');self.scene=SceneContacts(self.spec,self.folder)
        rows=permissions['actors'];require(isinstance(rows,dict) and rows and set(rows)<=set(self.comparison['transfer_actors']),
            'Choose transferred actors with explicit calibration permissions')
        fields(permissions['search'],('evaluations','calls','seconds','starts'),'search budget')
        for name,maximum in [('evaluations',300),('calls',10000)]:
            require(type(permissions['search'][name]) is int and 1<=permissions['search'][name]<=maximum,'Bounded integer search budget required')
        scalar(permissions['search']['seconds'],1,3600,'search seconds')
        require(type(permissions['search']['starts']) is int and 1<=permissions['search']['starts']<=7
            and permissions['search']['evaluations']>=permissions['search']['starts'],'Choose 1-7 starts within the total evaluation budget')
        self.search=permissions['search'];self.uniform=np.arange(int(np.floor(self.scene.duration*120))+1)/120
        require(len(self.uniform)>=3,'At least three 120 Hz source-rate samples required')
        self.clocks=scene_bridge.planned_clocks(self.scene,self.scene)
        self.times=np.unique(np.concatenate(self.clocks+[self.uniform,np.array([0.,self.scene.duration])]
            +[c[2] for a in self.scene.actors.values() for c in a['sampler'].channels]))
        require(len(self.times)<=scene_bridge.POSITION_QUERY_LIMIT,'Complete calibration clock exceeds fixed budget')
        self.rate_ids=np.searchsorted(self.times,self.uniform);self.actors={};self.size=0
        bound_inputs={name:scene_bridge.transfer_audit.bound_candidate(self.folder/'input/transfers'/name) for name in rows}
        pose_count=len(self.times)*(sum(len(a['rig'].document['nodes']) for a in self.scene.actors.values())
            +sum(len(b[2].document['nodes']) for b in bound_inputs.values()))
        require(pose_count<=POSE_TRANSFORM_LIMIT,'Complete calibration pose cache exceeds fixed budget; no truncation')
        self.original={name:np.array([a['sampler'].sample(float(t)) for t in self.times]) for name,a in self.scene.actors.items()}
        for name,entry in rows.items():
            fields(entry,('role_rotations_degrees','maximum_root_offset_m','maximum_joint_displacement_m'),'actor calibration')
            radius=scalar(entry['maximum_root_offset_m'],0,.22,'root offset bound')
            displacement=scalar(entry['maximum_joint_displacement_m'],1e-6,.22,'joint displacement bound')
            roles=entry['role_rotations_degrees'];require(isinstance(roles,dict) and len(roles)<=16 and (roles or radius>0),'Choose rotation roles or a root offset')
            bound=bound_inputs[name]
            _,report,source,target,tp,prepared,keys,_,_,_=bound
            sampler,sm,tm,skeleton,offset,scale,_=prepared
            require(set(roles)<=set(tm),'Calibration roles must exist in the target profile')
            limits=[np.deg2rad(scalar(v,1e-6,45,'reference rotation bound')) for v in roles.values()]
            base,_,_=calibration(target,tm,skeleton,tp.get('axis_alignment_xyzw'))
            source_world=np.array([sampler.sample(float(t)) for t in self.times])
            deltas={n:source_world[:,sm[role],:3,:3]@source.reference[sm[role],:3,:3].T for role,n in tm.items()}
            local=np.array([local_matrix(n) for n in target.document['nodes']])
            require(np.allclose(local[:,:3,:3]@local[:,:3,:3].transpose(0,2,1),np.eye(3),atol=1e-8,rtol=0),
                'Rigid unit-scale target reference required')
            order=[]
            def visit(n):
                if n in order:return
                if target.parents[n]>=0:visit(target.parents[n])
                order.append(n)
            for n in range(len(local)):visit(n)
            first=self.size;self.size+=3*(len(roles)+(radius>0))
            cap=SampledMotionCaps(features(self.original[name][self.rate_ids],target.joints),self.uniform,
                np.linspace(0,self.uniform[-1],5),tolerance=1e-5)
            self.actors[name]=dict(target=target,profile=tp,roles=list(roles),limits=limits,root_radius=radius,displacement=displacement,
                mapping=tm,base=base,deltas=deltas,local=local,order=order,root=tm['Hips'],
                root_positions=source_world[:,sm['Hips'],:3,3]*scale+offset,first=first,last=self.size,cap=cap,
                inputs=bound,keys=keys)
        require(self.size<=96,'Complete calibration exceeds the 96-control budget; no truncation')
        self.fixed_points={};self.object_poses={}
        for i,entry in enumerate(self.scene.rows):
            row=entry['authored'];clock=self.clocks[i];ids=np.searchsorted(self.times,clock)
            self.fixed_points[i]=(ids,entry)
            if row['target']['space']=='object':self.object_poses[i]=self.scene.object_poses(row['target']['object'],clock)

    def decode(self,value):
        value=np.asarray(value,float);require(value.shape==(self.size,) and np.isfinite(value).all() and np.max(abs(value),initial=0)<=20,
            'Complete finite bounded calibration coordinates required')
        result={}
        for name,a in self.actors.items():
            raw=value[a['first']:a['last']].reshape(-1,3);count=len(a['roles'])
            angles=rotation_ball(raw[:count],np.array(a['limits'])) if count else np.empty((0,3))
            root=a['root_radius']*raw[-1]/np.sqrt(1+raw[-1]@raw[-1]) if a['root_radius'] else np.zeros(3)
            result[name]=(angles,root)
        return result

    def profiles(self,value):
        result={}
        for name,(angles,root) in self.decode(value).items():
            a=self.actors[name];profile=copy.deepcopy(a['profile'])
            for role,delta in zip(a['roles'],angles):
                if not np.any(delta):continue
                node=a['mapping'][role];desired=Rotation.from_rotvec(delta).as_matrix()@a['base'][node]
                profile.setdefault('axis_alignment_xyzw',{})[role]=Rotation.from_matrix(desired@a['target'].reference[node,:3,:3].T).as_quat().tolist()
            if np.any(root):profile['world_offset_m']=(np.asarray(profile.get('world_offset_m',[0,0,0]))+root).tolist()
            result[name]=profile
        return result

    def worlds(self,value):
        worlds={n:w.copy() for n,w in self.original.items()}
        for name,(angles,offset) in self.decode(value).items():
            a=self.actors[name];base=dict(a['base'])
            for role,angle in zip(a['roles'],angles):
                node=a['mapping'][role];base[node]=Rotation.from_rotvec(angle).as_matrix()@base[node]
            output=np.empty_like(self.original[name])
            for node in a['order']:
                parent=a['target'].parents[node];local=np.repeat(a['local'][node][None],len(self.times),axis=0)
                if node in base:
                    desired=a['deltas'][node]@base[node]
                    rotation=output[:,parent,:3,:3] if parent>=0 else np.repeat(np.eye(3)[None],len(self.times),axis=0)
                    local[:,:3,:3]=Rotation.from_matrix(rotation.transpose(0,2,1)@desired).as_matrix()
                    if node==a['root']:
                        position=output[:,parent,:3,3] if parent>=0 else 0.
                        local[:,:3,3]=np.einsum('tji,tj->ti',rotation,a['root_positions']+offset-position)
                output[:,node]=output[:,parent]@local if parent>=0 else local
            worlds[name]=output
        return worlds

    def points(self,name,ids,worlds,indices,reduction):
        actor=self.scene.actors[name];skin=actor['skin'];p,r=actor['placement']
        points=np.einsum('tvkij,vkj,vk->tvi',worlds[name][indices][:,skin.nodes[ids],:3,:],skin.points[ids],skin.weights[ids])@r.T+p
        return points.mean(axis=1,keepdims=True) if reduction=='centroid' else points

    def measure(self,value,worlds=None,*,contact_fraction=1.):
        worlds=self.worlds(value) if worlds is None else worlds;residuals=[];contacts=[];bounds=[]
        for i,(indices,entry) in self.fixed_points.items():
            row=entry['authored'];target=row['target'];effector=self.points(row['actor'],entry['ids'],worlds,indices,row['reduction'])
            if target['space']=='actor':goal=self.points(target['actor'],entry['target_ids'],worlds,indices,target['reduction'])
            elif target['space']=='world':goal=np.repeat(entry['target_ids'][None],len(indices),axis=0)
            else:
                p,r=self.object_poses[i];goal=np.einsum('tij,vj->tvi',r,entry['target_ids'])+p[:,None]
            error=effector-goal;distance=np.linalg.norm(error,axis=2);residuals.extend((distance/max(row['limits']['position_m']*contact_fraction,1e-8)-1).ravel())
            speed_max=0.
            if row['mode']=='hold':
                relative=np.einsum('tvi,tij->tvj',error,self.object_poses[i][1]) if target['space']=='object' else error
                for population in frame_populations(row['interval_s']):
                    where=np.searchsorted(self.clocks[i],population['times_s'])
                    require(np.array_equal(self.clocks[i][where],population['times_s']),'Complete native frame speed population required')
                    if len(where)<2:residuals.append(100.);continue
                    speed=np.linalg.norm(np.diff(relative[where],axis=0),axis=2)*population['rate_hz']
                    residuals.extend((speed/max(row['limits']['relative_speed_m_s']*contact_fraction,1e-8)-1).ravel());speed_max=max(speed_max,float(speed.max()))
            contacts.append(dict(id=row['id'],maximum_position_error_m=float(distance.max()),maximum_relative_speed_m_s=speed_max if row['mode']=='hold' else None))
        for name,a in self.actors.items():
            ids=a['target'].joints;displacement=np.linalg.norm(worlds[name][:,ids,:3,3]-self.original[name][:,ids,:3,3],axis=2)
            residuals.extend((displacement/a['displacement']-1).ravel());failed=[]
            values=measures(features(worlds[name][self.rate_ids],ids),a['cap'].dt)
            for v,c in zip(values,a['cap'].caps):
                residuals.extend(((v-c-a['cap'].tolerance)/np.maximum(c,.001)).ravel());failed.append(int(np.count_nonzero(v>c+a['cap'].tolerance)))
            bounds.append(dict(actor=name,maximum_joint_displacement_m=float(displacement.max()),joint_displacement_limit_m=a['displacement'],source_rate_failed_rows=failed))
        return np.asarray(residuals),dict(contacts=contacts,actors=bounds)

    def preflight(self):
        rows=[]
        for i,(indices,entry) in self.fixed_points.items():
            row=entry['authored'];target=row['target'];times=self.clocks[i]
            left,right=scene_bridge.contact_points(self.scene,entry,times)
            if row['actor'] in self.actors and (target['space']!='actor' or target['actor'] not in self.actors):
                name=row['actor'];ids=entry['ids'];reduction=row['reduction'];goal=right
            elif target['space']=='actor' and row['actor'] not in self.actors and target['actor'] in self.actors:
                name=target['actor'];ids=entry['target_ids'];reduction=target['reduction'];goal=left
                left,right=right,left
            else:
                reason='Both sides editable' if row['actor'] in self.actors else 'Neither side editable'
                rows.append(dict(contact=row['id'],status='not_ruled_out',reason=reason+'; no fixed-target certificate claimed'));continue
            actor=self.scene.actors[name];skin=actor['skin'];p,r=actor['placement']
            require(np.array_equal(skin.points[ids,:,3],np.ones_like(skin.points[ids,:,3])),'Affine bind points required for reach certificate')
            distances=np.linalg.norm(left-right,axis=2);peak=np.unravel_index(distances.argmax(),distances.shape)
            stamps=np.unique([0,len(times)-1,peak[0]])
            groups=[ids] if reduction=='centroid' else [[v] for v in ids]
            for stamp in stamps:
                world=self.original[name][indices[stamp]]
                for point,vertices in enumerate(groups):
                    vertices=np.asarray(vertices,int);nodes=skin.nodes[vertices].ravel()
                    weights=skin.weights[vertices].ravel()/len(vertices)
                    inputs=dict(positions=(world[nodes,:3,3]@r.T+p).tolist(),weights=weights.tolist(),
                        local_points=skin.points[vertices,:,:3].reshape(-1,3).tolist(),target=goal[stamp,point].tolist(),
                        joint_budget=self.actors[name]['displacement'],pin_tolerance=row['limits']['position_m'])
                    component=point_bound(**inputs);sphere=sphere_bound(**inputs)
                    rows.append(dict(contact=row['id'],actor=name,time_s=float(times[stamp]),point=point,certificate_inputs=inputs,
                        conflict_verified=component['any_verified_conflict'] or sphere['conflict_verified'],component=component,sphere=sphere))
        return dict(status='incompatible_with_joint_bound' if any(r.get('conflict_verified',False) for r in rows) else 'not_ruled_out',
            rows=rows,quality_approved=False,scope='Necessary fixed-target skin reach at endpoints and peak original contact error, under the stated rotation-norm/arithmetic assumptions. No conflict is not feasibility; coupled editable targets are not certified.')


def fit(problem):
    initial=np.zeros(problem.size);started=time.monotonic();history=[];best=initial.copy();score=None
    class Exhausted(Exception):pass
    def objective(value):
        nonlocal best,score
        if history and (len(history)>=problem.search['calls'] or time.monotonic()-started>=problem.search['seconds']):raise Exhausted()
        residual,_=problem.measure(value,contact_fraction=SEARCH_CONTACT_FRACTION)
        # Only contact rows receive this search reserve. Joint and source-rate
        # acceptance bounds remain fixed, and exported candidates are remeasured.
        positive=np.maximum(residual,0);current=(float(positive.max(initial=0)),float(positive@positive))
        if score is None or current<score:best=value.copy();score=current
        history.append(dict(call=len(history)+1,maximum_violation=current[0],squared_violation=current[1]))
        return np.r_[positive,1e-5*value]
    seeds=[initial]
    for axis in range(3):
        for sign in (1.,-1.):
            seed=initial.copy()
            for a in problem.actors.values():
                for i in range(len(a['roles'])):seed[a['first']+3*i+axis]=sign*.4*(-1)**i
            seeds.append(seed)
    starts=[];exhausted=False;message='All bounded starts completed'
    allocations=[problem.search['evaluations']//problem.search['starts']+(i<problem.search['evaluations']%problem.search['starts']) for i in range(problem.search['starts'])]
    for index,(seed,budget) in enumerate(zip(seeds,allocations)):
        try:
            solved=least_squares(objective,seed,bounds=(-20,20),max_nfev=budget,ftol=1e-10,xtol=1e-10,gtol=1e-10)
            starts.append(dict(start=index,initial_controls=seed.tolist(),evaluation_budget=budget,evaluations=int(solved.nfev),evaluation_budget_exhausted=solved.status==0))
        except Exhausted:exhausted=True;message='Explicit shared objective-call or time budget exhausted';break
    return best,dict(history=history,objective_calls=len(history),elapsed_s=time.monotonic()-started,budget_exhausted=exhausted,
        starts=starts,solver_message=message,selected_score=list(score),controls=best.tolist(),quality_approved=False,
        search_contact_fraction=SEARCH_CONTACT_FRACTION)


def payload_hashes(output):
    return {p.relative_to(output).as_posix():sha256(p) for p in output.rglob('*')
        if p.is_file() and p!=output/'result.json' and p.name!='pipeline.json'}


def outcome(status,comparison=None,bounds=None,residual=None):
    completed=status=='complete'
    return dict(schema=SCHEMA,status=status,optimizer_started=completed,original_selected=True,
        candidate_contact_samples_pass=bool(completed and comparison['candidate_contact_samples_pass']),
        source_rates_pass=bool(completed and all(not any(a['source_rate_failed_rows']) for a in bounds['actors'])),
        joint_displacement_pass=bool(completed and all(a['maximum_joint_displacement_m']<=a['joint_displacement_limit_m'] for a in bounds['actors'])),
        sampled_calibration_conditions_pass=bool(completed and np.max(residual,initial=0)<=1e-5
            and comparison['candidate_contact_samples_pass']
            and all(a['maximum_joint_displacement_m']<=a['joint_displacement_limit_m'] for a in bounds['actors'])
            and all(not any(a['source_rate_failed_rows']) for a in bounds['actors'])),
        whole_clip_boundary_poses_may_change=completed,geometry_verified=False,surface_orientation_verified=False,
        engine_playback_verified=False,quality_approved=False,release_approved=False)


def candidate_spec(problem,output,profiles):
    spec=copy.deepcopy(problem.spec)
    for name,profile in profiles.items():
        folder=output/('transfer-'+name);bound=scene_bridge.transfer_audit.bound_candidate(folder)
        original=problem.actors[name]['inputs'];report=bound[1]
        require(read(output/(name+'-profile.json'))==profile and bound[4]==profile,'Calibration profile differs from bounded controls')
        for asset in ('source.glb','source-profile.json','target.glb'):
            require(sha256(folder/asset)==sha256(original[0]/asset),
                'Calibration transfer source/target snapshot changed')
        require(report['source_animation_index']==original[1]['source_animation_index']
            and report['sampling_rate_hz']==original[1]['sampling_rate_hz'],'Calibration source clip/rate changed')
        fidelity=transfer.verify(bound[2],bound[3],bound[5][0],bound[7],bound[8],bound[5],profile,bound[6])
        require(fidelity['passed'],'Calibrated native motion differs from its source/profile replay')
        spec['actors'][name].update(glb='transfer-'+name+'/character.glb',sha256=report['glb_sha256'],animation_index=report['output_animation_index'])
    for name in set(spec['actors'])-set(profiles):spec['actors'][name]['glb']='comparison/'+spec['actors'][name]['glb']
    return spec


def verify(output,expected_result_sha256=None):
    """Recompute scope, bounds and contacts from immutable portable inputs."""
    output=Path(output).resolve();result=read(output/'result.json')
    if expected_result_sha256 is not None:require(sha256(output/'result.json')==expected_result_sha256,'Selected calibration result changed')
    require(result.get('status') in ('complete','incompatible_with_joint_bound'),'Completed calibration receipt required')
    require(result.get('files_sha256')==payload_hashes(output),'Complete calibration payload changed')
    request=read(output/'request.json');fields(request,('schema','at','recipe_sha256','comparison_sha256','implementation_sha256'),'calibration request')
    require(request['schema']==SCHEMA and set(request['implementation_sha256'])==set(METHODS),'Complete calibration methods required')
    for name,digest in request['implementation_sha256'].items():
        require(sha256(SCRIPT_ROOT/name)==digest==sha256(output/'implementation'/name),'Calibration method binding changed')
    recipe=read(output/'recipe.json')
    require(request['recipe_sha256']==sha256(output/'recipe.json')
        and request['comparison_sha256']==recipe['comparison']['sha256'],'Calibration input binding changed')
    problem=CalibrationProblem(output/'comparison',recipe)
    preflight=problem.preflight();require(read(output/'preflight.json')==preflight,'Calibration reach certificate changed')
    if result['status']=='incompatible_with_joint_bound':
        require(preflight['status']=='incompatible_with_joint_bound'
            and not any((output/p).exists() for p in ('search.json','contacts.json','observations.npz'))
            and not list(output.glob('transfer-*')),'Incompatible calibration must not run the optimizer/export')
        expected=outcome(result['status'])
    else:
        require(preflight['status']=='not_ruled_out','Incompatible calibration was exported')
        search=read(output/'search.json');controls=np.asarray(search['controls'],float);problem.decode(controls)
        require(search.get('quality_approved') is False and search.get('search_contact_fraction')==SEARCH_CONTACT_FRACTION
            and type(search['objective_calls']) is int and search['objective_calls']==len(search['history'])
            and 1<=search['objective_calls']<=recipe['search']['calls'],'Calibration search budget/scope changed')
        scalar(search['elapsed_s'],0,1e12,'search elapsed time')
        require(type(search['budget_exhausted']) is bool and len(search['starts'])<=recipe['search']['starts']
            and sum(s['evaluations'] for s in search['starts'])<=recipe['search']['evaluations'],
            'Calibration shared evaluation budget changed')
        for i,s in enumerate(search['starts']):
            require(s['start']==i and type(s['evaluations']) is int and 0<s['evaluations']<=s['evaluation_budget']
                and type(s['evaluation_budget_exhausted']) is bool,'Invalid calibration search start')
            problem.decode(s['initial_controls'])
        for i,h in enumerate(search['history']):
            require(h['call']==i+1,'Calibration objective-call history changed')
            scalar(h['maximum_violation'],0,1e12,'maximum search violation');scalar(h['squared_violation'],0,1e24,'squared search violation')
        merit,_=problem.measure(controls,contact_fraction=SEARCH_CONTACT_FRACTION);positive=np.maximum(merit,0)
        require(np.allclose(search['selected_score'],[positive.max(initial=0),positive@positive],atol=1e-10,rtol=1e-10),
            'Selected calibration score does not replay')
        profiles=problem.profiles(controls);spec=candidate_spec(problem,output,profiles)
        require(read(output/'contacts.json')==spec,'Calibration contact intent/placement/timing/limits changed')
        candidate=SceneContacts(spec,output)
        comparison,arrays,_,frame_audit=scene_bridge.evaluate(problem.scene,candidate)
        require(read(output/'contact-comparison.json')==comparison,'Calibration contact comparison changed')
        stored=read(output/'frame-audit.json')
        canonical=lambda values:{Path(*Path(p).parts[-2:]).as_posix():h for p,h in values.items()}
        require({k:v for k,v in stored.items() if k!='inputs_sha256'}=={k:v for k,v in frame_audit.items() if k!='inputs_sha256'}
            and len(stored['inputs_sha256'])==len(frame_audit['inputs_sha256'])
            and canonical(stored['inputs_sha256'])==canonical(frame_audit['inputs_sha256']),'Calibration frame audit binding changed')
        with np.load(output/'observations.npz',allow_pickle=False) as saved:
            require(set(saved.files)==set(arrays) and all(saved[k].dtype==v.dtype and saved[k].shape==v.shape
                and saved[k].tobytes()==v.tobytes() for k,v in arrays.items()),'Complete calibration observations changed')
        worlds={n:np.array([a['sampler'].sample(float(t)) for t in problem.times]) for n,a in candidate.actors.items()}
        residual,bounds=problem.measure(controls,worlds=worlds)
        require(read(output/'decoded-bounds.json')==bounds,'Exported calibration bounds changed')
        expected=outcome(result['status'],comparison,bounds,residual)
    require(set(result)==set(expected)|{'files_sha256'} and all(type(result[k]) is type(v) and result[k]==v for k,v in expected.items()),
        'Typed calibration measurements/scope disagree with replay')
    return result


def run(recipe_path,output):
    recipe_path=Path(recipe_path).resolve();output=Path(output).resolve();require(not output.exists(),'Fresh calibration output required')
    recipe=read(recipe_path);fields(recipe,('schema','comparison','actors','search'),'calibration recipe')
    fields(recipe['comparison'],('path','sha256'),'comparison binding')
    require(isinstance(recipe['comparison']['path'],str) and bool(recipe['comparison']['path']),'Explicit comparison path required')
    folder=(recipe_path.parent/recipe['comparison']['path']).resolve()
    problem=CalibrationProblem(folder,recipe);require(not output.is_relative_to(folder),'Output cannot be inside the comparison')
    with worker_lock(),threadpool_limits(limits=1):
        output.mkdir(parents=True);save(output/'pipeline.json',dict(status='processing',original_selected=True,quality_approved=False))
        methods={n:sha256(SCRIPT_ROOT/n) for n in METHODS};archive=output/'implementation';archive.mkdir()
        for n in METHODS:shutil.copyfile(SCRIPT_ROOT/n,archive/n)
        shutil.copyfile(recipe_path,output/'recipe.json');shutil.copytree(folder,output/'comparison')
        save(output/'request.json',dict(schema=SCHEMA,at=now(),recipe_sha256=sha256(recipe_path),comparison_sha256=sha256(folder/'result.json'),implementation_sha256=methods))
        try:
            # Work from the checked portable copy so a concurrent source edit
            # cannot create an internally mixed input snapshot.
            problem=CalibrationProblem(output/'comparison',read(output/'recipe.json'))
            preflight=problem.preflight();save(output/'preflight.json',preflight)
            if preflight['status']!='not_ruled_out':
                result=outcome('incompatible_with_joint_bound');result['files_sha256']=payload_hashes(output)
                save(output/'result.json',result);verify(output,sha256(output/'result.json'))
                save(output/'pipeline.json',dict(status='complete',original_selected=True,quality_approved=False));return result
            controls,search=fit(problem);save(output/'search.json',search);profiles=problem.profiles(controls)
            spec=copy.deepcopy(problem.spec)
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise
    # Each transfer export owns its own worker lock. Never nest OS locks.
    try:
        for name,profile in profiles.items():
            bound=problem.actors[name]['inputs'];input_folder=bound[0];path=output/(name+'-profile.json');save(path,profile)
            report=transfer.export(input_folder/'source.glb',input_folder/'source-profile.json',input_folder/'target.glb',path,
                bound[1]['source_animation_index'],output/('transfer-'+name),bound[1]['sampling_rate_hz'])
            spec['actors'][name].update(glb='transfer-'+name+'/character.glb',sha256=report['glb_sha256'],animation_index=report['output_animation_index'])
        for name in set(spec['actors'])-set(profiles):spec['actors'][name]['glb']='comparison/'+spec['actors'][name]['glb']
        save(output/'contacts.json',spec);candidate=SceneContacts(spec,output)
        comparison,arrays,_,frame_audit=scene_bridge.evaluate(problem.scene,candidate)
        save(output/'contact-comparison.json',comparison);save(output/'frame-audit.json',frame_audit);np.savez_compressed(output/'observations.npz',**arrays)
        worlds={n:np.array([a['sampler'].sample(float(t)) for t in problem.times]) for n,a in candidate.actors.items()}
        residual,bounds=problem.measure(controls,worlds=worlds);save(output/'decoded-bounds.json',bounds)
        require(all(sha256(SCRIPT_ROOT/n)==h==sha256(archive/n) for n,h in methods.items()),'Calibration method changed during run')
        require(sha256(recipe_path)==sha256(output/'recipe.json') and sha256(folder/'result.json')==recipe['comparison']['sha256'],'Calibration inputs changed')
        scene_bridge.verify(folder,recipe['comparison']['sha256'])
        result=outcome('complete',comparison,bounds,residual);result['files_sha256']=payload_hashes(output)
        save(output/'result.json',result);verify(output,sha256(output/'result.json'))
        save(output/'pipeline.json',dict(status='complete',original_selected=True,quality_approved=False));return result
    except Exception as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('recipe',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();print(run(args.recipe,args.output))
