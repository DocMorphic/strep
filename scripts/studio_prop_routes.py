"""Bounded loopback static-prop API; no server, model or solver starts here."""
import json
import re
from urllib.parse import unquote,urlsplit

POST_PATHS=frozenset(('/api/props/import','/api/props/surface-preview','/api/props/grips'))
MAX_JSON_BYTES=16384


def _reply(handler,code,value):
    handler.respond(code,value)
    return True


def _body(handler,maximum):
    length=handler.headers.get('Content-Length','')
    if handler.headers.get('Transfer-Encoding') is not None or not re.fullmatch('[0-9]+',length):
        raise ValueError('Explicit bounded Content-Length required')
    length=int(length)
    if not 0<length<=maximum:raise ValueError('Prop request exceeds its body limit or is empty')
    raw=handler.rfile.read(length)
    if len(raw)!=length:raise ValueError('Incomplete prop request')
    return raw


def _object(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise ValueError('Duplicate prop request field')
        value[key]=item
    return value


def _constant(_):
    raise ValueError('Finite JSON values required')


def dispatch_post(handler):
    if handler.path not in POST_PATHS:return False
    host=handler.headers.get('Host')
    if host not in handler.server.allowed_hosts or handler.headers.get('Origin')!=f'http://{host}':
        return _reply(handler,403,dict(error='Submit from the local studio page'))
    binary=handler.path=='/api/props/import'
    expected='application/octet-stream' if binary else 'application/json'
    if handler.headers.get('Content-Type')!=expected:
        return _reply(handler,415,dict(error='GLB binary required' if binary else 'JSON required'))
    try:
        import studio_props as props
        if binary:
            raw=_body(handler,props.MAX_BYTES)
            value=props.import_bytes(raw,unquote(handler.headers.get('X-Filename','Prop.glb')),
                unquote(handler.headers.get('X-License-Note','')))
            return _reply(handler,201,value)
        raw=_body(handler,MAX_JSON_BYTES)
        value=json.loads(raw,object_pairs_hook=_object,parse_constant=_constant)
        if handler.path=='/api/props/surface-preview':return _reply(handler,200,props.surface_preview(value))
        return _reply(handler,201,props.save_grip(value))
    except (ValueError,TypeError,KeyError,OSError) as error:
        return _reply(handler,400,dict(error=str(error)))


def dispatch_get(handler):
    parsed=urlsplit(handler.path)
    if not parsed.path.startswith('/api/props/'):return False
    if handler.headers.get('Host') not in handler.server.allowed_hosts:
        return _reply(handler,403,dict(error='Loopback host required'))
    if parsed.query or parsed.fragment:return _reply(handler,400,dict(error='Exact prop or grip selection required'))
    match=re.fullmatch('/api/props/([a-f0-9]{64})(?:/grips/([a-f0-9]{64})|/(geometry))?',parsed.path)
    if not match:return _reply(handler,400,dict(error='Exact prop or grip selection required'))
    try:
        import studio_props as props
        asset_id,grip_id,geometry=match.groups()
        value=props.preview_geometry(asset_id) if geometry else props.grip(asset_id,grip_id) if grip_id else props.details(asset_id)
        return _reply(handler,200,value)
    except (ValueError,TypeError,KeyError,OSError) as error:
        return _reply(handler,400,dict(error=str(error)))
