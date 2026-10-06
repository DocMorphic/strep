"""Append an offline clip library using one shared target reference profile.

No action whitelist, blending, sampling model, contact or quality approval.
Explicit boundary limits measure pose and adjacent native-key velocity jumps.
"""
import argparse
import copy
import json
from pathlib import Path
import re
import shutil

import numpy as np
from scipy.spatial.transform import Rotation

import native_rig_transfer as transfer
from audit_native_rig_transfer import bound_candidate, METHODS as AUDIT_METHODS
from native_scene_contacts import fields, scalar
from retarget_rig import resolve_profile
from rig_asset import RigAsset
from strep import read, save, sha256, now

SCHEMA='strep-native-transfer-library-v1'
SCRIPT_ROOT=Path(__file__).resolve().parent
METHODS=tuple(dict.fromkeys(AUDIT_METHODS+('native_transfer_library.py',)))
FALSE_FLAGS=('quality_approved','release_approved','training_admitted','contact_verified',
    'surface_verified','geometry_verified','physics_verified','engine_import_verified','human_reviewed')
NAME=re.compile(r'[A-Za-z0-9_-]{1,100}')


def require(ok,message):
    if not ok:raise ValueError(message)


def equal(a,b):
    return json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)


def binding(value,base):
    fields(value,('path','sha256'),'library input binding')
    require(isinstance(value['path'],str) and value['path'],'Explicit input path required')
    path=(base/value['path']).resolve()
    require(path.is_file() and sha256(path)==value['sha256'],'Library input changed')
    return path


def source_basis(rig,profile,roles):
    mapping,_=resolve_profile(rig,profile)
    require(set(roles)<=set(mapping),'Every target role needs a source reference')
    return {role:rig.reference[mapping[role]].tolist() for role in sorted(roles)}


def planned(recipe,base):
    fields(recipe,('schema','target','clips','rate','maximum_planned_pose_transforms','boundaries'),'native library recipe')
    require(recipe['schema']==SCHEMA and type(recipe['rate']) is int and recipe['rate'] in (60,120,240),'Explicit library schema and native transfer rate required')
    fields(recipe['target'],('glb','profile'),'shared library target')
    target=binding(recipe['target']['glb'],base);profile_path=binding(recipe['target']['profile'],base)
    target_rig=RigAsset.load(target);profile=read(profile_path)
    require(profile.get('character_sha256')==sha256(target),'Shared target profile does not bind the target')
    roles,_=resolve_profile(target_rig,profile)
    require(isinstance(recipe['clips'],list) and 1<=len(recipe['clips'])<=16,'Choose 1-16 explicitly selected clips')
    require(type(recipe['maximum_planned_pose_transforms']) is int and 1<=recipe['maximum_planned_pose_transforms']<=1000000,'A complete 1-1000000 pose-transform budget is required')
    clips=[];basis=None;population=0;seen=set()
    for clip in recipe['clips']:
        fields(clip,('id','glb','profile','animation_index'),'selected library clip')
        require(isinstance(clip['id'],str) and NAME.fullmatch(clip['id']) and clip['id'] not in seen,'Distinct safe clip IDs required');seen.add(clip['id'])
        path=binding(clip['glb'],base);sp_path=binding(clip['profile'],base);source=RigAsset.load(path);sp=read(sp_path)
        require(sp.get('character_sha256')==sha256(path),'Selected source profile does not bind its source')
        prepared=transfer.prepare(source,sp,target_rig,profile,clip['animation_index']);times=transfer.clock(prepared[0],recipe['rate'])
        current=source_basis(source,sp,roles)
        if basis is None:basis=current
        require(all(np.allclose(current[n],basis[n],atol=1e-12,rtol=0) for n in basis),
            'Source reference basis changed; choose a separately calibrated library')
        # Full dense export and key/quarter/mid/three-quarter fidelity populations.
        # Counts are per complete export/readback pass, not a wall-time promise.
        population+=len(times)*(len(source.parents)+len(target_rig.parents))+(4*len(times)-3)*(len(source.parents)+2*len(target_rig.parents))
        clips.append(dict(id=clip['id'],source=str(path),source_profile=str(sp_path),animation_index=clip['animation_index'],
            keys=len(times),duration_s=float(times[-1])))
    require(population<=recipe['maximum_planned_pose_transforms'],'Complete library population exceeds its budget; no truncation')
    require(isinstance(recipe['boundaries'],list) and len(recipe['boundaries'])<=len(clips)-1,'Explicit adjacent boundary checks required')
    adjacent={(clips[i]['id'],clips[i+1]['id']) for i in range(len(clips)-1)};pairs=set()
    limits=('position_m','rotation_degrees','linear_speed_jump_m_s','angular_speed_jump_degrees_s')
    for row in recipe['boundaries']:
        fields(row,('from','to','limits'),'requested library boundary')
        require(all(isinstance(row[k],str) and NAME.fullmatch(row[k]) for k in ('from','to')),'Exact clip IDs required for a boundary')
        pair=(row['from'],row['to'])
        require(pair in adjacent and pair not in pairs,'Check each selected adjacent boundary at most once');pairs.add(pair)
        fields(row['limits'],limits,'boundary limits')
        for name in limits:scalar(row['limits'][name],0,10000,'finite boundary limit')
    return dict(clips=clips,target=str(target),target_profile=str(profile_path),source_reference_basis=basis,
        planned_pose_transforms=population,original_animation_count=len(target_rig.document.get('animations',[])))


