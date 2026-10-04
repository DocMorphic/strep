"""Portable original clips, bounds and contact intent for selected corrections.

Provenance transport only. A parent's numerical decisions never approve a new
scene, anatomy, animation quality or gameplay. No solver or engine is invoked.
"""
import copy
from pathlib import Path, PurePosixPath
import re
import shutil
from strep import read,save,sha256

PREFIX='/files/native-scene-fit-jobs/'
NAME=re.compile(r'[A-Za-z0-9_-]{1,100}')


def require(ok,message):
    if not ok:raise ValueError(message)


def origin(url):
    if not isinstance(url,str) or not url.startswith(PREFIX):return None
    parts=url[len(PREFIX):].split('/')
    require(len(parts)>=2 and NAME.fullmatch(parts[0]) and all(p and p not in ('.','..') for p in parts)
        and not any(c in url for c in ('?','#','\\','%')), 'Contained correction source URL required')
    return parts[0]


def has_origins(draft):
    return any(origin(a['glb']) is not None for a in draft['scene']['actors'].values())


def plan(draft):
    from studio_native_scene_fit import folder_for,manifest
    selection={};queue=[];jobs={};artifacts={};bindings={}
    def load(job):
        folder=folder_for(job);m=manifest(job)
        require(m['status']=='complete','Completed correction source required')
        return folder,m
    def bound(path):
        path=Path(path).resolve();bindings[str(path)]=sha256(path);return path
    def material(name,path,digest):
        path=bound(path);require(bindings[str(path)]==digest,'Correction lineage source changed')
        artifacts[name]=('file',path,digest)
    def json_file(name,value):artifacts[name]=('json',copy.deepcopy(value),None)
    for actor,entry in sorted(draft['scene']['actors'].items()):
        job=origin(entry['glb'])
        if job is None:continue
        folder,m=load(job);matches=[]
        for name,row in m['actors'].items():
            if entry['glb']==row['candidate_url']:
                matches.append((name,'proposal' if row['correction_requested'] else 'unchanged',row['candidate_sha256']))
            elif entry['glb']==row['original_url']:matches.append((name,'original',row['original_sha256']))
        require(len(matches)==1 and matches[0][2]==entry['sha256'],'Selected correction actor receipt changed')
        name,role,digest=matches[0]
        selection[actor]=dict(job=job,correction_actor=name,selected_role=role,selected_sha256=digest)
        queue.append(job)
    require(selection,'No correction sources in this scene')
    while queue:
        job=queue.pop(0)
        if job in jobs:continue
        require(len(jobs)<16,'Correction lineage exceeds 16 jobs; no ancestor truncation')
        folder,m=load(job);p=read(bound(folder/'prepared.json'));r=read(bound(folder/'fit/result.json'))
        bound(folder/'completion.json');request=read(bound(folder/'draft.json'))
        base=f'jobs/{job}';original=read(bound(folder/'fit/contacts.json'));candidate=read(bound(folder/'fit/proposal/contacts.json'))
        for index,(name,s) in enumerate(p['sources'].items()):
            src=f'source/actor-{index}.glb';out=f'candidate/actor-{index}.glb'
            material(base+'/'+src,folder/s['snapshot'],s['sha256'])
            row=m['actors'][name];relative=row['candidate_url'].removeprefix(PREFIX+job+'/')
            material(base+'/'+out,folder/relative,row['candidate_sha256'])
            original['actors'][name]['glb']=src;candidate['actors'][name]['glb']=out
        json_file(base+'/original-scene.json',original);json_file(base+'/candidate-scene.json',candidate)
        permissions=read(bound(folder/'permissions.json'));geometry=read(bound(folder/'geometry-policy.json'))
        # The new portable JSON hashes are filled after serialization. All other
        # bounds, timing, geometry and permissions remain exactly authored.
        json_file(base+'/permissions.json',permissions);json_file(base+'/geometry-policy.json',geometry)
        material(base+'/source-rate-caps.npz',folder/'fit/source-rate-caps.npz',r['source_rate_caps_sha256'])
        prior_intents=[]
        for spec_name,audit_name in (('original-intent-proposal.json','original-intent-audit/result.json'),
            ('fit/original-contact-intent.json','fit/original-contact-audit/result.json')):
            if (folder/spec_name).is_file():
                before=read(bound(folder/spec_name));audit=read(bound(folder/audit_name))
                before['actors']=copy.deepcopy(candidate['actors'])
                file=f'prior-intent-{len(prior_intents)}-candidate-scene.json';json_file(base+'/'+file,before)
                prior_intents.append(dict(scene_file=file,measured_pass=audit['passed'],audit_sha256=sha256(folder/audit_name)))
        expected=copy.deepcopy(request['draft']);expected.pop('contact_revision',None)
        for name,row in m['actors'].items():
            expected['scene']['actors'][name]['glb']=row['candidate_url'];expected['scene']['actors'][name]['sha256']=row['candidate_sha256']
        final=next(v for v in r['probes'] if v['label']=='final')
        jobs[job]=dict(prepared_sha256=sha256(folder/'prepared.json'),completion_sha256=sha256(folder/'completion.json'),
            fit_result_sha256=sha256(folder/'fit/result.json'),authoring_request_sha256=sha256(folder/'draft.json'),
            resume_from=p['resume_from'],options=p['options'],controls=final['controls'],
            native_conditions_pass=m['native_conditions_pass'],sampled_geometry_conditions_pass=m['geometry_conditions_pass'],
            source_rate_tolerance=r['source_rate_tolerance'],source_rate_bins=r['source_rate_bins'],
            original_scene='original-scene.json',candidate_scene='candidate-scene.json',permissions='permissions.json',
            geometry_policy='geometry-policy.json',source_rate_caps='source-rate-caps.npz',prior_intents=prior_intents,
            correction_scene_context_preserved=draft==expected,quality_approved=False,training_admitted=False,release_approved=False)
        if p['resume_from'] is not None:queue.append(p['resume_from'])
        for a in request['draft']['scene']['actors'].values():
            ancestor=origin(a['glb'])
            if ancestor is not None:queue.append(ancestor)
    require(len(artifacts)<=128,'Correction lineage exceeds 128 complete files; no population truncation')
    require(sum(v[1].stat().st_size for v in artifacts.values() if v[0]=='file')<=768*1024**2,
        'Correction lineage exceeds 768 MiB material budget; no partial snapshot')
    record=dict(schema='strep-native-correction-lineage-v1',selection=selection,jobs=jobs,
        original_sources_included=True,original_motion_caps_included=True,correction_intent_included=True,
        numerical_decisions_apply_to_parent_job_only=True,quality_approved=False,training_admitted=False,release_approved=False)
    return record,artifacts,bindings


