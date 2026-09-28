"""Independent saved-array and decoded-anchor checks for the complete study."""
import argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from verify_rig_clearance import localize
from inspect_motion import skeleton_metadata


def run(study):
    study=Path(study).resolve();output=study/'preservation-verification.json'
    if output.exists():raise ValueError('Preserve prior verification')
    if read(study/'pipeline.json')['status']!='complete_pending_geometry':raise ValueError('Incomplete study')
    request=read(study/'request.json');manifest=read(study/'manifest.json');scene_map={s['id']:read(study/s['variants']['palm'])['scene'] for s in manifest['scenes']}
    names,_,_=skeleton_metadata(77);selected=[i for i,n in enumerate(names) if n.startswith('LeftHand') and n[-1:].isdigit()];remaining=[i for i in range(77) if i not in selected]
    target_scene=read(ROOT/'reports/paired-contact-target-plan-v3/scene.json')['scene'];rows=[];files={}
    for seed in request['seeds']:
        for actor in ['A','B']:
            variants={};entries={}
            for mode in request['methods']:
                entry=scene_map[f'{mode}-seed-{seed}']['actors'][actor];entries[mode]=entry;path=ROOT/entry['motion'];glb=study/entry['preview_glb']
                if sha256(path)!=entry['source_sha256'] or sha256(glb)!=manifest['assets'][entry['preview_glb']]['sha256']:raise ValueError('Changed output payload')
                files[str(path)]=sha256(path);files[str(glb)]=sha256(glb);variants[mode]=dict(np.load(path,allow_pickle=False))
            raw,fit,post=(variants[k] for k in request['methods'])
            if set(fit)!=set(post):raise ValueError('Posture field set changed')
            for key in fit:
                if key not in ['local_rot_mats','global_rot_mats','posed_joints'] and not np.array_equal(fit[key],post[key]):raise ValueError('Posture changed protected metadata: '+key)
            frozen=np.r_[0:61,90:150]
            if not np.array_equal(fit['local_rot_mats'][:,remaining],post['local_rot_mats'][:,remaining]):raise ValueError('Posture changed non-finger joints')
            # Decode/localize introduces bounded floating error on rewritten finger matrices.
            outside=float(np.abs(fit['local_rot_mats'][frozen]-post['local_rot_mats'][frozen]).max())
            if outside>1e-5 or not np.array_equal(raw['foot_contacts'],post['foot_contacts']):raise ValueError('Outside interval or contact labels changed')
            target=target_scene['actors'][actor];guidepath=ROOT/target['motion']
            if sha256(guidepath)!=target['source_sha256']:raise ValueError('Changed authored guide')
            guide=dict(np.load(guidepath,allow_pickle=False));event=float(np.abs(post['local_rot_mats'][75,selected]-guide['local_rot_mats'][75,selected]).max())
            if event>1e-5:raise ValueError('Authored finger pose lost')
            delta=fit['local_rot_mats'][:,selected].transpose(0,1,3,2)@post['local_rot_mats'][:,selected]
            edit=float(np.degrees(Rotation.from_matrix(delta.reshape(-1,3,3)).magnitude()).max())
            steps=delta[:-1].transpose(0,1,3,2)@delta[1:];step=float(np.degrees(Rotation.from_matrix(steps.reshape(-1,3,3)).magnitude()).max())
            if edit>60+1e-3 or step>5+1e-3:raise ValueError('Posture exceeds declared limits')
            rig=RigAsset.load(study/entries['body_fit_posture']['preview_glb']);sampler=AnimationSampler(rig.document,rig.binary,0);nodes={n.get('name'):i for i,n in enumerate(rig.document['nodes'])}
            decoded=localize(sampler.sample(float(np.float32(75/30)))[None],rig.parents)[0]
            decoded_error=float(np.abs(decoded[[nodes[names[j]] for j in selected],:3,:3]-guide['local_rot_mats'][75,selected]).max())
            if decoded_error>1e-5:raise ValueError('Exported event fingers differ from authored target')
            body_delta=raw['local_rot_mats'].transpose(0,1,3,2)@fit['local_rot_mats']
            rows.append(dict(seed=seed,actor=actor,event_finger_matrix_error=event,decoded_event_finger_matrix_error=decoded_error,outside_interval_matrix_error=outside,
                max_finger_edit_degrees=edit,max_finger_correction_step_degrees=step,
                max_body_fit_root_displacement_m=float(np.linalg.norm(fit['root_positions']-raw['root_positions'],axis=1).max()),
                max_body_fit_joint_change_degrees=float(np.degrees(Rotation.from_matrix(body_delta.reshape(-1,3,3)).magnitude()).max())))
    if len(rows)!=10:raise ValueError('Incomplete actor population')
    save(output,dict(at=now(),request_sha256=sha256(study/'request.json'),manifest_sha256=sha256(study/'manifest.json'),verifier_sha256=sha256(__file__),files=files,rows=rows,
        quality_approved=False,scope='Every saved variant and source hash, preserved posture metadata/non-finger locals/unmodified frames/contact labels, finger edit bounds and actual decoded event targets. Body-fit edit magnitudes are measurements, not anatomical or edit-budget approval. No surface contact or whole-motion quality approval.'))
    print({'actors':len(rows),'max_decoded_finger_error':max(r['decoded_event_finger_matrix_error'] for r in rows),'max_body_root_displacement_m':max(r['max_body_fit_root_displacement_m'] for r in rows)},flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);run(p.parse_args().study)
