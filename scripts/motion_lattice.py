"""Second-order path search with decoded-edge and junction predicates."""
import numpy as np
from waypoint_lattice import shortest_path


def bounded_path(times,states,costs,limits,edge,join,prefix,suffix,weight=.1):
    # Reuse input validation, including unique zero state and finite clocks.
    shortest_path(times,states,costs,limits,weight)
    times,states,costs,limits=map(lambda v:np.asarray(v,float),[times,states,costs,limits])
    zero=int(np.flatnonzero(np.all(states==0,axis=1))[0])
    active={(-1,zero):(float(costs[0,zero]),[zero],prefix)}
    stats=dict(edges_checked=0,edges_rejected=0,junctions_checked=0,junctions_rejected=0,reachable_pairs=[])
    for layer,dt in enumerate(np.diff(times)):
        cache={};following={}
        for (_,current),(score,history,tail) in sorted(active.items()):
            if not np.isfinite(score):continue
            candidates=[zero] if layer==len(times)-2 else range(len(states))
            for target in candidates:
                speed=(states[target]-states[current])/dt
                if not np.isfinite(costs[layer+1,target]) or np.any(np.abs(speed)>limits+1e-12):continue
                key=(current,target)
                if key not in cache:
                    cache[key]=edge(layer,current,target);stats['edges_checked']+=1
                    if cache[key] is None:stats['edges_rejected']+=1
                payload=cache[key]
                if payload is None:continue
                stats['junctions_checked']+=1
                if not join(tail,payload):stats['junctions_rejected']+=1;continue
                total=score+costs[layer+1,target]+weight*dt*float(np.sum((speed/limits)**2))
                if key not in following or total<following[key][0]:following[key]=(total,history+[target],payload)
        active=following;stats['reachable_pairs'].append(len(active))
        if not active:break
    passing=[]
    for key,(score,history,tail) in sorted(active.items()):
        if len(history)!=len(times):continue
        stats['junctions_checked']+=1
        if join(tail,suffix):passing.append((score,history))
        else:stats['junctions_rejected']+=1
    if not passing:return None,dict(status='no_feasible_path',**stats)
    score,history=min(passing,key=lambda r:(r[0],r[1]));parameters=states[history]
    return parameters,dict(status='complete',state_indices=history,total_cost=float(score),
        maximum_parameter_rates=np.max(np.abs(np.diff(parameters,axis=0)/np.diff(times)[:,None]),axis=0).tolist(),**stats)
