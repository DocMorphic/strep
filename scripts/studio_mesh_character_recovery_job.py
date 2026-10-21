"""Recoverable Studio attempts; queue/status stay free of numerical imports."""
import argparse
import copy
from contextlib import contextmanager
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
import zipfile
import studio_mesh_character_job as jobs
from strep import read,save,sha256,offline_environment


def require(condition,message):
    if not condition:raise ValueError(message)


def local(folder,name):
    require(isinstance(name,str) and bool(name) and not Path(name).is_absolute(),'Relative correction artifact required')
    path=jobs.absolute(folder/name);base=jobs.absolute(folder)
    require(path!=base and path.is_relative_to(base),'Correction artifact escapes its job')
    return path


def immutable(path,value):
    if path.exists():
        require(read(path)==value,'Published correction metadata differs')
        return
    temporary=path.with_name(path.name+'.assembly-'+uuid.uuid4().hex)
    save(temporary,value);os.link(temporary,path);temporary.unlink()


def request_for(folder):
    require(jobs.absolute(folder)==jobs.folder_for(folder.name),'Exact correction job required')
    prepared=read(folder/'prepared.json')
    require(sha256(folder/'request.json')==prepared['request_sha256'],'Saved correction request changed')
    request=jobs.validate(read(folder/'request.json'))
    require(request.get('recoverable') is True,'This saved job does not support continuation')
    return request,prepared


@contextmanager
def queue_lock(folder):
    from action_worker_lock import _lock
    with (folder/'continuation.lock').open('a+b') as stream:
        if stream.seek(0,2)==0:stream.write(b'0');stream.flush()
        try:_lock(stream,True)
        except OSError as error:raise ValueError('Another continuation request is being prepared') from error
        try:yield
        finally:_lock(stream,False)


def active(folder):
    if not (folder/'active-attempt.json').exists():return None
    pointer=read(folder/'active-attempt.json');name=pointer['attempt']
    require(isinstance(name,str) and re.fullmatch('[a-f0-9]{32}',name),'Exact attempt identifier required')
    attempt=folder/'attempts'/name
    require(sha256(attempt/'request.json')==pointer['attempt_sha256'],'Attempt request changed')
    metadata=read(attempt/'request.json')
    require(metadata['request_sha256']==sha256(folder/'request.json'),'Attempt belongs to a different request')
    return attempt,metadata


def live(owner):
    import psutil
    try:
        process=psutil.Process(owner['pid'])
        return process.create_time()==owner['created_at'] and process.is_running() and process.status()!=psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:return False
    except psutil.AccessDenied as error:raise ValueError('Cannot confirm that the previous correction owner has stopped') from error


def attempt_status(attempt):
    startup=read(attempt/'startup.json') if (attempt/'startup.json').exists() else dict(status='starting')
    pipeline=read(attempt/'guard/pipeline.json') if (attempt/'guard/pipeline.json').exists() else (
        startup)
    if startup['status']=='failed' and pipeline['status']!='complete':
        pipeline={**pipeline,**startup}
    owned=False;known=False
    if (attempt/'supervisor.json').exists():
        known=True;owned=live(read(attempt/'supervisor.json'))
    if pipeline.get('worker_pid') is not None and pipeline.get('worker_created_at') is not None:
        known=True;owned |= live(dict(pid=pipeline['worker_pid'],created_at=pipeline['worker_created_at']))
    if pipeline['status'] not in ('complete','failed','deferred') and known and not owned:
        pipeline={**pipeline,'status':'failed','reason':'Correction supervisor stopped; saved progress is retained'}
    return pipeline,owned


def progress_token(folder):
    result=dict(request_sha256=sha256(folder/'request.json'),source_state_sha256=None,
        optimizer_state_sha256=None,checkpoint=None,publication_sha256=None)
    for filename,key in [('source-state.json','source_state_sha256'),('optimizer-state.json','optimizer_state_sha256'),
                         ('publication.json','publication_sha256')]:
        if (folder/filename).exists():result[key]=sha256(folder/filename)
    if result['optimizer_state_sha256'] is not None:
        pointer=read(folder/'optimizer-state.json');optimizer=local(folder,pointer['directory'])
        receipt=read(optimizer/'progress.json')
        require(sha256(local(optimizer,receipt['checkpoint']))==receipt['sha256'],'Saved optimizer checkpoint changed')
        result['checkpoint']={key:receipt[key] for key in ('checkpoint','sha256')}
    return result


