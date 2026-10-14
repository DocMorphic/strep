"""Explicit endpoint edits for native-key initialization; preserved by default."""


def boundary_policy(request,clock):
    names={'boundary_keys','acknowledge_changed_boundary_compatibility'}
    supplied=names&set(request)
    if not supplied:
        policy=dict(start='preserve',end='preserve')
    else:
        if supplied!=names:raise ValueError('Explicit boundary choices and compatibility acknowledgment required together')
        policy=request['boundary_keys']
        if (not isinstance(policy,dict) or set(policy)!={'start','end'}
                or any(v not in ('edit','preserve') for v in policy.values())):
            raise ValueError('Explicit start/end native-key boundary choices required')
        changed=any(v=='edit' for v in policy.values())
        if type(request['acknowledge_changed_boundary_compatibility']) is not bool or request['acknowledge_changed_boundary_compatibility'] is not changed:
            raise ValueError('Changed boundary compatibility must be explicitly acknowledged')
    endpoints=dict(start=float(clock[0]),end=float(clock[-1]));frozen=set(map(float,request['frozen_times_s']))
    window=list(map(float,request['window_s']))
    for side,t in endpoints.items():
        if policy[side]=='preserve' and t not in frozen:
            raise ValueError('Every preserved clip endpoint must be an explicit frozen native key')
        if policy[side]=='edit' and (t in frozen or window[0 if side=='start' else 1]!=t):
            raise ValueError('An edited clip endpoint must be inside the window and cannot also be frozen')
    return dict(policy)


def key_frozen(request,clock,time_s):
    policy=boundary_policy(request,clock);t=float(time_s);start,end=map(float,request['window_s'])
    if t in request['frozen_times_s'] or t<start or t>end:return True
    if t==start and not (t==float(clock[0]) and policy['start']=='edit'):return True
    if t==end and not (t==float(clock[-1]) and policy['end']=='edit'):return True
    return False