def relative_angle(a,b):
    return np.degrees(Rotation.from_matrix(a.swapaxes(-1,-2)@b).magnitude())


def endpoints(folder):
    with np.load(folder/'target-transforms.npz',allow_pickle=False) as z:
        times=z['times_s'].astype(float);world=z['global_matrices']
        require(len(times)>=2 and np.all(np.diff(times)>0),'Two distinct native keys required for boundary rates')
        samples=world[[0,1,-2,-1]].copy()
    dt=[times[1]-times[0],times[-1]-times[-2]]
    velocity=np.array([(samples[1,:,:3,3]-samples[0,:,:3,3])/dt[0],(samples[3,:,:3,3]-samples[2,:,:3,3])/dt[1]])
    # World angular velocity: R_next @ R_previous.T, radians/second.
    omega=np.array([Rotation.from_matrix(samples[1,:,:3,:3]@samples[0,:,:3,:3].transpose(0,2,1)).as_rotvec()/dt[0],
        Rotation.from_matrix(samples[3,:,:3,:3]@samples[2,:,:3,:3].transpose(0,2,1)).as_rotvec()/dt[1]])
    return samples,velocity,omega


def boundary_rows(recipe,folder,joints):
    rows=[]
    for row in recipe['boundaries']:
        a,av,ao=endpoints(folder/'stages'/row['from']);b,bv,bo=endpoints(folder/'stages'/row['to'])
        metrics=dict(position_m=float(np.linalg.norm(a[-1,joints,:3,3]-b[0,joints,:3,3],axis=1).max()),
            rotation_degrees=float(relative_angle(a[-1,joints,:3,:3],b[0,joints,:3,:3]).max()),
            linear_speed_jump_m_s=float(np.linalg.norm(av[-1,joints]-bv[0,joints],axis=1).max()),
            angular_speed_jump_degrees_s=float(np.degrees(np.linalg.norm(ao[-1,joints]-bo[0,joints],axis=1)).max()))
        passed={n:metrics[n]<=row['limits'][n] for n in metrics}
        rows.append(dict(**copy.deepcopy(row),measured=metrics,checks=passed,all_declared_samples_pass=all(passed.values()),
            scope='All target skin-joint endpoint poses and adjacent native-key world finite differences; not continuous velocity, blending, mesh contacts or action quality.'))
    return rows


def edit_profile(template,character):
    profile=copy.deepcopy(template)
    profile.update(character_sha256=sha256(character),world_offset_m=[0,0,0],axis_alignment_xyzw={})
    return profile


def catalog(recipe,plan,folder):
    rig=RigAsset.load(folder/'character.glb');rows=boundary_rows(recipe,folder,rig.joints)
    return dict(schema=SCHEMA,clips=[dict(id=c['id'],animation_index=plan['original_animation_count']+i,
        source_animation_index=c['animation_index'],duration_s=c['duration_s'],keys=c['keys']) for i,c in enumerate(plan['clips'])],
        original_animation_count=plan['original_animation_count'],planned_pose_transforms=plan['planned_pose_transforms'],
        shared_target_profile_sha256=sha256(folder/'input/target-profile.json'),source_reference_basis=plan['source_reference_basis'],
        profiles=dict(target='target-profile.json',edit='edit-profile.json',
            scope='Target retains shared calibration for further appends. Edit clears baked axes and placement for use as a motion source.'),
        boundary_checks=rows,boundary_checks_requested=bool(rows),
        all_declared_boundary_samples_pass=all(r['all_declared_samples_pass'] for r in rows) if rows else None,
        originals_unchanged=True,original_selected=True,**{k:False for k in FALSE_FLAGS},
        scope='Editable native clips appended using one fixed reference calibration. Original target animations and raw payload retained. '
            'Explicit indices preserve varied input motions. No concatenation, crossfade, automatic contact/event transfer or quality approval.')


