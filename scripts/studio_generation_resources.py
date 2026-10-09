"""Keep saved generation intent separate from resource-supervisor state."""
from dataclasses import asdict
from pathlib import Path
import re
import shutil
import subprocess
import sys
import psutil
from action_requests import validate_batch,request_digest
from resource_admission import ResourcePolicy
from strep import ROOT,read,save,sha256,now,offline_environment

ACTIVE={'waiting_resources','ready','starting','processing','encoding','generation','export'}
METHODS=['studio_generation_resources.py','studio_generation_worker.py','action_requests.py','generation_constraints.py','motion_profile.py','run_actions.py']


def default_policy():
    # Observed generation peaks reach 3.47 GB; this estimate includes margin.
    return ResourcePolicy(4*1024**3,stable_seconds=15,admission_seconds=60)


def job_folder(job):
    if type(job) is not str or not re.fullmatch(r'action-jobs/[A-Za-z0-9][A-Za-z0-9_-]{0,100}',job):
        raise ValueError('Saved generation job required')
    folder=(ROOT/'reports'/job).resolve()
    if not folder.is_relative_to((ROOT/'reports/action-jobs').resolve()):raise ValueError('Generation job escapes its directory')
    return folder


def validate_snapshot(folder,*,execution=False):
    folder=Path(folder).resolve();job_folder(folder.relative_to(ROOT/'reports').as_posix())
    launch=read(folder/'studio-launch.json');request=validate_batch(read(folder/'resource-request.json'))
    if (launch.get('schema')!='strep-studio-generation-resource-v1'
            or launch.get('worker')!='scripts/studio_generation_worker.py'
            or sha256(folder/'resource-request.json')!=launch['request_sha256']
            or set(launch['implementation_sha256'])!=set(METHODS)
            or any(sha256(folder/'request-implementation'/n)!=h for n,h in launch['implementation_sha256'].items())
            or launch.get('quality_approved') is not False or launch.get('release_approved') is not False):
        raise ValueError('Saved generation request or implementation binding changed')
    if execution and (request_digest(request)!=launch['resolved_request_digest']
            or any(sha256(Path(__file__).resolve().parent/n)!=h for n,h in launch['implementation_sha256'].items())):
        raise ValueError('Prepared generation implementation or resolved controls changed before execution')
    return request,launch


def prepare(batch,folder,policy=None,*,retry_of=None):
    batch=validate_batch(batch);policy=default_policy() if policy is None else policy
    if not isinstance(policy,ResourcePolicy) or policy.expected_rss_bytes%1024**2:
        raise ValueError('Explicit whole-MiB generation resource estimate required')
    if policy.min_available_bytes!=600*1024**2 or policy.max_tree_rss_bytes!=7*1024**3:
        raise ValueError('Studio preserves the established runtime RAM guards')
    folder=Path(folder).resolve();job_folder(folder.relative_to(ROOT/'reports').as_posix())
    folder.mkdir(parents=True,exist_ok=False);archive=folder/'request-implementation';archive.mkdir()
    root=Path(__file__).resolve().parent
    for name in METHODS:shutil.copyfile(root/name,archive/name)
    save(folder/'resource-request.json',batch);save(folder/'request.json',batch)
    save(folder/'studio-launch.json',dict(schema='strep-studio-generation-resource-v1',at=now(),
        worker='scripts/studio_generation_worker.py',request_sha256=sha256(folder/'resource-request.json'),
        resolved_request_digest=request_digest(batch),implementation_sha256={n:sha256(archive/n) for n in METHODS},
        policy=asdict(policy),retry_of=retry_of,quality_approved=False,release_approved=False))
    save(folder/'pipeline.json',dict(status='waiting_resources',quality_approved=False,release_approved=False))
    return folder