def snapshot(draft,folder):
    folder=Path(folder).resolve();require(not folder.exists(),'Fresh correction lineage snapshot required')
    record,artifacts,bindings=plan(draft);folder.mkdir(parents=True)
    for name,(kind,value,digest) in artifacts.items():
        target=folder/name;target.parent.mkdir(parents=True,exist_ok=True)
        if kind=='file':shutil.copyfile(value,target);require(sha256(target)==digest,'Correction lineage snapshot differs')
        else:save(target,value)
    for job in record['jobs']:
        base=folder/'jobs'/job;digest=sha256(base/'original-scene.json')
        for name in ('permissions.json','geometry-policy.json'):
            value=read(base/name);value['contacts_sha256']=digest;save(base/name,value)
    record['files_sha256']={n:sha256(folder/n) for n in sorted(artifacts)};save(folder/'record.json',record)
    receipt=dict(schema='strep-native-correction-lineage-snapshot-v1',record_sha256=sha256(folder/'record.json'),
        files_sha256=record['files_sha256'],source_bindings_sha256=bindings)
    verify(draft,folder,receipt);return receipt


def verify(draft,folder,receipt):
    folder=Path(folder).resolve()
    require(receipt['schema']=='strep-native-correction-lineage-snapshot-v1'
        and sha256(folder/'record.json')==receipt['record_sha256'],'Correction lineage record changed')
    expected,artifacts,bindings=plan(draft);actual=read(folder/'record.json')
    require(receipt['source_bindings_sha256']==bindings and set(receipt['files_sha256'])==set(artifacts),
        'Correction lineage binding or artifact population changed')
    require(actual==dict(expected,files_sha256=receipt['files_sha256']),'Correction lineage intent or decisions changed')
    require({p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}==set(artifacts)|{'record.json'},
        'Complete contained correction lineage files required')
    for name,(kind,value,digest) in artifacts.items():
        target=(folder/name).resolve();require(target.is_relative_to(folder) and sha256(target)==receipt['files_sha256'][name],
            'Correction lineage artifact changed')
        if kind=='file':require(sha256(target)==digest,'Correction lineage original bytes differ')
        else:
            expected_value=copy.deepcopy(value)
            if PurePosixPath(name).name in ('permissions.json','geometry-policy.json'):
                expected_value['contacts_sha256']=sha256(target.parent/'original-scene.json')
            require(read(target)==expected_value,'Correction lineage authored fields changed')
    return actual


def package_files(folder,receipt):
    folder=Path(folder)
    return {'corrections/record.json':folder/'record.json',
        **{'corrections/'+n:folder/n for n in receipt['files_sha256']}}
