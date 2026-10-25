"""Completed ground-contact clips as explicit scene sources with portable history.

Publication transport, not fresh solver/engine or motion-quality acceptance.
The original, authored limits and recorded parent decisions travel with scenes.
"""
import copy
import math
from pathlib import Path
import re
import shutil
import studio_surface_clip_jobs as jobs
from strep import read, save, sha256

PREFIX='/files/surface-clip-jobs/'
METHODS=('surface_clip_scene_source.py','studio_surface_clip_jobs.py','surface_clip_job.py','strep.py')
require=jobs.require


def origin(url):
    if not isinstance(url,str) or not url.startswith(PREFIX):return None
    match=re.fullmatch(r'/files/surface-clip-jobs/([a-f0-9]{32})/([a-f0-9]{32})/candidate\.glb',url)
    require(match is not None,'Choose a completed ground-contact candidate, not a partial or rejected version')
    return match[1],match[2]


def metadata(job,attempt):
    folder=jobs.folder_for(job);request=jobs.request_for(folder);result=jobs.publication(folder,attempt)
    r=result['summary'];count=r.get('total_keys')
    require(r.get('status')=='complete_numerical_candidate' and r.get('whole_clip_sampled') is True
        and type(count) is int and count>=2
        and all(type(r.get(k)) is int and r[k]==count-1 for k in ('validated_through','finalized_through'))
        and r.get('transition_review_required') is True and r.get('quality_approved') is False and r.get('release_approved') is False
        and 'candidate' in result['files'],'Only a completed whole-clip candidate can enter scene authoring')
    duration=result['duration_s'];require(type(duration) in (int,float) and math.isfinite(duration) and duration>0,'Positive finite clip duration required')
    require(result['files']['original']['sha256']==request['source_sha256'],'Correction original no longer matches its request')
    return dict(schema='strep-surface-clip-scene-source-v1',job=job,attempt=attempt,
        source_url=f'{PREFIX}{job}/{attempt}/candidate.glb',glb_sha256=result['files']['candidate']['sha256'],
        result_sha256=sha256(folder/'attempts'/attempt/'result.json'),request_sha256=sha256(folder/'request.json'),
        label='Ground-contact candidate '+job[:8],animation_index=0,duration_s=duration,root_node=request['root'],
        start_policy=request.get('start_policy','preserve'),end_policy=request['end_policy'],
        authored_contacts=len(request['contacts']),transition_review_required=True,scene_contacts_applied=False,
        original_selected=True,quality_approved=False,release_approved=False)


def selected(entry):
    identity=origin(entry['glb'])
    if identity is None:return None
    m=metadata(*identity)
    require(entry['sha256']==m['glb_sha256'] and type(entry['animation_index']) is int and entry['animation_index']==0,
        'Scene must bind the exact completed correction and animation')
    return m


def has_origins(draft):return any(origin(a['glb']) is not None for a in draft['scene']['actors'].values())


def plan(draft):
    selection={};artifacts={};bindings={};parents={}
    for actor,entry in sorted(draft['scene']['actors'].items()):
        m=selected(entry)
        if m is None:continue
        key=m['job']+'/'+m['attempt'];selection[actor]=copy.deepcopy(m)
        if key in parents:continue
        folder=jobs.folder_for(m['job']);attempt=folder/'attempts'/m['attempt'];result=jobs.publication(folder,m['attempt'])
        files={'original.glb':jobs.local(folder,result['files']['original']['path']),
            'candidate.glb':jobs.local(folder,result['files']['candidate']['path']),
            'request.json':folder/'request.json','prepared.json':folder/'prepared.json',
            'result.json':attempt/'result.json','publication.json':attempt/'publication.json',
            'guard-result.json':attempt/'guard/pipeline.json','resource-replay.json':attempt/'resource-replay.json'}
        for name,path in files.items():
            digest=sha256(path);bindings[str(path)]=digest;artifacts['jobs/'+key+'/'+name]=(path,digest)
        parents[key]=dict(original='jobs/'+key+'/original.glb',candidate='jobs/'+key+'/candidate.glb',
            request='jobs/'+key+'/request.json',result='jobs/'+key+'/result.json',summary=copy.deepcopy(result['summary']))
    require(selection and len(selection)<=8,'Choose 1-8 completed correction actors')
    require(sum(path.stat().st_size for path,_ in artifacts.values())<=768*1024**2,'Complete correction history exceeds 768 MiB; no partial snapshot')
    record=dict(schema='strep-surface-clip-scene-lineage-v1',selection=selection,parents=parents,
        files_sha256={name:digest for name,(_,digest) in artifacts.items()},original_clips_included=True,authored_limits_and_targets_included=True,
        parent_decisions_only=True,scene_contacts_applied=False,transition_review_required=True,quality_approved=False,release_approved=False)
    return record,artifacts,bindings


def snapshot(draft,folder):
    folder=Path(folder).resolve();require(not folder.exists(),'Fresh ground-contact history required')
    record,artifacts,bindings=plan(draft);folder.mkdir(parents=True)
    for name,(path,digest) in artifacts.items():
        dest=folder/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
        require(sha256(dest)==digest,'Ground-contact history changed during snapshot')
    save(folder/'record.json',record)
    receipt=dict(record_sha256=sha256(folder/'record.json'),files_sha256=record['files_sha256'],source_bindings_sha256=bindings)
    verify(draft,folder,receipt);return receipt


def verify(draft,folder,receipt):
    folder=Path(folder).resolve();record,artifacts,bindings=plan(draft)
    require(set(receipt)=={'record_sha256','files_sha256','source_bindings_sha256'} and receipt['source_bindings_sha256']==bindings
        and receipt['files_sha256']==record['files_sha256'],'Ground-contact history bindings changed')
    require(sha256(folder/'record.json')==receipt['record_sha256'] and read(folder/'record.json')==record,'Ground-contact history decisions changed')
    require({p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}==set(artifacts)|{'record.json'},'Complete ground-contact history required')
    for name,(path,digest) in artifacts.items():
        target=(folder/name).resolve();require(target.is_relative_to(folder) and sha256(target)==sha256(path)==digest,'Ground-contact history artifact changed')
    return record


def package_files(folder,receipt):
    folder=Path(folder)
    return {'surface-corrections/'+name:folder/name for name in ['record.json',*receipt['files_sha256']]}
