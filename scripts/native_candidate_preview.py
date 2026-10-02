"""CPU native-candidate visualization on the source's unchanged SOMA77 skin."""
import copy
import numpy as np
from scipy.spatial.transform import Rotation
from gltf_tools import read_glb,write_glb,accessor,append_accessor,hierarchy,sample_animation,authored_animation


def native_world(local,roots,offsets,parents):
    local=np.asarray(local,float);roots=np.asarray(roots,float);offsets=np.asarray(offsets,float)
    if (local.ndim!=4 or local.shape[1:]!=(77,3,3) or roots.shape!=(len(local),3)
        or offsets.shape!=(77,3) or len(parents)!=77 or parents[0]!=-1
        or any(type(p) is not int or not 0<=p<j for j,p in enumerate(parents[1:],1))
        or not all(np.isfinite(a).all() for a in (local,roots,offsets))
        or np.max(np.abs(local@local.transpose(0,1,3,2)-np.eye(3)))>1e-4
        or np.max(np.abs(np.linalg.det(local)-1))>1e-4):
        raise ValueError('Proper native rotations, roots, fixed offsets and ordered hierarchy required')
    world=np.tile(np.eye(4),(len(local),77,1,1));world[:,0,:3,:3]=local[:,0];world[:,0,:3,3]=roots
    for j,p in enumerate(parents[1:],1):
        world[:,j,:3,:3]=world[:,p,:3,:3]@local[:,j]
        world[:,j,:3,3]=world[:,p,:3,3]+np.einsum('fij,j->fi',world[:,p,:3,:3],offsets[j])
    return world


def source_offsets(source,parents):
    local=np.asarray(source['local_rot_mats']);roots=np.asarray(source['root_positions'])
    positions=np.asarray(source['posed_joints']);rotations=np.asarray(source['global_rot_mats'])
    if positions.shape!=(len(local),77,3) or rotations.shape!=local.shape or len(local)<2 or not np.isfinite(positions).all() or not np.isfinite(rotations).all():
        raise ValueError('Complete finite original native geometry required')
    offsets=np.zeros((77,3))
    if len(parents)!=77 or parents[0]!=-1 or any(type(p) is not int or not 0<=p<j for j,p in enumerate(parents[1:],1)):
        raise ValueError('Ordered native hierarchy required')
    for j,p in enumerate(parents[1:],1):offsets[j]=rotations[0,p].T@(positions[0,j]-positions[0,p])
    world=native_world(local,roots,offsets,parents)
    if np.max(np.linalg.norm(world[:,:,:3,3]-positions,axis=-1))>1e-5 or np.max(np.abs(world[:,:,:3,:3]-rotations))>1e-5:
        raise ValueError('Original motion does not reconstruct with a fixed native skeleton')
    return offsets


def skin_points(document,binary,world):
    """Use all eight original influences, without renormalizing or truncating."""
    attrs=document['meshes'][0]['primitives'][0]['attributes'];skin=document['skins'][0]
    points=np.c_[accessor(document,binary,attrs['POSITION']),np.ones(document['accessors'][attrs['POSITION']]['count'])]
    raw_joints=np.concatenate([accessor(document,binary,attrs['JOINTS_'+str(i)]) for i in range(2)],axis=1)
    if not np.issubdtype(raw_joints.dtype,np.integer):raise ValueError('Original integer skin joint indices required')
    joints=raw_joints.astype(int)
    weights=np.concatenate([accessor(document,binary,attrs['WEIGHTS_'+str(i)]) for i in range(2)],axis=1)
    if joints.shape!=weights.shape or joints.shape!=(len(points),8) or np.any(joints<0) or np.any(joints>=77) or not np.isfinite(points).all() or not np.isfinite(weights).all() or np.any(weights<0):
        raise ValueError('Finite original eight-influence skin required')
    inverse=accessor(document,binary,skin['inverseBindMatrices'])
    if inverse.shape!=(77,4,4) or not np.isfinite(inverse).all():raise ValueError('Finite native inverse bind matrices required')
    transforms=world[skin['joints']]@inverse
    posed=np.einsum('nvij,nj->nvi',transforms[joints],points)
    return np.sum(posed[:,:,:3]*weights[:,:,None],axis=1)


