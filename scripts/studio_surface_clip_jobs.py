"""Studio ground-contact jobs: lightweight queue, guarded work, verified artifacts."""
import argparse
from contextlib import contextmanager
import copy
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid
from strep import ROOT, read, save, sha256, offline_environment
from surface_clip_job import require, boundary_policy

NAMESPACE = 'surface-clip-jobs'


def folder_for(identifier):
    require(type(identifier) is str and re.fullmatch('[a-f0-9]{32}', identifier), 'Choose a saved ground-contact job')
    base = (ROOT/'reports'/NAMESPACE).resolve(); path = (base/identifier).resolve()
    require(base.is_relative_to(ROOT.resolve()) and path.parent == base, 'Job escapes its store')
    return path


def local(folder, name):
    from surface_clip_job import artifact
    return artifact(folder.resolve(), name)


def validate(p):
    fields = {'schema','source_job','variant','source_sha256','root','rotations','angles_degrees','contacts','limits',
              'end_policy','acknowledge_changed_end','maximum_windows','soft_seconds'}
    require(isinstance(p,dict),'Explicit ground-contact request required')
    if p.get('schema')=='strep-studio-surface-clip-v2':fields|={'start_policy','acknowledge_changed_start'}
    require(set(p)==fields and p['schema'] in ('strep-studio-surface-clip-v1','strep-studio-surface-clip-v2'), 'Explicit ground-contact request required')
    require(type(p['source_job']) is str and re.fullmatch('[A-Za-z0-9_-]{1,100}',p['source_job'])
            and p['variant'] in ('input','transfer','corrected','native_review'), 'Choose a saved character clip')
    require(type(p['source_sha256']) is str and re.fullmatch('[a-f0-9]{64}',p['source_sha256']), 'Exact selected clip required')
    integer = lambda v: type(v) is int and v>=0
    number = lambda v: type(v) in (int,float) and math.isfinite(v)
    require(integer(p['root']) and isinstance(p['rotations'],list) and 1<=len(p['rotations'])<=20
            and all(integer(n) for n in p['rotations']) and len(set(p['rotations']))==len(p['rotations']), 'Choose 1-20 distinct rotation joints')
    require(isinstance(p['angles_degrees'],list) and len(p['angles_degrees'])==len(p['rotations'])
            and all(number(v) and 0<v<=180 for v in p['angles_degrees']), 'Explicit angular limits required')
    limits = {'root_horizontal_m','root_vertical_m','floor_depth_m','contact_error_m','root_step_m','rotation_step_degrees'}
    require(isinstance(p['limits'],dict) and set(p['limits'])==limits and all(number(v) and 0<v<=1e6 for v in p['limits'].values())
            and p['limits']['rotation_step_degrees']<=180, 'Complete finite correction limits required')
    require(isinstance(p['contacts'],list) and len(p['contacts'])<=128, 'At most 128 explicit static contacts supported')
    for c in p['contacts']:
        require(isinstance(c,dict) and set(c)=={'vertex','target_m','start_time_s','end_time_s'}, 'Explicit surface point and static target required')
        require(isinstance(c['vertex'],list) and len(c['vertex'])==3 and all(integer(v) for v in c['vertex']), 'Bound material vertex required')
        require(isinstance(c['target_m'],list) and len(c['target_m'])==3 and all(number(v) and abs(v)<=1e6 for v in c['target_m']), 'Three finite target coordinates required')
        require(number(c['start_time_s']) and number(c['end_time_s']) and 0<=c['start_time_s']<=c['end_time_s']<=3600, 'Ordered contact times required')
    boundary_policy(p['end_policy'],p['acknowledge_changed_end'])
    boundary_policy(p.get('start_policy','preserve'),p.get('acknowledge_changed_start',False),boundary='starting')
    require(type(p['maximum_windows']) is int and 1<=p['maximum_windows']<=20 and type(p['soft_seconds']) is int
            and p['soft_seconds'] in (120,240,600), 'Choose a bounded correction attempt')
    require(len(json.dumps(p,allow_nan=False).encode())<=1024**2, 'Request exceeds 1 MiB')
    return p


def methods(): return {p.name:sha256(p) for p in sorted(Path(__file__).parent.glob('*.py'))}


def prepare(payload):
    validate(payload);require(payload['schema']=='strep-studio-surface-clip-v2','Submit the current explicit boundary policy')
    folder=folder_for(uuid.uuid4().hex);folder.mkdir(parents=True)
    save(folder/'request.json',payload)
    save(folder/'prepared.json',dict(request_sha256=sha256(folder/'request.json'),methods=methods()))
    return folder


