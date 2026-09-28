"""Transport the verified two-hand region pose through its authored grasp interval."""
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
from grasp_orientation import hand_frame, angular_error
from probe_sphere_region_support import contact_triangle
from region_grasp_track import object_local_targets, arm_columns, project, smoothstep5


def run(pose_report, output, outward_reserve_m=0.):
    if not np.isfinite(outward_reserve_m) or not 0 <= outward_reserve_m <= .0005: raise ValueError('Outward reserve must be finite and between zero and 0.5 mm')
    torch.set_num_threads(2); pose_report, output = Path(pose_report).resolve(), Path(output).resolve()
    pr, result = read(pose_report/'protocol.json'), read(pose_report/'result.json')
    if not result['region_pose_passed'] or sha256(pose_report/'pose.npz') != result['pose_sha256'] or sha256(pose_report/'protocol.json') != result['protocol_sha256']:
        raise ValueError('Verified region pose required')
    projections = [ROOT/n for n in pr['projections']]; projection_protocols = [read(r/'protocol.json') for r in projections]
    region_reports = [ROOT/r['region_report'] for r in projection_protocols]
    for report, projection in zip(region_reports, projection_protocols):
        for name in ['protocol', 'result']:
            if sha256(report/f'{name}.json') != projection[f'region_{name}_sha256']: raise ValueError('Region input changed')
    regions = [read(r/'protocol.json') for r in region_reports]
    inputs = dict(pr['inputs'])
    for report in region_reports:
        for name in ['protocol.json', 'result.json']: inputs[(report/name).relative_to(ROOT).as_posix()] = sha256(report/name)
    for r, p in zip(projections, projection_protocols):
        inputs.update(p['inputs'])
        for name in ['protocol', 'result']: inputs[(r/f'{name}.json').relative_to(ROOT).as_posix()] = sha256(r/f'{name}.json')
    for name in ['protocol.json', 'result.json', 'pose.npz']: inputs[(pose_report/name).relative_to(ROOT).as_posix()] = sha256(pose_report/name)
    for name, digest in inputs.items():
        if sha256(ROOT/name) != digest: raise ValueError('Input changed')
    if len({r['study'] for r in regions}) != 1 or len({r['frame'] for r in regions}) != 1: raise ValueError('Matched fixture required')
    fit = ROOT/regions[0]['study']/'fit'; summary = read(fit/'summary.json'); folder = fit/'assets'/summary['trials'][0]['id']/'A'
    skin = dict(np.load(ASSET, allow_pickle=False)); reference_frame = regions[0]['frame']; p0 = PoseProblem(folder, skin, reference_frame)
    reference_parameters = np.array(result['parameters']); reference_motion = dict(np.load(pose_report/'pose.npz', allow_pickle=False))
    ref_vertices = p0.surface.vertices(reference_motion['global_rot_mats'][0], reference_motion['posed_joints'][0])
    objects = p0.context['primitives']; object_track = objects[0]
    if object_track['geometry']['shape'] != 'sphere': raise ValueError('Sphere required')
    spans = []
    for c in p0.recipe['release_endpoint_guards']['solver_contact_spec']['regions'].values():
        for segment in c.get('segments', []): spans.append((segment['start_frame'], segment['end_frame']))
    if len(set(spans)) != 1: raise ValueError('Synchronized single grasp interval required')
    start, end = spans[0]
    if reference_frame != start: raise ValueError('Reference must be the first grasp key')
    targets = {}; region_bindings = []
    for binding, rp in zip(pr['contact_bindings'], regions):
        hand = binding['hand']; applied = apply_region_binding(p0, hand, binding['anchor'], rp['patch']); region_bindings.append(applied)
        faces = skin['faces'][rp['patch']['face_ids']]; wrist = p0.names.index(hand); knuckles = [p0.names.index(hand+f+'2') for f in ['Index', 'Middle', 'Ring', 'Pinky']]
        point, normal, tangent = hand_frame(ref_vertices, reference_motion['posed_joints'][0], faces, binding['anchor'], wrist, knuckles)
        inward = next(n.numpy() for name, faces, n in p0.normals if name == binding['normal_id'])
        point = point-outward_reserve_m*inward
        targets[hand] = object_local_targets(point, normal, tangent, object_track['positions_m'], object_track['rotations'], reference_frame)
    settings = dict(maximum_evaluations=100, seconds_per_frame=60, maximum_rss_bytes=2*1024**3, minimum_available_bytes=int(1.25*1024**3),
                    point_scale_m=.001, direction_scale=.01, regularization=1e-5, reach_point_m=.0001, reach_direction_degrees=.1, blend_frames=12)
    frames = len(p0.base['root_positions']); edit_start, edit_end = max(0, start-settings['blend_frames']), min(frames-1, end+settings['blend_frames'])
    output.mkdir(parents=True, exist_ok=False); (output/'implementation').mkdir()
    methods = ['study_region_grasp_track.py', 'region_grasp_track.py', 'grasp_contact_binding.py', 'grasp_pose_witness.py', 'grasp_pose_witness_bounded.py',
               'grasp_orientation.py', 'probe_sphere_region_support.py', 'support_contact_v8.py', 'support_contact_v5.py', 'floor_contact.py', 'scene_solver_context.py', 'object_geometry.py', 'inspect_motion.py']
    implementation = {n: sha256(ROOT/'scripts'/n) for n in methods}
    for n in methods: shutil.copyfile(ROOT/'scripts'/n, output/'implementation'/n)
    protocol = dict(at=now(), pose_report=pose_report.relative_to(ROOT).as_posix(), study=regions[0]['study'], frame_count=frames, reference_frame=reference_frame,
                    active_interval=[start, end], edited_interval=[edit_start, edit_end], settings=settings, outward_reserve_m=outward_reserve_m, inputs=inputs, implementation=implementation,
                    region_protocols=regions, contact_bindings=region_bindings, object_id=object_track['id'], targets={hand:{k:v.tolist() for k,v in target.items()} for hand,target in targets.items()},
                    condition='New region condition, original reference animation and object tracks. Constant reference-pose non-arm rotation edits/root lift during grasp; warm-start bounded arm fitting at every frame. Quintic physical-edit blends at approach/release, original pose exact outside edit interval.',
                    scope='Development trajectory. Contact/normal/full-skin checks required at keys and subframes. No anatomy, self-collision, dynamics or release approval.', quality_approved=False)
    save(output/'protocol.json', protocol)
    columns, _ = arm_columns(p0); frozen = np.setdiff1d(np.arange(p0.dim), columns)
    last = reference_parameters[columns].copy(); rows = []; parameters = {}; completed = True
    for frame in range(start, end+1):
        p = PoseProblem(folder, skin, frame)
        for binding, rp in zip(region_bindings, regions): apply_region_binding(p, binding['hand'], binding['anchor'], rp['patch'])
        local_targets = {hand:dict(point=t['points'][frame], normal=t['normals'][frame], tangent=t['tangents'][frame]) for hand,t in targets.items()}
        started = time.monotonic(); peak = 0
        def guard(evaluations):
            nonlocal peak
            peak = max(peak, psutil.Process().memory_info().rss)
            if time.monotonic()-started > settings['seconds_per_frame'] or peak > settings['maximum_rss_bytes'] or psutil.virtual_memory().available < settings['minimum_available_bytes']:
                raise TimeoutError('Region trajectory resource guard')
        values, solver = project(p, reference_parameters, last, local_targets, settings, guard, check_derivative=frame == start)
        last = values[columns].copy(); parameters[frame] = values; audit, motion = p.independent(values)
        np.testing.assert_array_equal(values[frozen], reference_parameters[frozen])
        vertices = p.surface.vertices(motion['global_rot_mats'][0], motion['posed_joints'][0]); contact_rows = []
        for binding, rp in zip(region_bindings, regions):
            hand = binding['hand']; ids = np.array(rp['patch']['vertices']); faces = skin['faces'][rp['patch']['face_ids']]
            point, normal, tangent = hand_frame(vertices, motion['posed_joints'][0], faces, binding['anchor'], p.names.index(hand), [p.names.index(hand+f+'2') for f in ['Index', 'Middle', 'Ring', 'Pinky']])
            target = local_targets[hand]; reach = dict(point_error_m=float(np.linalg.norm(point-target['point'])), normal_error_degrees=angular_error(normal,target['normal']), tangent_error_degrees=angular_error(tangent,target['tangent']))
            g, _, center, _ = p.objects[0]; gaps = np.linalg.norm(vertices[ids]-center.numpy()[0], axis=1)-g.dimensions[0]
            authored = next(c['target'] for c in p.contacts if c['region'] == hand); triangle = contact_triangle(vertices[ids], ids, np.array(authored), gaps, rp['limits'])
            reached = reach['point_error_m'] <= settings['reach_point_m'] and max(reach['normal_error_degrees'],reach['tangent_error_degrees']) <= settings['reach_direction_degrees']
            contact_rows.append(dict(hand=hand, reach=reach, target_reached=bool(reached), contact_triangle=triangle))
        passed = bool(audit['pose_witness_passed'] and all(r['target_reached'] and r['contact_triangle'] is not None for r in contact_rows))
        row = dict(frame=frame, parameters=values.tolist(), solver=solver, candidate=audit, contacts=contact_rows, region_pose_passed=passed, seconds=time.monotonic()-started, sampled_peak_rss_bytes=peak)
        rows.append(row); save(output/'progress.json', dict(at=now(), status='running', rows=rows))
        if frame == start or frame % 10 == 0 or frame == end: print(dict(frame=frame,passed=passed,minimum_sphere_clearance_m=audit['objects'][0]['minimum_clearance_m'],floor_m=audit['minimum_floor_height_m'],evaluations=solver['evaluations']),flush=True)
        if solver['status'] != 'complete': completed = False; break
    if not completed:
        save(output/'result.json', dict(at=now(), status='interrupted_resource_guard', rows=rows, motion_generated=False, quality_approved=False))
        save(output/'progress.json', dict(at=now(), status='interrupted_resource_guard', rows=rows)); return
    candidate = {k:v.copy() for k,v in p0.candidate.items()}
    # Store full physical parameter tracks for independent replay; untouched frames remain the baseline arrays.
    records = []; original_local = p0.previous['local_rot_mats']
    for frame in range(edit_start, edit_end+1):
        relative = original_local[frame].transpose(0,2,1)@p0.candidate['local_rot_mats'][frame]
        baseline = np.r_[Rotation.from_matrix(relative[p0.editable]).as_rotvec().ravel(), p0.recipe['root_lift_m'][frame]]
        if frame < start: weight = float(smoothstep5((frame-edit_start)/(start-edit_start))); values = (1-weight)*baseline+weight*parameters[start]
        elif frame > end: weight = float(1-smoothstep5((frame-end)/(edit_end-end))); values = (1-weight)*baseline+weight*parameters[end]
        else: weight = 1.; values = parameters[frame]
        if weight == 0: continue
        # PoseProblem requires active contacts; its FK/reconstruction uses self.frame independently.
        p0.frame = frame
        _, motion = p0.independent(values)
        for name in candidate: candidate[name][frame] = motion[name][0]
        records.append(dict(frame=frame, blend_weight=weight, parameters=values.tolist()))
    np.savez(output/'motion.npz', **candidate)
    for name,digest in inputs.items():
        if sha256(ROOT/name) != digest: raise ValueError('Input changed during study')
    for name,digest in implementation.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Implementation changed during study')
    save(output/'result.json', dict(at=now(), status='complete', rows=rows, parameter_track=records, active_pass_count=sum(r['region_pose_passed'] for r in rows), active_frame_count=len(rows),
         motion_generated=True, motion_sha256=sha256(output/'motion.npz'), protocol_sha256=sha256(output/'protocol.json'), quality_approved=False))
    save(output/'progress.json', dict(at=now(), status='complete', rows=rows))
    print(dict(status='complete',active_pass_count=sum(r['region_pose_passed'] for r in rows),active_frame_count=len(rows)),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('pose_report',type=Path); parser.add_argument('output',type=Path)
    parser.add_argument('--outward-reserve-m',type=float,default=0.,help='Move fit targets outward without changing authored contact or clearance gates')
    args=parser.parse_args()
    with threadpool_limits(limits=2): run(args.pose_report,args.output,args.outward_reserve_m)
