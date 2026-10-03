"""Explicit two-grip object-track proposals on supplied native rigs.

Actor bytes never change. A freely fitted object pose is only a proposal: saved
rigid interpolation, all contacts, sampled bounds and complete mesh geometry
must be checked. No inferred attachment, physics or animation-quality approval.
"""
import argparse
import copy
from pathlib import Path
import shutil
import sys
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from engine_contact_sampling import frame_populations, contract_sha256
from native_scene_contacts import SceneContacts, fields, scalar, vector
from native_scene_geometry import evaluate_to_archive as geometry_archive, policy_for, METHODS as GEOMETRY_METHODS
from two_hand_rigidity import fit_two_grips
from strep import ROOT, read, save, sha256, now

METHODS=tuple(dict.fromkeys(GEOMETRY_METHODS+('native_object_hold_fit.py','two_hand_rigidity.py')))


def request_for(scene, value, digest):
    fields(value,('schema','contacts_sha256','object','contact_ids','edit_window_s',
        'maximum_translation_m','maximum_rotation_degrees','maximum_keys'),'object hold fit')
    if value['schema']!='strep-native-object-hold-fit-v1' or value['contacts_sha256']!=digest:
        raise ValueError('Object hold fit must bind the exact source contact JSON')
    name=value['object']
    if not isinstance(name,str) or name not in scene.objects:raise ValueError('Existing declared object required')
    ids=value['contact_ids']
    if not isinstance(ids,list) or len(ids)!=2 or any(not isinstance(i,str) for i in ids) or len(set(ids))!=2:
        raise ValueError('Two distinct explicit contact IDs required')
    lookup={r['authored']['id']:r for r in scene.rows}
    if any(i not in lookup for i in ids):raise ValueError('Unknown object contact ID')
    selected=[lookup[i] for i in ids]
    for entry in selected:
        row=entry['authored'];target=row['target']
        points=1 if row['reduction']=='centroid' else len(entry['ids'])
        if (row['mode']!='hold' or target['space']!='object' or target['object']!=name
                or points!=1 or len(entry['target_ids'])!=1):
            raise ValueError('Each selected hold must supply one correspondence on the same object')
    hold=selected[0]['authored']['interval_s']
    if selected[1]['authored']['interval_s']!=hold:raise ValueError('Selected holds need the same complete interval')
    window=vector(value['edit_window_s'],2,'object edit window')
    if not 0<=window[0]<hold[0]<hold[1]<window[1]<=scene.duration:
        raise ValueError('Edit window must enclose the hold with positive ingress and egress')
    scalar(value['maximum_translation_m'],1e-6,.1,'object translation budget')
    scalar(value['maximum_rotation_degrees'],1e-6,45,'object rotation budget')
    if type(value['maximum_keys']) is not int or not 2<=value['maximum_keys']<=3601:
        raise ValueError('Explicit object-key budget from 2 to 3601 required')
    grips=np.array([e['target_ids'][0] for e in selected])
    if np.linalg.norm(grips[1]-grips[0])<1e-10:raise ValueError('Distinct object grip points required')
    return selected,np.asarray(hold,float),window,grips


def proposal(scene, value, digest):
    selected,hold,window,grips=request_for(scene,value,digest)
    populations=frame_populations(hold)
    native=np.unique(np.concatenate([c[2] for a in scene.actors.values() for c in a['sampler'].channels]
        +[o['times'] for o in scene.objects.values()]))
    native=native[(native>=hold[0])&(native<=hold[1])]
    hold_times=np.unique(np.concatenate([hold,native]+[p['times_s'] for p in populations]))
    clock=np.arange(int(np.ceil(window[0]*120)),int(np.floor(window[1]*120))+1)/120
    name=value['object'];obj=scene.objects[name]
    times=np.unique(np.r_[obj['times'],0.,scene.duration,window,hold_times,clock])
    if len(times)>value['maximum_keys']:
        raise ValueError('Complete object clock exceeds explicit resource budget; no subset returned')
    palms=[]
    for entry in selected:
        row=entry['authored'];points=scene.actor_points(row['actor'],entry['ids'],hold_times)
        palms.append(points.mean(axis=1) if row['reduction']=='centroid' else points[:,0])
    palms=np.stack(palms,axis=1);reference_p,reference_r=scene.object_poses(name,hold_times)
    fitted=[fit_two_grips(grips,points,r) for points,r in zip(palms,reference_r)]
    fitted_p=np.array([f[0] for f in fitted]);fitted_r=np.array([f[1] for f in fitted])
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
    keys=[dict(time_s=float(t),translation_m=p.tolist(),rotation_xyzw=q.tolist())
        for t,p,q in zip(times,positions,Rotation.from_matrix(rotations).as_quat())]
    return keys,dict(times_s=times,hold_times_s=hold_times,source_positions=source_p,
        source_rotations=source_r,proposed_positions=positions,proposed_rotations=rotations,
        ideal_point_bounds=np.array([f[2] for f in fitted]),palms=palms)


def audit_bounds(scene, candidate, value, times):
    name=value['object'];p,r=scene.object_poses(name,times);q,s=candidate.object_poses(name,times)
    translation=np.linalg.norm(q-p,axis=1)
    angles=np.rad2deg(Rotation.from_matrix(s@r.transpose(0,2,1)).magnitude())
    window=np.asarray(value['edit_window_s']);frozen=(times<=window[0])|(times>=window[1])
    frozen_error=float(max(np.max(abs(q[frozen]-p[frozen]),initial=0),np.max(abs(s[frozen]-r[frozen]),initial=0)))
    return dict(samples=len(times),maximum_translation_m=float(translation.max()),
        maximum_rotation_degrees=float(angles.max()),frozen_pose_maximum_component_error=frozen_error,
        passed=bool(translation.max()<=value['maximum_translation_m'] and angles.max()<=value['maximum_rotation_degrees'] and frozen_error<=1e-12),
        continuous_bounds_certified=False)


