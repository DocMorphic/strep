"""Compile selected shared-scene points into versioned actor-native tracks.

An actor target is sampled from the supplied source motion, never silently
updated during fitting. Reciprocal constraints are not a coupled actor solve.
World or object targets allow several actors to share the same authored goal.
"""
import argparse
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from scene_constraints import pose,sample_object,transform_motion,target_track
from inspect_motion import validate_motion
from contact_spec import validate
from support_contact import regions
from build_soma_preview import ASSET


def compile_contacts(scene,actor_id,contact_ids,skin,project_root=ROOT):
    if scene.get('schema_version')!=1 or scene.get('fps')!=30:raise ValueError('Scene schema/fps mismatch')
    frames=scene.get('frame_count')
    if type(frames)!=int or not 3<=frames<=1800:raise ValueError('Invalid scene duration')
    if actor_id not in scene['actors']:raise ValueError('Unknown source actor')
    if not contact_ids or len(contact_ids)!=len(set(contact_ids)):raise ValueError('Select distinct contact ids explicitly')
    contacts=scene.get('contacts',[])
    if len({c['id'] for c in contacts})!=len(contacts):raise ValueError('Duplicate scene contact ids')
    selected=[c for c in contacts if c['id'] in contact_ids]
    if len(selected)!=len(contact_ids) or any(c['actor']!=actor_id for c in selected):raise ValueError('Selected contacts must belong to source actor')
    origin,rotation=pose(scene['actors'][actor_id]['transform'])
    if abs(origin[1])>1e-7 or not np.allclose(rotation@[0.,1.,0.],[0.,1.,0.],atol=1e-7):
        raise ValueError('Current floor solver requires source actor on Y=0 with yaw-only placement')
    actors={};sources={};root=Path(project_root).resolve()
    for name,entry in scene['actors'].items():
        path=(root/entry['motion']).resolve()
        if not path.is_relative_to(root):raise ValueError('Motion escapes project')
        digest=sha256(path)
        if entry.get('source_sha256') and entry['source_sha256']!=digest:raise ValueError('Actor source hash mismatch')
        motion=dict(np.load(path,allow_pickle=False));validate_motion(motion,30)
        if len(motion['root_positions'])!=frames:raise ValueError('Actor clock/duration mismatch')
        actors[name]=transform_motion(motion,entry['transform'])
        sources[name]=dict(path=entry['motion'],sha256=digest)
    objects={name:sample_object(obj,frames) for name,obj in scene.get('objects',{}).items()}
    groups=regions(skin);spec=dict(schema_version=2,fps=30,frame_count=frames,regions={});compiled=[]
    for c in selected:
        effector=c['effector'];region=effector.get('joint');vertex=effector.get('surface_vertex')
        if region not in groups or type(vertex)!=int or vertex not in groups[region]:
            raise ValueError('Selected contact requires an explicit skin vertex in its support region')
        a,b=c['start_frame'],c['end_frame']
        if type(a)!=int or type(b)!=int or not 0<=a<=b<frames:raise ValueError('Contact interval outside scene')
        world=target_track(c['target'],actors,objects,frames,skin)
        native=(world-origin)@rotation
        segment=dict(start_frame=a,end_frame=b,space='track',positions_m=native[a:b+1].tolist(),vertex_id=vertex)
        spec['regions'].setdefault(region,dict(mode='explicit',segments=[]))['segments'].append(segment)
        compiled.append(dict(contact_id=c['id'],region=region,vertex_id=vertex,start_frame=a,end_frame=b,
            target=c['target'],target_provenance='Frozen source actor surface/joint track' if c['target']['space']=='actor' else 'Authored scene trajectory'))
    for entry in spec['regions'].values():entry['segments'].sort(key=lambda s:s['start_frame'])
    validate(spec,frames,groups)
    return spec,dict(scene_id=scene['id'],actor=actor_id,contacts=compiled,sources=sources,
        coordinate_space='Actor native metres, Y-up. Inverse of the recorded scene transform.',actor_transform=scene['actors'][actor_id]['transform'],
        scope='Point trajectories only. Not scene-conditioned model inference, attachment, orientation fitting, collision avoidance, force or joint partner optimization.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('scene',type=Path);parser.add_argument('--actor',required=True)
    parser.add_argument('--contact',action='append',required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    scene=read(args.scene);scene=scene.get('scene',scene)
    spec,record=compile_contacts(scene,args.actor,args.contact,dict(np.load(ASSET)))
    args.output.mkdir(parents=True,exist_ok=False)
    save(args.output/'contact-spec.json',spec)
    save(args.output/'compilation.json',dict(**record,created_at=now(),scene_file_sha256=sha256(args.scene),mesh_sha256=sha256(ASSET),compiler_sha256=sha256(__file__)))
    save(args.output/'scene.json',scene)
    print(args.output)
