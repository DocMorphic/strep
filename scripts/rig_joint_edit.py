"""Execute a snapshotted joint edit and audit the delivered finite rig clip."""
import copy
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_transition import localize
from rig_loop import encode
from rig_pose_trajectory import PoseTrajectoryFitter
from rig_coupled_pose import CoupledPoseFitter, window_basis
from rig_pose_tolerances import PoseTolerances
from rig_target_refinement import TargetPreservingRefiner


def angles(matrices):
    shape=matrices.shape[:-2]
    return np.degrees(Rotation.from_matrix(matrices.reshape(-1,3,3)).magnitude()).reshape(shape)


def audit_clip(path, before, spec, targets, guards=None):
    """Independent decoded FK, edit bounds, targets and integer/half-frame floors."""
    asset=RigAsset.load(path);sampler=AnimationSampler(asset.document,asset.binary,0)
    after=np.array([sampler.sample(float(np.float32(f/30))) for f in range(len(before))])
    weights=np.array(targets['envelope']);fixed=weights==0
    root=spec['root_node'];nodes=[v['node'] for v in spec['edit_joints'].values()]
    prior=localize(before,asset.parents);local=localize(after,asset.parents)
    untouched=[n for n in range(len(asset.parents)) if n not in nodes and n!=root]
    context_error=float(np.abs(after[fixed]-before[fixed]).max())
    untouched_error=float(np.abs(local[:,untouched]-prior[:,untouched]).max()) if untouched else 0.
    delta=np.linalg.solve(prior[:,nodes,:3,:3],local[:,nodes,:3,:3]);edits=angles(delta)
    caps=np.array([v['limit_degrees'] for v in spec['edit_joints'].values()])
    step=angles(np.linalg.solve(delta[:-1],delta[1:]))
    old_step=angles(np.linalg.solve(prior[:-1,nodes,:3,:3],prior[1:,nodes,:3,:3]))
    new_step=angles(np.linalg.solve(local[:-1,nodes,:3,:3],local[1:,nodes,:3,:3]))
    shift=after[:,root,:3,3]-before[:,root,:3,3];limits=spec['limits']
    horizontal=np.linalg.norm(shift[:,[0,2]],axis=1);vertical=np.abs(shift[:,1])
    root_step=np.linalg.norm(np.diff(shift,axis=0),axis=1)
    hard=dict(fixed_context=context_error<=1e-5,untouched_chains=untouched_error<=1e-5,
        local_translations=float(np.abs(local[:,nodes,:3,3]-prior[:,nodes,:3,3]).max())<=1e-5,
        joint_limits=bool(np.all(edits<=weights[:,None]*caps+1e-4)),
        edit_steps=bool(np.all(step<=limits['joint_step_degrees']+1e-4)),
        actual_steps=bool(np.all(new_step<=np.minimum(180,old_step+.5)+1e-4)),
        horizontal_root=bool(np.all(horizontal<=weights*limits['root_horizontal_m']+1e-6)),
        vertical_root=bool(np.all(vertical<=weights*limits['root_vertical_m']+1e-6)),
        root_steps=bool(np.all(root_step<=limits['root_step_m']+1e-6)))
    points=np.array([asset.vertices(w) for w in after]);floor=np.maximum(0,-points[:,:,1].min(axis=1))
    half=[max(0.,-float(asset.vertices(sampler.sample((f+.5)/30))[:,1].min())) for f in range(len(before)-1)]
    goals=[]
    for goal in targets['goals']:
        w=after[goal['frame'],goal['node']]
        position=float(np.linalg.norm(w[:3,3]-goal['position_m']))
        rotation=float(angles(np.linalg.solve(np.array(goal['rotation_matrix']),w[:3,:3])))
        goals.append(dict(frame=goal['frame'],node=goal['node'],position_error_m=position,
            orientation_error_degrees=rotation,within_tolerances=position<=.005 and rotation<=5))
    supports=[];guard_excess=[]
    for index,s in enumerate(targets['supports']):
        a,b=s['start_frame'],s['end_frame_exclusive'];track=points[a:b][:,s['vertices']].mean(axis=1)
        speed=np.linalg.norm(np.diff(track,axis=0),axis=1)*30
        supports.append(dict(side=s['side'],provenance=s['provenance'],
            position_error_max_m=float(np.linalg.norm(track-s['target_position_m'],axis=1).max()),
            speed_max_m_s=float(speed.max()) if len(speed) else 0.))
        if guards is not None:
            cap=guards['supports'][index]
            guard_excess.append(dict(side=s['side'],
                position_cap_excess_m=float(np.maximum(0,np.linalg.norm(track-s['target_position_m'],axis=1)-cap['position']).max()),
                edge_cap_excess_m=float(np.maximum(0,speed/30-cap['edge']).max()) if len(speed) else 0.))
    flags=[]
    if not all(hard.values()):flags.extend('hard_'+k+'_failed' for k,v in hard.items() if not v)
    if not all(g['within_tolerances'] for g in goals):flags.append('joint_targets_missed')
    if floor.max()>.005:flags.append('whole_clip_floor_failed')
    if max(half)>.005:flags.append('half_frame_floor_failed')
    if any(s['position_error_max_m']>.02 for s in supports):flags.append('authored_support_position_failed')
    delivered_guards=None
    if guards is not None:
        excess=float(np.maximum(0,floor-np.array(guards['floor_caps_m'])).max())
        delivered_guards=dict(floor_cap_excess_m=excess,support_cap_excess=guard_excess,
            exact_caps_met=excess==0 and all(r['position_cap_excess_m']==r['edge_cap_excess_m']==0 for r in guard_excess))
    return dict(hard_checks=hard,hard_checks_passed=all(hard.values()),context_max_matrix_error=context_error,
        target_metrics=goals,targets_reached=all(g['within_tolerances'] for g in goals),
        floor_depth_max_m=float(floor.max()),editable_floor_depth_max_m=float(floor[~fixed].max()),
        floor_frames_above_1cm=int((floor>.01).sum()),half_frame_floor_depth_max_m=max(half),
        support_metrics=supports,delivered_refinement_guards=delivered_guards,flags=flags,numerical_screen_passed=not flags,human_approved=False,
        scope='Decoded 30fps/half-frame geometry, authored joint goals, hard motion bounds and inherited support positions. No dynamics, continuous collision, action or animator approval.')


