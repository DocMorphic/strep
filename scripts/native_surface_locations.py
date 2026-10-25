"""Locate every recorded self-surface flag without changing its disposition.

Skin influences are location hints, not anatomical labels. Duplicate loaded
position/influence attributes are diagnostics, never automatic seam exemptions.
Caller must bind the audit, rig and sampled pose; this does not redo the screen.
"""
from collections import Counter
import copy
import hashlib
import math
import numpy as np
from native_scene_geometry import faces_for
from native_self_surface import METHOD


def require(ok,message):
    if not ok:raise ValueError(message)


def locate(rig,matrices,audit):
    matrices=np.asarray(matrices,float)
    require(matrices.shape==(len(rig.document['nodes']),4,4) and np.isfinite(matrices).all(),'Complete finite node pose required')
    faces,population=faces_for(rig);vertices=rig.vertices(matrices)
    digest=hashlib.sha256(faces.astype('<i8').tobytes()).hexdigest()
    require(audit.get('schema')=='strep-native-self-surface-v1' and audit.get('status')=='complete'
        and audit.get('method')==METHOD and audit.get('complete_triangle_population') is True
        and audit.get('faces_sha256')==digest and audit.get('triangles')==len(faces)
        and audit.get('vertices')==len(vertices),'Complete matching self-surface population required')
    require(audit.get('self_collision_free_certified') is False and audit.get('quality_approved') is False,'Unapproved diagnostic required')
    records=audit['records'];seen=set();used=set()
    require(isinstance(records,list) and len(records)<=100000,'Complete bounded record list required')
    for row in records:
        i,j=row['left_triangle'],row['right_triangle']
        require(type(i) is int and type(j) is int and 0<=i<j<len(faces) and (i,j) not in seen,'Unique ordered triangle pair required')
        require(row['kind'] in ('proper_crossing','coplanar_or_near_parallel_overlap','boundary_or_near_contact'),'Recorded flag kind required')
        overlap=row['overlap_length_m']
        require((overlap is None and row['kind']!='proper_crossing')
            or type(overlap) in (int,float) and math.isfinite(overlap) and overlap>=0,'Finite crossing overlap or unresolved boundary required')
        require(type(row['shared_vertices']) is int and row['shared_vertices']==len(set(faces[i])&set(faces[j])),'Shared vertex identity changed')
        seen.add((i,j));used.update((i,j))
    bad=audit['degenerate_faces']
    require(isinstance(bad,list) and all(type(i) is int and 0<=i<len(faces) for i in bad) and len(set(bad))==len(bad),'Unique existing degenerate faces required')
    used.update(bad)
    attributes=[];signatures=[];face_owners=[]
    for primitive,part in zip(rig.primitives,population):
        node=primitive['node'];mesh=rig.document['meshes'][rig.document['nodes'][node]['mesh']]
        source=mesh['primitives'][primitive['primitive']]
        face_owners.extend([dict(node=node,primitive=primitive['primitive'],material=source.get('material'))]*part['faces'])
        for v,point in enumerate(primitive['positions']):
            weights={}
            if primitive['joints'] is not None:
                for joint in set(map(int,primitive['joints'][v])):
                    weight=math.fsum(float(w) for j,w in zip(primitive['joints'][v],primitive['weights'][v]) if j==joint)
                    if weight:weights[int(rig.joints[joint])]=weight
            attributes.append(weights)
            # RigAsset's existing normalization is part of the native reader.
            # No raw-import equivalence or different-rig equivalence is asserted.
            signatures.append((('skin',) if primitive['joints'] is not None else ('node',node),
                tuple(map(float,point)),tuple(sorted(weights.items()))))
    triangles={};vertex_ids=set()
    for number in sorted(used):
        ids=list(map(int,faces[number]));vertex_ids.update(ids);weights={}
        for v in ids:
            for joint,w in attributes[v].items():weights.setdefault(joint,[]).append(w/3)
        influences=sorted(((joint,math.fsum(w)) for joint,w in weights.items()),key=lambda x:(-x[1],x[0]))
        triangles[str(number)]=dict(**face_owners[number],vertex_ids=ids,
            centroid_world_m=vertices[ids].mean(axis=0).tolist(),
            dominant_joint=None if not influences else influences[0][0],
            mean_skin_influences=[dict(node=j,name=rig.document['nodes'][j].get('name'),weight=w) for j,w in influences])
    localized=[];regions=Counter()
    for row in records:
        entry=copy.deepcopy(row);i,j=row['left_triangle'],row['right_triangle']
        entry['duplicate_loaded_attribute_pairs']=[[int(a),int(b)] for a in faces[i] for b in faces[j]
            if a!=b and signatures[a]==signatures[b]]
        localized.append(entry)
        left=triangles[str(i)]['dominant_joint'];right=triangles[str(j)]['dominant_joint']
        pair=tuple(sorted((left,right),key=lambda x:-1 if x is None else x));regions[(row['kind'],*pair)]+=1
    return dict(schema='strep-native-surface-locations-v1',faces_sha256=digest,
        pose_sha256=hashlib.sha256(matrices.astype('<f8').tobytes()).hexdigest(),
        audit_method=METHOD,record_count=len(records),records=localized,degenerate_faces=copy.deepcopy(bad),triangles=triangles,
        vertices_world_m={str(i):vertices[i].tolist() for i in sorted(vertex_ids)},
        regions=[dict(kind=k[0],joint_nodes=list(k[1:]),records=n) for k,n in sorted(regions.items(),key=lambda x:(-x[1],str(x[0])))],
        loaded_weight_convention='RigAsset normalized weights; native sampled pose only',
        flags_exempted=0,topology_modified=False,pose_modified=False,self_collision_free_certified=False,quality_approved=False,
        scope='Complete location metadata for supplied flags, not a fresh surface screen or anatomical diagnosis. Exact duplicate loaded attributes never remove a crossing or authorize welding.')
