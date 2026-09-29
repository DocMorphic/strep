"""Endpoint arm paths with bounded radial clearance correction after release."""
import argparse
import shutil
import time
from pathlib import Path
import numpy as np
import psutil
import torch
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from build_soma_preview import ASSET
from grasp_pose_witness import PoseProblem
from grasp_contact_binding import apply_region_binding
from grasp_orientation import hand_frame, unit
from region_grasp_track import arm_columns, project, smoothstep5
from sphere_approach import set_problem_frame, influenced_hand_vertices, outward_clearance_shift
from rotation_return import tangent_return, bounded_path_edits


def arm_path(first, last, fraction):
    if not np.isfinite(fraction) or not 0 <= fraction <= 1:
        raise ValueError('Path fraction must be finite and in [0, 1]')
    a, b = Rotation.from_matrix(first), Rotation.from_matrix(last)
    return (a * Rotation.from_rotvec((a.inv()*b).as_rotvec()*smoothstep5(fraction))).as_matrix()


def run(release_report, output, path_profile='quintic', bound_path=False):
    if path_profile not in ['quintic','tangent-cubic']: raise ValueError('Unknown path profile')
    torch.set_num_threads(2)
    release_report, output = Path(release_report).resolve(), Path(output).resolve()
    rp, rr = read(release_report/'protocol.json'), read(release_report/'result.json')
    if rr['status'] != 'complete' or sha256(release_report/'protocol.json') != rr['protocol_sha256'] or sha256(release_report/'motion.npz') != rr['motion_sha256']:
        raise ValueError('Completed unchanged release input required')
    study = ROOT/rp['base_study']; protocol = read(study/'protocol.json')
    inputs = dict(rp['inputs'])
    for name in ['protocol.json', 'result.json', 'motion.npz']:
        inputs[(release_report/name).relative_to(ROOT).as_posix()] = sha256(release_report/name)
    for name, digest in inputs.items():
        if sha256(ROOT/name) != digest: raise ValueError('Input changed')
    fit = ROOT/protocol['study']/'fit'; folder = fit/'assets'/read(fit/'summary.json')['trials'][0]['id']/'A'
    skin = dict(np.load(ASSET, allow_pickle=False)); p = PoseProblem(folder, skin, protocol['active_interval'][0])
    bindings, regions = protocol['contact_bindings'], protocol['region_protocols']
    for binding, region in zip(bindings, regions): apply_region_binding(p, binding['hand'], binding['anchor'], region['patch'])
    patches = {b['hand']: influenced_hand_vertices(p, b['hand']) for b in bindings}
    source = dict(np.load(release_report/'motion.npz', allow_pickle=False))
    candidate = {k:v.copy() for k,v in source.items()}; uncorrected = {k:v.copy() for k,v in source.items()}
    columns, arm_limits = arm_columns(p); frozen = np.setdiff1d(np.arange(p.dim), columns)
    arms = [p.names.index(s+n) for s in ['Left', 'Right'] for n in ['Shoulder', 'Arm', 'ForeArm', 'Hand']]
    first, last = rp['release_frame'], rp['blend_end']; stored = {r['frame']:np.array(r['parameters']) for r in rr['rows']}
    if first < 1 or last+1 >= len(source['root_positions']): raise ValueError('Surrounding endpoint keys required')
    settings = dict(maximum_evaluations=100, point_scale_m=.001, direction_scale=.01, regularization=1e-5,
                    guide_clearance_m=.0025, seconds_per_frame=60, maximum_rss_bytes=2*1024**3, minimum_available_bytes=int(1.25*1024**3))
    output.mkdir(parents=True, exist_ok=False); (output/'implementation').mkdir()
    methods = ['spatial_release.py','rotation_return.py','sphere_approach.py','region_grasp_track.py','grasp_contact_binding.py','grasp_pose_witness.py',
               'grasp_pose_witness_bounded.py','grasp_orientation.py','support_contact_v8.py','support_contact_v5.py','floor_contact.py','scene_solver_context.py','object_geometry.py','inspect_motion.py']
    implementation = {n:sha256(ROOT/'scripts'/n) for n in methods}
    for name in methods: shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    save(output/'protocol.json',dict(at=now(), release_report=release_report.relative_to(ROOT).as_posix(), base_study=rp['base_study'],
         inputs=inputs, implementation=implementation, settings=settings, path_profile=path_profile, path_bound_reserve_radians=.001 if bound_path else None, release_frame=first, blend_end=last, arm_joints=arms, arm_columns=columns.tolist(),
         eligible_frames=list(range(first+1,last)), scope='Eight absolute local arm rotations follow the recorded endpoint path profile. Tangent-cubic matches body rates estimated from adjacent keys before correction/baking; quintic has zero endpoint rates. Other edits/root retain the input release. Radial full-influence hand guidance is projected through bounded arm IK if needed. Events and all outside frames unchanged. Full exported validation required.', quality_approved=False))
    rows=[]; solves=0
    for frame in range(first+1,last):
        set_problem_frame(p,frame); base=stored[frame].copy()
        desired=arm_path(source['local_rot_mats'][first,arms],source['local_rot_mats'][last,arms],(frame-first)/(last-first))
        if path_profile=='tangent-cubic':
            desired=tangent_return(source['local_rot_mats'][first,arms],source['local_rot_mats'][last,arms],source['local_rot_mats'][first-1,arms],source['local_rot_mats'][last+1,arms],(frame-first)/(last-first),last-first)
        base[columns]=Rotation.from_matrix(p.previous['local_rot_mats'][frame,arms].transpose(0,2,1)@desired).as_rotvec().ravel()
        proposed=base.copy()
        if bound_path: base[columns]=bounded_path_edits(base[columns].reshape(-1,3),arm_limits).ravel()
        if np.any(np.linalg.norm(base[columns].reshape(-1,3),axis=1)>=arm_limits):
            save(output/'failure.json',dict(at=now(),status='failed',stage='path_seed',frame=frame,reason='Proposed arm path is not strictly inside original rotation budgets',
                 proposed_parameters=proposed.tolist(),motion_written=False,protocol_sha256=sha256(output/'protocol.json'),quality_approved=False))
            raise ValueError('Proposed arm path exceeds bounded solver seed domain; failure report retained')
        before, motion=p.independent(base)
        for name in source: uncorrected[name][frame]=motion[name][0]
        vertices=p.surface.vertices(motion['global_rot_mats'][0],motion['posed_joints'][0])
        sphere,_,center,_=next(o for o in p.objects if o[1]==protocol['object_id'])
        if sphere.shape!='sphere': raise ValueError('Sphere fixture required')
        targets={}; guides=[]
        for binding,region in zip(bindings,regions):
            hand=binding['hand']; knuckles=[p.names.index(hand+f+'2') for f in ['Index','Middle','Ring','Pinky']]
            point,normal,tangent=hand_frame(vertices,motion['posed_joints'][0],skin['faces'][region['patch']['face_ids']],binding['anchor'],p.names.index(hand),knuckles)
            outward=unit(point-center.numpy()[0]); distance=outward_clearance_shift(vertices[patches[hand]],center.numpy()[0],outward,sphere.dimensions[0],settings['guide_clearance_m'])
            targets[hand]=dict(point=point+outward*distance,normal=normal,tangent=tangent)
            guides.append(dict(hand=hand,outward=outward.tolist(),distance_m=distance,**{k:v.tolist() for k,v in targets[hand].items()}))
        began=time.monotonic(); values=base; solver=None
        if any(g['distance_m']>1e-10 for g in guides):
            def guard(evaluations):
                if time.monotonic()-began>settings['seconds_per_frame'] or psutil.Process().memory_info().rss>settings['maximum_rss_bytes'] or psutil.virtual_memory().available<settings['minimum_available_bytes']:
                    raise TimeoutError('Spatial release resource guard')
            values,solver=project(p,base,base[columns],targets,settings,guard,check_derivative=solves==0); solves+=1
        np.testing.assert_array_equal(values[frozen],stored[frame][frozen])
        audit,motion=p.independent(values)
        for name in candidate: candidate[name][frame]=motion[name][0]
        rows.append(dict(frame=frame,proposed_parameters=proposed.tolist(),initial_parameters=base.tolist(),parameters=values.tolist(),guides=guides,solver=solver,before=before,candidate=audit,seconds=time.monotonic()-began))
        save(output/'progress.json',dict(status='running',rows=rows))
        print(dict(frame=frame,projected=solver is not None,sphere_clearance_m=audit['objects'][0]['minimum_clearance_m'],bounds=audit['rotation_norm_bounds_passed']),flush=True)
        if solver and solver['status']!='complete': break
    for name,digest in inputs.items():
        if sha256(ROOT/name)!=digest: raise ValueError('Input changed during run')
    for name,digest in implementation.items():
        if sha256(ROOT/'scripts'/name)!=digest: raise ValueError('Implementation changed during run')
    protected=np.r_[np.arange(first+1),np.arange(last,len(source['root_positions']))]
    for name in source: np.testing.assert_array_equal(candidate[name][protected],source[name][protected])
    np.savez(output/'motion.npz',**candidate); np.savez(output/'uncorrected-motion.npz',**uncorrected)
    status='complete' if len(rows)==last-first-1 else 'interrupted_resource_guard'
    save(output/'result.json',dict(at=now(),status=status,rows=rows,protected_frames_exact=len(protected),motion_sha256=sha256(output/'motion.npz'),
         uncorrected_motion_sha256=sha256(output/'uncorrected-motion.npz'),protocol_sha256=sha256(output/'protocol.json'),quality_approved=False))
    save(output/'progress.json',dict(status=status,frames=len(rows),solves=solves))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('release_report',type=Path); parser.add_argument('output',type=Path); parser.add_argument('--path-profile',choices=['quintic','tangent-cubic'],default='quintic'); parser.add_argument('--bound-path',action='store_true'); args=parser.parse_args()
    with threadpool_limits(limits=2): run(args.release_report,args.output,args.path_profile,args.bound_path)