def prepare_attempt(folder,continuation=None):
    """Claim a new attempt without mutating any prior request, guard or output."""
    folder=jobs.absolute(folder)
    with queue_lock(folder):
        request,prepared=request_for(folder);jobs.verify_prepared(folder)
        previous=active(folder);number=1
        if previous is None:
            require(continuation is None,'No earlier attempt exists for this continuation')
        else:
            old,metadata=previous;pipeline,owned=attempt_status(old)
            require(not owned and pipeline['status'] in ('failed','deferred'),'Wait for the current correction attempt to stop')
            expected=dict(attempt=old.name,progress=progress_token(folder))
            require(continuation==expected,'Saved correction progress changed; refresh before continuing')
            number=metadata['number']+1
        name=uuid.uuid4().hex;attempt=folder/'attempts'/name;attempt.mkdir(parents=True)
        metadata=dict(schema='strep-mesh-character-attempt-v1',request_sha256=prepared['request_sha256'],
            number=number,previous=None if previous is None else previous[0].name,
            progress=progress_token(folder),max_runtime_seconds=request.get('max_runtime_seconds',900))
        save(attempt/'request.json',metadata)
        save(folder/'active-attempt.json',dict(attempt=name,attempt_sha256=sha256(attempt/'request.json')))
        return attempt


def launch(folder,continuation=None):
    import psutil
    attempt=prepare_attempt(folder,continuation);process=None
    try:
        with (attempt/'supervisor.log').open('w',encoding='utf8') as stream:
            process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),str(folder),attempt.name],
                cwd=jobs.ROOT,env=offline_environment(),stdout=stream,stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        save(attempt/'supervisor.json',dict(pid=process.pid,created_at=psutil.Process(process.pid).create_time()))
        return process
    except (OSError,psutil.Error) as error:
        if process is not None and process.poll() is None:process.terminate();process.wait(timeout=5)
        save(attempt/'startup.json',dict(status='failed',reason=str(error)))
        raise OSError(str(error)) from error


def verify_attempt(folder,name):
    request,prepared=request_for(folder);jobs.verify_prepared(folder)
    selected=active(folder)
    require(selected is not None and selected[0].name==name,'Attempt is no longer the active correction')
    attempt,metadata=selected
    require(metadata['max_runtime_seconds']==request.get('max_runtime_seconds',900),'Attempt processing budget changed')
    return request,attempt,metadata


def file_bindings(folder,directories):
    return {path.relative_to(folder).as_posix():sha256(path) for base in directories
        for path in sorted(base.rglob('*')) if path.is_file()}


def verify_files(folder,bindings):
    require(all(sha256(local(folder,name))==digest for name,digest in bindings.items()),'Saved correction artifacts changed')


def source_for(folder,request):
    from studio_mesh_scene_preview import verified
    package=verified(request['scene_job'],request['scene_result_sha256'])
    require(read(package/'studio-draft.json')==request['mesh_request'],'Saved scene differs from the bound object/contact draft')
    actors=copy.deepcopy(request['correction']['actors'])
    for name,permission in actors.items():
        require('editable_clip_boundaries' not in permission,'Duplicate clip-edge policy')
        permission['editable_clip_boundaries']=request['editable_clip_boundaries'][name]
    def permissions_for(source):
        return dict(schema='strep-native-mesh-character-edit-v1',mesh_scene='source/mesh-scene.json',
            mesh_scene_sha256=sha256(source/'mesh-scene.json'),actors=actors)
    if (folder/'source-state.json').exists():
        pointer=read(folder/'source-state.json')
        require(pointer['request_sha256']==sha256(folder/'request.json'),'Source preparation belongs to another request')
        verify_files(folder,pointer['files_sha256'])
        source,permissions=local(folder,pointer['source']),local(folder,pointer['permissions'])
        require(file_bindings(source,[source])==file_bindings(package,[package])
            and read(permissions)==permissions_for(source),'Saved source or original correction bounds differ')
        return source,permissions
    directory=folder/'preparation'/uuid.uuid4().hex;directory.mkdir(parents=True)
    source=directory/'source';shutil.copytree(package,source)
    expected=file_bindings(package,[package])
    require(file_bindings(source,[source])==expected,'Source snapshot differs from the measured scene')
    permissions=directory/'permissions.json'
    save(permissions,permissions_for(source))
    verified(request['scene_job'],request['scene_result_sha256']);jobs.verify_prepared(folder)
    pointer=dict(source=source.relative_to(folder).as_posix(),permissions=permissions.relative_to(folder).as_posix(),
        request_sha256=sha256(folder/'request.json'),files_sha256=file_bindings(folder,[directory]))
    immutable(folder/'source-state.json',pointer)
    return source,permissions


