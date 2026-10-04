"""Fit declared rigid-object holds to multiple supplied skin correspondences.

Characters and contact intent remain unchanged. Proper least-squares rigid
alignment is a proposal, not a minimax bound, grasp, physics or quality approval.
The existing two-point/reference-twist operation remains a separate protocol.
"""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from engine_contact_sampling import frame_populations,contract_sha256
from native_scene_contacts import SceneContacts,fields,scalar,vector
from native_scene_geometry import evaluate_to_archive as geometry_archive,policy_for,METHODS as GEOMETRY_METHODS
from native_object_hold_fit import audit_bounds
from strep import ROOT,read,save,sha256,now

SCHEMA='strep-native-object-correspondence-fit-v1'
METHODS=tuple(dict.fromkeys(GEOMETRY_METHODS+('native_object_correspondence_fit.py','native_object_hold_fit.py','two_hand_rigidity.py')))


def fit_points(local,observed):
    local=np.asarray(local,float);observed=np.asarray(observed,float)
    if local.ndim!=2 or local.shape[1:]!=(3,) or not 3<=len(local)<=256 or observed.shape!=local.shape:
        raise ValueError('Three to 256 matched XYZ correspondences required')
    if not np.isfinite(local).all() or not np.isfinite(observed).all():raise ValueError('Finite rigid correspondences required')
    a=local-local.mean(0);b=observed-observed.mean(0)
    for points in [a,b]:
        singular=np.linalg.svd(points,compute_uv=False)
        if singular[1]<=max(1e-10,singular[0]*1e-8):raise ValueError('Noncollinear correspondences required; object twist is not observable')
    u,s,v=np.linalg.svd(a.T@b)
    if s[1]<=max(1e-20,s[0]*1e-8):raise ValueError('Rigid correspondence covariance is degenerate')
    # Disallow reflection even when the correspondences cannot be rigidly fit.
    sign=np.eye(3);sign[2,2]=1. if np.linalg.det(v.T@u.T)>0 else -1.
    rotation=v.T@sign@u.T;position=observed.mean(0)-rotation@local.mean(0)
    errors=np.linalg.norm(local@rotation.T+position-observed,axis=1)
    return position,rotation,errors


def request_for(scene,value,digest):
    fields(value,('schema','contacts_sha256','object','contact_ids','edit_window_s',
        'maximum_translation_m','maximum_rotation_degrees','maximum_keys','maximum_correspondences'),'multi-point object fit')
    if value['schema']!=SCHEMA or value['contacts_sha256']!=digest:raise ValueError('Multi-point fit must bind exact source contact JSON')
    name=value['object']
    if not isinstance(name,str) or name not in scene.objects:raise ValueError('Existing declared object required')
    ids=value['contact_ids']
    if not isinstance(ids,list) or not 1<=len(ids)<=64 or any(not isinstance(i,str) for i in ids) or len(set(ids))!=len(ids):
        raise ValueError('One to 64 distinct explicit contact IDs required')
    lookup={r['authored']['id']:r for r in scene.rows}
    if any(i not in lookup for i in ids):raise ValueError('Unknown object contact ID')
    selected=[lookup[i] for i in ids];grips=[];layout=[]
    hold=selected[0]['authored']['interval_s']
    for entry in selected:
        row=entry['authored'];target=row['target'];count=1 if row['reduction']=='centroid' else len(entry['ids'])
        if row['mode']!='hold' or target['space']!='object' or target['object']!=name or row['interval_s']!=hold or len(entry['target_ids'])!=count:
            raise ValueError('Selected holds need matched correspondences on one object over the same complete interval')
        grips.extend(entry['target_ids']);layout.extend(dict(contact_id=row['id'],correspondence_index=i) for i in range(count))
    budget=value['maximum_correspondences']
    if type(budget) is not int or not 3<=budget<=256 or not 3<=len(grips)<=budget:
        raise ValueError('Complete correspondence population exceeds its explicit 3-256 budget; no subset returned')
    grips=np.asarray(grips)
    if len(np.unique(grips,axis=0))!=len(grips):raise ValueError('Distinct object-local correspondences required')
    fit_points(grips,grips) # Validate observable local geometry before querying actors.
    window=vector(value['edit_window_s'],2,'object edit window')
    if not 0<=window[0]<hold[0]<hold[1]<window[1]<=scene.duration:raise ValueError('Edit window needs positive ingress and egress around the complete hold')
    scalar(value['maximum_translation_m'],1e-6,.1,'object translation budget')
    scalar(value['maximum_rotation_degrees'],1e-6,45,'object rotation budget')
    if type(value['maximum_keys']) is not int or not 2<=value['maximum_keys']<=3601:raise ValueError('Explicit object-key budget from 2 to 3601 required')
    return selected,np.asarray(hold,float),window,grips,layout


