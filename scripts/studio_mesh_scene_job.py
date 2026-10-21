"""Lightweight queue/receipt layer; model-free scene work uses a RAM guard."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid
from strep import ROOT,save,read,sha256,offline_environment

NAMESPACE='mesh-scene-jobs'


def folder_for(job):
    if not isinstance(job,str) or not re.fullmatch('[a-f0-9]{32}',job):raise ValueError('Choose a saved mesh scene job')
    base=(ROOT/'reports'/NAMESPACE).resolve();folder=(base/job).resolve()
    if folder.parent!=base:raise ValueError('Scene job escapes its store')
    return folder


def prepare(payload):
    if not isinstance(payload,dict) or set(payload)!={'schema','draft','props','contacts'} or payload['schema']!='strep-studio-mesh-scene-v1':raise ValueError('Explicit mesh scene draft required')
    raw=json.dumps(payload,allow_nan=False).encode()
    if len(raw)>1024**2:raise ValueError('Mesh scene draft exceeds 1 MiB')
    folder=folder_for(uuid.uuid4().hex);folder.mkdir(parents=True,exist_ok=False)
    save(folder/'request.json',payload)
    methods={p.name:sha256(p) for p in sorted((ROOT/'scripts').glob('*.py'))}
    save(folder/'prepared.json',dict(request_sha256=sha256(folder/'request.json'),methods_sha256=methods))
    return folder


def launch(folder):
    import psutil
    process=None
    try:
        with (folder/'supervisor.log').open('w',encoding='utf8') as log:
            process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),str(folder)],cwd=ROOT,
                env=offline_environment(),stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        save(folder/'supervisor.json',dict(pid=process.pid,created_at=psutil.Process(process.pid).create_time()))
        return process
    except (OSError,psutil.Error) as error:
        if process is not None and process.poll() is None:
            process.terminate();process.wait(timeout=5)
        save(folder/'startup.json',dict(status='failed',reason=str(error)));raise OSError(str(error)) from error


def verify_prepared(folder):
    if folder.resolve()!=folder_for(folder.name):raise ValueError('Saved job folder required')
    prepared=read(folder/'prepared.json')
    if sha256(folder/'request.json')!=prepared['request_sha256']:raise ValueError('Queued scene request changed')
    if not prepared['methods_sha256'] or set(prepared['methods_sha256'])!={p.name for p in (ROOT/'scripts').glob('*.py')}:raise ValueError('Complete implementation binding required')
    if any(sha256(ROOT/'scripts'/name)!=digest for name,digest in prepared['methods_sha256'].items()):raise ValueError('Implementation changed; submit a fresh scene job')
    return read(folder/'request.json')


def execute(folder,resolver):
    from studio_mesh_scene import assemble
    payload=verify_prepared(folder);result=assemble(payload,folder/'package',resolver);verify_prepared(folder)
    save(folder/'receipt.json',dict(result_sha256=sha256(folder/'package/result.json'),zip_sha256=sha256(folder/'scene-package.zip'),request_sha256=sha256(folder/'request.json')))
    return result


def review(job):
    folder=folder_for(job);prepared=read(folder/'prepared.json')
    if sha256(folder/'request.json')!=prepared['request_sha256']:raise ValueError('Saved request changed')
    pipeline=read(folder/'guard/pipeline.json') if (folder/'guard/pipeline.json').is_file() else read(folder/'startup.json') if (folder/'startup.json').is_file() else dict(status='starting')
    if pipeline['status'] not in ('complete','failed','deferred') and (folder/'supervisor.json').is_file():
        import psutil
        process=read(folder/'supervisor.json')
        try:live=psutil.Process(process['pid']).create_time()==process['created_at']
        except psutil.NoSuchProcess:live=False
        if not live:pipeline=dict(status='failed',reason='Scene supervisor stopped before completion; submit a fresh request')
    result=dict(id=job,status=pipeline['status'],quality_approved=False,release_approved=False,downloads=[])
    if pipeline['status']=='complete':
        receipt=read(folder/'receipt.json')
        if receipt['request_sha256']!=prepared['request_sha256'] or sha256(folder/'package/result.json')!=receipt['result_sha256'] or sha256(folder/'scene-package.zip')!=receipt['zip_sha256']:raise ValueError('Saved scene receipt changed')
        report=read(folder/'package/result.json')
        for name,digest in report['files_sha256'].items():
            path=(folder/'package'/name).resolve()
            if not path.is_relative_to((folder/'package').resolve()) or sha256(path)!=digest:raise ValueError('Saved scene package changed')
        result.update(all_declared_point_contacts_pass=report['all_declared_point_contacts_pass'],contacts=report['contacts'],motion_fitted=False,geometry_evaluated=False,original_selected=True,
            downloads=[dict(label='Scene package',url=f'/files/{NAMESPACE}/{job}/scene-package.zip'),dict(label='Contact measurements',url=f'/files/{NAMESPACE}/{job}/contact-report.json')])
    elif pipeline['status'] in ('failed','deferred'):
        result['error']=read(folder/'failure.json')['error'] if (folder/'failure.json').is_file() else pipeline.get('reason') or 'Worker did not complete. Original assets are unchanged.'
    return result


def served_file(relative):
    match=re.fullmatch(r'/files/mesh-scene-jobs/([a-f0-9]{32})/(scene-package\.zip|contact-report\.json)',relative)
    if not match:return None
    job,name=match.groups();result=review(job)
    if result['status']!='complete':return None
    folder=folder_for(job);return folder/name if name=='scene-package.zip' else folder/'package'/name


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path);parser.add_argument('--worker',action='store_true');args=parser.parse_args();folder=args.folder.resolve()
    if folder!=folder_for(folder.name):raise ValueError('Existing queued scene required')
    if args.worker:
        from action_worker_lock import worker_lock
        from threadpoolctl import threadpool_limits
        from action_studio_server import allowed_file
        try:
            with worker_lock():
                # Load numerical pools before limiting them, only in the
                # admitted worker. Queue/status imports stay lightweight.
                import studio_mesh_scene
                with threadpool_limits(limits=1):execute(folder,allowed_file)
        except Exception as error:
            save(folder/'failure.json',dict(error=str(error)));raise
    else:
        from resource_admission import ResourcePolicy
        from run_guarded_job import run
        from audit_guarded_job import audit
        result=run(Path(__file__),folder/'guard',ResourcePolicy(expected_rss_bytes=512*1024**2,max_tree_rss_bytes=512*1024**2,stable_seconds=15,admission_seconds=600,max_seconds=300),worker_args=[str(folder),'--worker'])
        save(folder/'resource-replay.json',audit(folder/'guard'));return {'complete':0,'failed':1,'deferred':2}[result['status']]
    return 0


if __name__=='__main__':raise SystemExit(main())
