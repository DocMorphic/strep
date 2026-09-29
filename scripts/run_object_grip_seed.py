"""Build and measure an experimental object-frame grip seed, never an approval."""
import argparse
import copy
import shutil
import time
from pathlib import Path
import numpy as np
import torch
from strep import ROOT, read, save, sha256, now
from inspect_motion import skeleton_metadata, validate_motion
from scene_constraints import pose, sample_object, transform_motion, evaluate
from support_contact_v5 import correction_basis
from support_contact_v8 import CONFIG, finger_rotation_budgets
from object_grip_seed import transport_frames, fit_frames
from audit_scene_region_fit import edit_bounds, native_fk_error
from build_soma_preview import ASSET, make_preview
from gltf_tools import write_glb
from action_worker_lock import worker_lock


def validate_guide_reference(reference, start, end, frame_count):
    """Bind guide frame zero to a native frame inside the authored grasp."""
    if any(type(value) is not int for value in [reference, start, end, frame_count]):
        raise ValueError('Integer guide reference, interval and frame count required')
    if not 0 <= start <= reference <= end < frame_count:
        raise ValueError('Guide reference must lie within the authored contact interval')


def run(scene_path, guide_study, guide_audit, seed_path, output, reference=60, iterations=100):
    scene_path, guide_study, guide_audit, seed_path, output = map(lambda p: Path(p).resolve(),
        [scene_path, guide_study, guide_audit, seed_path, output])
    if not output.is_relative_to(ROOT/'reports') or output.exists():
        raise ValueError('Fresh local report directory required')
    scene, guide_scene = read(scene_path), read(guide_study/'authored-scene.json')
    if set(scene['actors']) != {'A'} or set(guide_scene['actors']) != {'A'}:
        raise ValueError('This experimental runner requires one actor A')
    result, audit = read(guide_study/'result.json'), read(guide_audit)
    if result['status'] != 'complete' or audit['result_sha256'] != sha256(guide_study/'result.json'):
        raise ValueError('Unchanged independently audited guide required')
    if sha256(guide_study/'motion.npz') != result['candidate_sha256'] or not audit['hard_edit_bounds_passed']:
        raise ValueError('Guide motion or original bounds failed')
    if audit['variants']['candidate']['contact_failures'] or audit['variants']['candidate']['geometry_failures']:
        raise ValueError('Guide contact and geometry must pass their independent audit')
    if sha256(guide_study/'authored-scene.json') != result['authored_scene_sha256']:
        raise ValueError('Guide scene changed')
    contacts = scene['contacts']
    if len(contacts) != 2 or {c['effector']['joint'] for c in contacts} != {'LeftHand', 'RightHand'}:
        raise ValueError('Two explicit hand contacts required')
    if any(c['actor'] != 'A' or c['target']['space'] != 'object' for c in contacts):
        raise ValueError('Actor A object contacts required')
    objects = {c['target']['object'] for c in contacts}
    intervals = {(c['start_frame'], c['end_frame']) for c in contacts}
    if len(objects) != 1 or len(intervals) != 1:
        raise ValueError('Matched interval on a single object required')
    object_id = next(iter(objects)); start, end = next(iter(intervals))
    validate_guide_reference(reference, start, end, scene['frame_count'])
    for contact in contacts:
        guide_contact = next(c for c in guide_scene['contacts'] if c['id'] == contact['id'])
        fields = lambda c: {k: v for k, v in c.items() if k not in ['start_frame', 'end_frame']}
        if fields(contact) != fields(guide_contact):
            raise ValueError('Guide contact definitions differ')
    if scene['objects'][object_id]['geometry'] != guide_scene['objects'][object_id]['geometry']:
        raise ValueError('Guide object geometry differs')
    op, orm = sample_object(scene['objects'][object_id], scene['frame_count'])
    gp, grm = sample_object(guide_scene['objects'][object_id], guide_scene['frame_count'])
    if not np.allclose(op[reference], gp[0], atol=1e-6, rtol=0) or not np.allclose(orm[reference], grm[0], atol=1e-6, rtol=0):
        raise ValueError('Guide object reference pose differs')
    source_path = ROOT/scene['actors']['A']['motion']
    if sha256(source_path) != scene['actors']['A']['source_sha256']:
        raise ValueError('Original full source changed')
    source, seed, guide = [dict(np.load(p, allow_pickle=False)) for p in [source_path, seed_path, guide_study/'motion.npz']]
    names, parents, _ = skeleton_metadata(77)
    validate_motion(source, 30); validate_motion(seed, 30); validate_motion(guide, 30)
    if not edit_bounds(source, seed, names, CONFIG)[0] or native_fk_error(source, seed, parents) > 3e-6:
        raise ValueError('Initial seed violates original bounds or offsets')
    body = ['Spine1','Spine2','Chest','Neck1','Neck2','Head',
        'LeftShoulder','LeftArm','LeftForeArm','LeftHand','RightShoulder','RightArm','RightForeArm','RightHand',
        'LeftLeg','LeftShin','LeftFoot','RightLeg','RightShin','RightFoot']
    fingers = finger_rotation_budgets(names)
    editable = [names.index(n) for n in body] + list(fingers)
    limits = np.deg2rad([CONFIG['max_rotation_degrees']]*len(body) + list(fingers.values()))
    joints = [names.index('LeftHand'), names.index('RightHand')] + list(fingers)
    world = transform_motion(guide, guide_scene['actors']['A']['transform'])
    tp, tr = transport_frames(op, orm, reference, world['positions'][0, joints], world['rotations'][0, joints])
    origin, placement = pose(scene['actors']['A']['transform'])
    tp = (tp-origin) @ placement; tr = placement.T @ tr
    basis, knots = correction_basis(scene['frame_count'], CONFIG['knot_spacing_frames'])
    weights = np.zeros(scene['frame_count']); weights[start:end+1] = 1
    inputs = {str(p): sha256(p) for p in [scene_path, source_path, seed_path, guide_study/'motion.npz',
        guide_study/'result.json', guide_study/'authored-scene.json', guide_audit, ASSET]}
    implementation = ['run_object_grip_seed.py', 'object_grip_seed.py', 'scene_fit_initialization.py',
        'support_contact_v5.py', 'support_contact_v8.py', 'floor_contact.py', 'scene_constraints.py',
        'inspect_motion.py', 'scene_region_contact.py', 'object_geometry.py', 'audit_scene_region_fit.py',
        'build_soma_preview.py', 'gltf_tools.py', 'strep.py']
    output.mkdir(parents=True); (output/'implementation').mkdir()
    for name in implementation: shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    shutil.copyfile(source_path, output/'source-motion.npz')
    save(output/'authored-scene.json', scene)
    save(output/'protocol.json', dict(at=now(), inputs=inputs, implementation={n: sha256(output/'implementation'/n) for n in implementation},
        actor='A', contact_ids=[c['id'] for c in contacts],
        reference_frame=reference, guide_frame=0, active_interval=[start,end], iterations=iterations,
        config=CONFIG, correction_knots=knots.tolist(), quality_approved=False,
        scope='Joint frames transported with prescribed object; source-relative bounded spline initialization. Not contact or release acceptance.'))
    started = time.monotonic()
    def progress(row):
        row = dict(seconds=time.monotonic()-started, **row)
        save(output/'progress.json', row); print(row, flush=True)
    try:
        torch.set_num_threads(2)
        with worker_lock():
            motion, recipe = fit_frames(source, seed, parents, editable, limits, len(body), basis,
                joints, tp, tr, weights, iterations, progress)
        for path, digest in inputs.items():
            if sha256(path) != digest: raise ValueError('Input changed during initialization')
        for name in implementation:
            if sha256(ROOT/'scripts'/name) != sha256(output/'implementation'/name): raise ValueError('Implementation changed')
        bounds, angles, _ = edit_bounds(source, motion, names, CONFIG)
        fk = native_fk_error(source, motion, parents)
        if not bounds or fk > 3e-6: raise ValueError('Candidate original bounds or FK failed')
        np.savez(output/'motion.npz', **motion); save(output/'recipe.json', recipe)
        candidate = copy.deepcopy(scene)
        candidate['actors']['A']['motion'] = (output/'motion.npz').relative_to(ROOT).as_posix()
        candidate['actors']['A']['source_sha256'] = sha256(output/'motion.npz')
        save(output/'candidate-scene.json', candidate)
        assessment = evaluate(candidate, dict(np.load(ASSET, allow_pickle=False)))
        save(output/'evaluation.json', assessment)
        for label, clip in [('source', source), ('candidate', motion)]:
            doc, binary, _, _ = make_preview(dict(np.load(ASSET, allow_pickle=False)), clip, np.zeros(3), repeat=False)
            write_glb(output/(label+'.glb'), doc, binary)
        summary = dict(status='complete', seconds=time.monotonic()-started, hard_edit_bounds_passed=bounds,
            native_fk_error=fk, maximum_rotation_edit_degrees=float(angles.max()),
            motion_sha256=sha256(output/'motion.npz'), glb_sha256=sha256(output/'candidate.glb'),
            candidate_sha256=sha256(output/'motion.npz'), candidate_glb_sha256=sha256(output/'candidate.glb'),
            source_glb_sha256=sha256(output/'source.glb'), recipe_sha256=sha256(output/'recipe.json'),
            authored_scene_sha256=sha256(output/'authored-scene.json'),
            protocol_sha256=sha256(output/'protocol.json'), quality_approved=False,
            contacts=[dict(id=c['id'], anchor_passes=c['frames_within_tolerance'], frames=c['interval_frames'],
                region_passes=c['region_contact']['passed_frames'], max_anchor_error_m=c['max_interval_error_m']) for c in assessment['contacts']],
            collisions=[dict(object=c['object'], max_depth_m=c['max_skin_vertex_depth_m']) for c in assessment['object_collisions']])
        save(output/'result.json', summary); print(summary, flush=True)
    except Exception as exc:
        save(output/'result.json', dict(status='failed', error=str(exc), seconds=time.monotonic()-started, quality_approved=False))
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['scene', 'guide_study', 'guide_audit', 'seed', 'output']: p.add_argument(name, type=Path)
    p.add_argument('--reference', type=int, default=60); p.add_argument('--iterations', type=int, default=100)
    a = p.parse_args(); run(a.scene, a.guide_study, a.guide_audit, a.seed, a.output, a.reference, a.iterations)