def proposal(scene,value,digest):
    selected,hold,window,grips,layout=request_for(scene,value,digest)
    native=np.unique(np.concatenate([c[2] for a in scene.actors.values() for c in a['sampler'].channels]+[o['times'] for o in scene.objects.values()]))
    native=native[(native>=hold[0])&(native<=hold[1])]
    hold_times=np.unique(np.concatenate([hold,native]+[p['times_s'] for p in frame_populations(hold)]))
    clock=np.arange(int(np.ceil(window[0]*120)),int(np.floor(window[1]*120))+1)/120
    times=np.unique(np.r_[scene.objects[value['object']]['times'],0.,scene.duration,window,hold_times,clock])
    if len(times)>value['maximum_keys']:raise ValueError('Complete object clock exceeds explicit resource budget; no subset returned')
    observed=[]
    for entry in selected:
        row=entry['authored'];points=scene.actor_points(row['actor'],entry['ids'],hold_times)
        observed.append(points.mean(axis=1,keepdims=True) if row['reduction']=='centroid' else points)
    observed=np.concatenate(observed,axis=1);fitted=[]
    for i,points in enumerate(observed):
        try:fitted.append(fit_points(grips,points))
        except ValueError as exc:raise ValueError('Unobservable object fit at time '+repr(float(hold_times[i]))+': '+str(exc)) from exc
    fitted_p=np.array([f[0] for f in fitted]);fitted_r=np.array([f[1] for f in fitted]);errors=np.array([f[2] for f in fitted])
    name=value['object'];reference_p,reference_r=scene.object_poses(name,hold_times)
    source_p,source_r=scene.object_poses(name,times);positions=source_p.copy();rotations=source_r.copy()
    inside=(times>=hold[0])&(times<=hold[1]);ids=np.searchsorted(hold_times,times[inside])
    if not np.array_equal(hold_times[ids],times[inside]):raise ValueError('Complete fit clock required')
    positions[inside]=fitted_p[ids];rotations[inside]=fitted_r[ids]
    for begin,end,endpoint,reverse in [(window[0],hold[0],0,False),(hold[1],window[1],-1,True)]:
        mask=(times>begin)&(times<end);u=(times[mask]-begin)/(end-begin)
        w=u*u*u*(10+u*(-15+6*u));w=1-w if reverse else w
        correction=fitted_r[endpoint]@reference_r[endpoint].T
        positions[mask]+=w[:,None]*(fitted_p[endpoint]-reference_p[endpoint])
        rotations[mask]=Rotation.from_rotvec(w[:,None]*Rotation.from_matrix(correction).as_rotvec()).as_matrix()@source_r[mask]
    keys=[dict(time_s=float(t),translation_m=p.tolist(),rotation_xyzw=q.tolist()) for t,p,q in zip(times,positions,Rotation.from_matrix(rotations).as_quat())]
    return keys,dict(times_s=times,hold_times_s=hold_times,source_positions=source_p,source_rotations=source_r,
        proposed_positions=positions,proposed_rotations=rotations,observed_world_points=observed,object_local_points=grips,
        least_squares_point_errors_m=errors,least_squares_rms_point_error_m=np.sqrt(np.mean(errors**2,axis=1))),layout


def saved_keys(keys,authored,value):
    keys=copy.deepcopy(keys);original={float(k['time_s']):k for k in authored['objects'][value['object']]['keyframes']}
    left,right=value['edit_window_s']
    for i,key in enumerate(keys):
        if (key['time_s']<=left or key['time_s']>=right) and key['time_s'] in original:keys[i]=copy.deepcopy(original[key['time_s']])
    return keys