def launch(folder):
    folder=Path(folder).resolve();_,record=validate_snapshot(folder,execution=True);p=ResourcePolicy(**record['policy'])
    args=[sys.executable,str(ROOT/'scripts/run_guarded_job.py'),'--worker',str(ROOT/record['worker']),
        '--output',str(folder/'guard'),'--expected-rss-mib',str(p.expected_rss_bytes//1024**2),
        '--stable-seconds',str(p.stable_seconds),'--admission-seconds',str(p.admission_seconds),
        '--max-seconds',str(p.max_seconds),'--poll-seconds',str(p.poll_seconds),'--',str(folder)]
    with (folder/'supervisor.log').open('x',encoding='utf-8') as log:
        process=subprocess.Popen(args,cwd=ROOT,env=offline_environment(),stdout=log,stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:save(folder/'worker.json',dict(pid=process.pid,created_at=psutil.Process(process.pid).create_time()))
    except psutil.NoSuchProcess:pass
    return process


def _live(identity):
    try:
        p=psutil.Process(identity['pid'])
        return p.is_running() and p.status()!=psutil.STATUS_ZOMBIE and abs(p.create_time()-identity['created_at'])<.001
    except psutil.NoSuchProcess:return False
    except psutil.AccessDenied:return None


def _observed_state(folder):
    """Read-only projection; never turn a guard result into motion approval."""
    folder=Path(folder);native=read(folder/'pipeline.json') if (folder/'pipeline.json').exists() else dict(status='unknown')
    if not (folder/'studio-launch.json').exists():return native
    try:validate_snapshot(folder)
    except (ValueError,KeyError,TypeError,OSError) as exc:return dict(status='failed',error=str(exc),can_retry=False)
    guard=read(folder/'guard/pipeline.json') if (folder/'guard/pipeline.json').exists() else None
    if guard is None and native.get('status')=='failed':return dict(native,can_retry=False)
    if guard is not None and guard['status'] in ['deferred','failed']:
        state=dict(status=guard['status'],reason=guard.get('reason'),can_retry=guard['status']=='deferred' and guard['worker_started'] is False,
            model_worker_started=guard['worker_started'],quality_approved=False,release_approved=False)
        if guard['status']=='failed':state['error']='Local generation stopped; its request and logs are preserved.'
        return state
    identity=read(folder/'worker.json') if (folder/'worker.json').exists() else None
    live=_live(identity) if identity is not None else None
    if guard is not None and guard['status']=='complete':
        if native.get('status')!='complete':return dict(status='failed',error='Generation worker exited without a completed motion result.',can_retry=False)
        return dict(native,can_retry=False)
    if live is False:
        if guard is not None and guard.get('worker_started'):
            child=guard.get('worker_created_at')
            if child is not None and _live(dict(pid=guard['worker_pid'],created_at=child)):
                return dict(status='processing',error='Generation is still running; its supervisor is unavailable.',can_retry=False)
        return dict(status='failed',error='Generation supervisor exited before recording a terminal result.',can_retry=False)
    if live is None:
        return dict(status='unknown',error='Generation supervisor liveness cannot be verified.',can_retry=False)
    if guard is None or guard['status'] in ['waiting_resources','ready']:
        return dict(status='waiting_resources',can_retry=False,model_worker_started=False,quality_approved=False,release_approved=False)
    return dict(native if native.get('status') in ACTIVE-{'waiting_resources','ready'} else dict(status='starting'),can_retry=False)


def observed_state(folder):
    try:return _observed_state(folder)
    except (ValueError,KeyError,TypeError,OSError) as exc:
        return dict(status='unknown',error='Saved generation state cannot be verified: '+str(exc),can_retry=False)


def retry_request(payload):
    if not isinstance(payload,dict) or set(payload)!={'job'}:raise ValueError('Saved deferred generation job required')
    folder=job_folder(payload['job']);request,_=validate_snapshot(folder);state=observed_state(folder)
    if state.get('status')!='deferred' or state.get('can_retry') is not True:
        raise ValueError('Only an unstarted deferred generation request can be retried')
    if request_digest(request)!=read(folder/'studio-launch.json')['resolved_request_digest']:
        raise ValueError('Saved controls resolve differently; submit a new reviewed request')
    return request


def generation_worker_busy():
    # Waiting supervisors do not hold the model lock, including after restart.
    for folder in (ROOT/'reports/action-jobs').glob('*'):
        if (folder/'studio-launch.json').exists() and (folder/'worker.json').exists():
            try:
                if _live(read(folder/'worker.json')) is not False:return True
            except (ValueError,KeyError,TypeError,OSError):return True
    return False
