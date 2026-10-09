"""Exact finite-precision ownership deadlines on an unchanged authored clock."""
import math,sys
import numpy as np
from native_engine_clock import check_clock_wire

SCHEMA='strep-scene-prop-physics-timing-v1'
MAX_TICK=2**31-1


def require(value,message):
    if not value:raise ValueError(message)


def first_tick(time,rate):
    require(type(rate) is int and rate in (60,120,240),'Supported physics rate required')
    require(type(time) in (int,float) and math.isfinite(time) and time>=0,'Finite source time required')
    require(time<=MAX_TICK/rate,'Ownership time exceeds bounded native tick range')
    tick=math.ceil(time*rate)
    # Product rounding is not the native target predicate time <= tick/rate.
    while tick/rate<time:tick+=1
    while tick>0 and (tick-1)/rate>=time:tick-=1
    require(tick<=MAX_TICK,'Ownership time exceeds bounded native tick range')
    return tick


def timing(plan,rate,maximum_delay_s):
    require(type(rate) is int and rate in (60,120,240),'Supported physics rate required')
    require(type(maximum_delay_s) in (int,float) and 0<=maximum_delay_s<=sys.float_info.max
            and math.isfinite(maximum_delay_s),
            'Explicit nonnegative finite Float64 delay limit required')
    require(isinstance(plan,dict) and plan.get('schema')=='strep-scene-prop-ownership-v1','Compiled ownership plan required')
    wire=plan.get('clock');require(isinstance(wire,dict),'Complete unchanged source clock required')
    try:times=np.frombuffer(bytes.fromhex(wire['bytes_hex']),dtype='<f8')
    except (KeyError,ValueError,TypeError) as exc:raise ValueError('Complete unchanged source clock required') from exc
    check_clock_wire(wire,times)
    groups=plan.get('groups');objects=plan.get('objects')
    require(isinstance(groups,list) and 1<=len(groups)<=1024 and isinstance(objects,list)
            and 1<=len(objects)<=32 and all(isinstance(n,str) for n in objects)
            and len(set(objects))==len(objects),'Complete bounded ownership population required')
    rows=[];seen={};collisions=[];previous=-1;triples=[]
    for index,group in enumerate(groups):
        require(isinstance(group,dict),'Complete ownership group required')
        sample=group.get('sample_index');transitions=group.get('transitions')
        require(type(sample) is int and previous<sample<len(times) and sample>=0
            and isinstance(transitions,list) and transitions,'Ordered complete native ownership groups required')
        previous=sample;names=[t.get('object') if isinstance(t,dict) else None for t in transitions]
        require(all(isinstance(n,str) and n in objects for n in names) and len(set(names))==len(names),'Exact per-group prop population required')
        source=float(times[sample]);tick=first_tick(source,rate);applied=tick/rate;delay=applied-source
        triples.extend((source,applied,delay))
        for obj in names:
            key=obj,tick
            if key in seen:collisions.append(dict(object=obj,tick=tick,first_group=seen[key],later_group=index))
            else:seen[key]=index
        rows.append(dict(group_index=index,sample_index=sample,tick=tick,objects=names))
    maximum=max(triples[2::3]);within=maximum<=maximum_delay_s
    return dict(schema=SCHEMA,physics_fps=rate,maximum_delay_f64le=np.asarray([maximum_delay_s],dtype='<f8').tobytes().hex(),
        application_clock=dict(schema='strep-physics-event-clock-f64le-v1',count=len(rows),bytes_hex=np.asarray(triples,dtype='<f8').tobytes().hex()),
        groups=rows,collapsed_prop_transactions=collisions,within_requested_delay=within,
        distinct_prop_boundaries=not collisions,contract_satisfied=within and not collisions,
        quality_approved=False,release_approved=False)


def enforce(report):
    require(report['distinct_prop_boundaries'],'Distinct source ownership changes for one prop collapse onto one physics boundary')
    if not report['within_requested_delay']:
        triples=np.frombuffer(bytes.fromhex(report['application_clock']['bytes_hex']),dtype='<f8').reshape(-1,3)
        cap=np.frombuffer(bytes.fromhex(report['maximum_delay_f64le']),dtype='<f8')[0]
        raise ValueError(f'Ownership delay {max(triples[:,2])*1000:.9g} ms exceeds requested {cap*1000:.9g} ms; source event times are unchanged')
    return report
