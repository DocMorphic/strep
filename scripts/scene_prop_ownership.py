"""Explicit atomic grip ownership on the unchanged native scene event clock.

Intent authorizes dispatch, not a successful grasp. No event-name inference,
anatomy inference, pose averaging or physical-quality approval.
"""
import copy
import hashlib
import json
import re
import numpy as np
from native_engine_clock import clock_wire,check_clock_wire


def require(value,message):
    if not value:raise ValueError(message)


def name(value):
    require(isinstance(value,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_:-]{0,80}',value),'Explicit safe participant ID required')
    return value


def compile_plan(document,objects,grips,commands,*,position_tolerance_m=.001,rotation_tolerance_rad=.001):
    require(isinstance(document,dict) and document.get('schema')=='strep-native-scene-game-events-v1','Native scene event document required')
    wire=document.get('clock');require(isinstance(wire,dict),'Exact native scene clock required')
    try:times=np.frombuffer(bytes.fromhex(wire['bytes_hex']),dtype='<f8')
    except (KeyError,TypeError,ValueError) as exc:raise ValueError('Exact native scene clock required') from exc
    check_clock_wire(wire,times)
    require(isinstance(objects,list) and 1<=len(objects)<=32 and len(set(map(name,objects)))==len(objects),'Choose 1–32 distinct props')
    require(isinstance(grips,dict) and 1<=len(grips)<=64,'Explicit grip providers required')
    for key,g in grips.items():
        name(key);require(isinstance(g,dict) and set(g)=={'actor'},'Grip actor binding required');name(g['actor'])
    for limit in (position_tolerance_m,rotation_tolerance_rad):
        require(type(limit) in (int,float) and np.isfinite(limit) and 0<limit<=.01,'Positive pose consistency bounds no larger than .01 required')
    source=document.get('events');require(isinstance(source,list) and len(source)<=1024,'Complete bounded source events required')
    seen={};last=-1;contracts=[]
    keys=['id','name','actor','kind','sample_index','timing_confirmed','runtime_dispatch_allowed']
    for e in source:
        require(isinstance(e,dict) and all(k in e for k in keys),'Complete source event contract required')
        name(e['id']);name(e['actor']);index=e['sample_index']
        require(type(index) is int and last<=index<len(times) and index>=0 and e['id'] not in seen,'Unique ordered native source events required')
        require(type(e['timing_confirmed']) is bool and type(e['runtime_dispatch_allowed']) is bool and e['kind'] in ('contact_intent','gameplay_intent'),'Explicit event intent/confirmation required')
        require(e['runtime_dispatch_allowed']==(e['kind']=='gameplay_intent' and e['timing_confirmed']),'Source event dispatch policy differs')
        contracts.append({k:copy.deepcopy(e[k]) for k in keys});seen[e['id']]=e;last=index
    require(isinstance(commands,list) and 1<=len(commands)<=1024,'Explicit ownership commands required')
    groups={}
    for command in commands:
        require(isinstance(command,dict) and set(command)=={'event_id','object','grip','action'},'Exact ownership command fields required')
        event=seen.get(command['event_id']);require(event is not None and event['runtime_dispatch_allowed'],'Confirmed gameplay event required; contact intent never commands ownership')
        require(command['object'] in objects and command['grip'] in grips and command['action'] in ('acquire','release'),'Bound prop/grip and acquire/release required')
        require(event['actor']==grips[command['grip']]['actor'],'Grip actor differs from authored event actor')
        groups.setdefault(event['sample_index'],[]).append(copy.deepcopy(command))
    owners={n:set() for n in objects};compiled=[]
    for index,changes in sorted(groups.items()):
        previous=copy.deepcopy(owners);pairs=set()
        for c in changes:
            pair=(c['object'],c['grip']);require(pair not in pairs,'Contradictory or duplicate grip changes at one native time');pairs.add(pair)
            held=c['grip'] in previous[c['object']]
            require(held if c['action']=='release' else not held,'Ownership command disagrees with previous grip membership')
        # Release and acquire form ONE simultaneous transaction, independent
        # of JSON order. A hand can transfer props without transient double use.
        for c in changes:
            if c['action']=='release':owners[c['object']].remove(c['grip'])
        for c in changes:
            if c['action']=='acquire':owners[c['object']].add(c['grip'])
        held=[g for gs in owners.values() for g in gs];require(len(set(held))==len(held),'One grip cannot own two props at the same native time')
        transitions=[]
        for obj in sorted({c['object'] for c in changes}):
            before,after=sorted(previous[obj]),sorted(owners[obj])
            transitions.append(dict(object=obj,before=before,after=after,
                mode='held' if after else 'released',last_grip_released=bool(before and not after),
                changes=sorted([c for c in changes if c['object']==obj],key=lambda c:(c['grip'],c['action'],c['event_id']))))
        compiled.append(dict(sample_index=index,time_s=float(times[index]),transitions=transitions))
    digest=hashlib.sha256(json.dumps(document,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return dict(schema='strep-scene-prop-ownership-v1',clock=copy.deepcopy(wire),source_events=contracts,
        source_semantic_sha256=digest,objects=sorted(objects),grips=copy.deepcopy(grips),groups=compiled,
        position_tolerance_m=float(position_tolerance_m),rotation_tolerance_rad=float(rotation_tolerance_rad),
        ownership_verified=False,physics_verified=False,quality_approved=False,release_approved=False)


def consistent_pose(candidates,position_tolerance_m=.001,rotation_tolerance_rad=.001):
    """Return an explicit deterministic rigid target only when ALL grips agree."""
    from scipy.spatial.transform import Rotation
    from primitive_penetration_bounds import rigid
    for limit in (position_tolerance_m,rotation_tolerance_rad):
        require(type(limit) in (int,float) and np.isfinite(limit) and 0<limit<=.01,'Positive pose consistency bounds no larger than .01 required')
    require(isinstance(candidates,dict) and candidates,'Nonempty explicit grip poses required')
    checked={}
    for key,value in candidates.items():
        name(key);t=np.asarray(value,dtype=float)
        require(t.shape==(4,4) and np.isfinite(t).all() and np.array_equal(t[3],[0,0,0,1]),'Finite rigid grip transform required')
        rigid(t[:3,:3]);checked[key]=t
    primary=min(checked);target=checked[primary]
    errors={key:dict(position_m=float(np.linalg.norm(t[:3,3]-target[:3,3])),rotation_rad=float(Rotation.from_matrix(t[:3,:3]@target[:3,:3].T).magnitude())) for key,t in checked.items()}
    require(all(e['position_m']<=position_tolerance_m and e['rotation_rad']<=rotation_tolerance_rad for e in errors.values()),'Active grips request incompatible prop poses; no averaging or hidden correction')
    return target.copy(),dict(primary=primary,grips=errors,pose_consistency_only=True,quality_approved=False)


def compile_files(event_path,request_path,output_path):
    """Save a source-bound intent plan once; no physics or pose files are edited."""
    from pathlib import Path
    event_bytes=Path(event_path).read_bytes();request_bytes=Path(request_path).read_bytes()
    document=json.loads(event_bytes);request=json.loads(request_bytes)
    require(isinstance(request,dict) and request.get('schema')=='strep-scene-prop-ownership-request-v1'
        and {'schema','objects','grips','commands'}<=set(request)
        and set(request)<={'schema','objects','grips','commands','position_tolerance_m','rotation_tolerance_rad'},'Exact ownership authoring request required')
    options={k:request[k] for k in ('position_tolerance_m','rotation_tolerance_rad') if k in request}
    plan=compile_plan(document,request['objects'],request['grips'],request['commands'],**options)
    plan.update(source_events_file_sha256=hashlib.sha256(event_bytes).hexdigest(),ownership_request_file_sha256=hashlib.sha256(request_bytes).hexdigest())
    with Path(output_path).open('x',encoding='utf8') as stream:stream.write(json.dumps(plan,indent=2,allow_nan=False)+'\n')
    return plan


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--events',required=True);parser.add_argument('--request',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();compile_files(args.events,args.request,args.output)
