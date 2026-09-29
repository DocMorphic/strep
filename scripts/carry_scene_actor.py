"""Carry a native actor clip with a baked rigid object, retaining relative motion."""
import argparse
import copy
import hashlib
from pathlib import Path
import shutil
import zipfile
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256
from gltf_tools import read_glb,write_glb,append_accessor,accessor
from rig_asset import RigAsset,parents_of
from rig_clip_import import AnimationSampler
from scene_constraints import pose
from scene_runtime import local,write as runtime
from retime_scene import native_motion


def transform(value):
    p,r=pose(value);m=np.eye(4);m[:3,:3]=r;m[:3,3]=p
    return m


def carry_export(actor_path,objects_path,object_id,placement,reference_frame,frames):
    """Factor P^-1 O(t) O(ref)^-1 P into nodes, avoiding a re-baked product."""
    rig=RigAsset.load(actor_path);doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
    objects,data=read_glb(objects_path)
    found=[i for i,n in enumerate(objects['nodes']) if n.get('extras',{}).get('strep_object_id')==object_id]
    if len(found)!=1:raise ValueError('Unique exported carrier object required')
    node=found[0];obj=objects['nodes'][node]
    if parents_of(objects)[node]!=-1 or 'matrix' in obj or not np.allclose(obj.get('scale',[1,1,1]),1,atol=1e-8):
        raise ValueError('Carrier requires a unit-scale root object TRS track')
    if any(type(n) is not int for n in [reference_frame,frames]) or not 3<=frames<=901 or not 0<=reference_frame<frames:
        raise ValueError('Reference must be inside a 3–901-frame scene')
    if len(doc.get('animations',[]))!=1 or len(objects.get('animations',[]))!=1:
        raise ValueError('One animation per export required')
    source=AnimationSampler(doc,binary,0);carrier=AnimationSampler(objects,data,0)
    if any(abs(s.duration-(frames-1)/30)>1e-5 for s in [source,carrier]):raise ValueError('Carrier and actor clocks differ')
    for target,prop,times,values,mode in carrier.channels:
        if target==node and (mode not in ['LINEAR','STEP'] or prop=='scale' and not np.allclose(values,1,atol=1e-8)):
            raise ValueError('Carrier requires rigid LINEAR/STEP animation')
    p=transform(placement);reference=carrier.sample(reference_frame/30)[node]
    if not np.allclose(reference[:3,:3].T@reference[:3,:3],np.eye(3),atol=1e-6):raise ValueError('Carrier is not rigid')
    first=len(doc['nodes']);roots=doc['scenes'][doc.get('scene',0)]['nodes'][:]
    prefix=f'StrepCarrier{first}'
    if any(n.get('name','').startswith(prefix) for n in doc['nodes']):raise ValueError('Carrier node identity collision')
    doc['nodes'].extend([
        dict(name=prefix+'World',matrix=np.linalg.inv(p).T.reshape(-1).tolist(),children=[first+1]),
        dict(name=prefix+'Motion',translation=obj.get('translation',[0,0,0]),rotation=obj.get('rotation',[0,0,0,1]),children=[first+2]),
        dict(name=prefix+'Offset',matrix=(np.linalg.inv(reference)@p).T.reshape(-1).tolist(),children=roots)])
    doc['scenes'][doc.get('scene',0)]['nodes']=[first]
    animation=doc['animations'][0]
    for target,prop,times,values,mode in carrier.channels:
        if target!=node:continue
        sampler=len(animation['samplers'])
        animation['samplers'].append(dict(input=append_accessor(doc,binary,times,'SCALAR'),output=append_accessor(doc,binary,values,'VEC4' if prop=='rotation' else 'VEC3'),interpolation=mode))
        animation['channels'].append(dict(sampler=sampler,target=dict(node=first+1,path=prop)))
    doc.setdefault('extras',{})['strep_carrier']=dict(object=object_id,reference_frame=reference_frame,
        source_actor_sha256=sha256(actor_path),source_objects_sha256=sha256(objects_path),
        scope='Baked object-relative carry; existing relative motion retained, no support correction or live attachment.')
    RigAsset(doc,binary);AnimationSampler(doc,binary,0)
    return doc,binary,node