def request_for(folder, *, execution=False):
    require(folder.resolve()==folder_for(folder.name), 'Exact saved ground-contact job required')
    receipt=read(folder/'prepared.json')
    require(sha256(folder/'request.json')==receipt['request_sha256'], 'Saved request changed')
    p=validate(read(folder/'request.json'))
    if execution:
        require(p['schema']=='strep-studio-surface-clip-v2','Submit the current explicit boundary policy')
        require(methods()==receipt['methods'],'Implementation changed; submit a fresh ground-contact job')
    return p


@contextmanager
def queue_lock(folder, *, wait=False):
    from action_worker_lock import _lock
    with (folder/'queue.lock').open('a+b') as f:
        if f.seek(0,2)==0:f.write(b'0');f.flush()
        deadline=time.monotonic()+(5 if wait else 0)
        while True:
            try:_lock(f,True);break
            except OSError as error:
                if time.monotonic()>=deadline:raise ValueError('This correction is still running') from error
                time.sleep(.05)
        try:yield
        finally:_lock(f,False)


def alive(attempt):
    import psutil
    if not (attempt/'owner.json').exists():return False
    owner=read(attempt/'owner.json')
    try:
        p=psutil.Process(owner['pid'])
        return p.create_time()==owner['created_at'] and p.is_running() and p.status()!=psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:return False
    except psutil.AccessDenied as error:raise ValueError('Cannot verify whether the previous worker has stopped') from error


def core_folder(folder):
    pointer=read(folder/'core.json');core=local(folder,pointer['path'])
    require(pointer['studio_request_sha256']==sha256(folder/'request.json'),'Core belongs to another Studio request')
    require(sha256(core/'request.json')==pointer['request_sha256'],'Core request changed')
    return core


def publication(folder, attempt_id):
    require(type(attempt_id) is str and re.fullmatch('[a-f0-9]{32}',attempt_id),'Exact attempt required')
    attempt=folder/'attempts'/attempt_id;p=read(attempt/'publication.json')
    require(sha256(attempt/'result.json')==p['result_sha256'],'Published correction result changed')
    require(sha256(attempt/'guard/pipeline.json')==p['pipeline_sha256'] and sha256(attempt/'resource-replay.json')==p['replay_sha256'],'Published resource evidence changed')
    require(read(attempt/'guard/pipeline.json')['status']=='complete','Worker did not complete its guarded checks')
    replay=read(attempt/'resource-replay.json')
    require(replay['all_archived_bindings_match'] is True and replay['status']=='complete'
            and replay['pipeline_sha256']==p['pipeline_sha256'],'Resource replay failed')
    result=read(attempt/'result.json')
    require(result['request_sha256']==sha256(folder/'request.json'),'Result belongs to another request')
    require(result['quality_approved'] is False and result['release_approved'] is False and result['original_selected'] is True
            and 'original' in result['files'] and set(result['files'])<={'original','candidate','rejected'},'Invalid correction publication')
    for entry in result['files'].values():require(sha256(local(folder,entry['path']))==entry['sha256'],'Published correction artifact changed')
    return result


def review(identifier):
    folder=folder_for(identifier);p=request_for(folder)
    active=read(folder/'active.json') if (folder/'active.json').exists() else None
    core=core_folder(folder) if (folder/'core.json').exists() else None
    state_path=core/'state.json' if core else None
    state_hash=sha256(state_path) if state_path and state_path.exists() else None
    value=dict(schema='strep-studio-surface-clip-status-v1',id=identifier,status='ready',can_continue=True,
               end_policy=p['end_policy'],start_policy=p.get('start_policy','preserve'),quality_approved=False,release_approved=False,original_selected=True,
               ticket=dict(request_sha256=sha256(folder/'request.json'),state_sha256=state_hash,attempt=None),downloads=[])
    if not active:return value
    attempt=local(folder,active['path']);require(attempt.parent==folder/'attempts','Invalid attempt path')
    require(sha256(attempt/'request.json')==active['sha256'],'Attempt metadata changed')
    value['ticket']['attempt']=active['sha256'];running=alive(attempt)
    pipeline=read(attempt/'guard/pipeline.json') if (attempt/'guard/pipeline.json').exists() else dict(status='starting')
    value['status']=pipeline['status']
    if (attempt/'publication.json').exists():
        result=publication(folder,attempt.name);value['result']=result['summary'];value['status']=result['summary']['status']
        value['preview_url']=f'/surface-clip-viewer.html?job={identifier}&attempt={attempt.name}'
        value['downloads']=[dict(label=e['label'],url=f'/files/surface-clip-jobs/{identifier}/{attempt.name}/{role}.glb') for role,e in result['files'].items()]
    elif not running and pipeline['status'] not in ('failed','deferred'):
        value['status']='interrupted'
    if (attempt/'failure.json').exists():value['error']=read(attempt/'failure.json')['error']
    elif pipeline.get('reason'):value['error']=pipeline['reason']
    value['can_continue']=not running and value['status'] in ('checkpointed','failed','deferred','interrupted')
    if (attempt/'failure.json').exists() and read(attempt/'failure.json').get('retryable') is False:value['can_continue']=False
    return value


