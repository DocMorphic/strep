"""Freeze and run a paired prop/body collision experiment, without new motion."""
import argparse
import copy
import shutil
import numpy as np
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from scene_constraints import evaluate,pose
from build_soma_preview import ASSET
from scene_release_job import metadata,prepare,run

OUT=ROOT/'reports/actor-proxy-release-v1'
SOURCE=ROOT/'reports/scene-release-jobs/actor-proxy-source-v1'


def setup():
    OUT.mkdir(exist_ok=False);SOURCE.mkdir(exist_ok=False)
    original=ROOT/'reports/object-release-v2/seed-22-original/palm.json';bundle=read(original);scene=bundle['scene'];release=121
    for name,entry in scene['actors'].items():
        target=SOURCE/(name+'.glb');shutil.copyfile(ROOT/'reports/object-release-v2'/entry['preview_glb'],target);entry['preview_glb']=target.name
    rig=RigAsset.load(SOURCE/scene['actors']['A']['preview_glb']);sampler=AnimationSampler(rig.document,rig.binary,0)
    head=next(i for i,n in enumerate(rig.document['nodes']) if n.get('name')=='Head')
    p,r=pose(scene['actors']['A']['transform']);center=r@sampler.sample(release/30)[head,:3,3]+p+[0,.4,0]
    scene['objects']=dict(crate=dict(shape='box',size_m=[.2,.2,.2],keyframes=[dict(frame=0,translation_m=center.tolist(),rotation_xyzw=[0,0,0,1])]))
    scene['contacts']=[];scene['id']='Authored prop dropped toward animated body'
    scene['review_note']='Physics component fixture: unheld crate above the existing actor at release frame 121. No generated catch, protective reaction, injury response or human-quality claim.'
    bundle['native_contact_tracks']={};bundle['evaluation']=evaluate(scene,dict(np.load(ASSET,allow_pickle=False)))
    save(SOURCE/'source.json',bundle);shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',SOURCE/'SOMA-preview-LICENSE.txt')
    save(SOURCE/'manifest.json',dict(scenes=[dict(id='source',label=scene['id'],variants=dict(palm='source.json'))]))
    save(OUT/'protocol.json',dict(at=now(),source=str(SOURCE.relative_to(ROOT)),source_sha256=sha256(SOURCE/'source.json'),original=str(original.relative_to(ROOT)),original_sha256=sha256(original),
        release_frame=release,mass_kg=2.,friction=.6,restitution=0.,backend='Jolt Physics',physics_fps=240,
        changed_factor='Actor proxy colliders only; actor and object input, engine, floor, material, clock unchanged.',
        screens=dict(skin_depth_m=.01,proxy_depth_m=.01,proxy_surface_distance_m=.01),
        scope='Exploratory component experiment after proxy fit diagnostic; not held-out release validation.',
        implementation={n:sha256(ROOT/'scripts'/n) for n in ['scene_release_job.py','object_release.py','godot_object_release.gd','actor_collision_proxies.py','moving_release_colliders.py','convex_colliders.py','release_colliders.py']}))


def execute():
    protocol=read(OUT/'protocol.json');assert sha256(SOURCE/'source.json')==protocol['source_sha256']
    for name,digest in protocol['implementation'].items():assert sha256(ROOT/'scripts'/name)==digest
    url='/files/'+SOURCE.relative_to(ROOT/'reports').as_posix()+'/source.json';revision=metadata(url)['revision'];rows=[]
    for variant,actor_mode in [('baseline','none'),('candidate','convex_skin')]:
        folder=ROOT/'reports/scene-release-jobs'/('actor-proxy-v1-'+variant)
        payload=dict(source_url=url,revision=revision,object='crate',release_frame=121,mass_kg=2.,friction=.6,restitution=0.,label='Animated body collision · '+variant,collision_mode='moving_scene',actor_collision_mode=actor_mode)
        print('Preparing',variant,flush=True);prepare(payload,folder);rows.append(dict(variant=variant,folder=str(folder.relative_to(ROOT))))
        save(OUT/'jobs.json',dict(jobs=rows));print('Running',variant,flush=True);run(folder)
        print('Finished',variant,read(folder/'pipeline.json'),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','run']);args=parser.parse_args()
    setup() if args.command=='prepare' else execute()
