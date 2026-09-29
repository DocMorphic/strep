"""Portable finite playback manifest: one owner for actors and baked objects."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
import numpy as np
from strep import ROOT,read,save,sha256,now
from scene_constraints import pose
from scene_object_export import export_objects
from gltf_tools import read_glb,accessor
from object_geometry import scene_geometry


def local(folder,name):
    if not isinstance(name,str) or not name or '\\' in name or ':' in name or any(p in ('','.','..') for p in name.split('/')): raise ValueError('Relative package path required')
    path=(folder/name).resolve()
    if not path.is_relative_to(folder.resolve()) or not path.is_file(): raise ValueError('Package asset missing/outside folder')
    return path


def import_rate(path):
    """Keep uniform exported keys on their own clock when Godot bakes tracks."""
    doc,binary=read_glb(path)
    if len(doc.get('animations',[]))!=1:raise ValueError('One scene animation required')
    clocks=[accessor(doc,binary,s['input']) for s in doc['animations'][0]['samplers']]
    if not clocks:raise ValueError('Animated scene tracks required')
    first=clocks[0]
    if len(first)<2 or first.ndim!=1 or not np.isfinite(first).all() or first[0]!=0 or np.any(np.diff(first)<=0):
        raise ValueError('Invalid scene animation clock')
    if any(c.shape!=first.shape or not np.array_equal(c,first) for c in clocks) or not np.allclose(first,np.linspace(0,first[-1],len(first)),rtol=0,atol=1e-5):
        raise ValueError('Runtime import currently requires a common uniform export key clock')
    rate=float((len(first)-1)/first[-1])
    if not .01<=rate<=30000:raise ValueError('Unsupported scene import sampling rate')
    return rate


def write(folder):
    folder=Path(folder).resolve();scene=read(folder/'portable-scene.json')
    frames=scene['frame_count']
    if type(frames) is not int or not 3<=frames<=1800 or scene['fps']!=30: raise ValueError('Scene requires 3–1800 frames at 30 fps')
    if not 1<=len(scene['actors'])<=4 or len(scene.get('objects',{}))>8: raise ValueError('Scene supports 1–4 actors and 0–8 objects')
    actors={};objects={}
    for id,entry in scene['actors'].items():
        pose(entry['transform'])
        source=local(folder,entry['motion']);glb=local(folder,entry['preview_glb'])
        if sha256(source)!=entry['source_sha256']: raise ValueError('Scene actor source hash mismatch')
        with np.load(source,allow_pickle=False) as motion:
            if motion['root_positions'].shape!=(frames,3): raise ValueError('Scene actor frame count mismatch')
        actors[id]=dict(path=entry['preview_glb'],sha256=sha256(glb),placement=entry['transform'],bake_fps=import_rate(glb))
    object_clip=None
    if scene.get('objects'):
        path=local(folder,scene['objects_glb']);document,_=read_glb(path)
        for id in scene['objects']:
            found=[n for n in document['nodes'] if n.get('extras',{}).get('strep_object_id')==id]
            if len(found)!=1: raise ValueError('Object GLB identity missing or ambiguous')
            geometry=scene_geometry(scene['objects'][id]);declared=found[0].get('extras',{}).get('strep_geometry')
            if declared is not None and declared!=geometry.record(): raise ValueError('Object GLB geometry differs from scene')
            if declared is None and 'geometry' in scene['objects'][id]: raise ValueError('Versioned object geometry missing from GLB')
            objects[id]=dict(node_name=found[0]['name'],ownership='baked_track')
        object_clip=dict(path=scene['objects_glb'],sha256=sha256(path),bake_fps=import_rate(path))
    events=read(folder/'events.json')
    if events['fps']!=30 or not isinstance(events['events'],list) or len(events['events'])>4096: raise ValueError('Invalid scene event document')
    markers=[]
    for index,event in enumerate(events['events']):
        frame=event.get('frame');time=event.get('time_s')
        if type(frame) not in (int,float) or not np.isfinite(frame) or not 0<=frame<=frames or type(time) not in (float,int) or not np.isfinite(time) or abs(time-frame/30)>1e-8: raise ValueError('Scene marker clock mismatch')
        if not isinstance(event.get('type'),str) or not event['type']: raise ValueError('Scene marker type required')
        if 'actor' in event and event['actor'] not in actors or 'object' in event and event['object'] not in objects: raise ValueError('Scene marker references unknown participant')
        digest=hashlib.sha256(json.dumps(event,sort_keys=True).encode()).hexdigest()[:16]
        markers.append(dict(id=f'event-{index}-{digest}',frame=frame,payload=event))
    markers.sort(key=lambda m:m['frame'])
    rates=[a['bake_fps'] for a in actors.values()]+([object_clip['bake_fps']] if object_clip else [])
    data=dict(schema='strep-runtime-scene-v2' if any(float(m['frame'])!=int(m['frame']) for m in markers) or any(abs(rate-30)>1e-5 for rate in rates) else 'strep-runtime-scene-v1',fps=30,frames=frames,actors=actors,objects=objects,markers=markers,source_scene_sha256=sha256(folder/'portable-scene.json'),source_events_sha256=sha256(folder/'events.json'),release_approved=False,scope='Shared finite baked-scene playback. Authored event notifications are not verified contacts or physics commands. Objects retain baked ownership; do not also drive them with live physics.')
    if object_clip: data['object_clip']=object_clip
    save(folder/'scene-runtime.json',data)
    shutil.copyfile(ROOT/'scripts/godot_scene_clock.gd',folder/'godot_scene_clock.gd')
    shutil.copyfile(ROOT/'integrations/godot/SCENES.md',folder/'GODOT-SCENES.md')
    return data


def package(source_file,output):
    source_file=Path(source_file).resolve();output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    original=read(source_file);scene=copy.deepcopy(original.get('scene',original));source=source_file.parent
    save(output/'source-scene.json',original)
    for index,(id,entry) in enumerate(scene['actors'].items()):
        motion=(source/entry['motion']).resolve()
        if not motion.is_file(): motion=(ROOT/entry['motion']).resolve()
        if sha256(motion)!=entry['source_sha256']: raise ValueError('Actor source changed')
        glb=(source/entry['preview_glb']).resolve()
        folder=output/'actors'/str(index);folder.mkdir(parents=True)
        shutil.copyfile(motion,folder/'motion.npz');shutil.copyfile(glb,folder/'actor.glb')
        entry['motion']=f'actors/{index}/motion.npz';entry['preview_glb']=f'actors/{index}/actor.glb'
    if scene.get('objects'):
        if scene.get('objects_glb'): shutil.copyfile(source/scene['objects_glb'],output/'objects.glb')
        else: export_objects(scene,output/'objects.glb')
        scene['objects_glb']='objects.glb'
    if (source/'events.json').exists(): shutil.copyfile(source/'events.json',output/'events.json')
    else:
        from package_generated_scenes import contact_events
        save(output/'events.json',contact_events(scene))
    save(output/'portable-scene.json',scene)
    evidence=output/'evaluation';evidence.mkdir()
    for name in ('completion.json','source-evidence.json','geometry-summary.json','bounds-summary.json','release-audit.json','orientation-audit.json','body-comparison.json'):
        if (source/name).exists(): shutil.copyfile(source/name,evidence/name)
    # This packager's current inputs are Strep's native SOMA study scenes.
    shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',output/'SOMA-LICENSE.txt')
    data=write(output)
    files={p.relative_to(output).as_posix():sha256(p) for p in output.rglob('*') if p.is_file()}
    manifest=dict(at=now(),source=str(source_file),source_sha256=sha256(source_file),files=files,quality_approved=False)
    save(output/'package-manifest.json',manifest)
    with zipfile.ZipFile(output/'scene-runtime.zip','x',zipfile.ZIP_DEFLATED) as archive:
        for path in files: archive.write(output/path,path)
        archive.write(output/'package-manifest.json','package-manifest.json')
    with zipfile.ZipFile(output/'scene-runtime.zip') as archive:
        assert archive.testzip() is None
        assert all(hashlib.sha256(archive.read(p)).hexdigest()==h for p,h in files.items())
    return data


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source');parser.add_argument('output')
    args=parser.parse_args();data=package(args.source,args.output);print(dict(actors=len(data['actors']),objects=len(data['objects']),markers=len(data['markers'])))