def listing():
    base=ROOT/'reports'/NAMESPACE;rows=[]
    if base.exists():
        for p in sorted(base.iterdir(),key=lambda p:p.name):
            if not re.fullmatch('[a-f0-9]{32}',p.name) or not p.is_dir():continue
            try:rows.append(review(p.name))
            except (ValueError,OSError,KeyError,TypeError) as error:rows.append(dict(id=p.name,status='unavailable',error=str(error),can_continue=False))
    return dict(jobs=rows)


def launch(folder, ticket=None):
    import psutil
    with queue_lock(folder):
        request_for(folder,execution=True);current=review(folder.name)
        require(current['can_continue'],'This job cannot continue; inspect its result or submit new constraints')
        require(ticket==current['ticket'] if (folder/'active.json').exists() else ticket is None or ticket==current['ticket'],'Saved progress changed; refresh before continuing')
        attempt=folder/'attempts'/uuid.uuid4().hex;attempt.mkdir(parents=True)
        save(attempt/'request.json',dict(request_sha256=sha256(folder/'request.json'),ticket=current['ticket']))
        save(folder/'active.json',dict(path=attempt.relative_to(folder).as_posix(),sha256=sha256(attempt/'request.json')))
        process=None
        try:
            with (attempt/'supervisor.log').open('w',encoding='utf-8') as log:
                process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'supervise',folder.name,attempt.name],cwd=ROOT,
                    env=offline_environment(),stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            save(attempt/'owner.json',dict(pid=process.pid,created_at=psutil.Process(process.pid).create_time()))
            return process
        except (OSError,psutil.Error) as error:
            if process is not None and process.poll() is None:process.terminate();process.wait(timeout=5)
            save(attempt/'failure.json',dict(error=str(error)));raise


def execute(folder, attempt):
    import surface_clip_job as core_jobs
    from studio_native_support import source
    from rig_asset import RigAsset
    from native_support_clock import NativeSupportSampler
    p=request_for(folder,execution=True)
    if not (folder/'core.json').exists():
        _,_,_,report,path=source(p['source_job'],p['variant'])
        require(sha256(path)==p['source_sha256'] and report['root_node']==p['root'],'Selected source or root changed')
        rig=RigAsset.load(path);require(len(rig.document['animations'])==1,'Choose one saved animation')
        contacts=[]
        for contact in p['contacts']:
            ref=contact['vertex'];offset=0;matches=[]
            for primitive in rig.primitives:
                if [primitive['node'],primitive['primitive']]==ref[:2] and ref[2]<len(primitive['positions']):matches.append(offset+ref[2])
                offset+=len(primitive['positions'])
            require(len(matches)==1,'Surface point no longer belongs to the selected mesh')
            contacts.append({**contact,'vertex':matches[0]})
        limits=p['limits'];reserve=lambda value:min(1e-5,value/10)
        clip=dict(animation_index=0,root=p['root'],rotations=p['rotations'],angles_degrees=p['angles_degrees'],contacts=contacts,limits=limits,
            fitting=dict(root_reserve_m=reserve(min(limits['root_horizontal_m'],limits['root_vertical_m'])),
                angle_reserve_radians=reserve(math.radians(min(p['angles_degrees']))),step_reserve_m=reserve(limits['root_step_m']),
                step_reserve_radians=reserve(math.radians(limits['rotation_step_degrees'])),
                floor_reserve_m=min(.0005,limits['floor_depth_m']/10),contact_reserve_m=min(.0005,limits['contact_error_m']/10)),
            sampling=dict(dense_hz=960,initial_fractions=[.25,.5,.75],maximum_samples=100000))
        core=folder/'cores'/uuid.uuid4().hex
        core_jobs.prepare(core,path,path,clip=clip,solver=dict(epochs=4,iterations_per_epoch=60,floor_batch_size=32,maximum_new_samples_per_epoch=8),
            end_policy=p['end_policy'],acknowledge_changed_end=p['acknowledge_changed_end'],
            start_policy=p['start_policy'],acknowledge_changed_start=p['acknowledge_changed_start'])
        require(sha256(core/'source.glb')==p['source_sha256'],'Source changed during snapshot')
        save(folder/'core.json',dict(path=core.relative_to(folder).as_posix(),request_sha256=sha256(core/'request.json'),studio_request_sha256=sha256(folder/'request.json')))
    core=core_folder(folder)
    bound=core_jobs.request_for(core)
    require(bound['inputs']=={'source.glb':p['source_sha256'],'initial.glb':p['source_sha256']}
            and bound['end_policy']==p['end_policy'] and bound['start_policy']==p['start_policy']
            and bound['clip']['limits']==p['limits'],'Core source or policy differs from the selected request')
    result=core_jobs._attempt(core,maximum_windows=p['maximum_windows'],soft_seconds=p['soft_seconds'])
    rig=RigAsset.load(core/'source.glb');reader=NativeSupportSampler(rig.document,rig.binary,0)
    files={}
    def add(role,path,label):
        files[role]=dict(path=path.relative_to(folder).as_posix(),sha256=sha256(path),label=label)
    add('original',core/'initial.glb','Original clip')
    if result['state'] is not None:add('candidate',core_jobs.artifact(core,result['state']['current_clip']),'Last accepted clip')
    last=core_jobs.artifact(core,read(core/'latest-attempt.json')['path'])
    for item in last.glob('window-*/result.json'):
        if read(item)['passed'] is False:add('rejected',item.parent/'candidate.glb','Rejected candidate')
    summary={k:v for k,v in result.items() if k!='state'}
    if result['state'] is not None:summary.update(finalized_through=result['state']['finalized_through'],validated_through=result['state']['validated_through'])
    summary['total_keys']=len(reader.channels[0][2])
    request_for(folder,execution=True)
    save(attempt/'result.json',dict(request_sha256=sha256(folder/'request.json'),summary=summary,files=files,duration_s=reader.duration,
        original_selected=True,quality_approved=False,release_approved=False))


