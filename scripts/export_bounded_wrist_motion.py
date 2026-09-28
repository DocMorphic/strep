"""Timed bounded wrist edits plus explicit fingers; retain every failed target."""
import argparse
import copy
import os
from pathlib import Path
import shutil
import traceback
import numpy as np
import psutil
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from bounded_pose_ik import hierarchy_order,world_matrices
from motion_edit_bounds import enforce
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from verify_rig_clearance import localize
from rig_loop import encode
from hand_posture import weight,run as author
from inspect_motion import skeleton_metadata


def joint_channels(world,joint_nodes):
    ordered=np.take(world,joint_nodes,axis=1)
    return ordered[:,:,:3,:3].copy(),ordered[:,:,:3,3].copy()


def run(study,output):
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Preserve prior export')
    if read(study/'pipeline.json')['status']!='complete':raise ValueError('Pose study incomplete')
    spec=read(study/'request.json');rows=read(study/'results.json')['rows']
    if len(rows)!=10 or {(r['seed'],r['actor']) for r in rows}!={(s,a) for s in spec['seeds'] for a in ['A','B']}:raise ValueError('Incomplete source population')
    source=ROOT/'reports/paired-pose-posture-v1';target_scene=read(ROOT/'reports/paired-contact-target-plan-v3/scene.json')['scene'];names,_,_=skeleton_metadata(77)
    output.mkdir();(output/'implementation').mkdir();sources=['export_bounded_wrist_motion.py','bounded_pose_ik.py','motion_edit_bounds.py','hand_posture.py','rig_asset.py','rig_clip_import.py','rig_loop.py','verify_rig_clearance.py','run_godot_scene_import.py','godot_scene_import_audit.gd']
    for name in sources:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    save(output/'request.json',dict(at=now(),pid=os.getpid(),created=psutil.Process().create_time(),seeds=spec['seeds'],pose_request_sha256=sha256(study/'request.json'),pose_results_sha256=sha256(study/'results.json'),
        methods=['raw','body_fit','body_fit_posture'],edit_limits=spec['edited_joints'],envelope_frames=[60,75,75,90],correction_speed_degrees_s=150.,root_edit_m=0.,
        implementation={n:sha256(output/'implementation'/n) for n in sources},quality_approved=False,
        scope='All ten actors, including the failed wrist target. body_fit here is bounded arm-only IK, not native unconstrained postprocessing. Timed edits and authored fingers; root and other body joints preserved. No foot cleanup, inference, contact or anatomical approval.'))
    manifest=dict(scenes=[],assets={});checks=[]
    try:
        with threadpool_limits(limits=1):
            for seed in spec['seeds']:
                scenes={mode:copy.deepcopy(target_scene) for mode in ['raw','body_fit','body_fit_posture']}
                for mode,scene in scenes.items():scene['id']=f'{mode}-seed-{seed}'
                for actor in ['A','B']:
                    row=next(r for r in rows if r['seed']==seed and r['actor']==actor);rawfolder=source/f'seed-{seed}'/actor/'raw';posepath=study/f'{seed}-{actor}'/'pose.npz'
                    if sha256(rawfolder/'character.glb')!=row['source_glb_sha256'] or sha256(rawfolder/'motion.npz')!=row['source_motion_sha256'] or sha256(posepath)!=row['pose_sha256']:raise ValueError('Changed pose/source data')
                    rig=RigAsset.load(rawfolder/'character.glb');sampler=AnimationSampler(rig.document,rig.binary,0);times=np.arange(150,dtype=np.float32)/30
                    original=np.array([sampler.sample(float(t)) for t in times]);local=localize(original,rig.parents);nodes={n.get('name'):i for i,n in enumerate(rig.document['nodes'])};labels=[str(n.get('name') or f'node-{i}') for i,n in enumerate(rig.document['nodes'])]
                    pose=dict(np.load(posepath,allow_pickle=False))
                    if not np.array_equal(local[75],pose['original_local']):raise ValueError('Source event differs from solved pose')
                    params=np.asarray(row['fit']['rotation_vectors_rad']);edited=row['fit']['edited_nodes'];candidate=local.copy();envelope=weight(150,dict(start_frame=60,full_start_frame=75,full_end_frame=75,end_frame=90,strength=1.))
                    for j,node in enumerate(edited):candidate[:,node,:3,:3]=local[:,node,:3,:3]@Rotation.from_rotvec(envelope[:,None]*params[j]).as_matrix()
                    order=hierarchy_order(rig.parents);world=np.array([world_matrices(frame,rig.parents,order) for frame in candidate]);hips=nodes['Hips']
                    budgets=dict(joint_rotation_degrees={n:spec['edited_joints'].get(n,0.) for n in labels},joint_correction_speed_degrees_s={n:150. for n in labels},root_components_m=[0.,0.,0.],root_correction_speed_m_s=0.)
                    bound=enforce(local[:,:,:3,:3],candidate[:,:,:3,:3],original[:,hips,:3,3],world[:,hips,:3,3],times,labels,budgets)
                    folder=output/f'seed-{seed}'/actor;body=folder/'body_fit';body.mkdir(parents=True);animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}|set(edited)
                    encode(rig,world,animated,rig.skin.get('skeleton',rig.joints[0]),body/'character.glb','Bounded wrist motion')
                    raw=dict(np.load(rawfolder/'motion.npz',allow_pickle=False));fit=copy.deepcopy(raw);joint_nodes=[nodes[n] for n in names]
                    fit['local_rot_mats']=candidate[:,joint_nodes,:3,:3].copy();fit['global_rot_mats'],fit['posed_joints']=joint_channels(world,joint_nodes);np.savez_compressed(body/'motion.npz',**fit)
                    guidepath=ROOT/target_scene['actors'][actor]['motion']
                    if sha256(guidepath)!=row['target_sha256']:raise ValueError('Changed authored finger target')
                    guide=dict(np.load(guidepath,allow_pickle=False));fingers=[j for j,n in enumerate(names) if n.startswith('LeftHand') and n[-1:].isdigit()]
                    recipe=dict(schema='strep-hand-posture-v1',source_glb_sha256=sha256(body/'character.glb'),frames=150,fps=30,hand_roots=[nodes['LeftHand']],
                        poses=[dict(id='authored-contact-hand',hand_root=nodes['LeftHand'],targets=[dict(node=nodes[names[j]],rotation_xyzw=Rotation.from_matrix(guide['local_rot_mats'][75,j]).as_quat().tolist()) for j in fingers],start_frame=60,full_start_frame=75,full_end_frame=75,end_frame=90,strength=1.)],
                        limits=dict(rotation_degrees=60,correction_step_degrees=5),provenance='Authored fingers from the recorded feasible surface target, applied separately after bounded wrist IK. Failed IK targets remain failures.')
                    postfolder=folder/'body_fit_posture';postworld=author(body/'character.glb',recipe,postfolder);postlocal=localize(postworld,rig.parents);post=copy.deepcopy(fit)
                    for j in fingers:post['local_rot_mats'][:,j]=postlocal[:,nodes[names[j]],:3,:3]
                    post['global_rot_mats'],post['posed_joints']=joint_channels(postworld,joint_nodes);np.savez_compressed(postfolder/'motion.npz',**post)
                    complete_budgets=copy.deepcopy(budgets)
                    for j in fingers:complete_budgets['joint_rotation_degrees'][names[j]]=60.
                    combined=enforce(local[:,:,:3,:3],postlocal[:,:,:3,:3],original[:,hips,:3,3],postworld[:,hips,:3,3],times,labels,complete_budgets)
                    rawcopy=folder/'raw';rawcopy.mkdir();shutil.copyfile(rawfolder/'motion.npz',rawcopy/'motion.npz');shutil.copyfile(rawfolder/'character.glb',rawcopy/'character.glb')
                    for mode in scenes:
                        dest=folder/mode;relative=(dest/'character.glb').relative_to(output).as_posix();scenes[mode]['actors'][actor].update(motion=(dest/'motion.npz').relative_to(ROOT).as_posix(),source_sha256=sha256(dest/'motion.npz'),preview_glb=relative)
                        manifest['assets'][relative]=dict(sha256=sha256(dest/'character.glb'))
                    checks.append(dict(seed=seed,actor=actor,target_matched=row['fit']['targets_matched'],body_bounds=bound,combined_bounds=combined,quality_approved=False));save(output/'bounds.json',dict(rows=checks));save(output/'pipeline.json',dict(status='exporting',actors=len(checks),quality_approved=False));print(seed,actor,row['fit']['targets_matched'],flush=True)
                for scene in scenes.values():
                    relative=scene['id']+'.json';save(output/relative,dict(scene=scene));manifest['scenes'].append(dict(id=scene['id'],variants={'palm':relative}))
                save(output/'manifest.json',manifest)
        from run_godot_scene_import import run as engine
        save(output/'pipeline.json',dict(status='engine_import',quality_approved=False));engine(output,output/'engine-audit');actual=read(output/'engine-audit/verification.json')['checks']
        if len(actual)!=30 or any(c['frames']!=150 for c in actual):raise ValueError('Incomplete engine population')
        shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',output/'SOMA-preview-LICENSE.txt');save(output/'pipeline.json',dict(status='complete_pending_geometry',engine_actor_frames=4500,quality_approved=False))
    except BaseException as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc),traceback=traceback.format_exc(),quality_approved=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.study,a.output)
