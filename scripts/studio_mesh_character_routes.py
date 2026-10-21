"""Lightweight local correction transport; numerical work stays in the worker."""
import json
import re
from studio_prop_routes import _body, _object, _constant, _reply


def dispatch_post(handler):
    continuation=re.fullmatch('/api/mesh-character-jobs/([a-f0-9]{32})/continue',handler.path)
    if handler.path != '/api/mesh-character-jobs' and continuation is None:return False
    host = handler.headers.get('Host')
    if host not in handler.server.allowed_hosts or handler.headers.get('Origin') != f'http://{host}': return _reply(handler,403,dict(error='Submit from the local Studio page'))
    if handler.headers.get('Content-Type') != 'application/json': return _reply(handler,415,dict(error='JSON required'))
    try:
        payload = json.loads(_body(handler,1024**2),object_pairs_hook=_object,parse_constant=_constant)
        from action_studio_server import worker_busy, external_pair_fit_busy
        from studio_mesh_character_job import prepare, launch
        with handler.server.job_lock:
            if worker_busy() or external_pair_fit_busy() or (handler.server.worker is not None and handler.server.worker.poll() is None): return _reply(handler,409,dict(error='Wait for the current local job'))
            if continuation:
                from studio_mesh_character_job import folder_for
                from studio_mesh_character_recovery_job import launch as launch_recovery
                folder=folder_for(continuation[1]);handler.server.worker=launch_recovery(folder,payload)
            else:
                folder = prepare(payload); handler.server.worker = launch(folder)
        return _reply(handler,202,dict(id=folder.name,status='starting'))
    except (ValueError,TypeError,KeyError,OSError) as error: return _reply(handler,400,dict(error=str(error)))


def dispatch_get(handler):
    if not handler.path.startswith('/api/mesh-character-jobs/'): return False
    if handler.headers.get('Host') not in handler.server.allowed_hosts: return _reply(handler,403,dict(error='Loopback host required'))
    match = re.fullmatch('/api/mesh-character-jobs/([a-f0-9]{32})(?:/preview/([a-f0-9]{64}))?',handler.path)
    if not match: return _reply(handler,400,dict(error='Choose an exact correction job'))
    try:
        if match[2]:
            from studio_mesh_character_preview import descriptor
            return _reply(handler,200,descriptor(match[1],match[2]))
        from studio_mesh_character_job import review
        return _reply(handler,200,review(match[1]))
    except (ValueError,TypeError,KeyError,OSError) as error: return _reply(handler,400,dict(error=str(error)))
