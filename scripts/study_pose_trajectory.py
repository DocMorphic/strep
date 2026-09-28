"""Frozen three-case temporal correction experiment on retained guided outputs."""
import copy,shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from target_rig_contact import baseline,floor_lower_bound
from rig_contact_authoring import empty_spec
from rig_clearance_fit import foot_regions
from rig_pose_trajectory import PoseTrajectoryFitter
from study_trajectory_fit import draft_supports
from rig_loop import encode

OUT=ROOT/'reports/pose-trajectory-v1'
CASES=['jump-land','dance','get-up']

def run_case(action):
    out=OUT/action;out.mkdir();trial=ROOT/'reports/action-jobs/pose-response-v1/takes'/f'{action}-offset-seed-502'
    spec_case=next(c for c in read(ROOT/'reports/pose-response-v1/protocol.json')['cases'] if c['action']==action)
    frame=spec_case['frame'];target=ROOT/spec_case['target_folder']/'candidate.npz';source=trial/'soma.glb'
    raw=read(trial/'generation-record.json');assert sha256(trial/'motion.npz')==raw['npz_sha256']
    guide=raw['request']['generation_constraints'][0];assert sha256(target)==guide['sha256'] and guide['frame_indices']==[frame]
    shutil.copyfile(source,out/'original.glb');shutil.copyfile(target,out/'target.npz');shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',out/'LICENSE.txt')
    rig=RigAsset.load(source);frames=len(np.load(trial/'motion.npz',allow_pickle=False)['posed_joints']);before,local=baseline(rig,frames)
    mapping={rig.document['nodes'][n]['name']:n for n in rig.joints};root=mapping['Hips']
    report=dict(glb_sha256=sha256(source),fps=30,frames=frames,root_node=root,mapping=mapping);spec=empty_spec(report)
    regions=foot_regions(rig,mapping);spec['patches']={s:dict(vertices=ids.tolist()) for s,ids in regions.items()};spec['max_nfev']=30
    from pose_target import CHAINS
    for name in CHAINS[spec_case['joint']]+[spec_case['joint']]:spec['edit_joints'][name]=dict(node=mapping[name],limit_degrees=25)
    spec['provenance']='Experimental guided-motion correction; inherited predicted support is unconfirmed. Native joint goal is authored, not surface contact.'
    points=np.array([rig.vertices(w) for w in before]);heights={s:np.maximum(0,points[:,ids,1].min(axis=1)) for s,ids in regions.items()}
    envelope=np.zeros(frames);a,b=frame-15,frame+15;t=np.minimum(np.arange(31),np.arange(31)[::-1]);u=np.clip((t-1)/14,0,1);envelope[a:b+1]=u*u*(3-2*u)
    supports=draft_supports(rig,before,spec,read(trial/'contacts.json'))
    if spec_case['joint'].endswith('Foot'):
        side='Right' if spec_case['joint'].startswith('Right') else 'Left';supports=[s for s in supports if s['side']!=side]
    with np.load(target,allow_pickle=False) as data:
        from inspect_motion import skeleton_metadata
        names,_,_=skeleton_metadata(77);j=names.index(spec_case['joint'])
        goal=dict(frame=frame,node=mapping[spec_case['joint']],position_m=data['posed_joints'][0,j].tolist(),rotation_matrix=data['global_rot_mats'][0,j].tolist(),position_weight=60.,rotation_weight=.5,provenance='Frozen authored target '+guide['motion']+' SHA256 '+guide['sha256'])
    save(out/'request.json',dict(action=action,source_glb_sha256=sha256(source),source_npz_sha256=raw['npz_sha256'],target_sha256=sha256(target),frame=frame,editable_first=a,editable_last=b,envelope=envelope.tolist(),joint_goal=goal,supports=supports,targets_m={s:v.tolist() for s,v in heights.items()},support_provenance='UNCONFIRMED model-predicted foot/toe union. Guided foot excluded to avoid pinning a deliberately moved foot.',quality_approved=False))
    save(out/'spec.json',spec);save(out/'feasibility.json',floor_lower_bound(rig,spec,before))
    fitter=PoseTrajectoryFitter(rig,spec,local,heights,envelope,supports,[goal]);save(out/'pipeline.json',dict(status='fitting',started_at=now()))
    with threadpool_limits(limits=1):parameters,solver,convergence=fitter.solve(out,max_sweeps=4)
    after=fitter.world.copy();after[envelope==0]=before[envelope==0]
    animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}|set(fitter.nodes)
    times,roundtrip=encode(rig,after,animated,root,out/'candidate.glb','Bounded temporal target candidate')
    np.savez_compressed(out/'fit.npz',before=before,after=after,parameters=parameters,local_before=local)
    save(out/'solver.json',solver);save(out/'fit-summary.json',dict(convergence=convergence,export=roundtrip,quality_approved=False))
    save(out/'root-motion.json',dict(space='SOMA pelvis world transform after experimental correction',times_s=times.tolist(),positions_m=after[:,root,:3,3].tolist(),rotations_xyzw=Rotation.from_matrix(after[:,root,:3,:3]).as_quat().tolist()))
    if sha256(source)!=report['glb_sha256'] or sha256(target)!=guide['sha256']:raise ValueError('Frozen source changed')
    save(out/'pipeline.json',dict(status='complete',finished_at=now(),quality_approved=False));print(action+' complete',flush=True)

def run():
    if OUT.exists():raise ValueError('Preserve prior experiment; output already exists')
    OUT.mkdir();save(OUT/'protocol.json',dict(created_at=now(),cases=CASES,seed=502,source_study='pose-response-v1',selection='Three documented absolute target misses; hand/foot and upright/ground contexts. Posthoc development selection, not held-out evaluation.',window_frames=31,fixed_boundary_frames=2,max_sweeps=4,max_nfev=30,position_weight=60.,rotation_weight=.5,position_screen_m=.005,orientation_screen_degrees=5.,floor_screen_m=.01,source_model_unchanged=True,quality_approved=False))
    snapshot=OUT/'implementation';snapshot.mkdir()
    for name in ['study_pose_trajectory.py','rig_pose_trajectory.py','rig_trajectory_fit.py','rig_clearance_fit.py','target_rig_contact.py','rig_periodic_contact.py','study_trajectory_fit.py','rig_loop.py']:
        shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    from action_worker_lock import worker_lock
    with worker_lock():
        for action in CASES:
            save(OUT/'pipeline.json',dict(status='fitting',case=action,updated_at=now()));run_case(action)
    save(OUT/'pipeline.json',dict(status='complete',finished_at=now(),quality_approved=False))

if __name__=='__main__':run()
