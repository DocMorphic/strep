"""Explicit Studio native transfer jobs; originals and selection stay intact."""
import argparse
import copy
import os
from pathlib import Path
import re
import shutil
import zipfile

import numpy as np
import audit_native_rig_transfer as engine
import native_rig_transfer as bridge
import studio_characters as characters
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from strep import ROOT,read,save,sha256,now

NAMESPACE='native-transfer-jobs'
NAME=re.compile(r'^[A-Za-z0-9_-]{1,100}$')
SCRIPT_ROOT=Path(__file__).resolve().parent
METHODS=tuple(dict.fromkeys(engine.METHODS+('studio_native_rig_transfer.py','studio_characters.py')))
INPUTS=('source.glb','source-profile.json','target.glb','target-profile.json')
DOWNLOADS=('candidate.zip','transfer/character.glb','edit-profile.json','transfer/root-motion.json',
           'transfer/report.json','audit/animation.res','audit/result.json','result.json')
FIELDS={'source_asset_id','source_profile_id','target_asset_id','target_profile_id','animation_index','rate'}


def require(value,message):
    if not value:raise ValueError(message)


def folder_for(job):
    require(isinstance(job,str) and NAME.fullmatch(job),'Invalid native transfer job')
    base=(ROOT/'reports'/NAMESPACE).resolve();folder=(base/job).resolve()
    require(folder.parent==base,'Native transfer job escapes namespace');return folder


def inputs(payload,*,active=False):
    require(isinstance(payload,dict) and set(payload)==FIELDS,'Exact source/target mappings, clip and sampling rate required')
    require(type(payload['animation_index']) is int and type(payload['rate']) is int and payload['rate'] in (60,120,240),'Integer clip and 60/120/240 Hz rate required')
    files=[]
    for side in ('source','target'):
        asset=payload[side+'_asset_id'];profile_id=payload[side+'_profile_id']
        folder=characters.asset_folder(asset);profile=characters.profile_path(asset,profile_id)
        require(sha256(folder/'character.glb')==asset,'Imported character changed')
        if active:require(read(folder/'active-profile.json')['id']==profile_id,'Saved mapping changed; bind the characters again')
        files.extend([folder/'character.glb',profile])
    require(payload['source_asset_id']!=payload['target_asset_id'],'Choose a different target character')
    source,target=RigAsset.load(files[0]),RigAsset.load(files[2])
    prepared=bridge.prepare(source,read(files[1]),target,read(files[3]),payload['animation_index'])
    bridge.clock(prepared[0],payload['rate'])
    return files


def validate_request(payload):return inputs(payload,active=True)


def character_metadata(asset):
    details=characters.details(asset);profile_id=details['profile_id']
    require(profile_id is not None,'Save this character mapping in Characters first')
    folder=characters.asset_folder(asset);profile=characters.profile_path(asset,profile_id)
    require(sha256(folder/'character.glb')==asset,'Imported character changed')
    rig=RigAsset.load(folder/'character.glb');p=read(profile)
    from retarget_rig import resolve_profile
    resolve_profile(rig,p)
    clips=[]
    for i,clip in enumerate(rig.document.get('animations',[])):
        row=dict(index=i,name=clip.get('name','Clip '+str(i+1)),supported=False)
        try:
            sampler=NativeSupportSampler(rig.document,rig.binary,i)
            require(all(c[4]=='LINEAR' for c in sampler.channels),'Native transfer requires LINEAR channels')
            row.update(supported=True,duration_s=sampler.duration)
        except (ValueError,KeyError,TypeError,IndexError) as exc:row['reason']=str(exc)
        clips.append(row)
    return dict(asset_id=asset,name=details['name'],profile_id=profile_id,clips=clips,
        source_profile_ready=not np.any(np.asarray(p.get('world_offset_m',[0,0,0]))) and not p.get('axis_alignment_xyzw'),
        quality_approved=False)


def prepare(payload,folder):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name) and not folder.exists(),'Fresh native transfer job required')
    files=validate_request(payload);methods={n:sha256(SCRIPT_ROOT/n) for n in METHODS};folder.mkdir(parents=True)
    save(folder/'pipeline.json',dict(status='preparing',original_selected=True,quality_approved=False))
    try:
        source=folder/'input';source.mkdir();archive=folder/'implementation';archive.mkdir()
        for path,name in zip(files,INPUTS):shutil.copyfile(path,source/name)
        for n in METHODS:shutil.copyfile(SCRIPT_ROOT/n,archive/n)
        save(folder/'request.json',payload)
        save(folder/'prepared.json',dict(schema='strep-studio-native-transfer-prepared-v1',
            request_sha256=sha256(folder/'request.json'),input_sha256={n:sha256(source/n) for n in INPUTS},
            implementation_sha256=methods,original_selected=True,quality_approved=False))
        frozen(folder);save(folder/'pipeline.json',dict(status='starting',original_selected=True,quality_approved=False))
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


