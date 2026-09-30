"""Replay native wrist tracks and audit exported quarter-frame geometry/bounds."""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from strep import ROOT,read,save,sha256,now
from regional_pose_witness import RegionalPoseProblem
from region_grasp_track import arm_columns
from audit_scene_region_fit import run as geometry_audit
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler
from scene_constraints import pose,sample_object
from scene_region_contact import compile_region,measure_frame


def quintic(t):return 6*t**5-15*t**4+10*t**3


def run(study,output):
    study,output=Path(study).resolve(),Path(output).resolve();protocol,result=read(study/'protocol.json'),read(study/'result.json')
    if result['status']!='complete' or not result['motion_generated']:raise ValueError('Complete wrist trajectory required')
    output.mkdir(parents=True,exist_ok=False);shutil.copyfile(__file__,output/Path(__file__).name)
    p=RegionalPoseProblem(ROOT/protocol['fit'],protocol['reference_frame']);p.regions=[]
    source=p.base;candidate=dict(np.load(study/'motion.npz',allow_pickle=False));recipe=read(study/'recipe.json')
    reference=np.array(read(ROOT/protocol['pose_report']/'result.json')['parameters'])
    reference_motion=dict(np.load(ROOT/protocol['pose_report']/'pose.npz',allow_pickle=False))
    start,end=protocol['projection_interval'];left,right=protocol['edited_interval'];active={row['frame']:row for row in result['rows']}
    if set(active)!=set(range(start,end+1)) or len(active)!=len(result['rows']):raise ValueError('Incomplete native projection keys')
    track=result['parameter_track'];assert track==recipe['parameter_track']
    assert [row['frame'] for row in track]==list(range(left+1,right))
    untouched=np.setdiff1d(np.arange(protocol['frame_count']),[row['frame'] for row in track])
    for key in source:np.testing.assert_array_equal(source[key][untouched],candidate[key][untouched])
    arms,_=arm_columns(p);arm_joints=np.array(p.editable)[arms.reshape(-1,3)[:,0]//3]
    finger_slots=[i for i,j in enumerate(p.editable) if 'Hand' in p.names[j] and p.names[j] not in ['LeftHand','RightHand']]
    finger_columns=np.array([3*i+k for i in finger_slots for k in range(3)]);fixed=np.setdiff1d(np.arange(p.dim),np.r_[arms,finger_columns]);native_bounds=0
    for record in track:
        frame=record['frame'];values=np.array(record['parameters']);p.frame=frame
        if frame<start:weight=quintic((frame-left)/(start-left));expected=weight*np.array(active[start]['parameters'])
        elif frame>end:weight=1-quintic((frame-end)/(right-end));expected=weight*np.array(active[end]['parameters'])
        else:
            weight=1.;expected=np.array(active[frame]['parameters']);np.testing.assert_array_equal(values[fixed],reference[fixed])
            joints=[p.editable[i] for i in finger_slots]
            angles=Rotation.from_matrix(source['local_rot_mats'][frame,joints].transpose(0,2,1)@reference_motion['local_rot_mats'][0,joints]).as_rotvec()
            np.testing.assert_array_equal(values[finger_columns],angles.ravel())
        np.testing.assert_allclose(values,expected,atol=1e-12,rtol=0);assert abs(weight-record['blend_weight'])<1e-12
        audit,motion=p.independent(values);assert audit['bounds_passed'];native_bounds+=1
        for key in candidate:np.testing.assert_array_equal(motion[key][0].astype(candidate[key].dtype),candidate[key][frame])
    native_steps=[]
    for frame in range(start+1,end+1):
        before=Rotation.from_matrix(candidate['local_rot_mats'][frame-1,arm_joints]);after=Rotation.from_matrix(candidate['local_rot_mats'][frame,arm_joints])
        angles=np.rad2deg(np.linalg.norm((before.inv()*after).as_rotvec(),axis=1));row=active[frame]
        if 'arm_step_degrees' in row:
            np.testing.assert_allclose(angles,row['arm_step_degrees'],atol=1e-12,rtol=0)
            expected=not protocol.get('continuity_weight',0) or bool(angles.max()<=protocol['maximum_step_degrees'])
            assert expected==row['sampled_step_passed']
        native_steps.append(dict(frame=frame,maximum_step_degrees=float(angles.max())))
    # Existing independent auditor verifies native FK and GLB keys, samples all
    # full-skin geometry and authored contacts, and reports speed/acceleration.
    geometry_audit(study,output/'geometry');dense=read(output/'geometry/verification.json')
    scene=read(study/'authored-scene.json');original=read(study/'original-scene.json');origin,placement=pose(scene['actors'][protocol['actor']]['transform'])
    samples={};channels={}
    for label in ['source','candidate']:
        doc,binary=read_glb(study/(label+'.glb'));sampler=AnimationSampler(doc,binary,0);joints=doc['skins'][0]['joints']
        samples[label]=(sampler,joints);channels[label]={j:c for c in sampler.channels for j in [c[0]] if c[1]=='rotation'}
        assert len([j for j in joints if j in channels[label]])==len(p.names)
    limits=np.zeros(len(p.names));limits[p.editable]=np.rad2deg(p.limits)
    times=np.arange((protocol['frame_count']-1)*4+1)/4;bounds=[];original_rows=[];guard_rows=[]
    objects={}
    for name,obj in scene['objects'].items():
        op,orr=sample_object(obj,protocol['frame_count']);objects[name]=(op,Slerp(np.arange(len(orr)),Rotation.from_matrix(orr)))
    region_specs={c['id']:compile_region(c,scene,p.skin) for c in scene['contacts']}
    previous_dense_local=None;dense_steps=[]
    for frame in times:
        matrices={};local={}
        for label,(sampler,joints) in samples.items():
            matrices[label]=sampler.sample(frame/30)[joints]
            local[label]=Rotation.from_quat([AnimationSampler.value(*channels[label][j][1:],frame/30) for j in joints]).as_matrix()
        if start<frame<=end:
            change=(Rotation.from_matrix(previous_dense_local[arm_joints]).inv()*Rotation.from_matrix(local['candidate'][arm_joints])).as_rotvec()
            dense_steps.append(dict(frame=float(frame),maximum_step_degrees=float(np.rad2deg(np.linalg.norm(change,axis=1)).max())))
        previous_dense_local=local['candidate']
        angles=np.rad2deg(np.linalg.norm(Rotation.from_matrix((local['source'].transpose(0,2,1)@local['candidate']).reshape(-1,3,3)).as_rotvec(),axis=1))
        delta=matrices['candidate'][0,:3,3]-matrices['source'][0,:3,3]
        passed=bool(np.all(angles<=limits+1e-4) and -1e-7<=delta[1]<=p.config['max_root_lift_m']+1e-7 and abs(delta[[0,2]]).max()<1e-7)
        bounds.append(dict(frame=float(frame),passed=passed,maximum_rotation_edit_degrees=float(angles.max()),root_lift_m=float(delta[1])))
        world=matrices['candidate'];rotations=placement@world[:,:3,:3];positions=world[:,:3,3]@placement.T+origin
        if start<=frame<=protocol['active_interval'][1]:
            vertices=p.surface.vertices(rotations,positions,[c['effector']['surface_vertex'] for c in original['contacts']]);errors=[]
            for index,c in enumerate(original['contacts']):
                op,slerp=objects[c['target']['object']];position=np.array([np.interp(frame,np.arange(len(op)),op[:,k]) for k in range(3)]);rotation=slerp([frame]).as_matrix()[0]
                error=float(np.linalg.norm(vertices[index]-position-rotation@c['target']['point_m']))
                errors.append(dict(id=c['id'],error_m=error,passed=error<=c['tolerance_m']))
            original_rows.append(dict(frame=float(frame),guides=errors))
        if protocol['active_interval'][1]<frame<=end:
            vertices=p.surface.vertices(rotations,positions);contacts=[]
            for c in scene['contacts']:
                op,slerp=objects[c['target']['object']];position=np.array([np.interp(frame,np.arange(len(op)),op[:,k]) for k in range(3)]);rotation=slerp([frame]).as_matrix()[0]
                ids,faces,geometry,normal=region_specs[c['id']];target=position+rotation@c['target']['point_m']
                row=measure_frame(vertices,ids,faces,target,rotation@normal,geometry,position,rotation,c['region_contact']['limits'])
                error=float(np.linalg.norm(vertices[c['effector']['surface_vertex']]-target))
                contacts.append(dict(id=c['id'],anchor_error_m=error,all_conditions_passed=bool(row['passed'] and error<=c['tolerance_m']),**row))
            guard_rows.append(dict(frame=float(frame),contacts=contacts))
    phases={}
    for label,variant in dense['variants'].items():
        summary={}
        for name,predicate in [('before',lambda f:f<=left),('approach',lambda f:left<f<start),('grasp',lambda f:start<=f<=protocol['active_interval'][1]),('release_guard',lambda f:protocol['active_interval'][1]<f<=end),('release_blend',lambda f:end<f<right),('after',lambda f:f>=right)]:
            selected=[r for r in variant['rows'] if predicate(r['frame'])]
            summary[name]=dict(samples=len(selected),geometry_failures=sum(not r['geometry_passed'] for r in selected),contact_failures=sum(not c['all_conditions_passed'] for r in selected for c in r['contacts']),
                minimum_floor_m=min(r['minimum_floor_m'] for r in selected),minimum_object_clearance_m=min(v for r in selected for v in r['object_clearances_m'].values()))
        phases[label]=summary
    report=dict(at=now(),study=study.relative_to(ROOT).as_posix(),result_sha256=sha256(study/'result.json'),auditor_sha256=sha256(__file__),
        native_replayed_frames=len(track),native_bounds_passes=native_bounds,unchanged_frames=len(untouched),geometry_audit_sha256=sha256(output/'geometry/verification.json'),
        dense_bounds=bounds,dense_bound_failures=sum(not r['passed'] for r in bounds),original_guides=original_rows,
        native_arm_steps=native_steps,maximum_native_arm_step_degrees=max(r['maximum_step_degrees'] for r in native_steps),
        dense_active_arm_steps=dense_steps,maximum_dense_active_arm_speed_degrees_s=max(r['maximum_step_degrees'] for r in dense_steps)*120,
        sampled_step_failures=sum(r['maximum_step_degrees']>protocol['maximum_step_degrees']+1e-4 for r in native_steps) if protocol.get('continuity_weight',0) else None,
        dense_step_failures=sum(r['maximum_step_degrees']>protocol['maximum_step_degrees']/4+1e-4 for r in dense_steps) if protocol.get('continuity_weight',0) else None,
        original_guide_failures=sum(not c['passed'] for r in original_rows for c in r['guides']),release_guard=guard_rows,
        release_guard_contact_failures=sum(not c['all_conditions_passed'] for r in guard_rows for c in r['contacts']),phases=phases,quality_approved=False)
    save(output/'verification.json',report);print({k:report[k] for k in ['native_replayed_frames','unchanged_frames','dense_bound_failures','original_guide_failures','release_guard_contact_failures','phases']},flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args();run(args.study,args.output)
