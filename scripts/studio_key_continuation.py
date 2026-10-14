"""Registered local key corrections: guarded build, continuation and full replay."""
import argparse
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from strep import ROOT,read,save,sha256,now,offline_environment

NAMESPACE='key-continuation-jobs'
REGISTRY='key-continuation-sources'
ID=re.compile(r'[a-f0-9]{64}')
JOB=re.compile(r'[A-Za-z0-9_-]{1,100}')
METHODS=('studio_key_continuation.py','frozen_key_continuation.py','run_guarded_job.py','audit_guarded_job.py','strep.py')
FLAGS=dict(original_selected=True,quality_approved=False,release_approved=False)


def require(condition,message):
    if not condition:raise ValueError(message)


def bounded_read(path):
    require(Path(path).stat().st_size<=64*1024**2,'Bounded correction metadata required')
    return read(path)


def contained(path):
    path=Path(path).resolve();require(path.is_relative_to((ROOT/'reports').resolve()),'Correction source escapes reports');return path


def folder_for(job):
    require(isinstance(job,str) and JOB.fullmatch(job),'Invalid continuation job')
    folder=contained(ROOT/'reports'/NAMESPACE/job)
    require(folder.parent==(ROOT/'reports'/NAMESPACE).resolve(),'Invalid continuation folder');return folder


def source(source_id):
    require(isinstance(source_id,str) and ID.fullmatch(source_id),'Select a registered verified source')
    registry=ROOT/'reports'/REGISTRY/(source_id+'.json');value=bounded_read(registry)
    require(sha256(registry)==source_id and value['schema']=='strep-studio-key-continuation-source-v1','Registered source binding changed')
    parent=contained(value['producer']);proof=contained(value['replay'])
    require(all(sha256(p)==h for p,h in value['bindings'].items()),'Registered source changed; do not silently register replacement bytes')
    result=bounded_read(parent/'result.json');request=bounded_read(parent/'request.json');replay=bounded_read(proof)
    require(result['schema']==request['schema']=='strep-native-key-interval-restoration-v1' and result['status']=='complete'
        and result['source_request_sha256']==sha256(parent/'request.json'),'Completed standard restoration required')
    require(replay['schema']=='strep-native-key-restoration-replay-v1' and replay['status']=='complete'
        and replay['producer_result_sha256']==sha256(parent/'result.json') and replay['producer_request_sha256']==sha256(parent/'request.json')
        and replay['retention_history_replayed'] is True and replay['optimizer_executed'] is False,'Matching complete numerical replay required')
    require([r['label'] for r in replay['cases']]==[r['label'] for r in result['probes']]
        and all(r['exact_bytes_and_complete_observations'] is True for r in replay['cases']),'Complete source replay required')
    for v in (result,request,replay):require(all(v[k] is expected for k,expected in FLAGS.items()),'Source approval/scope changed')
    for k in ('sampled_conditions_pass','original_rate_failures','floor_failures'):require(result[k]==replay[k],'Source replay summary changed')
    final=result['probes'][-1];require(final['label']=='final' and sha256(parent/'probes/final/character.glb')==final['glb_sha256'],'Source clip changed')
    return value,result,request


def register(producer,result_digest,request_digest,replay,replay_digest,label):
    producer,replay=contained(producer),contained(replay)
    require(isinstance(label,str) and 0<len(label.strip())<=120,'Short source label required')
    bindings={str(producer/'result.json'):result_digest,str(producer/'request.json'):request_digest,str(replay):replay_digest}
    require(all(isinstance(h,str) and ID.fullmatch(h) and sha256(p)==h for p,h in bindings.items()),'Trusted source digests changed')
    value=dict(schema='strep-studio-key-continuation-source-v1',producer=str(producer),replay=str(replay),label=label.strip(),bindings=bindings)
    import hashlib,json
    raw=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode();key=hashlib.sha256(raw).hexdigest()
    path=ROOT/'reports'/REGISTRY/(key+'.json');path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():require(path.read_bytes()==raw,'Existing registry entry changed')
    else:path.write_bytes(raw)
    try:source(key)
    except BaseException:
        # An invalid registration is retained but never appears as usable.
        raise
    return key


