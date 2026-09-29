"""Correct only the pre-contact path; preserve the accepted moving grasp exactly."""
import argparse
import shutil
import time
from pathlib import Path
import numpy as np
import psutil
import torch
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from grasp_pose_witness import PoseProblem
from grasp_contact_binding import apply_region_binding
from grasp_orientation import hand_frame,unit
from region_grasp_track import arm_columns,project
from sphere_approach import set_problem_frame,influenced_hand_vertices,outward_clearance_shift


def run(study,output,guide_clearance_m=.0025):
    torch.set_num_threads(2);study,output=Path(study).resolve(),Path(output).resolve()
    protocol,result=read(study/'protocol.json'),read(study/'result.json')
    if result['status']!='complete' or sha256(study/'motion.npz')!=result['motion_sha256'] or sha256(study/'protocol.json')!=result['protocol_sha256']:raise ValueError('Completed unchanged region track required')
    if not np.isfinite(guide_clearance_m) or not .002<=guide_clearance_m<=.005:raise ValueError('Guide clearance must lie between 2 and 5 mm; acceptance stays 2 mm')
    inputs=dict(protocol['inputs'])
    for name in ['protocol.json','result.json','motion.npz']:inputs[(study/name).relative_to(ROOT).as_posix()]=sha256(study/name)
    for name,digest in inputs.items():
        if sha256(ROOT/name)!=digest:raise ValueError('Input changed')
    fit=ROOT/protocol['study']/'fit';summary=read(fit/'summary.json');folder=fit/'assets'/summary['trials'][0]['id']/'A'
    skin=dict(np.load(ASSET,allow_pickle=False));start,end=protocol['active_interval'];edit_start=protocol['edited_interval'][0]
    p=PoseProblem(folder,skin,start);bindings=protocol['contact_bindings'];regions=protocol['region_protocols']
    for binding,rp in zip(bindings,regions):apply_region_binding(p,binding['hand'],binding['anchor'],rp['patch'])
    patches={b['hand']:influenced_hand_vertices(p,b['hand']) for b in bindings}
    source=dict(np.load(study/'motion.npz',allow_pickle=False));candidate={k:v.copy() for k,v in source.items()};parameters={r['frame']:np.array(r['parameters']) for r in result['parameter_track']}
    columns,_=arm_columns(p);frozen=np.setdiff1d(np.arange(p.dim),columns)
    settings=dict(maximum_evaluations=100,point_scale_m=.001,direction_scale=.01,regularization=1e-5,seconds_per_frame=60,
                  maximum_rss_bytes=2*1024**3,minimum_available_bytes=int(1.25*1024**3),guide_clearance_m=guide_clearance_m)
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    methods=['correct_region_approach.py','sphere_approach.py','region_grasp_track.py','grasp_contact_binding.py','grasp_pose_witness.py','grasp_pose_witness_bounded.py','grasp_orientation.py','support_contact_v8.py','support_contact_v5.py','floor_contact.py','scene_solver_context.py','object_geometry.py','inspect_motion.py']
    implementation={n:sha256(ROOT/'scripts'/n) for n in methods}
    for n in methods:shutil.copyfile(ROOT/'scripts'/n,output/'implementation'/n)
    patch_protocol=dict(at=now(),base_study=study.relative_to(ROOT).as_posix(),inputs=inputs,implementation=implementation,settings=settings,
                        eligible_frames=list(range(edit_start+1,start)),arm_columns=columns.tolist(),
                        scope='Pre-contact guidance only. For each original blended hand frame, translate the influenced hand patch radially outward to guide clearance, then fit the actual bounded arms. Keep the existing hand orientation and all non-arm parameters. Mixed forearm/hand vertices included in guidance; full articulated skin rechecked. Authored event times and grasp/release frames unchanged. No anatomical, self-collision or dynamics certification.',quality_approved=False)
    save(output/'protocol.json',patch_protocol);rows=[];changed=[];solves=0
    for frame in patch_protocol['eligible_frames']:
        set_problem_frame(p,frame);base=parameters[frame];before,motion=p.independent(base)
        vertices=p.surface.vertices(motion['global_rot_mats'][0],motion['posed_joints'][0])
        with torch.no_grad():_,_,_,tv=p.fk(p.t(base))
        fk_error=float(np.max(np.abs(tv.numpy()-vertices)))
        if fk_error>2e-6:raise ValueError('Pre-contact FK frame mismatch')
        sphere,_,center,_=p.objects[0]
        if sphere.shape!='sphere':raise ValueError('Sphere required')
        targets={};guides=[]
        for binding,rp in zip(bindings,regions):
            hand=binding['hand'];faces=skin['faces'][rp['patch']['face_ids']];wrist=p.names.index(hand);knuckles=[p.names.index(hand+f+'2') for f in ['Index','Middle','Ring','Pinky']]
            point,normal,tangent=hand_frame(vertices,motion['posed_joints'][0],faces,binding['anchor'],wrist,knuckles)
            outward=unit(point-center.numpy()[0]);distance=outward_clearance_shift(vertices[patches[hand]],center.numpy()[0],outward,sphere.dimensions[0],guide_clearance_m)
            targets[hand]=dict(point=point+outward*distance,normal=normal,tangent=tangent)
            guides.append(dict(hand=hand,vertices=len(patches[hand]),outward=outward.tolist(),distance_m=distance,point=targets[hand]['point'].tolist(),normal=normal.tolist(),tangent=tangent.tolist()))
        if not any(g['distance_m']>1e-10 for g in guides):
            rows.append(dict(frame=frame,changed=False,guides=guides,fk_error_m=fk_error));continue
        began=time.monotonic();peak=0
        def guard(evaluations):
            nonlocal peak
            peak=max(peak,psutil.Process().memory_info().rss)
            if time.monotonic()-began>settings['seconds_per_frame'] or peak>settings['maximum_rss_bytes'] or psutil.virtual_memory().available<settings['minimum_available_bytes']:raise TimeoutError('Approach resource guard')
        values,solver=project(p,base,base[columns],targets,settings,guard,check_derivative=solves==0);solves+=1
        np.testing.assert_array_equal(values[frozen],base[frozen]);audit,motion=p.independent(values)
        for name in candidate:candidate[name][frame]=motion[name][0]
        changed.append(frame);row=dict(frame=frame,changed=True,guides=guides,parameters=values.tolist(),solver=solver,before=before,candidate=audit,
                                     geometry_and_bounds_passed=bool(audit['rotation_norm_bounds_passed'] and audit['minimum_floor_height_m']>=p.config['clearance_m']-1e-6 and all(o['minimum_clearance_m']>=p.config['object_clearance_m']-1e-6 for o in audit['objects'])),
                                     seconds=time.monotonic()-began,sampled_peak_rss_bytes=peak,fk_error_m=fk_error)
        rows.append(row);save(output/'progress.json',dict(status='running',rows=rows));print(dict(frame=frame,offsets_m=[g['distance_m'] for g in guides],geometry_passed=row['geometry_and_bounds_passed'],sphere_clearance_m=audit['objects'][0]['minimum_clearance_m']),flush=True)
        if solver['status']!='complete':break
    complete=len(rows)==len(patch_protocol['eligible_frames'])
    for name,digest in inputs.items():
        if sha256(ROOT/name)!=digest:raise ValueError('Input changed during correction')
    for name,digest in implementation.items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Implementation changed during correction')
    unchanged=np.setdiff1d(np.arange(protocol['frame_count']),changed)
    for name in source:np.testing.assert_array_equal(candidate[name][unchanged],source[name][unchanged])
    np.savez(output/'motion.npz',**candidate)
    status='complete' if complete else 'interrupted_resource_guard'
    save(output/'result.json',dict(at=now(),status=status,rows=rows,changed_frames=changed,unchanged_frames=len(unchanged),grasp_and_release_exact=True,
         motion_sha256=sha256(output/'motion.npz'),protocol_sha256=sha256(output/'protocol.json'),quality_approved=False))
    save(output/'progress.json',dict(status=status,rows=rows));print(dict(status=status,changed_frames=changed,grasp_and_release_exact=True),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--guide-clearance-m',type=float,default=.0025);args=parser.parse_args()
    with threadpool_limits(limits=2):run(args.study,args.output,args.guide_clearance_m)