def carried_native(motion,document,binary,carrier,object_node,placement,reference_frame,frames):
    result=native_motion(motion,document,binary,frames,frames)
    p=transform(placement);reference=carrier.sample(reference_frame/30)[object_node]
    changes=np.array([np.linalg.inv(p)@carrier.sample(f/30)[object_node]@np.linalg.inv(reference)@p for f in range(frames)])
    if 'smooth_root_pos' in result:
        result['smooth_root_pos']=np.einsum('fij,fj->fi',changes[:,:3,:3],motion['smooth_root_pos'])+changes[:,:3,3]
    if 'global_root_heading' in result:
        h=motion['global_root_heading'];directions=np.c_[h[:,0],np.zeros(frames),h[:,1]]
        transformed=np.einsum('fij,fj->fi',changes[:,:3,:3],directions)[:,[0,2]]
        norms=np.linalg.norm(transformed,axis=1)
        if np.any(norms<1e-6):raise ValueError('Carrier makes horizontal heading undefined')
        result['global_root_heading']=transformed/norms[:,None]
    return result


def audit_export(original,document,binary,carrier,node,placement,reference_frame,frames):
    rigs=[RigAsset.load(original),RigAsset(document,binary)]
    clocks=[AnimationSampler(r.document,r.binary,0) for r in rigs]
    p=transform(placement);reference=carrier.sample(reference_frame/30)[node]
    error=movement=depth=0.
    with threadpool_limits(limits=1):
        for i in range((frames-1)*4+1):
            time=i/120
            vertices=[r.vertices(c.sample(time))@p[:3,:3].T+p[:3,3] for r,c in zip(rigs,clocks)]
            obj=carrier.sample(time)[node]
            relative=[(v-m[:3,3])@m[:3,:3] for v,m in zip(vertices,[reference,obj])]
            error=max(error,float(np.linalg.norm(relative[1]-relative[0],axis=1).max()))
            movement=max(movement,float(np.linalg.norm(vertices[1]-vertices[0],axis=1).max()))
            depth=max(depth,-float(vertices[1][:,1].min()))
    if error>1e-5:raise ValueError('Carry changed object-relative skin motion')
    return dict(samples=(frames-1)*4+1,maximum_relative_skin_error_m=error,
        maximum_world_displacement_m=movement,maximum_world_floor_depth_m=depth,quality_approved=False,
        scope='All decoded mesh vertices at source 120 Hz. Relative-motion preservation and world floor diagnostic; no planted-foot, object/partner collision, force, balance or continuous-time approval.')