def descriptor(identifier, attempt_id):
    folder=folder_for(identifier);request_for(folder);result=publication(folder,attempt_id)
    return dict(id=identifier,attempt=attempt_id,result=result['summary'],versions=[dict(label=e['label'],kind='native_surface_correction',
        preview_url=f'/files/surface-clip-jobs/{identifier}/{attempt_id}/{role}.glb',preview_sha256=e['sha256'],
        preview_start_s=0.,preview_end_s=result['duration_s'],animation_index=0,animation_count=1) for role,e in result['files'].items()],quality_approved=False,release_approved=False)


def served_file(url):
    match=re.fullmatch(r'/files/surface-clip-jobs/([a-f0-9]{32})/([a-f0-9]{32})/(original|candidate|rejected)\.glb',url)
    require(match is not None,'Exact saved correction asset required')
    folder=folder_for(match[1]);request_for(folder);result=publication(folder,match[2])
    require(match[3] in result['files'],'No such saved correction version')
    return local(folder,result['files'][match[3]]['path'])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('supervise','worker'));parser.add_argument('job');parser.add_argument('attempt');args=parser.parse_args()
    folder=folder_for(args.job);require(re.fullmatch('[a-f0-9]{32}',args.attempt),'Exact queued attempt required');attempt=folder/'attempts'/args.attempt
    require(read(folder/'active.json')['sha256']==sha256(attempt/'request.json'),'Attempt has been superseded')
    if args.mode=='supervise':
        from run_guarded_job import run
        from resource_admission import ResourcePolicy
        from audit_guarded_job import audit
        with queue_lock(folder,wait=True):
            require(read(folder/'active.json')['sha256']==sha256(attempt/'request.json'),'Attempt has been superseded')
            p=request_for(folder,execution=True)
            result=run(Path(__file__),attempt/'guard',ResourcePolicy(expected_rss_bytes=512*1024**2,max_tree_rss_bytes=1024*1024**2,
                max_seconds=p['soft_seconds']+120,stable_seconds=10,admission_seconds=60),worker_args=['worker',args.job,args.attempt])
            replay=audit(attempt/'guard');save(attempt/'resource-replay.json',replay)
            if result['status']=='complete':
                require(replay['status']=='complete' and replay['all_archived_bindings_match'] is True,'Resource replay failed')
                save(attempt/'publication.json',dict(result_sha256=sha256(attempt/'result.json'),pipeline_sha256=sha256(attempt/'guard/pipeline.json'),replay_sha256=sha256(attempt/'resource-replay.json')))
        return {'complete':0,'deferred':2,'failed':1}[result['status']]
    from action_worker_lock import worker_lock
    try:
        with worker_lock():
            from threadpoolctl import threadpool_limits
            with threadpool_limits(limits=1):execute(folder,attempt)
    except Exception as error:
        save(attempt/'failure.json',dict(error=str(error),retryable=not isinstance(error,(ValueError,TypeError,KeyError))));raise
    return 0


if __name__=='__main__':raise SystemExit(main())
