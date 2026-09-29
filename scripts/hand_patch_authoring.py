"""Canonical hand triangles for visual selection and explicit region requests."""
import numpy as np
from scene_region_contact import SCHEMA, mesh_fingerprint, validate_binding


def hand_mesh(skin, hand):
    if hand not in ('LeftHand','RightHand'):
        raise ValueError('Select a supported hand')
    names=list(map(str,skin['rig_joint_names']))
    allowed=np.array([n.startswith(hand) for n in names])
    supported=np.all(allowed[skin['lbs_indices']] | (skin['lbs_weights']==0),axis=1)
    triangles=skin['faces'];points=skin['bind_vertices'][triangles]
    area=np.linalg.norm(np.cross(points[:,1]-points[:,0],points[:,2]-points[:,0]),axis=1)
    faces=np.flatnonzero(supported[triangles].all(axis=1)&(area>1e-12))
    ids=np.unique(triangles[faces])
    return dict(mesh_sha256=mesh_fingerprint(skin),hand=hand,vertex_count=len(skin['bind_vertices']),
        face_count=len(triangles),joint_names=names,
        inverse_bind_matrices=np.linalg.inv(skin['bind_rig_transform'].astype(float)).transpose(0,2,1).astype(np.float32).reshape(-1,16).tolist(),
        faces=[dict(id=int(f),vertices=triangles[f].tolist()) for f in faces],
        vertices=[dict(id=int(v),position=skin['bind_vertices'][v].astype(np.float32).tolist(),
            joints=skin['lbs_indices'][v].tolist(),weights=skin['lbs_weights'][v].astype(np.float32).tolist()) for v in ids])


def custom_patch(skin, contact, edit):
    ids=edit['patch_face_ids']
    if (not isinstance(ids,list) or not ids or len(ids)>512 or any(type(i)!=int for i in ids)
            or len(set(ids))!=len(ids) or min(ids)<0 or max(ids)>=len(skin['faces'])):
        raise ValueError('Select unique valid hand triangles (at most 512)')
    binding=dict(schema=SCHEMA,mesh_sha256=edit['patch_mesh_sha256'],hand=contact['effector']['joint'],
                 face_ids=sorted(ids),limits=edit['limits'])
    vertices=np.unique(skin['faces'][ids]);old=contact['effector']['surface_vertex']
    anchor=int(vertices[np.linalg.norm(skin['bind_vertices'][vertices]-skin['bind_vertices'][old],axis=1).argmin()])
    validate_binding(binding,dict(joint=binding['hand'],surface_vertex=anchor),skin)
    return binding,anchor
