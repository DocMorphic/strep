"""Transport a passing alternative-guide pose through the authored grasp."""
import argparse
import copy
from pathlib import Path
import shutil
import time
import numpy as np
import psutil
import torch
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from regional_pose_witness import RegionalPoseProblem
from regional_wrist_track import frame_problem,fixed_finger_parameters,project
from region_grasp_track import arm_columns,smoothstep5
from scene_solver_context import context_primitives
from build_soma_preview import make_preview
from gltf_tools import write_glb


def run(pose_report,output,reserve=.0001):
    if type(reserve) not in [int,float] or not np.isfinite(reserve) or not 0<=reserve<=.0005:raise ValueError('Reserve must be within 0--0.5 mm')
    torch.set_num_threads(2);pose_report,output=Path(pose_report).resolve(),Path(output).resolve()
    pp,pr=read(pose_report/'protocol.json'),read(pose_report/'result.json')
    if not pr['alternative_pose_passed'] or pr['protocol_sha256']!=sha256(pose_report/'protocol.json') or pr['pose_sha256']!=sha256(pose_report/'pose.npz'):raise ValueError('Passing matching alternative pose required')
    for path,digest in pp['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Pose input changed')
    for name,digest in pp['methods'].items():
        if sha256(pose_report/'implementation'/name)!=digest:raise ValueError('Pose method snapshot changed')
    gp=read(ROOT/pp['source']/'protocol.json');hp=read(ROOT/gp['source']/'protocol.json');prior=read(ROOT/hp['study']/'protocol.json')
    fit=ROOT/prior['fit'];p0=RegionalPoseProblem(fit,prior['frame']);source_scene=read(fit/'authored-scene.json');scene=copy.deepcopy(source_scene)
    reference=np.array(pr['parameters']);reference_motion=dict(np.load(pose_report/'pose.npz',allow_pickle=False));anchors={};bindings=[]
    for hand,digest in pr['hand_results'].items():
        if sha256(pose_report/hand/'result.json')!=digest:raise ValueError('Projection hand result changed')
        result=read(pose_report/hand/'result.json');shape=gp['shapes'][result['source_rank']['shape_index']]
        contact=next(c for c in scene['contacts'] if c['region_contact']['hand']==hand);anchor=result['source_rank']['anchor']
        anchors[contact['id']]=anchor;contact['effector']['surface_vertex']=anchor
        bindings.append(dict(hand=hand,contact_id=contact['id'],original_anchor=shape['original_anchor'],anchor=anchor,object_id=contact['target']['object']))
    spans={(c['start_frame'],c['end_frame']) for c in scene['contacts']}
    if len(spans)!=1 or scene['fps']!=30:raise ValueError('Synchronized 30 fps grasp required')
    start,end=spans.pop();guard_end=end+1;frames=scene['frame_count']
    if guard_end>=frames:raise ValueError('Release guard outside clip')
    edit_start=max(0,start-12);edit_end=min(frames-1,guard_end+12)
    targets={}
    for binding in bindings:
        hand=binding['hand'];wrist=p0.names.index(hand);r=next(r for r in p0.regions if r['id']==binding['contact_id'])
        _,object_track=next((g,o) for g,o in context_primitives(p0.context) if o['id']==binding['object_id'])
        op=np.array(object_track['positions_m']);orr=np.array(object_track['rotations']);reference_rotation=orr[p0.frame]
        local_position=reference_rotation.T@(reference_motion['posed_joints'][0,wrist]-reserve*r['normal']-op[p0.frame])
        local_rotation=reference_rotation.T@reference_motion['global_rot_mats'][0,wrist]
        targets[hand]=dict(positions=np.einsum('fij,j->fi',orr,local_position)+op,rotations=orr@local_rotation)
    # Validate the physical finger shape at every key before allocating output.
    for frame in range(start,guard_end+1):fixed_finger_parameters(frame_problem(p0,frame,scene,anchors),reference,reference_motion['local_rot_mats'][0])
    output.mkdir(parents=True,exist_ok=False);snap=output/'implementation';snap.mkdir()
    for path in (ROOT/'scripts').glob('*.py'):shutil.copyfile(path,snap/path.name)
    inputs=dict(pp['inputs']);inputs.update({str(pose_report/n):sha256(pose_report/n) for n in ['protocol.json','result.json','pose.npz']})
    inputs.update({str(pose_report/h/'result.json'):digest for h,digest in pr['hand_results'].items()})
    settings=dict(maximum_evaluations=100,seconds_per_frame=45.,maximum_seconds=600.,maximum_rss_bytes=2*1024**3,minimum_available_bytes=int(1.25*1024**3),blend_frames=12)
    protocol=dict(at=now(),pose_report=pose_report.relative_to(ROOT).as_posix(),fit=prior['fit'],reference_frame=p0.frame,frame_count=frames,
        active_interval=[start,end],projection_interval=[start,guard_end],edited_interval=[edit_start,edit_end],bindings=bindings,outward_reserve_m=reserve,
        settings=settings,inputs=inputs,implementation={q.name:sha256(q) for q in snap.iterdir()},actor=read(fit/'protocol.json')['actor'],
        contact_ids=[c['id'] for c in scene['contacts']],config=p0.config,targets={hand:{k:v.tolist() for k,v in t.items()} for hand,t in targets.items()},
        condition='Explicit alternative guides fixed for the whole clip; unchanged regions/targets/numeric limits. Fixed absolute reference finger rotations within each frame original edit budgets. Other non-arm edits/root lift fixed during grasp. Original source clip outside quintic 12-frame blends.',
        scope='Development trajectory, not a scene solver V14 rerun. Exported dense contact/geometry/edit checks required. No anatomy, self-collision, balance, force, semantic or human review approval.',quality_approved=False)
    save(output/'protocol.json',protocol);save(output/'authored-scene.json',scene);save(output/'original-scene.json',source_scene)
    shutil.copyfile(fit/'source-motion.npz',output/'source-motion.npz')
    reference_audit,_=frame_problem(p0,p0.frame,scene,anchors).independent(reference)
    if reference_audit!=pr['alternative_condition_audit']:raise ValueError('Reference pose replay changed')
    columns,_=arm_columns(p0);last=reference[columns].copy();parameters={};rows=[];started=time.monotonic();peak=0
    for frame in range(start,guard_end+1):
        p=frame_problem(p0,frame,scene,anchors);fixed=fixed_finger_parameters(p,reference,reference_motion['local_rot_mats'][0]);frame_start=time.monotonic()
        def guard():
            nonlocal peak
            peak=max(peak,psutil.Process().memory_info().rss)
            if time.monotonic()-frame_start>settings['seconds_per_frame'] or time.monotonic()-started>settings['maximum_seconds'] or peak>settings['maximum_rss_bytes'] or psutil.virtual_memory().available<settings['minimum_available_bytes']:raise TimeoutError('Moving grasp resource guard')
        local_targets={hand:dict(position=t['positions'][frame],rotation=t['rotations'][frame]) for hand,t in targets.items()}
        values,solver=project(p,fixed,last,local_targets,guard,settings['maximum_evaluations'],frame==start);last=values[columns].copy()
        audit,motion=p.independent(values);parameters[frame]=values;reach=[]
        for hand,t in local_targets.items():
            wrist=p.names.index(hand);position_error=float(np.linalg.norm(motion['posed_joints'][0,wrist]-t['position']))
            angle=float(np.rad2deg(np.linalg.norm(Rotation.from_matrix(t['rotation'].T@motion['global_rot_mats'][0,wrist]).as_rotvec())))
            reach.append(dict(hand=hand,position_error_m=position_error,rotation_error_degrees=angle,passed=position_error<=.0001 and angle<=.1))
        passed=audit['pose_witness_passed'] and all(r['passed'] for r in reach)
        rows.append(dict(frame=frame,parameters=values.tolist(),candidate=audit,reach=reach,passed=bool(passed),solver=solver,seconds=time.monotonic()-frame_start))
        save(output/'progress.json',dict(status='running',pid=psutil.Process().pid,frame=frame,rows=rows))
        if frame==start or frame%10==0 or frame==guard_end:print(dict(frame=frame,passed=passed,clearance=audit['objects'][0]['minimum_clearance_m'],evaluations=solver['solver']['evaluations']),flush=True)
        if solver['status']!='complete':
            save(output/'result.json',dict(status='interrupted_resource_guard',rows=rows,motion_generated=False,quality_approved=False));return
    candidate={k:v.copy() for k,v in p0.base.items()};track=[]
    for frame in range(edit_start+1,edit_end):
        if frame<start:weight=float(smoothstep5((frame-edit_start)/(start-edit_start)));values=weight*parameters[start]
        elif frame>guard_end:weight=float(1-smoothstep5((frame-guard_end)/(edit_end-guard_end)));values=weight*parameters[guard_end]
        else:weight=1.;values=parameters[frame]
        p=frame_problem(p0,frame,scene,anchors,contacts=False);audit,motion=p.independent(values)
        if not audit['bounds_passed']:raise ValueError('Blended trajectory exceeded original edit bounds')
        for key in candidate:candidate[key][frame]=motion[key][0]
        track.append(dict(frame=frame,blend_weight=weight,parameters=values.tolist()))
    np.savez(output/'motion.npz',**candidate)
    recipe=dict(kind='alternative-guide-wrist-transport-v1',parameter_track=track,reference_parameters=reference.tolist(),quality_approved=False);save(output/'recipe.json',recipe)
    for label,motion in [('source',p0.base),('candidate',candidate)]:
        doc,binary,_,_=make_preview(p0.skin,motion,np.zeros(3),repeat=False);write_glb(output/(label+'.glb'),doc,binary)
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Trajectory input changed')
    for name,digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Trajectory method changed')
    result=dict(at=now(),status='complete',rows=rows,parameter_track=track,motion_generated=True,active_pass_count=sum(r['passed'] for r in rows),active_frame_count=len(rows),
        seconds=time.monotonic()-started,peak_rss_bytes=peak,protocol_sha256=sha256(output/'protocol.json'),candidate_sha256=sha256(output/'motion.npz'),
        candidate_glb_sha256=sha256(output/'candidate.glb'),source_glb_sha256=sha256(output/'source.glb'),recipe_sha256=sha256(output/'recipe.json'),authored_scene_sha256=sha256(output/'authored-scene.json'),quality_approved=False)
    save(output/'result.json',result);save(output/'progress.json',dict(status='complete',active_pass_count=result['active_pass_count'],active_frame_count=len(rows)))
    print({k:result[k] for k in ['status','active_pass_count','active_frame_count','seconds','peak_rss_bytes']},flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('pose_report',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--outward-reserve-m',type=float,default=.0001)
    args=parser.parse_args()
    with threadpool_limits(limits=2):run(args.pose_report,args.output,args.outward_reserve_m)
