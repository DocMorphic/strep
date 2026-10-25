"""Find recorded crossings that a declared rotation-only edit cannot move.

This conservative dependency check never treats a zero sampled derivative as
invariance. Any positive skin influence below any editable node counts as
potentially affected. No translations, weight or topology edits are permitted.
"""
import numpy as np
from native_scene_geometry import faces_for
from native_surface_locations import locate


def analyze(rig,world,audit,rotations):
    if (type(rotations) is not list or len(rotations)>20
            or any(type(n) is not int or n not in rig.joints for n in rotations) or len(set(rotations))!=len(rotations)):
        raise ValueError('At most twenty distinct existing skin rotations required')
    locations=locate(rig,world,audit)
    influenced=[]
    for n in range(len(rig.parents)):
        chain=set();a=n
        while a>=0:
            if a in chain or a>=len(rig.parents):raise ValueError('Complete acyclic node hierarchy required')
            chain.add(a);a=rig.parents[a]
        influenced.append(bool(chain.intersection(rotations)))
    influenced=np.asarray(influenced,bool);vertices=[]
    for p in rig.primitives:
        if p['joints'] is None:vertices.extend([bool(influenced[p['node']])]*len(p['positions']))
        else:
            nodes=np.asarray(rig.joints)[p['joints']]
            vertices.extend(np.any((p['weights']>0)&influenced[nodes],axis=1).tolist())
    vertices=np.asarray(vertices,bool);faces,_=faces_for(rig);affected=np.any(vertices[faces],axis=1)
    fixed=[];potential=[]
    for record in audit['records']:
        if record['kind']!='proper_crossing':continue
        i,j=record['left_triangle'],record['right_triangle']
        entry=dict(left_triangle=i,right_triangle=j,overlap_length_m=record['overlap_length_m'])
        (potential if affected[i] or affected[j] else fixed).append(entry)
    return dict(schema='strep-native-self-edit-preflight-v1',rotations=rotations.copy(),
        faces_sha256=locations['faces_sha256'],pose_sha256=locations['pose_sha256'],
        affected_vertices=int(vertices.sum()),unaffected_vertices=int((~vertices).sum()),
        unaffected_vertex_ids=np.flatnonzero(~vertices).tolist(),unaffected_proper_pairs=fixed,
        potentially_affected_proper_pairs=potential,
        cannot_resolve_all_recorded_crossings_with_these_rotations=bool(fixed),
        feasibility_proven=False,translations_fixed=True,skin_weights_fixed=True,topology_fixed=True,
        quality_approved=False,release_approved=False,
        scope='Recorded proper crossings whose six vertices have no positive skin influence below any editable node remain unchanged under rotation-only edits. Other pairs are unresolved, not feasible or safe. No angular-range, contact, temporal or full collision certificate.')