def catalog():
    entries=[]
    for path in sorted((ROOT/'reports'/REGISTRY).glob('*.json'))[:256]:
        try:
            value,result,request=source(path.stem)
            entries.append(dict(id=path.stem,label=value['label'],controls=request['controls'],
                rate_failures=result['original_rate_failures'],floor_failures=result['floor_failures']))
        except (ValueError,KeyError,TypeError,OSError):continue
    return dict(schema='strep-studio-key-continuation-catalog-v1',sources=entries,**FLAGS)


def prepare(payload,folder):
    require(isinstance(payload,dict) and set(payload)=={'schema','source_id','iterations'},'Explicit continuation request required')
    require(payload['schema']=='strep-studio-key-continuation-v1' and type(payload['iterations']) is int and 1<=payload['iterations']<=4,'Choose 1-4 continuation iterations')
    value,result,request=source(payload['source_id']);folder=Path(folder).resolve()
    require(folder==folder_for(folder.name) and not folder.exists(),'Fresh continuation job required')
    folder.mkdir(parents=True);parent=Path(value['producer']);saved=folder/'input/saved-start.glb';saved.parent.mkdir()
    shutil.copyfile(parent/'probes/final/character.glb',saved)
    require(sha256(saved)==result['probes'][-1]['glb_sha256'],'Saved-start snapshot changed')
    recipe=dict(schema='strep-native-key-continuation-job-v1',parent=dict(path=value['producer'],
        result_sha256=value['bindings'][str(parent/'result.json')],request_sha256=value['bindings'][str(parent/'request.json')],
        replay=value['replay'],replay_sha256=value['bindings'][value['replay']]),iterations=payload['iterations'],trust=.02,difference_step=.001,backoffs=8,maximum_seconds=650)
    save(folder/'request.json',payload);save(folder/'recipe.json',recipe)
    methods={n:sha256(ROOT/'scripts'/n) for n in METHODS};archive=folder/'implementation';archive.mkdir()
    for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
    p=dict(schema='strep-studio-key-continuation-prepared-v1',source_registry_sha256=payload['source_id'],
        source_bindings=value['bindings'],request_sha256=sha256(folder/'request.json'),recipe_sha256=sha256(folder/'recipe.json'),
        saved_start_sha256=sha256(saved),methods_sha256=methods,**FLAGS)
    save(folder/'prepared.json',p);save(folder/'pipeline.json',dict(status='starting',stage='runtime',**FLAGS));return p


def frozen(folder):
    p=read(folder/'prepared.json')
    require(p['schema']=='strep-studio-key-continuation-prepared-v1' and all(p[k] is v for k,v in FLAGS.items()),'Prepared continuation scope changed')
    require(sha256(folder/'request.json')==p['request_sha256'] and sha256(folder/'recipe.json')==p['recipe_sha256']
        and sha256(folder/'input/saved-start.glb')==p['saved_start_sha256'],'Prepared request or snapshot changed')
    source(p['source_registry_sha256'])
    require(all(sha256(path)==h for path,h in p['source_bindings'].items()),'Prepared source changed')
    require(set(p['methods_sha256'])==set(METHODS) and all(sha256(ROOT/'scripts'/n)==h==sha256(folder/'implementation'/n) for n,h in p['methods_sha256'].items()),'Prepared worker methods changed')
    return p