def run(folder, *, feasibility_iterations=60, refinement_iterations=40):
    folder=Path(folder);request=read(folder/'request.json');source=folder/'input/character.glb'
    if sha256(source)!=request['input_glb_sha256'] or any(sha256(folder/name)!=digest for name,digest in request['input_files'].items()):
        raise ValueError('Joint edit input snapshot changed')
    edit=read(folder/'joint-edit.json');spec=read(folder/'joint-spec.json');targets=read(folder/'joint-targets.json')
    data=dict(np.load(folder/'joint-input.npz',allow_pickle=False));before=data['before']
    rig=RigAsset.load(source);report=read(folder/'input/report.json')
    fitter=PoseTrajectoryFitter(rig,spec,data['local'],{k:np.array(v) for k,v in targets['targets_m'].items()},
        targets['envelope'],targets['supports'],targets['goals'])
    basis=window_basis(targets['envelope'],spacing=10)
    stage=folder/'target-fit';stage.mkdir(exist_ok=False)
    save(folder/'pipeline.json',dict(status='processing',stage='Fitting sparse joint targets with fixed context'))
    with threadpool_limits(limits=1):
        values,trace,fit=PoseTolerances(CoupledPoseFitter(fitter,basis)).solve(stage,max_iterations=feasibility_iterations)
    save(stage/'summary.json',fit);save(stage/'trace.json',trace)
    animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}|set(fitter.nodes)
    fixed=np.array(targets['envelope'])==0
    warm=fitter.world.copy();warm[fixed]=before[fixed]
    encode(rig,warm,animated,spec['root_node'],stage/'character.glb','Target feasibility · '+edit['label'])
    warm_values=values.copy();quality=None
    if fit['targets_reached']:
        stage=folder/'quality-fit';stage.mkdir(exist_ok=False)
        refiner=TargetPreservingRefiner(CoupledPoseFitter(fitter,basis))
        save(stage/'guards.json',dict(floor_caps_m=refiner.floor_caps.tolist(),
            supports=[{k:v.tolist() for k,v in c.items()} for c in refiner.support_caps]))
        save(folder/'pipeline.json',dict(status='processing',stage='Refining quality while retaining joint targets'))
        with threadpool_limits(limits=1):values,trace,quality=refiner.solve(stage,max_iterations=refinement_iterations)
        save(stage/'summary.json',quality);save(stage/'trace.json',trace)
    after=fitter.world.copy();after[fixed]=before[fixed]
    if not np.array_equal(after[fixed],before[fixed]):raise ValueError('Fixed source context changed')
    out=folder/'transfer';out.mkdir(exist_ok=False)
    times,roundtrip=encode(rig,after,animated,spec['root_node'],out/'character.glb',edit['label'])
    guards=read(folder/'quality-fit/guards.json') if quality is not None else None
    audit=audit_clip(out/'character.glb',before,spec,targets,guards)
    audit.update(created_at=now(),input_glb_sha256=sha256(source),glb_sha256=sha256(out/'character.glb'),
        feasibility=fit,refinement=quality,export=roundtrip,refinement_skipped=quality is None,
        requested_window=[edit['start_frame'],edit['last_frame']],solver_budgets=dict(feasibility=feasibility_iterations,refinement=refinement_iterations))
    save(out/'joint-edit-audit.json',audit)
    if not audit['hard_checks_passed']:raise ValueError('Exported joint edit violated a hard motion/context bound; candidate retained for diagnosis')
    for name in ('inventory.json','rig-profile.json','contacts.json','events.json','contact-review.json'):
        if (folder/'input'/name).exists():shutil.copyfile(folder/'input'/name,out/name)
    annotations=read(out/'contacts.json')
    annotations.setdefault('origin','none_supplied' if report.get('source_kind')=='gltf_animation' else 'source_model_predictions')
    save(out/'contacts.json',annotations)
    if (folder/'input/contact-spec.json').exists():
        contacts=read(folder/'input/contact-spec.json');contacts['glb_sha256']=sha256(out/'character.glb')
        contacts['provenance']+=' Joint-target edit retained targets and timing; motion/contact validity needs review.'
        save(folder/'contact-spec.json',contacts)
    root=spec['root_node']
    save(out/'root-motion.json',dict(node=root,space='Edited mapped pelvis world transform; source time and placement retained',
        times_s=times.tolist(),positions_m=after[:,root,:3,3].tolist(),rotations_xyzw=Rotation.from_matrix(after[:,root,:3,:3]).as_quat().tolist()))
    np.savez_compressed(out/'joint-fit.npz',before=before,after=after,parameters=values,warm_start=warm,warm_parameters=warm_values,basis=basis)
    save(out/'timeline.json',dict(fps=30,frames=len(before),source_frames=list(range(len(before))),
        input_sha256=sha256(source),input_variant=request['input_variant'],requested_window=[edit['start_frame'],edit['last_frame']],
        annotations='Timing and provenance retained verbatim; edited geometry requires contact/event review.'))
    report.update(glb_sha256=sha256(out/'character.glb'),timeline_edited=True,
        contact_annotations_file=str((out/'contacts.json').resolve()),contact_annotations_sha256=sha256(out/'contacts.json'),
        target_mesh_floor_depth_max_m=audit['floor_depth_max_m'],target_mesh_floor_frames_above_1cm=audit['floor_frames_above_1cm'],
        animation_name=edit['label'],last_key_time_s=float(times[-1]),edit_parent_glb_sha256=sha256(source))
    save(out/'report.json',report)
    return report,audit
