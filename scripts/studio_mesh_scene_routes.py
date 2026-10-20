"""Local authoring transport; queue before loading rig or mesh geometry."""
import json
import re
from studio_prop_routes import _body,_object,_constant,_reply


def dispatch_post(handler):
    from studio_mesh_character_routes import dispatch_post as correction_post
    if correction_post(handler):return True
    if handler.path!='/api/mesh-scene-jobs':return False
    host=handler.headers.get('Host')
    if host not in handler.server.allowed_hosts or handler.headers.get('Origin')!=f'http://{host}':return _reply(handler,403,dict(error='Submit from the local Studio page'))
    if handler.headers.get('Content-Type')!='application/json':return _reply(handler,415,dict(error='JSON required'))
    try:
        payload=json.loads(_body(handler,1024**2),object_pairs_hook=_object,parse_constant=_constant)
        from action_studio_server import worker_busy,external_pair_fit_busy
        from studio_mesh_scene_job import prepare,launch
        with handler.server.job_lock:
            if worker_busy() or external_pair_fit_busy() or (handler.server.worker is not None and handler.server.worker.poll() is None):return _reply(handler,409,dict(error='Wait for the current local job'))
            folder=prepare(payload);handler.server.worker=launch(folder)
        return _reply(handler,202,dict(id=folder.name,status='starting'))
    except (ValueError,TypeError,KeyError,OSError) as error:return _reply(handler,400,dict(error=str(error)))


def dispatch_get(handler):
    from studio_mesh_character_routes import dispatch_get as correction_get
    if correction_get(handler):return True
    if not handler.path.startswith('/api/mesh-scene-jobs/'):return False
    if handler.headers.get('Host') not in handler.server.allowed_hosts:return _reply(handler,403,dict(error='Loopback host required'))
    match=re.fullmatch('/api/mesh-scene-jobs/([a-f0-9]{32})(?:/preview/([a-f0-9]{64}))?',handler.path)
    if not match:return _reply(handler,400,dict(error='Choose an exact scene job'))
    try:
        from studio_mesh_scene_job import review,folder_for
        from strep import sha256
        if match[2]:
            from studio_mesh_scene_preview import descriptor
            return _reply(handler,200,descriptor(match[1],match[2]))
        result=review(match[1])
        if result['status']=='complete':
            digest=sha256(folder_for(match[1])/'package/result.json')
            result['preview_url']=f'/mesh-scene-viewer.html?job={match[1]}&result={digest}'
        return _reply(handler,200,result)
    except (ValueError,TypeError,KeyError,OSError) as error:return _reply(handler,400,dict(error=str(error)))