def optimizer_for(folder,request,source,permissions):
    import native_mesh_character_recovery as recovery
    if (folder/'optimizer-state.json').exists():
        pointer=read(folder/'optimizer-state.json');optimizer=local(folder,pointer['directory'])
        require(pointer['request_sha256']==sha256(folder/'request.json')
            and pointer['source_state_sha256']==sha256(folder/'source-state.json')
            and sha256(optimizer/'request.json')==pointer['optimizer_request_sha256'], 'Optimizer preparation changed')
        receipt=read(optimizer/'progress.json')
    else:
        optimizer=folder/'optimizers'/uuid.uuid4().hex
        receipt=recovery.prepare(permissions,source/'geometry-policy.json',optimizer,
            iterations=request['correction']['options']['iterations'])
        pointer=dict(directory=optimizer.relative_to(folder).as_posix(),request_sha256=sha256(folder/'request.json'),
            source_state_sha256=sha256(folder/'source-state.json'),optimizer_request_sha256=sha256(optimizer/'request.json'),genesis=receipt)
        immutable(folder/'optimizer-state.json',pointer)
    bound=read(optimizer/'request.json')
    require(bound['permissions']==str(permissions.resolve()) and bound['policy']==str((source/'geometry-policy.json').resolve())
        and bound['iterations']==request['correction']['options']['iterations'] and bound['trust']==.02 and bound['backtracks']==8,
        'Optimizer must retain the exact saved Studio correction settings')
    # The optimizer itself verifies source, methods, original bounds, complete
    # checkpoint lineage and recorded geometry before doing further work.
    receipt=recovery.finish(optimizer,receipt['checkpoint'],receipt['sha256'])
    checked=recovery.verify(optimizer,receipt['checkpoint'],receipt['sha256'])
    require(checked['optimizer_completed'],'Complete optimizer required before publication')
    state=read(local(optimizer,receipt['checkpoint']))
    return optimizer,receipt,state,read(optimizer/'result.json')


def publication(folder):
    pointer=read(folder/'publication.json');directory=local(folder,pointer['directory'])
    require(sha256(directory/'receipt.json')==pointer['receipt_sha256'],'Publication receipt changed')
    receipt=read(directory/'receipt.json')
    require(receipt['request_sha256']==sha256(folder/'request.json')
        and sha256(directory/'result.json')==receipt['result_sha256']
        and sha256(directory/'correction-package.zip')==receipt['zip_sha256'],'Completed correction package changed')
    result=read(directory/'result.json');verify_files(folder,result['files_sha256'])
    return directory,result,receipt