def frozen(folder,*,current=True):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name),'Bound native transfer folder required')
    p=read(folder/'prepared.json');payload=read(folder/'request.json');files=inputs(payload)
    require(p['schema']=='strep-studio-native-transfer-prepared-v1' and p['request_sha256']==sha256(folder/'request.json'),'Native transfer request changed')
    require(set(p['input_sha256'])==set(INPUTS) and set(p['implementation_sha256'])==set(METHODS),'Complete native transfer preparation required')
    require(p['original_selected'] is True and p['quality_approved'] is False,'Native transfer preparation scope changed')
    for path,name in zip(files,INPUTS):require(sha256(path)==p['input_sha256'][name]==sha256(folder/'input'/name),'Original character/mapping or snapshot changed')
    for name,digest in p['implementation_sha256'].items():
        require(sha256(folder/'implementation'/name)==digest,'Archived native transfer implementation changed')
        if current:require(sha256(SCRIPT_ROOT/name)==digest,'Native transfer implementation changed during job')
    return p,payload


def edit_profile(folder):
    profile=copy.deepcopy(read(folder/'input/target-profile.json'))
    profile.update(character_sha256=sha256(folder/'transfer/character.glb'),world_offset_m=[0,0,0],axis_alignment_xyzw={},
        notes='Native transfer edit mapping. Placement/axis corrections were baked into the clip; original target profile remains in the transfer provenance.')
    return profile


def package_files(folder):
    return {'character.glb':folder/'transfer/character.glb','rig-profile.json':folder/'edit-profile.json',
        'root-motion.json':folder/'transfer/root-motion.json','contacts.json':folder/'transfer/contacts.json',
        'transfer-report.json':folder/'transfer/report.json','animation.res':folder/'audit/animation.res',
        'engine-audit.json':folder/'audit/result.json','asset-lineage.json':folder/'asset-lineage.json'}


