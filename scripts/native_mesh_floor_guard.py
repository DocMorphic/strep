"""Rebuilt full-clock floor witnesses, retaining current measured depth caps.

Worst vertices guide the affine step. Every decoded triangle/vertex is still
checked by MeshPropScene; these witnesses never certify the proposed geometry.
"""
import numpy as np
from scipy import sparse
from native_scene_norms import NormRows
from native_surface_lift import lift


def add_floor_guards(problem, value, worlds, policy, geometry, system, jacobian, hard_rows, trust, *, additional_witnesses=()):
    records=[];caps={}
    for sample in geometry['samples']:
        for row in sample['base_scene']['world_planes']:
            key=(row['actor'],row['plane']);caps[key]=max(caps.get(key,0.),row['maximum_depth_m'])
            records.append((row['actor'],row['plane'],sample['time_s'],row['peak_vertex']))
    population={(a,p,t) for a,p,t,_ in records};seen=set(records)
    for row in additional_witnesses:
        record=(row['actor'],row['plane'],row['time_s'],row['vertex']);actor,plane,time,vertex=record
        if ((actor,plane,time) not in population or type(vertex) is not int
            or not 0<=vertex<sum(len(p['positions']) for p in problem.scene.actors[actor]['rig'].primitives)):
            raise ValueError('Retained floor witness must belong to the original actor/plane/time population')
        if record not in seen:records.append(record);seen.add(record)
    if not records:
        return system,jacobian,hard_rows,dict(rows=0,complete_declared_geometry_clock=True)
    if len(records)>100000 or len(records)*problem.size>16_000_000:
        raise ValueError('Complete floor witness model exceeds budget; no samples dropped')
    groups={};anchored=[]
    for ordinal,(name,plane,time,vertex) in enumerate(records):
        index=int(np.searchsorted(problem.times,time))
        if index==len(problem.times) or problem.times[index]!=time:raise ValueError('Full geometry clock must precede floor guidance')
        groups.setdefault(name,[]).append((ordinal,index,vertex,plane))
    # Anchor with the same arithmetic as the actual geometry audit, rather
    # than replacing a measured zero by a small negative proxy roundoff.
    anchored=np.zeros(len(records))
    for name,group in groups.items():
        actor=problem.scene.actors[name];position,rotation=actor['placement'];cache={}
        for ordinal,index,vertex,plane in group:
            if index not in cache:cache.clear();cache[index]=actor['rig'].vertices(worlds[name][index])@rotation.T+position
            definition=policy['planes'][plane]
            anchored[ordinal]=float(cache[index][vertex]@np.asarray(definition['normal_world'])-definition['offset_m']+caps[name,plane])
    def gaps(matrices):
        result=np.zeros(len(records))
        for name,group in groups.items():
            actor=problem.scene.actors[name];skin=actor['skin'];ids=np.array([r[2] for r in group]);clock=np.array([r[1] for r in group]);position,rotation=actor['placement']
            selected=matrices[name][clock[:,None],skin.nodes[ids],:3,:]
            points=np.einsum('vkij,vkj,vk->vi',selected,skin.points[ids],skin.weights[ids])@rotation.T+position
            for point,(ordinal,_,_,plane) in zip(points,group):
                definition=policy['planes'][plane]
                result[ordinal]=float(point@np.asarray(definition['normal_world'])-definition['offset_m']+caps[name,plane])
        return result
    smooth=gaps(problem.worlds(value,quantized=False));columns=[];stencils=[]
    for i in range(problem.size):
        if value[i]-.001>=problem.lower[i] and value[i]+.001<=problem.upper[i]:
            plus=value.copy();minus=value.copy();plus[i]+=.001;minus[i]-=.001
            derivative=(gaps(problem.worlds(plus,quantized=False))-gaps(problem.worlds(minus,quantized=False)))/.002
            stencils.append([.001,-.001])
        else:
            room=problem.upper[i]-value[i] if problem.upper[i]-value[i]>=value[i]-problem.lower[i] else problem.lower[i]-value[i]
            h=np.copysign(min(.001,abs(room)),room)
            if h==0:raise ValueError('No floor derivative room')
            other=value.copy();other[i]+=h;derivative=(gaps(problem.worlds(other,quantized=False))-smooth)/h;stencils.append([float(h)])
        columns.append(sparse.csc_matrix(derivative[:,None]))
    extra,extra_jac,conversion=lift(anchored,sparse.hstack(columns,format='csr'),value,problem.lower,problem.upper,trust,clearance=0)
    vectors=np.r_[system.vectors[:hard_rows],extra.vectors,system.vectors[hard_rows:]]
    limits=np.r_[system.caps[:hard_rows],extra.caps,system.caps[hard_rows:]]
    scales=np.r_[system.scales[:hard_rows],extra.scales,system.scales[hard_rows:]]
    matrix=sparse.vstack([jacobian[:3*hard_rows],extra_jac,jacobian[3*hard_rows:]],format='csc')
    return NormRows(vectors,limits,scales),matrix,hard_rows+len(records),dict(rows=len(records),
        complete_declared_geometry_clock=True,witnesses=[dict(actor=a,plane=p,time_s=t,vertex=v) for a,p,t,v in records],
        measured_depth_caps=[dict(actor=a,plane=p,maximum_depth_m=d) for (a,p),d in caps.items()],
        stencil_offsets=stencils,conversion=conversion,all_vertices_verified_only_by_decoded_geometry=True)
