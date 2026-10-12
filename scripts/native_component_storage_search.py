"""Finite typed component search, including self/ancestor positional translations."""
import copy
import numpy as np
from sampled_motion_caps import features,measures
from native_component_storage_repair import ComponentAdjustedEdits
from native_rotation_storage_search import search as checked_search

IDENTITY=('actor','node','path','key_index','component')


def apply_choice(corrections,choice):
    identity=tuple(choice[k] for k in IDENTITY)
    if type(choice['step']) is not int or choice['step'] not in (-1,0,1):
        raise ValueError('Absolute negative/nearest/positive component choice required')
    output=[copy.deepcopy(r) for r in corrections if tuple(r[k] for k in IDENTITY)!=identity]
    if choice['step']:output.append(copy.deepcopy(choice))
    return output


def plan(problem,worlds,corrections,*,allowed_paths=('rotation','translation')):
    groups={};failures=[]
    for name,actor in problem.scene.actors.items():
        if name not in problem.caps:continue
        rate=problem.caps[name]
        for metric,(values,cap) in enumerate(zip(measures(features(worlds[name][problem.rate_ids],actor['rig'].joints),rate.dt),rate.caps)):
            for frame,joint in np.argwhere(values-cap-rate.tolerance>0):
                node=int(actor['rig'].joints[int(joint)]);excess=float(values[frame,joint]-cap[frame,joint]-rate.tolerance)
                failures.append(dict(actor=name,metric=metric,frame=int(frame),node=node,excess=excess))
                if name not in problem.edits.actors:continue
                ancestors=[];parent=node
                while parent>=0:ancestors.append(parent);parent=actor['rig'].parents[parent]
                for entry in problem.edits.actors[name]['tracks']:
                    path=entry['path'];track_node=entry['node']
                    eligible=(path=='translation' and metric<2 and track_node in ancestors
                        or path=='rotation' and track_node in (ancestors[1:] if metric<2 else ancestors))
                    if not eligible or path not in allowed_paths:continue
                    width=2 if metric in (0,2) else 3
                    key=name,track_node,path,int(frame),width
                    # A directly failing joint origin cannot be moved by its
                    # own/descendant rotations; cover its authored translation first.
                    direct=int(path=='translation' and track_node==node)
                    score=direct,excess/max(cap[frame,joint],.001)
                    groups[key]=max(groups.get(key,(-1,-np.inf)),score)
    used={tuple(r[k] for k in IDENTITY):r['step'] for r in corrections};options=[];seen=set()
    for (name,node,path,frame,width),score in sorted(groups.items(),key=lambda item:(item[1],item[0]),reverse=True):
        entry=next(e for e in problem.edits.actors[name]['tracks'] if (e['node'],e['path'])==(node,path))
        clock=entry['clock'];keys=set();support=problem.uniform[frame:frame+width]
        for time in support:
            i=int(np.searchsorted(clock,time))
            keys.update([i] if i<len(clock) and clock[i]==time else [max(0,i-1),min(len(clock)-1,i)])
        center=problem.uniform[frame+1] if width==3 else float((support[0]+support[-1])*.5)
        for key in sorted(keys,key=lambda k:(abs(float(clock[k])-center),k)):
            if key not in entry['ids']:continue
            for component in ((3,2,1,0) if path=='rotation' else (2,1,0)):
                identity=name,node,path,key,component
                choices=(0,-used[identity]) if identity in used else (-1,1)
                for step in choices:
                    if identity+(step,) in seen:continue
                    seen.add(identity+(step,));options.append(dict(actor=name,node=node,path=path,key_index=key,component=component,step=step))
    return options,failures


def search(problem,value,policy,corrections,decode,*,stages=8,probes_per_stage=32):
    return checked_search(problem,value,policy,corrections,decode,stages=stages,probes_per_stage=probes_per_stage,
        _adjusted_type=ComponentAdjustedEdits,_planner=lambda p,w,c:plan(p,w,c,allowed_paths=policy['allowed_paths']),
        _chooser=apply_choice,_result_schema='strep-native-component-storage-search-v1')
