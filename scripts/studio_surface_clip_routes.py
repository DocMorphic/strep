"""Bounded loopback transport for selected-clip ground-contact correction."""
import json
import re
from studio_prop_routes import _body, _object, _constant, _reply


def dispatch_get(handler):
    if not handler.path.startswith('/api/surface-clip-jobs'):return False
    if handler.headers.get('Host') not in handler.server.allowed_hosts:return _reply(handler,403,dict(error='Loopback host required'))
    try:
        from studio_surface_clip_jobs import listing,review,descriptor
        if handler.path=='/api/surface-clip-jobs':return _reply(handler,200,listing())
        match=re.fullmatch('/api/surface-clip-jobs/([a-f0-9]{32})(?:/attempt/([a-f0-9]{32}))?',handler.path)
        if not match:raise ValueError('Choose an exact saved correction')
        return _reply(handler,200,descriptor(match[1],match[2]) if match[2] else review(match[1]))
    except (ValueError,TypeError,KeyError,OSError) as error:return _reply(handler,400,dict(error=str(error)))


def dispatch_post(handler):
    continuation=re.fullmatch('/api/surface-clip-jobs/([a-f0-9]{32})/continue',handler.path)
    if handler.path!='/api/surface-clip-jobs' and continuation is None:return False
    host=handler.headers.get('Host')
    if host not in handler.server.allowed_hosts or handler.headers.get('Origin')!=f'http://{host}':return _reply(handler,403,dict(error='Submit from the local Studio page'))
    if handler.headers.get('Content-Type')!='application/json':return _reply(handler,415,dict(error='JSON required'))
    try:
        payload=json.loads(_body(handler,1024**2),object_pairs_hook=_object,parse_constant=_constant)
        from action_studio_server import worker_busy,external_pair_fit_busy
        from studio_surface_clip_jobs import prepare,launch,folder_for
        with handler.server.job_lock:
            if worker_busy() or external_pair_fit_busy() or handler.server.worker is not None and handler.server.worker.poll() is None:
                return _reply(handler,409,dict(error='Wait for the current local job'))
            folder=folder_for(continuation[1]) if continuation else prepare(payload)
            handler.server.worker=launch(folder,payload if continuation else None)
        return _reply(handler,202,dict(id=folder.name,status='starting'))
    except (ValueError,TypeError,KeyError,OSError) as error:return _reply(handler,400,dict(error=str(error)))
