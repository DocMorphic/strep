"""Transfer exact-pose native candidates, splice, then fit target surface clearance."""
import copy
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_transition import localize,compose,blend
from rig_prompt_edit import weights
from rig_loop import encode
from rig_clearance_fit import prepare,ClearanceFitter,native_heights


def root_track(out,world,root,times):
    save(out/'root-motion.json',dict(node=root,space='Target pelvis world transform; no root extraction',times_s=times.tolist(),positions_m=world[:,root,:3,3].tolist(),rotations_xyzw=Rotation.from_matrix(world[:,root,:3,:3]).as_quat().tolist()))


def run_case(case,out):
    from kimodo.skeleton import SOMASkeleton77
    from retarget_rig import transfer,resolve_profile
    from build_soma_preview import ASSET
    source=ROOT/'reports/motion-correction-v2'/case/'guided_pose_only'
    record=read(source/'record.json');job=record['source_job'];original=ROOT/'reports/rig-jobs'/job
    if sha256(source/'motion.npz')!=record['output_sha256']:raise ValueError('Corrected source changed')
    rig,raw_splice,report,spec,targets,envelope=prepare(job,out)
    shutil.copytree(out/'input',out/'raw-splice')
    shutil.copyfile(out/'request.json',out/'raw-request.json')
    snapshot=out/'implementation';snapshot.mkdir()
    for name in ['study_corrected_rig_transfer.py','rig_clearance_fit.py','target_rig_contact.py','rig_periodic_contact.py','retarget_rig.py','rig_prompt_edit.py']:
        shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    edit=read(original/'prompt-edit.json');a,b,k=(edit[n] for n in ('start_frame','last_frame','blend_frames'))
    reference=RigAsset.load(original/'source/character.glb');profile=read(original/'source/rig-profile.json');mapping,offset=resolve_profile(reference,profile)
    native=dict(np.load(source/'motion.npz',allow_pickle=False))
    origin=np.array(read(original/'transfer/prompt-edit-audit.json')['origin_offset_m'])
    for name in ('root_positions','posed_joints'):native[name]=native[name]+origin
    np.savez_compressed(out/'aligned-native.npz',**native)
    shutil.copyfile(source/'motion.npz',out/'corrected-native.npz')
    replacement,*_=transfer(reference,native,SOMASkeleton77(),mapping,offset,profile.get('axis_alignment_xyzw'))
    input_rig=RigAsset.load(original/'input/character.glb');sampler=AnimationSampler(input_rig.document,input_rig.binary,0)
    before=np.array([sampler.sample(float(np.float32(f/30))) for f in range(report['frames'])])
    n=b-a+1;local=localize(before,rig.parents);local[a:b+1]=blend(local[a:b+1],localize(replacement,rig.parents),weights(n,k));spliced=compose(local,rig.parents)
    animated={c[0] for c in sampler.channels}|set(mapping.values())
    times,roundtrip=encode(rig,spliced,animated,report['root_node'],out/'input/character.glb','Exact native pose fitting, target splice')
    root_track(out/'input',spliced,report['root_node'],times)
    # Full transfer is also retained: splice preservation cannot hide rig-space errors.
    (out/'unblended').mkdir();encode(reference,replacement,set(mapping.values()),report['root_node'],out/'unblended/character.glb','Unblended exact-pose transfer')
    request=read(out/'request.json');heights=native_heights(native,dict(np.load(ASSET,allow_pickle=False)))
    for name in targets:
        base=np.array(request['original_heights_m'][name])
        targets[name]=base.copy();targets[name][a:b+1]=(1-envelope[a:b+1])*base[a:b+1]+envelope[a:b+1]*np.maximum(0,heights[name]*request['leg_scale']+offset[1])
    spec['glb_sha256']=sha256(out/'input/character.glb');save(out/'spec.json',spec)
    request.update(source_glb_sha256=sha256(out/'input/character.glb'),native_motion_sha256=sha256(out/'aligned-native.npz'),corrected_native_sha256=record['output_sha256'],targets_m={k:v.tolist() for k,v in targets.items()},raw_native_heights_m={k:v.tolist() for k,v in heights.items()},source_model_guides_passed=False,corrected_native_guides_passed=True,scope='Raw generation still fails. Pose-only corrected native constraints pass. All target splice and mesh changes audited separately.')
    save(out/'request.json',request)
    report=copy.deepcopy(report);report.update(glb_sha256=sha256(out/'input/character.glb'),target_mesh_floor_depth_max_m=roundtrip['floor_depth_max_m'],target_mesh_floor_frames_above_1cm=roundtrip['floor_frames_above_1cm'])
    save(out/'input/report.json',report)
    timeline=read(out/'input/timeline.json');timeline['corrected_motion_sha256']=record['output_sha256'];timeline['scope']='Original clock and envelope; pose-only corrected native input. Raw generated_motion_sha256 remains original provenance.';save(out/'input/timeline.json',timeline)
    save(out/'transfer-record.json',dict(case=case,job=job,origin_m=origin.tolist(),edit=edit,mapped_nodes=mapping,corrected_source=source.relative_to(ROOT).as_posix(),original_source_sha256=sha256(original/'input/character.glb'),raw_splice_sha256=sha256(original/'transfer/character.glb'),corrected_source_sha256=record['output_sha256'],human_approved=False))
    horizontal=np.array([rig.vertices(world) for world in spliced])
    fitter=ClearanceFitter(rig,spec,localize(spliced,rig.parents),targets,envelope,horizontal)
    save(out/'pipeline.json',dict(status='fitting'))
    with threadpool_limits(limits=1):parameters,solver,convergence=fitter.solve(out)
    after=np.array([fitter.pose(f,x)[0] for f,x in enumerate(parameters)])
    target=out/'candidate';target.mkdir()
    times,roundtrip=encode(rig,after,animated|set(fitter.nodes),report['root_node'],target/'character.glb','Exact-pose transfer with bounded surface correction')
    for name in ('inventory.json','rig-profile.json','contacts.json','events.json','timeline.json','contact-review.json'):
        if (out/'input'/name).exists():shutil.copyfile(out/'input'/name,target/name)
    root_track(target,after,report['root_node'],times)
    report.update(glb_sha256=sha256(target/'character.glb'),target_mesh_floor_depth_max_m=roundtrip['floor_depth_max_m'],target_mesh_floor_frames_above_1cm=roundtrip['floor_frames_above_1cm'],contact_annotations_file=str((target/'contacts.json').resolve()),contact_annotations_sha256=sha256(target/'contacts.json'),human_approved=False)
    save(target/'report.json',report);np.savez_compressed(out/'fit.npz',before=spliced,after=after,parameters=parameters)
    save(out/'solver.json',solver);save(out/'fit-summary.json',dict(convergence=convergence,export=roundtrip,scope='Exact native boundary fitting plus original envelope splice and bounded target-mesh clearance. Not semantic/physics/contact approval.'))
    save(out/'pipeline.json',dict(status='complete',finished_at=now(),quality_approved=False))


def run(out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    cases=['jump-205','jump-204','dance-203','dance-204'];save(out/'design.json',dict(cases=cases,method='Pose-only native correction then unchanged transfer/splice and v3 bounded mesh clearance; same four seeds. No inference or training.'))
    from action_worker_lock import worker_lock
    with worker_lock():
        for case in cases:
            save(out/'pipeline.json',dict(status='fitting',case=case));run_case(case,out/case)
    save(out/'pipeline.json',dict(status='complete',finished_at=now()))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);args=p.parse_args();existed=args.output.exists()
    try:run(args.output)
    except Exception as exc:
        if not existed and args.output.exists():save(args.output/'pipeline.json',dict(status='failed',error=str(exc)))
        raise