def frozen(folder):
    p=read(folder/'prepared.json')
    fields(p,('schema','at','recipe_base','recipe_original_path','recipe_sha256','original_inputs_sha256','snapshots_sha256','implementation_sha256','plan'),'library preparation')
    require(p['schema']==SCHEMA,'Library preparation schema changed')
    require(set(p['implementation_sha256'])==set(METHODS),'Complete library methods required')
    for n,h in p['implementation_sha256'].items():require(sha256(SCRIPT_ROOT/n)==sha256(folder/'implementation'/n)==h,'Library methods changed')
    for path,h in p['original_inputs_sha256'].items():require(sha256(path)==h,'Original library input changed')
    for n,h in p['snapshots_sha256'].items():require(sha256(folder/n)==h,'Library input snapshot changed')
    require(sha256(folder/'recipe.json')==p['recipe_sha256'],'Library recipe changed')
    plan=planned(read(folder/'recipe.json'),Path(p['recipe_base']))
    require(equal(plan,p['plan']),'Library reference basis or complete population changed')
    expected={str(Path(p['recipe_original_path']).resolve()),plan['target'],plan['target_profile']}
    expected.update(c[k] for c in plan['clips'] for k in ('source','source_profile'))
    require(set(p['original_inputs_sha256'])==expected and sha256(p['recipe_original_path'])==p['recipe_sha256'],
        'Complete original input bindings required')
    snapshots={'input/target.glb':plan['target'],'input/target-profile.json':plan['target_profile']}
    for i,c in enumerate(plan['clips']):snapshots.update({f'input/source-{i}.glb':c['source'],f'input/source-{i}-profile.json':c['source_profile']})
    require(set(p['snapshots_sha256'])==set(snapshots) and all(sha256(folder/n)==sha256(path) for n,path in snapshots.items()),
        'Complete input snapshots must retain the selected source bytes')
    return p,plan


def verify(folder):
    folder=Path(folder).resolve();p,plan=frozen(folder);recipe=read(folder/'recipe.json');result=read(folder/'result.json')
    require(read(folder/'pipeline.json')['status']=='complete','Completed library required')
    require(read(folder/'completion.json')==dict(result_sha256=sha256(folder/'result.json')),'Library result changed')
    previous=folder/'input/target.glb';template=read(folder/'input/target-profile.json')
    for i,c in enumerate(plan['clips']):
        stage=folder/'stages'/c['id'];_,report,source,target,tp,prepared,times,derived,index,_=bound_candidate(stage)
        expected=copy.deepcopy(template);expected['character_sha256']=sha256(previous)
        require(equal(tp,expected) and sha256(stage/'target.glb')==sha256(previous),'Shared reference profile or preceding library changed')
        require(sha256(stage/'source.glb')==sha256(c['source']) and sha256(stage/'source-profile.json')==sha256(c['source_profile'])
            and report['source_animation_index']==c['animation_index'] and report['sampling_rate_hz']==recipe['rate'],
            'Library source selection changed')
        require(index==plan['original_animation_count']+i,'Appended library clip index changed')
        fidelity=transfer.verify(source,target,prepared[0],derived,index,prepared,tp,times)
        require(fidelity['passed'] is True and equal(fidelity,report['fidelity']),'Complete library fidelity no longer replays')
        expected_world,_,_=transfer.evaluate_transfer(source,target,prepared[0],prepared[1],prepared[2],prepared[3],prepared[4],tp,times)
        with np.load(stage/'target-transforms.npz',allow_pickle=False) as z:
            require(np.array_equal(z['global_matrices'],expected_world),'Complete library motion arrays changed')
        require(all(report[k] is False for k in ('quality_approved','contact_verified','engine_import_verified','release_approved')),'Library stage cannot approve quality or engine import')
        previous=stage/'character.glb'
    require(sha256(folder/'character.glb')==sha256(previous),'Final library changed')
    expected=copy.deepcopy(template);expected['character_sha256']=sha256(previous)
    require(equal(read(folder/'target-profile.json'),expected),'Final target profile changes the shared reference')
    require(equal(read(folder/'edit-profile.json'),edit_profile(template,folder/'character.glb')),'Baked motion edit profile changed')
    expected_catalog=catalog(recipe,plan,folder);require(equal(read(folder/'catalog.json'),expected_catalog),'Library boundary measurements or clip catalog changed')
    expected_result=dict(schema=SCHEMA,status='complete',prepared_sha256=sha256(folder/'prepared.json'),catalog_sha256=sha256(folder/'catalog.json'),
        files_sha256={n:sha256(folder/n) for n in ('character.glb','target-profile.json','edit-profile.json','catalog.json')},
        stage_reports_sha256={c['id']:sha256(folder/'stages'/c['id']/'report.json') for c in plan['clips']},
        original_selected=True,**{k:False for k in FALSE_FLAGS})
    require(equal(result,expected_result),'Library decisions or scope changed');return result