def run(contacts_path,request_path,policy_path,output):
    contacts_path,request_path,policy_path,output=[Path(p).resolve() for p in (contacts_path,request_path,policy_path,output)]
    if output.exists():raise ValueError('Fresh multi-point object fit output required')
    with worker_lock(),threadpool_limits(limits=1):
        inputs={str(p):sha256(p) for p in (contacts_path,request_path,policy_path)}
        authored=read(contacts_path);scene=SceneContacts(authored,contacts_path.parent);value=read(request_path);policy=read(policy_path)
        request_for(scene,value,inputs[str(contacts_path)]);policy_for(policy,scene,inputs[str(contacts_path)])
        methods={n:sha256(ROOT/'scripts'/n) for n in METHODS};output.mkdir(parents=True);archive=output/'implementation';archive.mkdir()
        for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
        for path,name in [(contacts_path,'source-contacts.json'),(request_path,'fit-request.json'),(policy_path,'source-policy.json')]:shutil.copyfile(path,output/name)
        snapshots={};derived=copy.deepcopy(authored)
        for i,(name,a) in enumerate(scene.actors.items()):
            src=(contacts_path.parent/authored['actors'][name]['glb']).resolve();dest=output/'input'/f'actor-{i}.glb'
            dest.parent.mkdir(exist_ok=True);shutil.copyfile(src,dest)
            if sha256(dest)!=authored['actors'][name]['sha256']:raise ValueError('Actor snapshot changed')
            snapshots[name]=dict(path=dest.relative_to(output).as_posix(),sha256=sha256(dest));derived['actors'][name]['glb']=str(dest)
        save(output/'pipeline.json',dict(status='processing',original_selected=True))
        try:
            keys,arrays,layout=proposal(scene,value,inputs[str(contacts_path)])
            derived['objects'][value['object']]['keyframes']=saved_keys(keys,authored,value)
            save(output/'proposal-contacts.json',derived);digest=sha256(output/'proposal-contacts.json');candidate=SceneContacts(derived,output)
            derived_policy=copy.deepcopy(policy);derived_policy['contacts_sha256']=digest
            derived_policy['clock']=dict(mode=policy['clock']['mode'],times_s=np.unique(np.r_[policy['clock']['times_s'],arrays['times_s']]).tolist())
            clocks,_,_=policy_for(derived_policy,candidate,digest);bounds=audit_bounds(scene,candidate,value,clocks)
            contacts,observations=candidate.evaluate();save(output/'contact-audit.json',contacts)
            geometry,transport=geometry_archive(candidate,derived_policy,digest,output/'geometry-observations.npz',
                lambda p:save(output/'pipeline.json',dict(**p,original_selected=True)))
            geometry.update(**transport);save(output/'geometry-policy.json',derived_policy);save(output/'geometry-audit.json',geometry)
            np.savez_compressed(output/'proposal-observations.npz',**arrays);np.savez_compressed(output/'contact-observations.npz',**observations)
            scene.check_inputs();candidate.check_inputs()
            if any(sha256(Path(p))!=h for p,h in inputs.items()):raise ValueError('Object fit input changed')
            if any(sha256(ROOT/'scripts'/n)!=h or sha256(archive/n)!=h for n,h in methods.items()):raise ValueError('Object fit implementation changed')
            for path,name in [(contacts_path,'source-contacts.json'),(request_path,'fit-request.json'),(policy_path,'source-policy.json')]:
                if sha256(path)!=sha256(output/name):raise ValueError('Authored snapshot changed')
            result=dict(schema=SCHEMA,at=now(),status='complete',object=value['object'],contact_ids=value['contact_ids'],
                correspondence_layout=layout,correspondences=len(layout),keys=len(keys),bounds=bounds,
                all_contact_conditions_pass=contacts['passed'],sampled_geometry_conditions_pass=geometry['sampled_conditions_pass'],
                sampled_constraints_pass=bool(bounds['passed'] and contacts['passed'] and geometry['sampled_conditions_pass']),
                actor_bytes_unchanged=True,actor_snapshots=snapshots,input_sha256=inputs,actor_inputs_sha256=scene.inputs,
                implementation_sha256=methods,frame_contract_sha256=contract_sha256(),proposal_contacts_sha256=digest,
                geometry_samples=len(clocks),original_selected=True,quality_approved=False,release_approved=False,training_admitted=False,
                scope='Equal-per-correspondence proper least-squares rigid object fit. Every selected correspondence affects rotation; no two-point twist fallback. All saved contacts, original-relative pose bounds and complete sampled geometry remain acceptance conditions. No minimax/lower-bound claim, character edits, anatomy, forces, continuous collision, engine or human-quality approval.')
            result['files_sha256']={n:sha256(output/n) for n in ['source-contacts.json','fit-request.json','source-policy.json','proposal-contacts.json','geometry-policy.json','contact-audit.json','geometry-audit.json','proposal-observations.npz','contact-observations.npz','geometry-observations.npz']}
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',original_selected=True));return result
        except Exception as exc:save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('contacts','request','policy','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();result=run(args.contacts,args.request,args.policy,args.output)
    print(dict(correspondences=result['correspondences'],keys=result['keys'],sampled_constraints_pass=result['sampled_constraints_pass'],quality_approved=False),flush=True)
