"""Exact local continuation routes with bounded requests and registered sources."""
import json
import subprocess
import uuid
from urllib.parse import urlsplit,parse_qs
from strep import ROOT,save,sha256,offline_environment
from studio_prop_routes import _body,_object,_constant


def dispatch_get(handler):
    parsed=urlsplit(handler.path)
    if parsed.path not in ('/api/key-continuation-sources','/api/key-continuation-jobs','/api/key-continuation-review'):return False
    if handler.headers.get('Host') not in handler.server.allowed_hosts:
        handler.respond(403,dict(error='Loopback host required'));return True
    try:
        if parsed.fragment:raise ValueError('Exact continuation route required')
        import studio_key_continuation as jobs
        if parsed.path=='/api/key-continuation-review':
            query=parse_qs(parsed.query,keep_blank_values=True)
            if set(query)!={'id'} or len(query['id'])!=1:raise ValueError('Exact continuation job selection required')
            value=jobs.manifest(query['id'][0])
        else:
            if parsed.query or parsed.fragment:raise ValueError('Exact continuation catalog route required')
            value=jobs.catalog() if parsed.path.endswith('sources') else jobs.listing()
        handler.respond(200,value)
    except (ValueError,KeyError,TypeError,OSError) as error:handler.respond(400,dict(error=str(error)))
    return True


def dispatch_post(handler):
    if handler.path!='/api/key-continuations':return False
    host=handler.headers.get('Host')
    if host not in handler.server.allowed_hosts or handler.headers.get('Origin')!=f'http://{host}':
        handler.respond(403,dict(error='Submit from the local studio page'));return True
    if handler.headers.get('Content-Type')!='application/json':
        handler.respond(415,dict(error='JSON required'));return True
    folder=None
    try:
        import studio_key_continuation as jobs
        from action_studio_server import worker_busy,external_pair_fit_busy
        import shutil,psutil
        payload=json.loads(_body(handler,16384),object_pairs_hook=_object,parse_constant=_constant)
        with handler.server.job_lock:
            if worker_busy() or external_pair_fit_busy() or jobs.running() or handler.server.worker is not None and handler.server.worker.poll() is None:
                handler.respond(409,dict(error='A local job is running'));return True
            uv=shutil.which('uv')
            if uv is None:raise ValueError('Prepare the offline uv runtime before continuation')
            job='keys-'+uuid.uuid4().hex[:16];folder=jobs.folder_for(job);jobs.prepare(payload,folder)
            argv=[uv,'run','--offline','--isolated','--no-project','--python','3.10','--with-requirements',str(ROOT/'requirements-ci.txt'),
                'python',str(ROOT/'scripts/studio_key_continuation.py'),str(folder)]
            with (folder/'supervisor.log').open('x',encoding='utf-8') as log:
                process=subprocess.Popen(argv,cwd=ROOT,env=offline_environment(),stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            handler.server.worker=process
            # uv's parent PID is not the numerical driver's identity. The driver
            # records its own OS birth identity on entry; the launch is distinct.
            try:created_at=psutil.Process(process.pid).create_time()
            except psutil.NoSuchProcess:raise ValueError('Continuation launcher exited before identity recording')
            save(folder/'launch.json',dict(pid=process.pid,created_at=created_at,prepared_sha256=sha256(folder/'prepared.json')))
        handler.respond(202,dict(id=job,status='starting'))
    except (ValueError,KeyError,TypeError,OSError) as error:
        if folder is not None and folder.exists():save(folder/'pipeline.json',dict(status='failed',stage='launch',error=str(error),**jobs.FLAGS))
        handler.respond(400,dict(error=str(error)))
    return True
