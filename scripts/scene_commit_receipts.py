"""Independently match committed gameplay receipts to complete recorded boundaries.

No physics, motion quality, absent boundary coverage or human approval is inferred.
"""
import numpy as np
from native_engine_clock import check_clock_wire,clock_echo_matches

RECORD_FIELDS={'tick','session','source_time_s','group_cursor','members','modes','tracking','props',
               'physics_root_deltas','transport','failure','command'}


def require(value,message):
    if not value:raise ValueError(message)


def root_matrix(columns):
    value=np.asarray(columns,dtype=float)
    require(value.shape==(4,3) and np.isfinite(value).all(),'Complete recorded actor root required')
    matrix=np.eye(4);matrix[:3,:3]=value[:3].T;matrix[:3,3]=value[3];return matrix


def finite(value,shape):
    array=np.asarray(value,dtype=float)
    require(array.shape==shape and np.isfinite(array).all(),'Complete finite committed state required')
    return array


def pose(value):
    array=finite(value,(4,4));require(np.array_equal(array[3],[0,0,0,1]),'Homogeneous committed transform required')


def prop_state(state):
    fields={'pose','velocity','spin','contacts','collision_layer','collision_mask','step_s','gravity','inverse_mass','inverse_inertia','direct_state_class'}
    require(isinstance(state,dict) and set(state)==fields,'Complete physical prop observation required')
    pose(state['pose'])
    for field in ['velocity','spin','gravity','inverse_inertia']:finite(state[field],(3,))
    for field in ['step_s','inverse_mass']:
        require(type(state[field]) in (int,float) and np.isfinite(state[field]) and state[field]>0,'Positive physical state scalar required')
    require(type(state['direct_state_class']) is str and state['direct_state_class'] and isinstance(state['contacts'],list) and all(type(c) is str for c in state['contacts']),'Direct-state identity and complete contact observations required')
    require(all(type(state[f]) is int and 0<=state[f]<=4294967295 for f in ['collision_layer','collision_mask']),'Explicit physical collision bitfields required')


