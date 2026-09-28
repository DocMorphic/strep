"""Persist a complete sphere release job from a recorded development actor/track."""
import argparse
import shutil
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from scene_release_job import metadata,prepare,run


def study(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    if not output.is_relative_to(ROOT/'reports/scene-release-jobs'):raise ValueError('Study must be in the saved scene release collection')
    source=ROOT/'reports/object-release-v2/seed-11-original/palm.json';bundle=read(source)
    collection=output/'authored';collection.mkdir()
    for name,entry in bundle['scene']['actors'].items():
        destination=collection/'actors'/name/'actor.glb';destination.parent.mkdir(parents=True)
        shutil.copyfile(source.parent.parent/entry['preview_glb'],destination)
        entry['preview_glb']=destination.relative_to(collection).as_posix()
    obj=bundle['scene']['objects']['box'];obj.pop('shape');obj.pop('size_m')
    obj['geometry']=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.25)
    obj['trajectory_provenance']='Authored spherical release fixture using a previous box trajectory; not sphere-conditioned motion generation.'
    for contact in bundle['scene']['contacts']:
        point=np.array(contact['target']['point_m']);contact['target']['point_m']=(point*.25/np.linalg.norm(point)).tolist()
    bundle['scene']['id']='sphere-release-development'
    bundle['scene']['review_note']='Development fixture. Contact targets projected to sphere; actor unchanged. Grasp/reaction quality unapproved.'
    bundle['scene']['objects']['moving-prop']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.2),
        keyframes=[dict(frame=0,translation_m=[4,.2,0],rotation_xyzw=[0,0,0,1]),dict(frame=179,translation_m=[4.3,.2,0],rotation_xyzw=[0,0,0,1])],trajectory_provenance='Authored distant prescribed collider; contact impact tested separately.')
    save(collection/'palm.json',bundle);save(collection/'manifest.json',dict(scenes=[dict(variants=dict(palm='palm.json'))]))
    if (source.parent/'events.json').exists():shutil.copyfile(source.parent/'events.json',collection/'events.json')
    url='/files/'+collection.relative_to(ROOT/'reports').as_posix()+'/palm.json'
    payload=dict(source_url=url,revision=metadata(url)['revision'],object='box',release_frame=121,mass_kg=3.,friction=.4,restitution=.1,collision_mode='moving_scene',label='Sphere release development')
    save(output/'protocol.json',dict(at=now(),source_sha256=sha256(source),fixture_sha256=sha256(collection/'palm.json'),preparer_sha256=sha256(__file__),
        scope='One existing actor and two authored sphere tracks. Verify retained prefix, actual collision shapes/inertia, baked export and import. Not a grasp or human quality test.',quality_approved=False))
    prepare(payload,output/'job');run(output/'job')
    print(dict(job=str(output/'job'),status=read(output/'job/pipeline.json')['status'],quality_approved=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);args=parser.parse_args();study(args.output)
