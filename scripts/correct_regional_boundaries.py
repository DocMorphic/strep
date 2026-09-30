"""Correct only approach/release keys around a retained regional wrist track."""
import argparse
from pathlib import Path
import shutil
import time
import numpy as np
import psutil
import torch
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from regional_pose_witness import RegionalPoseProblem
from regional_wrist_track import frame_problem,project
from region_grasp_track import arm_columns
from sphere_approach import influenced_hand_vertices
from cylinder_approach import cylinder_clearance_shift
from grasp_orientation import unit
from build_soma_preview import make_preview
from gltf_tools import write_glb


def run(study,output,clearance=.0025):
    if type(clearance) not in [int,float] or not np.isfinite(clearance) or not .002<=clearance<=.005:raise ValueError('Guidance clearance must be between 2 and 5 mm')
    torch.set_num_threads(2);study,output=Path(study).resolve(),Path(output).resolve();prior,result=read(study/'protocol.json'),read(study/'result.json')
    if result['status']!='complete' or not result['motion_generated'] or result['protocol_sha256']!=sha256(study/'protocol.json') or result['candidate_sha256']!=sha256(study/'motion.npz'):raise ValueError('Completed unchanged moving grasp required')
    inputs=dict(prior['inputs']);inputs.update({str(study/n):sha256(study/n) for n in ['protocol.json','result.json','motion.npz','authored-scene.json','source-motion.npz','source.glb']})
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Boundary input changed')
    for name,digest in prior['implementation'].items():
        if sha256(study/'implementation'/name)!=digest:raise ValueError('Track snapshot changed')
    p0=RegionalPoseProblem(ROOT/prior['fit'],prior['reference_frame']);scene=read(study/'authored-scene.json');anchors={b['contact_id']:b['anchor'] for b in prior['bindings']}
    columns,_=arm_columns(p0);frozen=np.setdiff1d(np.arange(p0.dim),columns);source=dict(np.load(study/'motion.npz',allow_pickle=False));candidate={k:v.copy() for k,v in source.items()}
    parameters={row['frame']:np.array(row['parameters']) for row in result['parameter_track']};left,right=prior['edited_interval'];start,end=prior['projection_interval']
    eligible=list(range(left+1,start))+list(range(end+1,right));patches={b['hand']:influenced_hand_vertices(p0,b['hand']) for b in prior['bindings']}
    settings=dict(guide_clearance_m=clearance,continuity_weight=1.,maximum_evaluations=100,seconds_per_frame=45.,maximum_seconds=600.,maximum_rss_bytes=2*1024**3,minimum_available_bytes=int(1.25*1024**3))
    output.mkdir(parents=True,exist_ok=False);snap=output/'implementation';snap.mkdir()
    for path in (ROOT/'scripts').glob('*.py'):shutil.copyfile(path,snap/path.name)
    protocol={**prior,**dict(at=now(),base_study=study.relative_to(ROOT).as_posix(),inputs=inputs,implementation={q.name:sha256(q) for q in snap.iterdir()},
        boundary_settings=settings,eligible_frames=eligible,arm_columns=columns.tolist(),
        scope='Boundary-only cylinder guidance on all positively hand-influenced skin, including mixed vertices. Conservative expanded-cylinder radial interval union; actual articulated full skin independently checked. Wrist orientation and non-arm parameters follow the retained blended clip. Grasp/guard and outside frames exact. No temporal, anatomical, self-collision, dynamics or quality approval.',quality_approved=False)}
    save(output/'protocol.json',protocol)
    for name in ['source-motion.npz','source.glb','authored-scene.json','original-scene.json']:shutil.copyfile(study/name,output/name)
    began=time.monotonic();peak=0;rows=[];changed=[];solves=0;status='complete'
    for frame in eligible:
        p=frame_problem(p0,frame,scene,anchors,contacts=False);base=parameters[frame];before,motion=p.independent(base)
        for key in source:np.testing.assert_array_equal(motion[key][0].astype(source[key].dtype),source[key][frame])
        vertices=p.surface.vertices(motion['global_rot_mats'][0],motion['posed_joints'][0]);targets={};guides=[]
        for binding in prior['bindings']:
            hand=binding['hand'];wrist=p.names.index(hand);g,_,center,rotation=next(o for o in p.objects if o[1]==binding['object_id']);center,rotation=center.numpy()[0],rotation.numpy()[0]
            anchor=vertices[binding['anchor']];radial=(anchor-center)@rotation;radial[1]=0.;direction=rotation@unit(radial)
            distance=cylinder_clearance_shift(vertices[patches[hand]],g,center,rotation,direction,clearance)
            targets[hand]=dict(position=motion['posed_joints'][0,wrist]+direction*distance,rotation=motion['global_rot_mats'][0,wrist])
            guides.append(dict(hand=hand,anchor=binding['anchor'],vertex_count=len(patches[hand]),direction=direction.tolist(),distance_m=distance))
        if all(g['distance_m']<=1e-10 for g in guides):
            rows.append(dict(frame=frame,changed=False,guides=guides));continue
        frame_start=time.monotonic()
        def guard():
            nonlocal peak
            peak=max(peak,psutil.Process().memory_info().rss)
            if time.monotonic()-frame_start>settings['seconds_per_frame'] or time.monotonic()-began>settings['maximum_seconds'] or peak>settings['maximum_rss_bytes'] or psutil.virtual_memory().available<settings['minimum_available_bytes']:raise TimeoutError('Boundary projection resource guard')
        values,solver=project(p,base,base[columns],targets,guard,settings['maximum_evaluations'],solves==0,candidate['local_rot_mats'][frame-1],settings['continuity_weight']);solves+=1
        np.testing.assert_array_equal(values[frozen],base[frozen]);audit,motion=p.independent(values)
        for key in candidate:candidate[key][frame]=motion[key][0]
        changed.append(frame);row=dict(frame=frame,changed=True,guides=guides,parameters=values.tolist(),solver=solver,before=before,candidate=audit,
            geometry_and_bounds_passed=bool(audit['pose_witness_passed']),seconds=time.monotonic()-frame_start)
        rows.append(row);save(output/'progress.json',dict(status='running',pid=psutil.Process().pid,frame=frame,rows=rows))
        print(dict(frame=frame,guide_shifts_m=[g['distance_m'] for g in guides],passed=row['geometry_and_bounds_passed'],minimum_clearance_m=audit['objects'][0]['minimum_clearance_m']),flush=True)
        if solver['status']!='complete':status='interrupted_resource_guard';break
    locked=np.setdiff1d(np.arange(prior['frame_count']),changed)
    for key in source:np.testing.assert_array_equal(source[key][locked],candidate[key][locked])
    np.savez(output/'motion.npz',**candidate);save(output/'recipe.json',dict(kind='cylinder-boundary-guidance-v1',base_study=protocol['base_study'],rows=rows,quality_approved=False))
    doc,binary,_,_=make_preview(p0.skin,candidate,np.zeros(3),repeat=False);write_glb(output/'candidate.glb',doc,binary)
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Boundary input changed during projection')
    for name,digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Boundary method changed during projection')
    record=dict(at=now(),status=status,rows=rows,changed_frames=changed,unchanged_frames=len(locked),grasp_and_guard_exact=True,seconds=time.monotonic()-began,peak_rss_bytes=peak,
        candidate_sha256=sha256(output/'motion.npz'),candidate_glb_sha256=sha256(output/'candidate.glb'),source_glb_sha256=sha256(output/'source.glb'),
        recipe_sha256=sha256(output/'recipe.json'),authored_scene_sha256=sha256(output/'authored-scene.json'),protocol_sha256=sha256(output/'protocol.json'),quality_approved=False)
    save(output/'result.json',record);save(output/'progress.json',dict(status=status,changed_frames=changed));print(dict(status=status,changed_frames=changed,seconds=record['seconds']),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--guide-clearance-m',type=float,default=.0025);args=parser.parse_args()
    with threadpool_limits(limits=2):run(args.study,args.output,args.guide_clearance_m)