def run(recipe_path,folder):
    recipe_path=Path(recipe_path).resolve();folder=Path(folder).resolve();recipe=read(recipe_path);plan=planned(recipe,recipe_path.parent)
    require(not folder.exists(),'Fresh library output required')
    inputs={recipe_path,Path(plan['target']),Path(plan['target_profile'])}
    inputs.update(Path(c[k]) for c in plan['clips'] for k in ('source','source_profile'))
    require(all(not p.is_relative_to(folder) for p in inputs),'Library output contains an input')
    folder.mkdir(parents=True);save(folder/'pipeline.json',dict(status='preparing',original_selected=True,quality_approved=False))
    try:
        shutil.copyfile(recipe_path,folder/'recipe.json');(folder/'input').mkdir();(folder/'implementation').mkdir();snapshots={}
        names={'input/target.glb':Path(plan['target']),'input/target-profile.json':Path(plan['target_profile'])}
        for i,c in enumerate(plan['clips']):names.update({f'input/source-{i}.glb':Path(c['source']),f'input/source-{i}-profile.json':Path(c['source_profile'])})
        for n,path in names.items():shutil.copyfile(path,folder/n);snapshots[n]=sha256(folder/n);require(snapshots[n]==sha256(path),'Library input changed during snapshot')
        methods={n:sha256(SCRIPT_ROOT/n) for n in METHODS}
        for n,h in methods.items():shutil.copyfile(SCRIPT_ROOT/n,folder/'implementation'/n);require(sha256(folder/'implementation'/n)==h,'Library method changed during snapshot')
        save(folder/'prepared.json',dict(schema=SCHEMA,at=now(),recipe_base=str(recipe_path.parent),recipe_original_path=str(recipe_path),recipe_sha256=sha256(folder/'recipe.json'),
            original_inputs_sha256={str(p):sha256(p) for p in inputs},snapshots_sha256=snapshots,implementation_sha256=methods,plan=plan))
        frozen(folder);(folder/'stages').mkdir();template=read(folder/'input/target-profile.json');previous=folder/'input/target.glb'
        for i,c in enumerate(plan['clips']):
            frozen(folder);save(folder/'pipeline.json',dict(status='processing',stage=c['id'],original_selected=True,quality_approved=False))
            profile=copy.deepcopy(template);profile['character_sha256']=sha256(previous);profile_path=folder/'input'/f'target-profile-{i}.json';save(profile_path,profile)
            transfer.export(folder/'input'/f'source-{i}.glb',folder/'input'/f'source-{i}-profile.json',previous,profile_path,
                c['animation_index'],folder/'stages'/c['id'],recipe['rate'])
            previous=folder/'stages'/c['id']/'character.glb'
        frozen(folder);shutil.copyfile(previous,folder/'character.glb');profile=copy.deepcopy(template);profile['character_sha256']=sha256(previous);save(folder/'target-profile.json',profile)
        save(folder/'edit-profile.json',edit_profile(template,folder/'character.glb'))
        save(folder/'catalog.json',catalog(recipe,plan,folder))
        r=dict(schema=SCHEMA,status='complete',prepared_sha256=sha256(folder/'prepared.json'),catalog_sha256=sha256(folder/'catalog.json'),
            files_sha256={n:sha256(folder/n) for n in ('character.glb','target-profile.json','edit-profile.json','catalog.json')},
            stage_reports_sha256={c['id']:sha256(folder/'stages'/c['id']/'report.json') for c in plan['clips']},
            original_selected=True,**{k:False for k in FALSE_FLAGS})
        save(folder/'result.json',r);save(folder/'completion.json',dict(result_sha256=sha256(folder/'result.json')))
        save(folder/'pipeline.json',dict(status='complete',original_selected=True,quality_approved=False));verify(folder);return r
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('recipe',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    print(run(args.recipe,args.output))
