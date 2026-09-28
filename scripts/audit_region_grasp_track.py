"""Replay native trajectory edits and measure exported full skin at quarter frames."""
import argparse
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation, Slerp
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from build_soma_preview import ASSET, make_preview
from gltf_tools import write_glb, read_glb
from rig_clip_import import AnimationSampler
from grasp_pose_witness import PoseProblem
from grasp_contact_binding import apply_region_binding
from audit_sphere_region import triangle_audit
from audit_grasp_restoration import compare_record
from scene_solver_context import context_primitives


def quintic(t):
    t = min(1., max(0., t)); return 6*t**5-15*t**4+10*t**3


def run(study, output):
    study, output = Path(study).resolve(), Path(output).resolve(); protocol, result = read(study/'protocol.json'), read(study/'result.json')
    if result['status'] != 'complete' or not result['motion_generated']: raise ValueError('Completed trajectory required')
    for path, digest in [(study/'protocol.json', result['protocol_sha256']), (study/'motion.npz', result['motion_sha256'])]:
        if sha256(path) != digest: raise ValueError('Trajectory artifact changed')
    for name, digest in protocol['inputs'].items():
        if sha256(ROOT/name) != digest: raise ValueError('Trajectory input changed')
    for name, digest in protocol['implementation'].items():
        if sha256(study/'implementation'/name) != digest: raise ValueError('Trajectory implementation snapshot changed')
    regions, bindings = protocol['region_protocols'], protocol['contact_bindings']
    fit = ROOT/protocol['study']/'fit'; summary = read(fit/'summary.json'); folder = fit/'assets'/summary['trials'][0]['id']/'A'
    skin = dict(np.load(ASSET, allow_pickle=False)); start, end = protocol['active_interval']; edit_start, edit_end = protocol['edited_interval']
    p0 = PoseProblem(folder, skin, start); candidate = dict(np.load(study/'motion.npz', allow_pickle=False)); source = p0.candidate
    reference = np.array(read(ROOT/protocol['pose_report']/'result.json')['parameters']); active = {r['frame']: r for r in result['rows']}
    if set(active) != set(range(start, end+1)): raise ValueError('Missing or duplicate active frames')
    expected_edited = set(range(edit_start+1, edit_end)); stored = {r['frame']:r for r in result['parameter_track']}
    if set(stored) != expected_edited or len(stored) != len(result['parameter_track']): raise ValueError('Unexpected edited frame set')
    outside = np.array(sorted(set(range(protocol['frame_count']))-expected_edited))
    for name in source: np.testing.assert_array_equal(source[name][outside], candidate[name][outside])
    columns = [3*p0.lookup[p0.names.index(side+name)]+k for side in ['Left','Right'] for name in ['Shoulder','Arm','ForeArm','Hand'] for k in range(3)]
    frozen = np.setdiff1d(np.arange(p0.dim), columns); max_serialized_error = 0.; replay_passes = 0
    for frame, record in stored.items():
        relative = p0.previous['local_rot_mats'][frame].transpose(0,2,1)@source['local_rot_mats'][frame]
        baseline = np.r_[Rotation.from_matrix(relative[p0.editable]).as_rotvec().ravel(), p0.recipe['root_lift_m'][frame]]
        if frame < start: weight = quintic((frame-edit_start)/(start-edit_start)); expected = (1-weight)*baseline+weight*np.array(active[start]['parameters'])
        elif frame > end: weight = 1-quintic((frame-end)/(edit_end-end)); expected = (1-weight)*baseline+weight*np.array(active[end]['parameters'])
        else: weight = 1.; expected = np.array(active[frame]['parameters']); np.testing.assert_array_equal(expected[frozen],reference[frozen])
        values = np.array(record['parameters']); np.testing.assert_allclose(values, expected, atol=1e-12, rtol=0.); np.testing.assert_allclose(record['blend_weight'],weight,atol=1e-12)
        p0.frame = frame; audit, replay = p0.independent(values)
        for name in candidate:
            serialized = replay[name][0].astype(candidate[name].dtype)
            np.testing.assert_array_equal(serialized,candidate[name][frame])
            if name in ['posed_joints','root_positions','global_rot_mats']: max_serialized_error=max(max_serialized_error,float(np.max(np.abs(replay[name][0]-candidate[name][frame]))))
        if not audit['rotation_norm_bounds_passed']: raise ValueError('Original edit budget violated')
        if start <= frame <= end:
            p = PoseProblem(folder,skin,frame)
            for binding,rp in zip(bindings,regions): apply_region_binding(p,binding['hand'],binding['anchor'],rp['patch'])
            actual,_=p.independent(values); compare_record(actual,active[frame]['candidate'])
            replay_passes += actual['pose_witness_passed']
    output.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(Path(__file__),output/Path(__file__).name)
    metadata = dict(at=now(), study=study.relative_to(ROOT).as_posix(), protocol_sha256=sha256(study/'protocol.json'), result_sha256=sha256(study/'result.json'),
                    native_replay_exact=True, untouched_frames_exact=len(outside), original_edit_budgets_pass=True, serialization_max_error=max_serialized_error,
                    substeps=4, scope='Decoded GLB full-skin integer/quarter-frame samples; exact original native edits and untouched frames verified. Discrete samples do not certify continuous collision, anatomy, self-collision, dynamics or human quality.', quality_approved=False)
    save(output/'protocol.json',metadata)
    times=np.arange((protocol['frame_count']-1)*4+1)/4; count=protocol['frame_count']; originals={}; hand_specs=[]
    for geometry,obj in context_primitives(p0.context):
        positions=np.asarray(obj['positions_m']); rotations=np.asarray(obj['rotations'])
        sampled_p=np.stack([np.interp(times,np.arange(count),positions[:,i]) for i in range(3)],1)
        sampled_r=Slerp(np.arange(count),Rotation.from_matrix(rotations))(times).as_matrix()
        originals[obj['id']]=(geometry,sampled_p,sampled_r,positions,rotations)
    geometry,op,orr,object_p,object_r=originals[protocol['object_id']]
    for binding,rp in zip(bindings,regions):
        hand=binding['hand']; contact=next(c for c in p0.contacts if c['region']==hand)
        # p0 contacts retain frame-start authored targets; transport through the same object track.
        authored_local=object_r[start].T@(np.array(contact['target'])-object_p[start])
        n=next(n.numpy() for name,f,n in p0.normals if name==binding['normal_id']); normal_local=object_r[start].T@n
        declared=protocol['targets'][hand]; anchor_local=object_r[start].T@(np.array(declared['points'][start])-object_p[start])
        hand_specs.append(dict(hand=hand,anchor=binding['anchor'],ids=np.array(rp['patch']['vertices']),faces=skin['faces'][rp['patch']['face_ids']],limits=rp['limits'],
                               targets=op+np.einsum('fij,j->fi',orr,authored_local),normals=np.einsum('fij,j->fi',orr,normal_local),anchor_local=anchor_local))
    variants={}; active_mask=(times>=start)&(times<=end); edited_mask=(times>=edit_start)&(times<=edit_end)
    for label,motion in [('baseline',source),('candidate',candidate)]:
        doc,binary,_,_=make_preview(skin,motion,np.zeros(3),repeat=False); write_glb(output/(label+'.glb'),doc,binary)
        doc,binary=read_glb(output/(label+'.glb')); sampler=AnimationSampler(doc,binary,0); joints=doc['skins'][0]['joints']
        floor=[]; objects={name:[] for name in originals}; poses=[]; hand_rows={s['hand']:[] for s in hand_specs}; key_error=0.; bound_rows=[]
        for index,time in enumerate(times):
            world=sampler.sample(float(np.float32(time/30)))[joints]; rotation=world[:,:3,:3]; positions=world[:,:3,3]; poses.append(positions)
            left=int(np.floor(time));right=int(np.ceil(time));fraction=float(time-left)
            if right!=left:
                ta,tb,tt=[float(np.float32(f/30)) for f in [left,right,time]];fraction=(tt-ta)/(tb-ta)
            previous_a=Rotation.from_matrix(p0.previous['local_rot_mats'][left]);previous_b=Rotation.from_matrix(p0.previous['local_rot_mats'][right])
            previous=(previous_a*Rotation.from_rotvec((previous_a.inv()*previous_b).as_rotvec()*fraction)).as_matrix()
            local=rotation.copy()
            for joint,parent in enumerate(p0.parents):
                if parent>=0:local[joint]=rotation[parent].T@rotation[joint]
            angles=Rotation.from_matrix(previous.transpose(0,2,1)@local).magnitude()
            base_root=(1-fraction)*p0.base['root_positions'][left]+fraction*p0.base['root_positions'][right]
            root_delta=positions[0]-base_root;fixed_joints=np.setdiff1d(np.arange(77),p0.editable)
            bound_pass=bool(np.all(angles[p0.editable]<=p0.limits+1e-6) and angles[fixed_joints].max()<1e-6 and -.000001<=root_delta[1]<=p0.config['max_root_lift_m']+.000001 and abs(root_delta[[0,2]]).max()<1e-6)
            bound_rows.append(dict(frame=float(time),passed=bound_pass,maximum_rotation_edit_degrees=float(np.rad2deg(angles).max()),root_lift_m=float(root_delta[1])))
            if time.is_integer(): key_error=max(key_error,float(abs(rotation-motion['global_rot_mats'][int(time)]).max()),float(abs(positions-motion['posed_joints'][int(time)]).max()))
            vertices=p0.surface.vertices(rotation,positions); floor.append(float(vertices[:,1].min()))
            for name,(g,po,ro,_,_) in originals.items():
                gap=np.linalg.norm(vertices-po[index],axis=1)-g.dimensions[0] if g.shape=='sphere' else (np.abs((vertices-po[index])@ro[index])-np.array(g.dimensions)/2).max(-1)
                objects[name].append(float(gap.min()))
            for spec in hand_specs:
                tri=vertices[spec['faces']]; normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]).sum(0); normal/=np.linalg.norm(normal)
                anchor=vertices[spec['anchor']]; error=float(np.linalg.norm(anchor-spec['targets'][index])); angle=float(np.rad2deg(np.arccos(np.clip(normal@spec['normals'][index],-1,1))))
                gaps=np.linalg.norm(vertices[spec['ids']]-op[index],axis=1)-geometry.dimensions[0]
                triangle,_=triangle_audit(vertices[spec['ids']],spec['ids'],spec['targets'][index],gaps,spec['limits']) if active_mask[index] else (None,None)
                hand_rows[spec['hand']].append(dict(frame=float(time),anchor=anchor.tolist(),object_local_anchor=((anchor-op[index])@orr[index]).tolist(),point_error_m=error,normal_error_degrees=angle,contact_triangle=triangle))
        if key_error>1e-5: raise ValueError('Export differs from native keys')
        contacts={}
        for spec in hand_specs:
            rows=hand_rows[spec['hand']]; local=np.array([r['object_local_anchor'] for r in rows]); point=np.array([r['anchor'] for r in rows]); speed=np.linalg.norm(np.diff(point,axis=0),axis=1)*120
            slip=np.linalg.norm(np.diff(local,axis=0),axis=1)*120; mask=active_mask[:-1]&active_mask[1:]
            boundary={}
            for name,frame in [('entry',start),('release',end)]:
                near=(times[1:]>=frame-1)&(times[:-1]<=frame+1);boundary[name]=dict(peak_anchor_speed_m_s=float(speed[near].max()),peak_object_relative_speed_m_s=float(slip[near].max()))
            active_rows=[r for r,a in zip(rows,active_mask) if a]
            contacts[spec['hand']]=dict(maximum_point_error_m=max(r['point_error_m'] for r in active_rows),maximum_normal_error_degrees=max(r['normal_error_degrees'] for r in active_rows),
                distributed_contact_passes=sum(r['contact_triangle'] is not None for r in active_rows),active_samples=len(active_rows),maximum_relative_slip_m_s=float(slip[mask].max()),boundary=boundary)
        floor=np.array(floor); positions=np.array(poses); velocity=np.diff(positions,axis=0)*120; acceleration=np.diff(velocity,axis=0)*120
        all_geometry=(floor>=p0.config['clearance_m']-1e-6)
        for v in objects.values(): all_geometry &= np.array(v)>=p0.config['object_clearance_m']-1e-6
        region_pass=all_geometry & np.array([r['passed'] for r in bound_rows])
        for spec in hand_specs:
            rows=hand_rows[spec['hand']]
            region_pass &= np.array([r['point_error_m']<=p0.config['point_tolerance_m']+1e-6 and r['normal_error_degrees']<=p0.config['normal_tolerance_degrees']+1e-4 and r['contact_triangle'] is not None for r in rows])
        variants[label]=dict(key_matrix_error=key_error,minimum_floor_m=float(floor.min()),minimum_active_floor_m=float(floor[active_mask].min()),
            objects={name:dict(minimum_clearance_m=min(v),minimum_active_clearance_m=float(np.array(v)[active_mask].min()),worst_frame=float(times[np.argmin(v)])) for name,v in objects.items()},
            contacts=contacts,active_region_pass_count=int(region_pass[active_mask].sum()),active_samples=int(active_mask.sum()),
            original_edit_bound_fail_count=sum(not r['passed'] for r in bound_rows),maximum_rotation_edit_degrees=max(r['maximum_rotation_edit_degrees'] for r in bound_rows),
            edited_geometry_fail_count=int((~all_geometry[edited_mask]).sum()),maximum_joint_speed_m_s=float(np.linalg.norm(velocity,axis=-1).max()),
            maximum_joint_acceleration_m_s2=float(np.linalg.norm(acceleration,axis=-1).max()),glb_sha256=sha256(output/(label+'.glb')))
        save(output/(label+'.json'),dict(frames=times.tolist(),floor_height_m=floor.tolist(),object_clearance_m=objects,hands=hand_rows,edit_bounds=bound_rows,summary=variants[label]))
        print(dict(variant=label,active_passes=variants[label]['active_region_pass_count'],active_samples=int(active_mask.sum()),minimum_active_sphere_m=variants[label]['objects'][protocol['object_id']]['minimum_active_clearance_m'],edited_geometry_fail_count=variants[label]['edited_geometry_fail_count']),flush=True)
    save(output/'verification.json',dict(**metadata,variants=variants,auditor_sha256=sha256(Path(__file__)),release_approved=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    with threadpool_limits(limits=2):run(args.study,args.output)