def run(source,output,actor,object_id,reference_frame=0):
    source,output=Path(source).resolve(),Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'reports'):raise ValueError('Fresh reports output required')
    scene=read(source/'portable-scene.json');clock=read(source/'scene-runtime.json')
    if scene['fps']!=30 or clock['fps']!=30 or clock['frames']!=scene['frame_count'] or set(clock['actors'])!=set(scene['actors']) or set(clock['objects'])!=set(scene['objects']):raise ValueError('Scene/runtime clocks or population differ')
    if actor not in scene['actors'] or object_id not in scene['objects']:raise ValueError('Select an existing actor and carrier')
    if any(e['ownership']!='baked_track' for e in clock['objects'].values()):raise ValueError('Carrier requires baked ownership')
    for f,key in [('portable-scene.json','source_scene_sha256'),('events.json','source_events_sha256')]:
        if sha256(source/f)!=clock[key]:raise ValueError('Scene/events changed')
    files={str(source/n):sha256(source/n) for n in ['portable-scene.json','events.json','scene-runtime.json','SOMA-LICENSE.txt']}
    for name,a in scene['actors'].items():
        if a['transform']!=clock['actors'][name]['placement']:raise ValueError('Actor placement changed')
        for field,digest in [('motion',a['source_sha256']),('preview_glb',clock['actors'][name]['sha256'])]:
            path=local(source,a[field])
            if sha256(path)!=digest:raise ValueError('Actor input changed')
            files[str(path)]=digest
    objects=local(source,scene['objects_glb'])
    if sha256(objects)!=clock['object_clip']['sha256']:raise ValueError('Object export changed')
    files[str(objects)]=sha256(objects)
    exact=source/'retime-contact-windows.json'
    if exact.exists():files[str(exact)]=sha256(exact)
    a=scene['actors'][actor];frames=scene['frame_count']
    doc,binary,node=carry_export(local(source,a['preview_glb']),objects,object_id,a['transform'],reference_frame,frames)
    carrier=AnimationSampler(*read_glb(objects),0)
    motion=carried_native(dict(np.load(local(source,a['motion']),allow_pickle=False)),doc,binary,carrier,node,a['transform'],reference_frame,frames)
    audit=audit_export(local(source,a['preview_glb']),doc,binary,carrier,node,a['transform'],reference_frame,frames)
    if any(sha256(p)!=digest for p,digest in files.items()):raise ValueError('Inputs changed during carry')
    output.mkdir(parents=True)
    result=copy.deepcopy(scene)
    for index,(name,entry) in enumerate(result['actors'].items()):
        folder=output/'actors'/str(index);folder.mkdir(parents=True)
        if name==actor:
            write_glb(folder/'actor.glb',doc,binary);np.savez_compressed(folder/'motion.npz',**motion)
        else:
            shutil.copyfile(local(source,entry['preview_glb']),folder/'actor.glb');shutil.copyfile(local(source,entry['motion']),folder/'motion.npz')
        entry.update(motion=f'actors/{index}/motion.npz',preview_glb=f'actors/{index}/actor.glb',source_sha256=sha256(folder/'motion.npz'))
    shutil.copyfile(objects,output/'objects.glb');result['objects_glb']='objects.glb';result['id']+='-carry-'+actor
    for name in ['events.json','SOMA-LICENSE.txt']:
        shutil.copyfile(source/name,output/name)
    if exact.exists():shutil.copyfile(exact,output/exact.name)
    save(output/'portable-scene.json',result);save(output/'source-scene.json',scene)
    save(output/'carry-audit.json',audit)
    save(output/'carry-recipe.json',dict(actor=actor,object=object_id,reference_frame=reference_frame,inputs=files,
        implementation={n:sha256(ROOT/'scripts'/n) for n in ['carry_scene_actor.py','retime_scene.py','scene_runtime.py','scene_animation_curves.py','rig_asset.py','rig_clip_import.py','gltf_tools.py']},quality_approved=False,
        scope='Existing animation carried by the selected exported object. Relative pose, mesh, actor placement and event times retained. Native poses and heading updated; predicted foot labels retained as predictions. Ground, other-object and partner contacts may be invalidated and require review; no automatic floor/foot fit or physics attachment.'))
    runtime(output)
    manifest={p.relative_to(output).as_posix():sha256(p) for p in output.rglob('*') if p.is_file()}
    save(output/'package-manifest.json',dict(files=manifest,quality_approved=False))
    with zipfile.ZipFile(output/'scene-runtime.zip','x',zipfile.ZIP_DEFLATED) as archive:
        for name in [*manifest,'package-manifest.json']:archive.write(output/name,name)
    with zipfile.ZipFile(output/'scene-runtime.zip') as archive:
        if archive.testzip() or any(hashlib.sha256(archive.read(n)).hexdigest()!=d for n,d in manifest.items()):raise ValueError('Carry archive verification failed')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--actor',required=True);p.add_argument('--object',required=True,dest='object_id')
    p.add_argument('--reference-frame',type=int,default=0)
    a=p.parse_args();run(a.source,a.output,a.actor,a.object_id,a.reference_frame)