def export_candidate(source_preview,original,local,roots,names,parents,output):
    """Preserve geometry/materials/skin; replace only selected clip pose channels."""
    document,binary=read_glb(source_preview)
    preserved={key:copy.deepcopy(document.get(key)) for key in ('meshes','skins','materials','images','textures')}
    if (len(document.get('skins',[]))!=1 or len(document.get('meshes',[]))!=1
        or len(document['meshes'][0]['primitives'])!=1 or len(document.get('nodes',[]))!=78
        or any(row.get('uri') and not row['uri'].startswith('data:') for kind in ('buffers','images') for row in document.get(kind,[]))):
        raise ValueError('Self-contained native SOMA body and one skin required')
    joints=document['skins'][0]['joints'];links=hierarchy(document)
    if (len(joints)!=77 or len(set(joints))!=77 or [document['nodes'][n].get('name') for n in joints]!=names
        or joints!=list(range(1,78)) or links[0]!=-1 or document['nodes'][0].get('mesh')!=0
        or document['nodes'][0].get('skin')!=0 or links[joints[0]]!=-1
        or any(links[joints[j]]!=joints[p] for j,p in enumerate(parents[1:],1))
        or any('matrix' in n or n.get('scale',[1,1,1])!=[1,1,1] for n in document['nodes'])
        or document['nodes'][0].get('translation',[0,0,0])!=[0,0,0]
        or document['nodes'][0].get('rotation',[0,0,0,1])!=[0,0,0,1]):
        raise ValueError('Original standard native node identities and hierarchy required')
    offsets=source_offsets(original,parents);expected=native_world(local,roots,offsets,parents)
    document=copy.deepcopy(document);payload=bytearray(binary)
    times=append_accessor(document,payload,np.arange(len(local),dtype=np.float32)/30,'SCALAR')
    animation=authored_animation('Native authored candidate')
    for j,node in enumerate(joints):
        q=Rotation.from_matrix(np.asarray(local)[:,j]).as_quat()
        for frame in range(1,len(q)):
            if np.dot(q[frame-1],q[frame])<0:q[frame]*=-1
        translations=np.asarray(roots) if j==0 else np.repeat(offsets[j][None],len(local),axis=0)
        for prop,values,kind in [('translation',translations,'VEC3'),('rotation',q,'VEC4')]:
            index=append_accessor(document,payload,values,kind);sampler=len(animation['samplers'])
            animation['samplers'].append({'input':times,'output':index,'interpolation':'LINEAR'})
            animation['channels'].append({'sampler':sampler,'target':{'node':node,'path':prop}})
    document['animations']=[animation]
    document.setdefault('extras',{})['native_candidate_preview']={'schema':'strep-native-candidate-preview-v1','fps':30,'frames':len(local),'quality_approved':False}
    write_glb(output,document,payload);decoded,stored=read_glb(output)
    position_error=rotation_error=surface_error=0.
    for frame in range(len(local)):
        actual=sample_animation(decoded,stored,0,frame)
        position_error=max(position_error,float(np.linalg.norm(actual[joints,:3,3]-expected[frame,:,:3,3],axis=-1).max()))
        rotation_error=max(rotation_error,float(np.abs(actual[joints,:3,:3]-expected[frame,:,:3,:3]).max()))
        reference=actual.copy();reference[joints]=expected[frame]
        surface_error=max(surface_error,float(np.linalg.norm(skin_points(decoded,stored,actual)-skin_points(decoded,stored,reference),axis=-1).max()))
    if max(position_error,rotation_error,surface_error)>1e-5:raise ValueError('Serialized native candidate exceeds preview geometry tolerance')
    if stored[:len(binary)]!=binary:raise ValueError('Original mesh/skin payload changed')
    for section,value in preserved.items():
        if decoded.get(section)!=value:raise ValueError('Original skin/material content changed')
    return {'frames':len(local),'fps':30,'duration_s':float((len(local)-1)/30),
            'max_joint_error_m':position_error,'max_rotation_error':rotation_error,'max_skin_error_m':surface_error,
            'all_eight_influences_preserved':True,'quality_approved':False}
