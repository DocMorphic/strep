"""Necessary-condition screening for a contact-adjacent native motion edge."""
import itertools
import numpy as np


def population():
    directions=np.array([v for v in itertools.product([-1.,0.,1.],repeat=3) if any(v)])
    directions/=np.linalg.norm(directions,axis=1)[:,None]
    states=np.array(list(itertools.product([0.,.005,.01,.02,.03,.04],[-15.,-7.5,0.,7.5,15.],[-15.,-7.5,0.,7.5,15.])))
    return directions,states


def candidates(directions,states,dt,limits):
    directions,states,limits=map(lambda x:np.asarray(x,float),[directions,states,limits])
    if directions.ndim!=2 or directions.shape[1]!=3 or not len(directions) or not np.isfinite(directions).all() or not np.allclose(np.linalg.norm(directions,axis=1),1,atol=1e-12,rtol=0):
        raise ValueError('Finite unit directions required')
    if states.ndim!=2 or states.shape[1]!=3 or not len(states) or not np.isfinite(states).all():raise ValueError('Finite magnitude and swivel states required')
    if np.any(states[:,0]<0) or np.any(states[:,0]>.06+1e-12) or np.any(np.abs(states[:,1:])>30+1e-12):raise ValueError('Planning domain exceeded')
    if not np.isfinite(dt) or dt<=0 or limits.shape!=(3,) or not np.isfinite(limits).all() or np.any(limits<=0):raise ValueError('Positive edge duration and guide limits required')
    seen=set();result=[]
    for axis,direction in enumerate(directions):
        for state,control in enumerate(states):
            # Magnitude rate is the Euclidean wrist speed for a fixed direction,
            # including diagonals; no componentwise diagonal speed allowance.
            if np.any(np.abs(control/dt)>limits+1e-12):continue
            physical=np.r_[direction*control[0],control[1:]]
            key=tuple(physical)
            if key in seen:continue
            seen.add(key);result.append((axis,state))
    return result


def terminal_motion_pass(decoder,layer,start,zero):
    decoded=decoder.decode(layer,start,zero)
    if decoded is None:return None,'native_pose'
    ids,worlds=decoded;payload=decoder.combine(worlds,ids)
    if not decoder.caps.check(payload):return None,'edge_motion'
    if not decoder.caps.join(payload,decoder.suffix):return None,'frozen_junction_motion'
    return (ids,worlds),'pass'


def reject_hand_edge(ids,worlds,query,priority=None,tolerance=.005):
    """Stop at a witnessed failure; partial maxima must not rank as full peaks."""
    ids=np.asarray(ids)
    if ids.ndim!=1 or not len(ids) or len(np.unique(ids))!=len(ids):raise ValueError('Distinct sample IDs required')
    order=list(range(len(ids))) if priority is None else list(priority)
    if sorted(order)!=list(range(len(ids))):raise ValueError('Every sample must appear once in priority')
    if not np.isfinite(tolerance) or tolerance<=0:raise ValueError('Positive hand tolerance required')
    rows=[]
    for local in order:
        directions=query([world[local] for world in worlds])
        if len(directions)!=2:raise ValueError('Both directional hand queries required')
        values=np.array([d['max_depth_m'] for d in directions],float)
        if not np.isfinite(values).all() or np.any(values<0):raise ValueError('Finite nonnegative depths required')
        peak=float(values.max());rows.append(dict(sample=int(ids[local]),directions=directions,hand_peak_m=peak))
        if peak>tolerance:
            return dict(passed=False,complete_clock=len(rows)==len(ids),observed_peak_lower_bound_m=max(r['hand_peak_m'] for r in rows),rows=rows)
    return dict(passed=True,complete_clock=True,observed_peak_lower_bound_m=max(r['hand_peak_m'] for r in rows),rows=rows)
