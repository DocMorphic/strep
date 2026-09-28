"""Attach corrected box fixtures to one palm; retain second-hand/collision failures."""
import copy
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from scene_constraints import transform_motion,effector_track,sample_object,evaluate
from object_attachment import attach_trajectory
from run_scene_fit import bundle
from audit_scene_orientation import audit
from inspect_motion import skeleton_metadata


def run():
    out=ROOT/'reports/object-attachment-v1';out.mkdir(exist_ok=False);skin=dict(np.load(ASSET));names,_,_=skeleton_metadata(77)
    manifest=dict(created_at=now(),scenes=[],assets={});summary=dict(created_at=now(),trials=[],scope='Authored kinematic attachment experiment on existing unreviewed corrected motion. No physics or joint hand/object solve.')
    snapshot=out/'source-snapshot';snapshot.mkdir()
    for name in ['object_attachment.py','build_attachment_study.py','audit_scene_orientation.py','palm_contacts.py','scene_constraints.py']:shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',out/'SOMA-preview-LICENSE.txt')
    save(out/'pipeline.json',dict(status='processing'))
    for seed in [11,22]:
        source=ROOT/f'reports/scene-fitting-v5/anatomical-grips-seed-{seed}/candidate.json';scene=copy.deepcopy(read(source)['scene'])
        scene['id']=f'palm-attached-box-seed-{seed}';entry=scene['actors']['A'];motion=dict(np.load(ROOT/entry['motion']))
        actor=transform_motion(motion,entry['transform']);grip=next(c for c in scene['contacts'] if c['id']=='left-grip')
        points=effector_track(actor,grip['effector'],skin);rotations=actor['rotations'][:,names.index(grip['effector']['joint'])]
        p,r=sample_object(scene['objects']['box'],scene['frame_count']);p,r,recipe=attach_trajectory(p,r,points,rotations,60,121)
        quats=Rotation.from_matrix(r).as_quat()
        for f in range(1,len(quats)):
            if np.dot(quats[f-1],quats[f])<0:quats[f]*=-1
        scene['objects']['box']['keyframes']=[dict(frame=f,translation_m=pos.tolist(),rotation_xyzw=q.tolist()) for f,(pos,q) in enumerate(zip(p,quats))]
        scene['objects']['box']['trajectory_provenance']='Rigidly bound to the left skinned palm position and wrist orientation at frame 60; release at frame 121, then aligned authored tail. No physics.'
        scene['review_note']='Experimental left-palm attachment. Right-hand contact and collisions must be checked. Release tail is authored, not gravity.'
        folder=out/scene['id'];folder.mkdir();save(folder/'attachment.json',recipe)
        save(folder/'object-track.json',dict(fps=30,object='box',size_m=scene['objects']['box']['size_m'],positions_m=p.tolist(),rotations_xyzw=quats.tolist(),space='World metres, Y-up',provenance=scene['objects']['box']['trajectory_provenance']))
        save(folder/'events.json',dict(fps=30,events=[dict(type='grasp',actor='A',hand='LeftHand',object='box',frame=60,time_s=2),dict(type='release',actor='A',hand='LeftHand',object='box',frame=121,time_s=121/30)],provenance='Authored attachment events, not automatically detected action success.'))
        asset=out/'assets'/scene['id'];asset.mkdir(parents=True)
        original=ROOT/'reports/scene-fitting-v5'/entry['preview_glb'];shutil.copyfile(original,asset/'actor.glb');entry['preview_glb']=(asset/'actor.glb').relative_to(out).as_posix()
        assert sha256(original)==sha256(asset/'actor.glb');manifest['assets'][entry['preview_glb']]=dict(sha256=sha256(asset/'actor.glb'))
        assessment=evaluate(scene,skin);orientation=audit(scene,skin);save(folder/'orientation-audit.json',orientation)
        save(folder/'scene.json',scene);save(folder/'evaluation.json',assessment);save(folder/'palm.json',bundle(scene,{'A':motion},assessment))
        manifest['scenes'].append(dict(id=scene['id'],label=scene['id'].replace('-',' '),variants=dict(palm=scene['id']+'/palm.json')))
        summary['trials'].append(dict(id=scene['id'],source_scene_sha256=sha256(source),actor_motion_sha256=sha256(ROOT/entry['motion']),contacts=assessment['contacts'],object_collisions=assessment['object_collisions'],orientation=[{k:v for k,v in c.items() if 'world' not in k and k!='per_frame_error_degrees'} for c in orientation['contacts']],human_approved=False))
        print(scene['id'],[(c['id'],round(c['max_interval_error_m'],4)) for c in assessment['contacts']],flush=True)
        save(out/'manifest.json',manifest);save(out/'summary.json',summary)
    save(out/'pipeline.json',dict(status='complete'))


if __name__=='__main__':run()