def run(contacts_path, request_path, policy_path, output):
    contacts_path,request_path,policy_path,output=[Path(p).resolve() for p in (contacts_path,request_path,policy_path,output)]
    if output.exists():raise ValueError('Fresh object hold fit output required')
    with worker_lock(),threadpool_limits(limits=1):
        inputs={str(p):sha256(p) for p in (contacts_path,request_path,policy_path)}
        authored=read(contacts_path);scene=SceneContacts(authored,contacts_path.parent);value=read(request_path);policy=read(policy_path)
        request_for(scene,value,inputs[str(contacts_path)]);policy_for(policy,scene,inputs[str(contacts_path)])
        methods={n:sha256(ROOT/'scripts'/n) for n in METHODS};output.mkdir(parents=True);archive=output/'implementation';archive.mkdir()
        for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
        for path,name in [(contacts_path,'source-contacts.json'),(request_path,'fit-request.json'),(policy_path,'source-policy.json')]:shutil.copyfile(path,output/name)
        snapshots={};derived=copy.deepcopy(authored)
        for i,(name,a) in enumerate(scene.actors.items()):
            src=(contacts_path.parent/authored['actors'][name]['glb']).resolve()
            dest=output/'input'/f'actor-{i}.glb';dest.parent.mkdir(exist_ok=True);shutil.copyfile(src,dest)
            if sha256(dest)!=authored['actors'][name]['sha256']:raise ValueError('Actor snapshot changed')
            snapshots[name]=dict(path=dest.relative_to(output).as_posix(),sha256=sha256(dest))
            derived['actors'][name]['glb']=str(dest)
        save(output/'pipeline.json',dict(status='processing',original_selected=True))
        try:
            keys,arrays=proposal(scene,value,inputs[str(contacts_path)])
            original_keys={float(k['time_s']):k for k in authored['objects'][value['object']]['keyframes']}
            left,right=value['edit_window_s']
            for i,k in enumerate(keys):
                if (k['time_s']<=left or k['time_s']>=right) and k['time_s'] in original_keys:keys[i]=copy.deepcopy(original_keys[k['time_s']])
            derived['objects'][value['object']]['keyframes']=keys
            save(output/'proposal-contacts.json',derived);digest=sha256(output/'proposal-contacts.json')
            candidate=SceneContacts(derived,output)
            coverage=np.unique(np.r_[policy['clock']['times_s'],arrays['times_s']])
            derived_policy=copy.deepcopy(policy);derived_policy['contacts_sha256']=digest
            derived_policy['clock']=dict(mode=policy['clock']['mode'],times_s=coverage.tolist())
            clocks,_,_=policy_for(derived_policy,candidate,digest)
            bounds=audit_bounds(scene,candidate,value,clocks)
            contacts,observations=candidate.evaluate();save(output/'contact-audit.json',contacts)
            geometry,transport=geometry_archive(candidate,derived_policy,digest,output/'geometry-observations.npz',
                lambda p:save(output/'pipeline.json',dict(**p,original_selected=True)))
            geometry.update(**transport)
            save(output/'geometry-policy.json',derived_policy);save(output/'geometry-audit.json',geometry)
            np.savez_compressed(output/'proposal-observations.npz',**arrays)
            np.savez_compressed(output/'contact-observations.npz',**observations)
            scene.check_inputs();candidate.check_inputs()
            if any(sha256(Path(p))!=h for p,h in inputs.items()):raise ValueError('Object fit input changed')
            if any(sha256(ROOT/'scripts'/n)!=h or sha256(archive/n)!=h for n,h in methods.items()):raise ValueError('Object fit implementation changed')
            for path,name in [(contacts_path,'source-contacts.json'),(request_path,'fit-request.json'),(policy_path,'source-policy.json')]:
                if sha256(path)!=sha256(output/name):raise ValueError('Authored object fit snapshot changed')
            result=dict(at=now(),status='complete',object=value['object'],contact_ids=value['contact_ids'],keys=len(keys),bounds=bounds,
                all_contact_conditions_pass=contacts['passed'],sampled_geometry_conditions_pass=geometry['sampled_conditions_pass'],
                sampled_constraints_pass=bool(bounds['passed'] and contacts['passed'] and geometry['sampled_conditions_pass']),
                actor_bytes_unchanged=True,actor_snapshots=snapshots,input_sha256=inputs,actor_inputs_sha256=scene.inputs,
                implementation_sha256=methods,frame_contract_sha256=contract_sha256(),proposal_contacts_sha256=digest,
                geometry_samples=len(clocks),original_selected=True,quality_approved=False,release_approved=False,training_admitted=False,
                scope='Explicit two-grip object pose proposal and sampled original-relative bounds. All saved scene contacts and complete actor/object/partner geometry checked on the expanded clock. '
                    'Fixed actor clips; unconstrained two-point twist follows the reference. No forces, attachment/release simulation, contact-normal, self/continuous collision, engine or human-quality approval.')
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',original_selected=True));return result
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('contacts','request','policy','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();run(args.contacts,args.request,args.policy,args.output)
