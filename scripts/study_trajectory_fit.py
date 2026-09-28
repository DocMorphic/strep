"""Matched clearance versus explicit-support/trajectory fit on retained inputs."""
import copy
import shutil
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_transition import localize
from rig_loop import encode
from rig_clearance_fit import ClearanceFitter
from rig_trajectory_fit import TrajectoryFitter, DEFAULTS
from study_corrected_rig_transfer import root_track


def draft_supports(rig,world,spec,annotations):
    """Unconfirmed experimental targets, never production/human annotations."""
    points=np.array([rig.vertices(w) for w in world]);result=[]
    for side,patch in spec['patches'].items():
        mask=np.zeros(len(world),bool)
        for interval in annotations.get('intervals',[]):
            if interval['joint'] in (side+'Foot',side+'ToeBase'):
                mask[interval['start_frame']:interval['end_frame_exclusive']]=True
        edges=np.diff(np.r_[False,mask,False].astype(int))
        for a,b in zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)):
            if b-a<2:continue
            region=np.array(patch['vertices']);height=points[a,region,1]
            ids=region[height<=height.min()+.003]
            centroid=points[a:b][:,ids].mean(axis=1)
            target=np.median(centroid,axis=0);target[1]=.0015
            result.append(dict(side=side,vertices=ids.tolist(),start_frame=int(a),end_frame_exclusive=int(b),target_position_m=target.tolist(),provenance='UNCONFIRMED experimental draft: inherited foot/toe prediction union; lowest 3 mm of weighted foot region at interval start; median XZ and 1.5 mm floor target. No human confirmation.'))
    return result


def run_case(case,mode,out):
    old=ROOT/'reports/corrected-rig-transfer-v1'/case
    source=ROOT/'reports/context-transfer-v1'/f'{case}-pose_fitted/context/character.glb'
    out.mkdir(parents=True,exist_ok=False);shutil.copytree(old/'input',out/'input')
    shutil.copyfile(source,out/'input/character.glb')
    rig=RigAsset.load(source);report=read(old/'input/report.json');count=report['frames']
    sampler=AnimationSampler(rig.document,rig.binary,0)
    before=np.array([sampler.sample(float(np.float32(f/30))) for f in range(count)])
    input_floor=np.array([max(0.,-float(rig.vertices(w)[:,1].min())) for w in before])
    request=read(old/'request.json');spec=read(old/'spec.json');spec['glb_sha256']=sha256(source)
    report.update(glb_sha256=sha256(source),target_mesh_floor_depth_max_m=float(input_floor.max()),target_mesh_floor_frames_above_1cm=int(np.sum(input_floor>.01)),contact_annotations_file=str((out/'input/contacts.json').resolve()),contact_annotations_sha256=sha256(out/'input/contacts.json'))
    request['source_glb_sha256']=sha256(source)
    request['scope']='Matched source-context-preserving pose-fitted input. All support targets are unconfirmed experimental drafts.'
    save(out/'input/report.json',report);save(out/'request.json',request);save(out/'spec.json',spec)
    root_track(out/'input',before,report['root_node'],np.arange(count)/30)
    supports=draft_supports(rig,before,spec,read(out/'input/contacts.json'))
    save(out/'support-targets.json',dict(supports=supports,confirmed=False))
    save(out/'trajectory-settings.json',DEFAULTS)
    envelope=np.array(request['envelope']);targets={k:np.array(v) for k,v in request['targets_m'].items()}
    local=localize(before,rig.parents)
    if mode=='trajectory':fitter=TrajectoryFitter(rig,spec,local,targets,envelope,supports)
    elif mode=='clearance':fitter=ClearanceFitter(rig,spec,local,targets,envelope,np.array([rig.vertices(w) for w in before]))
    else:raise ValueError(mode)
    snapshot=out/'implementation';snapshot.mkdir()
    for name in ['study_trajectory_fit.py','rig_trajectory_fit.py','rig_clearance_fit.py','target_rig_contact.py','rig_periodic_contact.py']:
        shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    save(out/'pipeline.json',dict(status='fitting',case=case,mode=mode))
    with threadpool_limits(limits=1):parameters,solver,convergence=fitter.solve(out)
    after=np.array([fitter.pose(f,x)[0] for f,x in enumerate(parameters)])
    target=out/'candidate';shutil.copytree(out/'input',target)
    animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}|set(fitter.nodes)
    times,roundtrip=encode(rig,after,animated,report['root_node'],target/'character.glb','Bounded '+mode+' experiment')
    root_track(target,after,report['root_node'],times)
    report.update(glb_sha256=sha256(target/'character.glb'),target_mesh_floor_depth_max_m=roundtrip['floor_depth_max_m'],target_mesh_floor_frames_above_1cm=roundtrip['floor_frames_above_1cm'],human_approved=False)
    report.update(contact_annotations_file=str((target/'contacts.json').resolve()),contact_annotations_sha256=sha256(target/'contacts.json'))
    save(target/'report.json',report);np.savez_compressed(out/'fit.npz',before=before,after=after,parameters=parameters)
    save(out/'solver.json',solver);save(out/'fit-summary.json',dict(convergence=convergence,export=roundtrip,quality_approved=False))
    save(out/'pipeline.json',dict(status='complete',finished_at=now()))


def run(out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    cases=['jump-204','dance-203'];modes=['clearance','trajectory']
    save(out/'design.json',dict(cases=cases,modes=modes,source='context-transfer-v1 pose_fitted context',support_targets_confirmed=False,settings=DEFAULTS,no_inference_or_training=True,quality_approved=False))
    from action_worker_lock import worker_lock
    with worker_lock():
        for case in cases:
            for mode in modes:
                save(out/'pipeline.json',dict(status='fitting',case=case,mode=mode));run_case(case,mode,out/case/mode)
    save(out/'pipeline.json',dict(status='complete',finished_at=now()))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args()
    run(a.output)
