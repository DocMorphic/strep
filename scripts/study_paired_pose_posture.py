"""Frozen all-seed body correction and explicit authored finger-layer comparison."""
import argparse
import copy
import os
from pathlib import Path
import shutil
import sys
import traceback
import numpy as np
import psutil
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now,offline_environment


def run(output):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Preserve previous study')
    os.environ.update(offline_environment());sys.path.insert(0,str(ROOT/'.cache/motion-correction-package'))
    import torch
    import motion_correction._motion_correction as native
    from kimodo.skeleton import SOMASkeleton30,SOMASkeleton77
    from kimodo.postprocess import post_process_motion
    from kimodo.exports.motion_io import save_kimodo_npz
    from generation_constraints import compile_guides,load_guides
    from paired_guide_study import validate
    from build_soma_preview import ASSET,make_preview
    from gltf_tools import write_glb
    from rig_asset import RigAsset
    from verify_rig_clearance import localize
    from hand_posture import run as author
    from action_worker_lock import worker_lock
    from run_godot_scene_import import run as engine
    torch.set_num_threads(1)
    study=ROOT/'reports/paired-guide-generation-v1';protocol=validate(study)
    target=ROOT/'reports/paired-contact-target-plan-v3';proof=read(target/'verification.json');target_scene=read(target/'scene.json')['scene']
    if not proof['decoded']['passed'] or proof['request_sha256']!=sha256(target/'request.json') or proof['trials_sha256']!=sha256(target/'trials.json'):raise ValueError('Unverified authored target')
    # The representation failure is an explicit reason for the posture variant.
    representation=read(target/'model-representation-verification.json')
    if representation['target_screens_passed']:raise ValueError('Study premise changed; inspect design')
    trials=read(study/'generation/summary.json')['trials'];pairs=[p for p in protocol['pairs'] if p['method']=='body']
    if [p['seed'] for p in pairs]!=[1301,2089,3253,4099,5101]:raise ValueError('Require all five fixed body-guided seeds')
    small,full=SOMASkeleton30(),SOMASkeleton77();skin=dict(np.load(ASSET,allow_pickle=False));names=full.bone_order_names
    selected=[i for i,n in enumerate(names) if n.startswith('LeftHand') and n[-1:].isdigit()]
    output.mkdir();(output/'implementation').mkdir();sources=['study_paired_pose_posture.py','hand_posture.py','generation_constraints.py','build_soma_preview.py','gltf_tools.py','rig_asset.py','rig_clip_import.py','rig_loop.py','verify_rig_clearance.py','run_godot_scene_import.py','godot_scene_import_audit.gd']
    for name in sources:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    save(output/'request.json',dict(at=now(),pid=os.getpid(),created=psutil.Process().create_time(),source_protocol_sha256=sha256(study/'protocol.json'),
        target_proof_sha256=sha256(target/'verification.json'),representation_proof_sha256=sha256(target/'model-representation-verification.json'),target_scene_sha256=sha256(target/'scene.json'),
        seeds=[p['seed'] for p in pairs],methods=['raw','body_fit','body_fit_posture'],guide_frames=[0,75,149],posture_frames=[60,75,75,90],
        posture_limits=dict(rotation_degrees=60,correction_step_degrees=5),contact_mode='Zero solver contacts; retain original unconfirmed output labels',
        root_margin_m=.04,loaded_native_sha256=sha256(Path(native.__file__)),implementation={n:sha256(output/'implementation'/n) for n in sources},
        scope='All five body-guided development seeds. Native deterministic body fit to authored pose anchors, then optional explicit finger layer. This does not claim SOMA30 generates fingers. Fixed world placement, no inference/training, no anatomy/contact/naturalness or release approval.',quality_approved=False))
    manifest=dict(scenes=[],assets={});records=[]
    try:
        with worker_lock(),threadpool_limits(limits=1):
            for pair in pairs:
                scenes={mode:copy.deepcopy(target_scene) for mode in ['raw','body_fit','body_fit_posture']}
                for mode,scene in scenes.items():scene['id']=f'{mode}-seed-{pair["seed"]}'
                for actor in ['A','B']:
                    save(output/'pipeline.json',dict(status='correcting',seed=pair['seed'],actor=actor,quality_approved=False))
                    take=next(t for t in trials if t['request_id']==pair['requests'][actor] and t['seed']==pair['seed']);source=study/'generation/takes'/take['id']
                    for name,digest in take['hashes'].items():
                        if sha256(source/name)!=digest:raise ValueError('Changed raw take')
                    raw=dict(np.load(source/'motion.npz',allow_pickle=False));entry=target_scene['actors'][actor];guidepath=ROOT/entry['motion']
                    if sha256(guidepath)!=entry['source_sha256']:raise ValueError('Changed authored target')
                    guide=dict(np.load(guidepath,allow_pickle=False));common=dict(motion=entry['motion'],sha256=entry['source_sha256'])
                    compiled,provenance=compile_guides(dict(segments=[dict(duration_s=5)],generation_constraints=[dict(type='fullbody',source_frames=[0,75,149],frame_indices=[0,75,149],**common)]))
                    folder=output/f'seed-{pair["seed"]}'/actor;folder.mkdir(parents=True);save(folder/'body-guides.json',dict(compiled=compiled,provenance=provenance))
                    local=small.from_SOMASkeleton77(torch.tensor(raw['local_rot_mats'],dtype=torch.float32))[None];root=torch.tensor(raw['root_positions'],dtype=torch.float32)[None]
                    if not np.array_equal(raw['foot_contacts'][:,1],raw['foot_contacts'][:,2]) or not np.array_equal(raw['foot_contacts'][:,4],raw['foot_contacts'][:,5]):raise ValueError('Unexpected toe contact channels')
                    contacts=torch.tensor(raw['foot_contacts'][:,[0,1,3,4]],dtype=torch.float32)[None]
                    inputs=[x.clone() for x in [local,root,contacts]];constraints=load_guides(compiled,small)
                    corrected=post_process_motion(local,root,torch.zeros_like(contacts),small,constraints,contact_threshold=.5,root_margin=.04)
                    repeated=post_process_motion(local,root,torch.zeros_like(contacts),small,load_guides(compiled,small),contact_threshold=.5,root_margin=.04)
                    repeat=max(float((corrected[k]-repeated[k]).abs().max()) for k in corrected)
                    if repeat!=0 or any(not torch.equal(a,b) for a,b in zip(inputs,[local,root,contacts])):raise ValueError('Nondeterministic correction or changed inputs')
                    corrected['foot_contacts']=contacts;expanded=small.output_to_SOMASkeleton77(corrected);fit={k:v[0].numpy() for k,v in expanded.items()}
                    bodyfolder=folder/'body_fit';bodyfolder.mkdir();save_kimodo_npz(str(bodyfolder/'motion.npz'),fit)
                    doc,binary,_,_=make_preview(skin,fit,np.zeros(3),repeat=False);write_glb(bodyfolder/'character.glb',doc,binary)
                    rig=RigAsset.load(bodyfolder/'character.glb');nodes={n.get('name'):i for i,n in enumerate(rig.document['nodes'])}
                    recipe=dict(schema='strep-hand-posture-v1',source_glb_sha256=sha256(bodyfolder/'character.glb'),frames=150,fps=30,hand_roots=[nodes['LeftHand']],
                        poses=[dict(id='authored-contact-hand',hand_root=nodes['LeftHand'],targets=[dict(node=nodes[names[j]],rotation_xyzw=Rotation.from_matrix(guide['local_rot_mats'][75,j]).as_quat().tolist()) for j in selected],start_frame=60,full_start_frame=75,full_end_frame=75,end_frame=90,strength=1.)],
                        limits=dict(rotation_degrees=60,correction_step_degrees=5),provenance='Explicit local finger pose from hash-bound authored contact target at frame75; timed layer after body correction, not generated finger motion or anatomical approval.')
                    postfolder=folder/'body_fit_posture';world=author(bodyfolder/'character.glb',recipe,postfolder);authored=localize(world,rig.parents);post=copy.deepcopy(fit)
                    for j in selected:post['local_rot_mats'][:,j]=authored[:,nodes[names[j]],:3,:3]
                    r,p,_=full.fk(torch.tensor(post['local_rot_mats']),torch.tensor(post['root_positions']));post.update(global_rot_mats=r.numpy(),posed_joints=p.numpy())
                    unselected=[j for j in range(77) if j not in selected]
                    if not np.array_equal(post['local_rot_mats'][:,unselected],fit['local_rot_mats'][:,unselected]) or not np.array_equal(post['root_positions'],fit['root_positions']) or not np.array_equal(post['foot_contacts'],raw['foot_contacts']):raise ValueError('Posture altered protected motion')
                    save_kimodo_npz(str(postfolder/'motion.npz'),post)
                    rawfolder=folder/'raw';rawfolder.mkdir();shutil.copyfile(source/'motion.npz',rawfolder/'motion.npz');shutil.copyfile(source/'soma.glb',rawfolder/'character.glb')
                    for mode in scenes:
                        dest=folder/mode;glb=(dest/'character.glb').relative_to(output).as_posix();motion=(dest/'motion.npz').relative_to(ROOT).as_posix()
                        scenes[mode]['actors'][actor].update(motion=motion,source_sha256=sha256(dest/'motion.npz'),preview_glb=glb)
                        manifest['assets'][glb]=dict(sha256=sha256(dest/'character.glb'))
                    record=dict(seed=pair['seed'],actor=actor,raw_sha256=take['hashes']['motion.npz'],target_sha256=entry['source_sha256'],repeat_max_error=repeat,
                        body_anchor_position_max_error_m=float(np.abs(fit['posed_joints'][[0,75,149]]-guide['posed_joints'][[0,75,149]]).max()),
                        body_anchor_wrist_position_max_error_m=float(np.abs(fit['posed_joints'][[0,75,149],names.index('LeftHand')]-guide['posed_joints'][[0,75,149],names.index('LeftHand')]).max()),quality_approved=False)
                    records.append(record);save(output/'actors.json',dict(rows=records));print(pair['seed'],actor,record['body_anchor_wrist_position_max_error_m'],flush=True)
                for mode,scene in scenes.items():
                    relative=f'{scene["id"]}.json';save(output/relative,dict(scene=scene));manifest['scenes'].append(dict(id=scene['id'],variants={'palm':relative}))
                save(output/'manifest.json',manifest)
        save(output/'pipeline.json',dict(status='engine_import',quality_approved=False));engine(output,output/'engine-audit')
        checks=read(output/'engine-audit/verification.json')['checks']
        if len(checks)!=30 or sum(c['frames'] for c in checks)!=4500:raise ValueError('Incomplete engine population')
        shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',output/'SOMA-preview-LICENSE.txt')
        save(output/'pipeline.json',dict(status='complete_pending_geometry',actor_clips=30,engine_actor_frames=4500,quality_approved=False))
    except BaseException as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc),traceback=traceback.format_exc(),quality_approved=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);run(p.parse_args().output)