def guarded(folder,stage,args):
    uv=shutil.which('uv');require(uv is not None,'Offline uv runtime must be prepared before correction')
    guard=folder/(stage+'-guard');prefix=[uv,'run','--offline','--isolated','--no-project','--python','3.10','--with-requirements',str(ROOT/'requirements-ci.txt'),'python']
    argv=prefix+[str(ROOT/'scripts/run_guarded_job.py'),'--worker',str(ROOT/'scripts/frozen_key_continuation.py'),
        '--output',str(guard),'--expected-rss-mib','2048','--stable-seconds','15','--admission-seconds','600','--max-seconds','900','--',*map(str,args)]
    with (folder/(stage+'-supervisor.log')).open('x',encoding='utf-8') as log:
        result=subprocess.run(argv,cwd=ROOT,env=offline_environment(),stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    state=read(guard/'pipeline.json');proof=folder/(stage+'-resource-replay.json')
    # Replay terminal failures/deferrals as well; preserve their exact evidence.
    replay=subprocess.run(prefix+[str(ROOT/'scripts/audit_guarded_job.py'),str(guard),'--output',str(proof)],cwd=ROOT,
        env=offline_environment(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    require(replay.returncode==0 and read(proof)['status']==state['status'],'Resource trace did not replay')
    if state['status']!='complete':return state['status']
    require(result.returncode==0,'Guard process failed despite complete receipt');return 'complete'


def run(folder):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name),'Registered continuation folder required')
    prepared=frozen(folder);state=read(folder/'pipeline.json');require(state['status']=='starting','Continuation job cannot be restarted or overwritten')
    save(folder/'worker.json',dict(pid=os.getpid(),created_at=__import__('psutil').Process(os.getpid()).create_time(),prepared_sha256=sha256(folder/'prepared.json')))
    try:
        runtime=folder/'runtime';runtime_digest=None
        for stage,args in [('runtime',['build',folder/'recipe.json',runtime]),('correction',None),('replay',None)]:
            frozen(folder)
            if stage=='correction':
                runtime_digest=sha256(runtime/'runtime.json');save(folder/'runtime-binding.json',dict(sha256=runtime_digest))
                args=['run',runtime,folder/'study','--expected-runtime-sha256',runtime_digest]
            if stage=='replay':
                require(sha256(runtime/'runtime.json')==runtime_digest,'Bound runtime changed')
                args=['audit',runtime,folder/'study',folder/'replay','--expected-runtime-sha256',runtime_digest,
                    '--expected-result-sha256',sha256(folder/'study/result.json'),'--expected-request-sha256',sha256(folder/'study/request.json')]
            save(folder/'pipeline.json',dict(status='processing',stage=stage,**FLAGS));status=guarded(folder,stage,args)
            if status!='complete':
                save(folder/'pipeline.json',dict(status=status,stage=stage,**FLAGS));return
        result=read(folder/'study/result.json');proof=read(folder/'replay/result.json');frozen(folder)
        require(result['schema']=='strep-native-key-continuation-job-v1' and result['status']=='complete'
            and proof['schema']=='strep-native-key-continuation-job-replay-v1' and proof['original_reference_unchanged'] is True,'Explicit complete original-reference continuation required')
        for value in (result,proof):require(all(value[k] is v for k,v in FLAGS.items()),'Continuation cannot inherit approval')
        require(result['training_admitted'] is False and result['all_original_caps_preserved'] is True
            and all(proof[k]==result[k] for k in ('original_rate_failures','floor_failures','sampled_conditions_pass')),'Original cap/decision replay required')
        require(proof['producer_result_sha256']==sha256(folder/'study/result.json') and proof['producer_request_sha256']==sha256(folder/'study/request.json')
            and proof['status']=='complete' and proof['retention_history_replayed'] is True and proof['optimizer_executed'] is False,'Complete bound correction replay required')
        require([c['label'] for c in proof['cases']]==[c['label'] for c in result['probes']]
            and all(c['exact_bytes_and_complete_observations'] is True for c in proof['cases']),'Complete returned-export replay required')
        paths=['study/result.json','study/request.json','study/probes/final/character.glb','replay/result.json','runtime/runtime.json','runtime-binding.json']
        for stage in ('runtime','correction','replay'):paths.extend([stage+'-guard/pipeline.json',stage+'-resource-replay.json'])
        save(folder/'completion.json',dict(schema='strep-studio-key-continuation-completion-v1',prepared_sha256=sha256(folder/'prepared.json'),
            artifacts={n:sha256(folder/n) for n in paths},rate_failures=result['original_rate_failures'],floor_failures=result['floor_failures'],
            sampled_conditions_pass=result['sampled_conditions_pass'],full_replay_pass=True,**FLAGS))
        save(folder/'pipeline.json',dict(status='complete',stage='review',**FLAGS))
    except BaseException as error:
        save(folder/'pipeline.json',dict(status='failed',stage=read(folder/'pipeline.json').get('stage'),error=str(error),**FLAGS));raise


def observed(folder):
    state=read(folder/'pipeline.json')
    if state['status'] in ('complete','failed','deferred','cancelled'):return state
    try:
        import psutil
        r=read(folder/('worker.json' if (folder/'worker.json').exists() else 'launch.json'));require(r['prepared_sha256']==sha256(folder/'prepared.json'),'Worker request changed')
        require(type(r['pid']) is int and r['pid']>0 and type(r['created_at']) in (int,float) and math.isfinite(r['created_at']),'Worker identity required')
        p=psutil.Process(r['pid'])
        if p.create_time()!=r['created_at'] or not p.is_running() or p.status()==psutil.STATUS_ZOMBIE:return dict(state,status='failed',error='Continuation worker ended before completion')
    except (OSError,ValueError,KeyError,TypeError):return dict(state,status='unknown',error='Continuation worker cannot be verified')
    except psutil.NoSuchProcess:return dict(state,status='failed',error='Continuation worker ended before completion')
    except psutil.AccessDenied:return dict(state,status='unknown',error='Continuation worker cannot be verified')
    guard=folder/(str(state.get('stage'))+'-guard/pipeline.json')
    if state['status']=='processing' and guard.exists():
        try:
            if read(guard)['status']=='waiting_resources':return dict(state,status='waiting_resources')
        except (OSError,ValueError,KeyError,TypeError):pass
    return state


def running():
    # A direct CLI driver may still be waiting for admission outside this server.
    # Unknown identities remain occupied until they can be verified.
    for folder in (ROOT/'reports'/NAMESPACE).glob('*'):
        if not folder.is_dir() or not JOB.fullmatch(folder.name):continue
        try:
            if observed(folder)['status'] not in ('complete','failed','deferred','cancelled'):return True
        except (OSError,ValueError,KeyError,TypeError):continue
    return False


def manifest(job):
    folder=folder_for(job);state=observed(folder);p=read(folder/'prepared.json');result=dict(schema='strep-studio-key-continuation-review-v1',id=job,
        status=state['status'],stage=state.get('stage'),error=state.get('error'),source_id=p['source_registry_sha256'],downloads=[],**FLAGS)
    if state['status']!='complete':return result
    c=read(folder/'completion.json');expected={'study/result.json','study/request.json','study/probes/final/character.glb','replay/result.json','runtime/runtime.json','runtime-binding.json'}
    for stage in ('runtime','correction','replay'):expected.update([stage+'-guard/pipeline.json',stage+'-resource-replay.json'])
    require(c['schema']=='strep-studio-key-continuation-completion-v1' and c['prepared_sha256']==sha256(folder/'prepared.json')
        and c['full_replay_pass'] is True and all(c[k] is v for k,v in FLAGS.items()) and set(c['artifacts'])==expected
        and all(sha256(folder/n)==h for n,h in c['artifacts'].items()) and sha256(folder/'input/saved-start.glb')==p['saved_start_sha256'],
        'Completed correction artifacts changed')
    result.update(**{k:c[k] for k in ('rate_failures','floor_failures','sampled_conditions_pass','full_replay_pass')})
    for n,label in [('input/saved-start.glb','Saved starting clip'),('study/probes/final/character.glb','Returned proposal'),('study/result.json','Correction results'),('replay/result.json','Full replay receipt')]:
        result['downloads'].append(dict(label=label,url=f'/files/{NAMESPACE}/{job}/{n}',sha256=sha256(folder/n)))
    return result


def listing():
    jobs=[]
    for folder in sorted((ROOT/'reports'/NAMESPACE).glob('*'))[-256:]:
        if not folder.is_dir() or not JOB.fullmatch(folder.name):continue
        try:jobs.append(manifest(folder.name))
        except (OSError,ValueError,KeyError,TypeError):continue
    return dict(jobs=jobs)


def served_file(relative):
    parts=relative.split('/')
    if len(parts)<3 or parts[0]!=NAMESPACE:return None
    try:
        m=manifest(parts[1]);download=next((d for d in m['downloads'] if d['url']=='/files/'+relative),None)
        if download is None:return None
        path=folder_for(parts[1])/('/'.join(parts[2:]));require(sha256(path)==download['sha256'],'Downloaded correction changed');return path
    except (OSError,ValueError,KeyError,TypeError):return None


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path);a=parser.parse_args();run(a.folder)