def run(folder):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name),'Bound native transfer worker folder required')
    require(read(folder/'pipeline.json')['status']=='starting' and not any((folder/n).exists() for n in ('transfer','audit','completion.json')),'Fresh native transfer worker required')
    if (folder/'worker.json').exists():
        import psutil
        identity=read(folder/'worker.json')
        require(identity['pid']==os.getpid() and abs(identity['created_at']-psutil.Process().create_time())<.001,'Worker identity belongs to another process')
    try:
        import psutil
        save(folder/'worker.json',dict(pid=os.getpid(),created_at=psutil.Process().create_time()))
        p,payload=frozen(folder);save(folder/'pipeline.json',dict(status='processing',stage='native-transfer-and-readback',original_selected=True,quality_approved=False))
        report=bridge.export(*(folder/'input'/n for n in INPUTS),payload['animation_index'],folder/'transfer',payload['rate'])
        frozen(folder);save(folder/'pipeline.json',dict(status='processing',stage='saved-resource-and-root-playback-audit',original_selected=True,quality_approved=False))
        audited=engine.run(folder/'transfer',folder/'audit');frozen(folder)
        save(folder/'edit-profile.json',edit_profile(folder))
        lineage={side:{k:read(characters.asset_folder(payload[side+'_asset_id'])/'asset.json').get(k) for k in ('id','name','license_metadata')} for side in ('source','target')}
        lineage.update(source_animation_index=payload['animation_index'],note='Original asset/motion terms continue to apply; transfer and local import do not grant redistribution rights.')
        save(folder/'asset-lineage.json',lineage)
        files=package_files(folder)
        with zipfile.ZipFile(folder/'candidate.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
            for name,path in files.items():z.write(path,name)
        result=dict(schema='strep-studio-native-transfer-job-v1',status='complete',prepared_sha256=sha256(folder/'prepared.json'),
            request=payload,transfer_fidelity=report['fidelity'],sampled_runtime_conditions_pass=audited['sampled_runtime_conditions_pass'],
            source_skin_joints=report['source_skin_joints'],target_skin_joints=report['target_skin_joints'],duration_s=report['source_duration_s'],
            output_animation_index=report['output_animation_index'],samples=audited['samples'],original_selected=True,studio_selection_changed=False,
            source_bytes_unchanged=True,contact_verified=False,human_reviewed=False,quality_approved=False,release_approved=False,
            files_sha256={n:sha256(folder/n) for n in DOWNLOADS if n!='result.json'},
            artifacts_sha256={n:sha256(folder/n) for n in ('audit/runtime-engine.json','audit/observations.npz','audit/runtime-request.json','audit/prepare.log.terminal.json','audit/runtime.log.terminal.json','asset-lineage.json')})
        save(folder/'result.json',result);save(folder/'completion.json',dict(result_sha256=sha256(folder/'result.json')))
        verify_output(folder,p,result)
        save(folder/'pipeline.json',dict(status='complete',finished_at=now(),original_selected=True,quality_approved=False));return result
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


def verify_output(folder,p,r):
    require(r['schema']=='strep-studio-native-transfer-job-v1' and r['status']=='complete' and r['prepared_sha256']==sha256(folder/'prepared.json')
        and read(folder/'completion.json')['result_sha256']==sha256(folder/'result.json'),'Completed native transfer receipt changed')
    require(r['request']==read(folder/'request.json') and all(r[k] is True for k in ('original_selected','source_bytes_unchanged'))
        and all(r[k] is False for k in ('studio_selection_changed','contact_verified','human_reviewed','quality_approved','release_approved')),'Native transfer scope changed')
    require(set(r['files_sha256'])==set(DOWNLOADS)-{'result.json'} and all(sha256(folder/n)==h for n,h in r['files_sha256'].items()),'Complete native transfer downloads changed')
    artifacts={'audit/runtime-engine.json','audit/observations.npz','audit/runtime-request.json','audit/prepare.log.terminal.json','audit/runtime.log.terminal.json','asset-lineage.json'}
    require(set(r['artifacts_sha256'])==artifacts and all(sha256(folder/n)==h for n,h in r['artifacts_sha256'].items()),'Native transfer playback evidence changed')
    bound=engine.bound_candidate(folder/'transfer');report=bound[1]
    measured=bridge.verify(bound[2],bound[3],bound[5][0],bound[7],bound[8],bound[5],bound[4],bound[6])
    require(measured==report['fidelity'] and measured['passed'],'Native transfer motion no longer matches its source')
    require(report['input_snapshots_sha256']==p['input_sha256'] and report['source_animation_index']==r['request']['animation_index']
        and report['sampling_rate_hz']==r['request']['rate'],'Native transfer candidate source changed')
    require(read(folder/'edit-profile.json')==edit_profile(folder),'Baked edit mapping changed')
    audited=read(folder/'audit/result.json')
    require(audited['schema']=='strep-native-rig-transfer-engine-v1' and audited['input_sha256']['character.glb']==report['glb_sha256']
        and audited['animation_resource_sha256']==sha256(folder/'audit/animation.res')
        and audited['implementation_sha256']=={n:p['implementation_sha256'][n] for n in engine.METHODS},'Native transfer resource/method binding changed')
    require(audited['source_bytes_unchanged'] is True and audited['original_selected'] is True
        and all(audited[k] is False for k in ('quality_approved','contact_verified','physics_verified','release_approved')),'Native transfer engine scope changed')
    for name,digest in audited['input_sha256'].items():require(sha256(folder/'transfer'/name)==digest==sha256(folder/'audit'/name),'Native transfer audit source differs')
    rig,index,root=bound[-3],bound[-2],bound[-1]
    request=read(folder/'audit/runtime-request.json');times=np.frombuffer(bytes.fromhex(request['clock']['bytes_hex']),dtype='<f8')
    keys=bound[6].astype(float);expected=np.sort(np.concatenate([keys]+[keys[:-1]+f*np.diff(keys) for f in (.25,.5,.75)]))
    require(np.array_equal(times,expected),'Complete native transfer audit clock changed')
    from native_engine_clock import check_clock_wire
    check_clock_wire(request['clock'],expected)
    require(set(request)=={'glb','animation_resource','animation_index','root_bone','clock','placement'}
        and request['glb']==str(folder/'audit/character.glb') and request['animation_resource']==str(folder/'audit/animation.res')
        and request['animation_index']==index and request['root_bone']==rig.document['nodes'][root]['name'],'Native transfer audit participant selection changed')
    sampler,times,placement=engine.runtime.validate(rig,index,root,times,request['placement'])
    actual=read(folder/'audit/runtime-engine.json');checked,arrays=engine.runtime.evaluate(rig,sampler,times,placement,actual)
    require(all(audited[k]==v for k,v in checked.items()),'Native transfer observations disagree with summary')
    with np.load(folder/'audit/observations.npz',allow_pickle=False) as stored:
        require(set(stored.files)==set(arrays) and all(stored[n].dtype==v.dtype and stored[n].shape==v.shape and stored[n].tobytes()==v.tobytes() for n,v in arrays.items()),'Complete transfer observations changed')
    require(audited['raw_engine_sha256']==sha256(folder/'audit/runtime-engine.json') and audited['observations_sha256']==sha256(folder/'audit/observations.npz'),'Native transfer raw evidence binding changed')
    for name in ('prepare.log.terminal.json','runtime.log.terminal.json'):
        terminal=read(folder/'audit'/name);require(terminal['exit_code']==0 and terminal['owned_tree_stopped'] is True,'Native engine stage is not terminal')
    require(all(r[k]==report[k] for k in ('source_skin_joints','target_skin_joints','output_animation_index'))
        and r['transfer_fidelity']==report['fidelity'] and r['duration_s']==report['source_duration_s']
        and r['samples']==audited['samples'] and r['sampled_runtime_conditions_pass']==audited['sampled_runtime_conditions_pass'],'Native transfer decision changed')
    with zipfile.ZipFile(folder/'candidate.zip') as z:
        files=package_files(folder);require(len(z.namelist())==len(files) and set(z.namelist())==set(files),'Complete candidate ZIP required')
        require(all(z.read(n)==path.read_bytes() for n,path in files.items()),'Candidate ZIP payload changed')


def manifest(job):
    folder=folder_for(job)
    from contact_edit_job import observed_state
    state=observed_state(folder);data=dict(id=job,status=state['status'],stage=state.get('stage'),error=state.get('error'),downloads=[],quality_approved=False,release_approved=False)
    if state['status']!='complete':return data
    p,payload=frozen(folder,current=False);r=read(folder/'result.json');verify_output(folder,p,r)
    data.update(**{k:r[k] for k in ('source_skin_joints','target_skin_joints','duration_s','output_animation_index','samples','transfer_fidelity','sampled_runtime_conditions_pass','contact_verified','original_selected')},result_sha256=sha256(folder/'result.json'))
    data['downloads']=[dict(label=n,url=f'/files/{NAMESPACE}/{job}/{n}',sha256=sha256(folder/n)) for n in DOWNLOADS]
    source=RigAsset.load(folder/'input/source.glb');target=RigAsset.load(folder/'transfer/character.glb')
    data['previews']=[dict(id='source',label='Original source clip',preview_url=f'/files/character-assets/{payload["source_asset_id"]}/character.glb',preview_sha256=payload['source_asset_id'],animation_index=payload['animation_index'],animation_count=len(source.document['animations'])),
        dict(id='candidate',label='Transferred candidate',preview_url=f'/files/{NAMESPACE}/{job}/transfer/character.glb',preview_sha256=sha256(folder/'transfer/character.glb'),animation_index=r['output_animation_index'],animation_count=len(target.document['animations']))]
    for v in data['previews']:v.update(kind='native_rig_transfer',preview_start_s=0.,preview_end_s=r['duration_s'])
    data['preview_url']=f'/native-transfer-viewer.html?id={job}&result={data["result_sha256"]}'
    return data


def listing():
    from contact_edit_job import observed_state
    return dict(jobs=[dict(id=p.name,status=observed_state(p)['status']) for p in sorted((ROOT/'reports'/NAMESPACE).glob('*'),reverse=True)
        if p.is_dir() and NAME.fullmatch(p.name) and (p/'pipeline.json').is_file()])


def served_file(relative):
    parts=Path(relative).parts
    if len(parts)<3 or parts[0]!=NAMESPACE:return None
    try:
        folder=folder_for(parts[1]);target=(ROOT/'reports'/relative).resolve();require(target.is_relative_to(folder),'Transfer download escapes job')
        return target if any(d['url']=='/files/'+relative for d in manifest(parts[1])['downloads']) else None
    except (ValueError,TypeError,KeyError,OSError,zipfile.BadZipFile):return None


def import_candidate(payload):
    require(isinstance(payload,dict) and set(payload)=={'job','result_sha256'},'Exact completed candidate selection required')
    m=manifest(payload['job']);folder=folder_for(payload['job'])
    require(m['status']=='complete' and m['result_sha256']==payload['result_sha256'] and m['sampled_runtime_conditions_pass'] is True,'Select a completed playback-verified candidate')
    imported=characters.import_bytes((folder/'transfer/character.glb').read_bytes(),'Transferred candidate.glb')
    profile=read(folder/'edit-profile.json');require(profile['character_sha256']==imported['id'],'Candidate edit profile belongs to another asset')
    saved=characters.save_profile(dict(asset_id=imported['id'],profile=profile))
    return dict(asset_id=imported['id'],profile_id=saved['profile_id'],source_job=payload['job'],quality_approved=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path);run(parser.parse_args().folder)
