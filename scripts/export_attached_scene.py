"""Portable GLB containing one skinned actor and the authored box animation."""
import argparse
import json
import zipfile
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from scene_constraints import sample_object,pose
from gltf_tools import read_glb,write_glb,append_accessor,sample_animation


def export(folder,replace=False):
    folder=Path(folder).resolve();scene=read(folder/'scene.json');out=folder/'portable';out.mkdir(exist_ok=replace)
    if list(scene['actors'])!=['A'] or list(scene['objects'])!=['box']:raise ValueError('Current portable scene exporter requires actor A and box')
    entry=scene['actors']['A'];report=folder.parent;source=report/entry['preview_glb'];digest=sha256(source)
    doc,payload=read_glb(source);binary=bytearray(payload);actor_roots=doc['scenes'][doc.get('scene',0)]['nodes'][:]
    # Keep skinned mesh nodes at the scene root; their skin already uses world
    # joint transforms. Place the skeleton under the authored actor transform.
    skinned_roots=[n for n in actor_roots if 'skin' in doc['nodes'][n]]
    skeleton_roots=[n for n in actor_roots if n not in skinned_roots]
    actor_node=len(doc['nodes']);doc['nodes'].append(dict(name='Actor_A',children=skeleton_roots,translation=entry['transform']['translation_m'],rotation=entry['transform']['rotation_xyzw']))
    size=np.asarray(scene['objects']['box']['size_m']);vertices=[];normals=[]
    for axis in range(3):
        u,v=(axis+1)%3,(axis+2)%3
        for sign in [-1,1]:
            points=[];normal=np.zeros(3);normal[axis]=sign
            for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]:
                point=np.zeros(3);point[axis]=sign*size[axis]/2;point[u]=x*size[u]/2;point[v]=y*size[v]/2;points.append(point)
            for i in ([0,1,2,0,2,3] if sign>0 else [0,2,1,0,3,2]):vertices.append(points[i]);normals.append(normal)
    vertices=np.asarray(vertices);position=append_accessor(doc,binary,vertices,'VEC3');doc['accessors'][position].update(min=vertices.min(0).tolist(),max=vertices.max(0).tolist())
    normal=append_accessor(doc,binary,normals,'VEC3');material=len(doc['materials'])
    doc['materials'].append(dict(name='Box',pbrMetallicRoughness=dict(baseColorFactor=[.44,.26,.12,1],metallicFactor=0,roughnessFactor=.85)))
    mesh=len(doc['meshes']);doc['meshes'].append(dict(name='Contact_box',primitives=[dict(attributes=dict(POSITION=position,NORMAL=normal),material=material,mode=4)]))
    p,r=sample_object(scene['objects']['box'],scene['frame_count']);quats=Rotation.from_matrix(r).as_quat()
    for f in range(1,len(quats)):
        if np.dot(quats[f-1],quats[f])<0:quats[f]*=-1
    node=len(doc['nodes']);doc['nodes'].append(dict(name='Interaction_box',mesh=mesh,translation=p[0].tolist(),rotation=quats[0].tolist()))
    doc['scenes'][doc.get('scene',0)]['nodes']=[*skinned_roots,actor_node,node]
    animation=doc['animations'][0];animation['name']=scene['id'];times=append_accessor(doc,binary,np.arange(len(p))/30,'SCALAR')
    # Keep complete TRS tracks to avoid Godot's Euler fallback for rigid nodes.
    for prop,values,kind in [('translation',p,'VEC3'),('rotation',quats,'VEC4'),('scale',np.ones((len(p),3)),'VEC3')]:
        index=len(animation['samplers']);animation['samplers'].append(dict(input=times,output=append_accessor(doc,binary,values,kind),interpolation='LINEAR'))
        animation['channels'].append(dict(sampler=index,target=dict(node=node,path=prop)))
    events=read(folder/'events.json');doc.setdefault('extras',{})['strep_scene']=dict(fps=30,events=events,object_trajectory=scene['objects']['box']['trajectory_provenance'],human_approved=False)
    target=out/'scene.glb';write_glb(target,doc,binary);decoded,data=read_glb(target)
    motion=dict(np.load(ROOT/entry['motion']));origin,rotation=pose(entry['transform']);position_error=0.;rotation_error=0.
    for f in range(len(p)):
        world=sample_animation(decoded,data,0,f)
        position_error=max(position_error,float(np.abs(world[node,:3,3]-p[f]).max()),float(np.abs(world[1:78,:3,3]-(motion['posed_joints'][f]@rotation.T+origin)).max()))
        rotation_error=max(rotation_error,float(np.abs(world[node,:3,:3]-r[f]).max()),float(np.abs(world[1:78,:3,:3]-rotation@motion['global_rot_mats'][f]).max()))
    assert max(position_error,rotation_error)<1e-5 and sha256(source)==digest
    for name in ['events.json','object-track.json','attachment.json','evaluation.json','orientation-audit.json']:
        (out/name).write_bytes((folder/name).read_bytes())
    (out/'LICENSE.txt').write_bytes((report/'SOMA-preview-LICENSE.txt').read_bytes())
    save(out/'verification.json',dict(checked_at=now(),frames_checked=len(p),max_position_error_m=position_error,max_rotation_element_error=rotation_error,
        actor_glb_source_sha256=digest,scene_glb_sha256=sha256(target),exporter_sha256=sha256(__file__),engine_import=None,
        scope='Every-frame decoded GLB hierarchy matches actor and object tracks. Contact/collision failures remain; no engine playback or naturalness approval.'))
    with zipfile.ZipFile(folder/'scene-pack.zip','w',zipfile.ZIP_DEFLATED) as package:
        for file in out.iterdir():package.write(file,file.name)
    print(scene['id'],position_error,rotation_error)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path);parser.add_argument('--replace',action='store_true');args=parser.parse_args();export(args.folder,args.replace)