def audit(plan,actors,observed,*,physics_fps):
    require(isinstance(plan,dict) and plan.get('schema')=='strep-scene-prop-ownership-v1','Bound ownership plan required')
    times=np.frombuffer(bytes.fromhex(plan['clock']['bytes_hex']),dtype='<f8');check_clock_wire(plan['clock'],times)
    require(isinstance(actors,dict) and actors and all(mode in ('embedded','extracted') for mode in actors.values()),'Complete actor root modes required')
    require(type(physics_fps) is int and physics_fps in (60,120,240),'Explicit expected physics rate required')
    receipts=observed['commit_receipts'];callbacks=observed['commit_callbacks'];records=observed['records']
    require(isinstance(receipts,list) and len(receipts)<=len(records) and len(receipts)==len(callbacks),'Complete committed callback population required')
    require(observed['detached_copies']==len(receipts),'Every first listener must exercise detached-copy isolation')
    by_boundary={};commit_ids=set();owner=None
    for receipt,callback in zip(receipts,callbacks):
        require(receipt.get('schema')=='strep-scene-prop-commit-v1','Versioned commit receipt required')
        record=receipt['record'];key=(record['session'],record['tick']);instance=receipt['owner_instance_id']
        require(all(type(value) is int and value>=0 for value in key),'Explicit nonnegative integer session and tick required')
        require(type(instance) is str and instance.isascii(),'Explicit live owner identity required')
        number=int(instance)
        require(str(number)==instance and -(1<<63)<=number<(1<<63) and number!=0,'Canonical signed live owner identity required')
        if owner is None:owner=instance
        require(instance==owner and receipt['commit_id']==f'{instance}:{key[0]}:{key[1]}' and receipt['commit_id'] not in commit_ids and key not in by_boundary,'Unique owner/session/boundary receipt required')
        commit_ids.add(receipt['commit_id']);by_boundary[key]=receipt
        require(set(record)==RECORD_FIELDS and record['failure']=='' and record['transport']=='live','Only successful complete live boundaries can commit')
        require(receipt['quality_approved'] is False and receipt['release_approved'] is False,'Commit is never a quality or release approval')
        require(receipt['props_state_phase']=='assigned_before_force_integration','Assigned prop states must not imply completed collision/force resolution')
        require(receipt['source_clock']==plan['clock'] and receipt['source_semantic_sha256']==plan['source_semantic_sha256'],'Original binary clock and source semantic binding required')
        require(receipt['root_modes']==actors and set(receipt['actor_root_motion'])==set(actors),'Every actor/root mode must be present')
        require(receipt['physics_rate_hz']==physics_fps,'Original physics rate must be retained')
        require(set(record['props'])==set(plan['objects']) and set(record['members'])==set(plan['objects']) and set(record['modes'])==set(plan['objects']), 'Every prop state and membership must be present')
        require(set(record['tracking'])==set(plan['objects']) and set(record['physics_root_deltas'])==set(actors),'Complete tracking and actor root deltas required')
        for state in record['props'].values():prop_state(state)
        for state in record['tracking'].values():
            require(set(state)=={'pose','time_s'} and type(state['time_s']) in (int,float) and np.isfinite(state['time_s']) and 0<=state['time_s']<=record['source_time_s'],'Complete finite incoming tracking clock required')
            pose(state['pose'])
        for value in [*receipt['actor_root_motion'].values(),*record['physics_root_deltas'].values()]:pose(value)
        require(callback==dict(commit_id=receipt['commit_id'],all_containers_read_only=True,all_bodies_seen=True,owner_state_matches=True),'Actual immutable complete-state callbacks required')
        require(clock_echo_matches(record['source_time_s'],receipt['scene_pose_time_s']) and clock_echo_matches(record['source_time_s'],receipt['scene_playback_time_s']),'Actors must share the committed source clock')
        ids={event for action in receipt['actions'] for event in action['event_ids']}
        expected=[dict(event,time_s=float(times[event['sample_index']])) for event in plan['source_events'] if event['id'] in ids]
        require(len(receipt['source_events'])==len(expected) and {e['id'] for e in expected}==ids,'Complete unchanged source event contracts required')
        for actual,source in zip(receipt['source_events'],expected):
            require(set(actual)==set(source) and all(actual[k]==source[k] for k in source if k!='time_s') and clock_echo_matches(source['time_s'],actual['time_s']),'Exact source contract and binary event time required')
    cursors={};members={};modes={};used=set();flattened=[]
    for record in records:
        key=(record['session'],record['tick'])
        if record['failure'] or record['transport']!='live':
            # A preview can have the same tick as a prior live commit; it must
            # neither dispatch another receipt nor reset forward coverage.
            continue
        before=cursors.get(record['session'],0);after=record['group_cursor']
        require(type(after) is int and before<=after<=len(plan['groups']),'Monotonic complete live ownership cursor required')
        expected=[(group,transition) for group in plan['groups'][before:after] for transition in group['transitions']]
        cursors[record['session']]=after
        if record['session'] not in members:
            members[record['session']]={obj:[] for obj in plan['objects']}
            modes[record['session']]={obj:'parked' for obj in plan['objects']}
        for _,transition in expected:
            members[record['session']][transition['object']]=transition['after']
            modes[record['session']][transition['object']]=transition['mode']
        require(record['members']==members[record['session']] and record['modes']==modes[record['session']],'Every prop must retain the complete original planned ownership state')
        if not expected:continue
        require(key in by_boundary and key not in used,'Every newly committed group needs exactly one boundary receipt')
        receipt=by_boundary[key];used.add(key)
        require(len(receipt['actions'])==len(expected),'All simultaneous prop transitions must be reported')
        require(all(receipt['record'][field]==record[field] for field in RECORD_FIELDS),'Receipt differs from independently recorded complete body boundary')
        require(set(record['scene']['actors'])==set(actors),'Complete independently observed actor population required')
        for actor in actors:
            np.testing.assert_array_equal(receipt['actor_root_motion'][actor],root_matrix(record['scene']['actors'][actor]['root_motion']))
        wire=receipt['action_clock'];count=len(receipt['actions'])
        require(set(wire)=={'schema','count','bytes_hex'} and wire['schema']=='strep-scene-prop-action-clock-f64le-v1' and type(wire['count']) is int and wire['count']==count and type(wire['bytes_hex']) is str and len(wire['bytes_hex'])==count*48,'Complete binary per-action source/application/delay clock required')
        encoded=bytes.fromhex(wire['bytes_hex']);require(encoded.hex()==wire['bytes_hex'],'Canonical little-endian action clock required')
        clocks=np.frombuffer(encoded,dtype='<f8').reshape(count,3)
        for action,(group,transition),(source,application,delay) in zip(receipt['actions'],expected,clocks):
            ids=list(dict.fromkeys(c['event_id'] for c in transition['changes']))
            require(action['object']==transition['object'] and action['before']==transition['before'] and action['after']==transition['after'] and action['last_grip_released']==transition['last_grip_released'] and action['event_ids']==ids,'Receipt changes differ from the original complete simultaneous plan')
            require(action['session']==key[0] and action['tick']==key[1] and clock_echo_matches(group['time_s'],action['source_time_s']),'Exact action source time and boundary identity required')
            require(np.isfinite([application,source,delay]).all() and source==times[group['sample_index']] and application==key[1]/physics_fps and application>=source and delay>=0 and delay==application-source,'Exact physical boundary and delay must be retained, never hidden')
            require(all(clock_echo_matches(value,action[field]) for value,field in zip([source,application,delay],['source_time_s','physics_application_time_s','application_delay_s'])),'Descriptive action clocks differ from exact binary clock')
        flattened.extend(receipt['actions'])
    require(used==set(by_boundary) and flattened==observed['actions'],'No missing, extra, failed or transport-only receipts; legacy actions must match')
    return dict(receipts=len(receipts),actions=len(flattened),all_recorded_commit_boundaries_checked=True,
                actual_callbacks_checked=True,quality_approved=False,release_approved=False,
                scope='Complete recorded successful boundaries, source plan, actor roots and prop states. Does not establish unsampled boundary coverage, physical event exactness, collision quality or human approval.')