def publish_package(folder,request,source,optimizer,checkpoint,state,result):
    if (folder/'publication.json').exists():return publication(folder)[1]
    directory=folder/'publications'/uuid.uuid4().hex;directory.mkdir(parents=True)
    jobs.preview_package(source,None,directory/'preview/original')
    if result['candidate'] is not None:jobs.preview_package(source,local(optimizer,result['candidate']),directory/'preview/candidate')
    relative=lambda path:path.relative_to(folder).as_posix()
    geometry_reports=dict(original=relative(local(optimizer,state['original_geometry'])),
        candidate=None if result['candidate'] is None else relative(local(optimizer,state['current']['geometry'])))
    files=file_bindings(folder,[folder/'preparation',folder/'optimizers',directory/'preview'])
    for name in ('source-state.json','optimizer-state.json'):files[name]=sha256(folder/name)
    report=dict(schema='strep-studio-mesh-character-result-v1',**result,recoverable=True,
        fit_directory=relative(optimizer),preview_directory=relative(directory/'preview'),geometry_reports=geometry_reports,
        optimizer_checkpoint={key:checkpoint[key] for key in ('checkpoint','sha256')},files_sha256=files,
        request_sha256=sha256(folder/'request.json'),scene_result_sha256=request['scene_result_sha256'])
    save(directory/'result.json',report)
    temporary=directory/'correction-package.zip.partial'
    with zipfile.ZipFile(temporary,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in files:archive.write(local(folder,name),name)
        archive.write(directory/'result.json','result.json')
        for name in ('request.json','prepared.json'):archive.write(folder/name,name)
    temporary.rename(directory/'correction-package.zip')
    jobs.verify_prepared(folder);verify_files(folder,files)
    require(read(optimizer/'progress.json')['sha256']==checkpoint['sha256'],'Optimizer advanced during publication')
    receipt=dict(result_sha256=sha256(directory/'result.json'),zip_sha256=sha256(directory/'correction-package.zip'),
        request_sha256=sha256(folder/'request.json'))
    save(directory/'receipt.json',receipt)
    immutable(folder/'publication.json',dict(directory=relative(directory),receipt_sha256=sha256(directory/'receipt.json')))
    return report


def execute(folder,attempt_id):
    folder=jobs.absolute(folder)
    request,attempt,metadata=verify_attempt(folder,attempt_id)
    require(progress_token(folder)==metadata['progress'],'Queued continuation progress changed')
    source,permissions=source_for(folder,request)
    optimizer,checkpoint,state,result=optimizer_for(folder,request,source,permissions)
    report=publish_package(folder,request,source,optimizer,checkpoint,state,result)
    jobs.verify_prepared(folder)
    save(attempt/'completion.json',dict(publication_sha256=sha256(folder/'publication.json'),
        request_sha256=sha256(folder/'request.json'),optimizer_checkpoint=checkpoint))
    return report


def review(folder):
    request,prepared=request_for(folder);selected=active(folder)
    response=dict(id=folder.name,status='starting',recoverable=True,can_continue=False,
        original_selected=True,quality_approved=False,release_approved=False,max_runtime_seconds=request.get('max_runtime_seconds',900))
    if selected is None:return response
    attempt,metadata=selected;pipeline,owned=attempt_status(attempt)
    response.update(status=pipeline['status'],attempt=attempt.name,attempt_number=metadata['number'])
    if pipeline['status']=='complete':
        completion=read(attempt/'completion.json')
        require(completion['publication_sha256']==sha256(folder/'publication.json')
            and completion['request_sha256']==prepared['request_sha256'],'Completed attempt binding changed')
        _,result,receipt=publication(folder)
        response.update(result=result,diagnostics=jobs.diagnostics(folder,result),result_sha256=receipt['result_sha256'],
            comparison_url=f'/mesh-character-viewer.html?job={folder.name}&result={receipt["result_sha256"]}',
            download_url=f'/files/mesh-character-jobs/{folder.name}/correction-package.zip')
    elif pipeline['status'] in ('failed','deferred'):
        response['error']=read(attempt/'failure.json')['error'] if (attempt/'failure.json').exists() else pipeline.get('reason') or 'Correction did not complete'
        if not owned:
            try:
                jobs.verify_prepared(folder)
                response.update(can_continue=True,continuation=dict(attempt=attempt.name,progress=progress_token(folder)))
            except (ValueError,KeyError,OSError,TypeError) as error:response['continuation_error']=str(error)
    return response


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path)
    parser.add_argument('attempt');parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    folder=jobs.absolute(args.folder);request,attempt,metadata=verify_attempt(folder,args.attempt)
    if args.worker:
        from action_worker_lock import worker_lock
        from threadpoolctl import threadpool_limits
        try:
            with worker_lock():
                import native_mesh_character_recovery
                with threadpool_limits(limits=1):execute(folder,args.attempt)
        except Exception as error:save(attempt/'failure.json',dict(error=str(error)));raise
        return 0
    from resource_admission import ResourcePolicy
    from run_guarded_job import run
    from audit_guarded_job import audit
    result=run(Path(__file__),attempt/'guard',ResourcePolicy(expected_rss_bytes=512*1024**2,max_tree_rss_bytes=512*1024**2,
        stable_seconds=15,admission_seconds=600,max_seconds=metadata['max_runtime_seconds']),
        worker_args=[str(folder),args.attempt,'--worker'])
    save(attempt/'resource-replay.json',audit(attempt/'guard'))
    return {'complete':0,'failed':1,'deferred':2}[result['status']]


if __name__=='__main__':raise SystemExit(main())
