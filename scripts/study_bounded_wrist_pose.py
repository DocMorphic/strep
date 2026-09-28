"""All-seed necessary budget checks and bounded wrist-target feasibility."""
import argparse
import os
from pathlib import Path
import shutil
import numpy as np
import psutil
from strep import ROOT,read,save,sha256,now
from bounded_pose_ik import solve
from motion_edit_bounds import enforce,check
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from verify_rig_clearance import localize
from inspect_motion import skeleton_metadata
from threadpoolctl import threadpool_limits


def run(output,method='box'):
    if method not in ['box','norm']:raise ValueError('Unknown solver method')
    solver=solve
    if method=='norm':
        from bounded_pose_ball_ik import solve as solver
    output=Path(output).resolve()
    if output.exists():raise ValueError('Preserve previous study')
    source=ROOT/'reports/paired-pose-posture-v1';proof=read(source/'preservation-verification.json');target=ROOT/'reports/paired-contact-target-plan-v3';scene=read(target/'scene.json')['scene']
    if proof['manifest_sha256']!=sha256(source/'manifest.json'):raise ValueError('Changed source population')
    names,_,_=skeleton_metadata(77);roles={'LeftShoulder':15.,'LeftArm':25.,'LeftForeArm':35.,'LeftHand':30.}
    output.mkdir();(output/'implementation').mkdir();scripts=['study_bounded_wrist_pose.py','bounded_pose_ik.py','motion_edit_bounds.py','rig_asset.py','rig_clip_import.py','verify_rig_clearance.py']
    if method=='norm':scripts.append('bounded_pose_ball_ik.py')
    for name in scripts:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    save(output/'request.json',dict(at=now(),pid=os.getpid(),created=psutil.Process().create_time(),source_proof_sha256=sha256(source/'preservation-verification.json'),
        target_scene_sha256=sha256(target/'scene.json'),seeds=[1301,2089,3253,4099,5101],frame=75,edited_joints=roles,position_tolerance_m=.0005,rotation_tolerance_degrees=.5,
        max_evaluations=200,method=method,implementation={n:sha256(output/'implementation'/n) for n in scripts},quality_approved=False,
        scope='Development event-pose feasibility. Existing paired-arm edit budgets, not anatomical limits. Root, torso, legs and fingers fixed. All five seeds and both actors retained. No animation, skin-contact, temporal or human approval.'))
    rows=[]
    with threadpool_limits(limits=1):
        for seed in [1301,2089,3253,4099,5101]:
            for actor in ['A','B']:
                folder=source/f'seed-{seed}'/actor;path=folder/'raw/character.glb';motionpath=folder/'raw/motion.npz'
                if sha256(path)!=proof['files'][str(path)] or sha256(motionpath)!=proof['files'][str(motionpath)]:raise ValueError('Changed raw source')
                entry=scene['actors'][actor];guidepath=ROOT/entry['motion']
                if sha256(guidepath)!=entry['source_sha256']:raise ValueError('Changed target')
                guide=dict(np.load(guidepath,allow_pickle=False));rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0)
                world=sampler.sample(float(np.float32(75/30)));local=localize(world[None],rig.parents)[0];nodes={n.get('name'):i for i,n in enumerate(rig.document['nodes'])}
                limits={nodes[name]:value for name,value in roles.items()};hand=names.index('LeftHand');desired=np.eye(4);desired[:3,:3]=guide['global_rot_mats'][75,hand];desired[:3,3]=guide['posed_joints'][75,hand]
                fitted,report=solver(local,rig.parents,[dict(node=nodes['LeftHand'],world_matrix=desired,position_tolerance_m=.0005,rotation_tolerance_degrees=.5)],limits,max_evaluations=200)
                labels=[str(n.get('name') or f'node-{i}') for i,n in enumerate(rig.document['nodes'])]
                budgets=dict(joint_rotation_degrees={name:roles.get(name,0.) for name in labels},joint_correction_speed_degrees_s={name:150. for name in labels},root_components_m=[0.,0.,0.],root_correction_speed_m_s=0.)
                bounded=enforce(local[None,:,:3,:3],fitted[None,:,:3,:3],np.zeros((1,3)),np.zeros((1,3)),[75/30],labels,budgets)
                dest=output/f'{seed}-{actor}';dest.mkdir();np.savez_compressed(dest/'pose.npz',original_local=local,candidate_local=fitted,parents=rig.parents,target=desired)
                row=dict(seed=seed,actor=actor,source_glb_sha256=sha256(path),source_motion_sha256=sha256(motionpath),target_sha256=sha256(guidepath),
                    pose_sha256=sha256(dest/'pose.npz'),fit=report,bounds=bounded,quality_approved=False)
                rows.append(row);save(output/'results.json',dict(rows=rows,quality_approved=False));save(output/'pipeline.json',dict(status='fitting',actors_completed=len(rows),planned=10,quality_approved=False))
                print(seed,actor,report['targets'],report['max_edit_degrees'],flush=True)
    save(output/'pipeline.json',dict(status='complete',actors=10,matched=sum(r['fit']['targets_matched'] for r in rows),quality_approved=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--method',choices=['box','norm'],default='box');a=p.parse_args();run(a.output,a.method)
