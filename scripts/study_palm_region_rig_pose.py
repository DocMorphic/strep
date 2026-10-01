"""Fit region contacts to actual arm chains; validate one pose, not an animation."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now


def run(source, baseline, output):
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from scene_pair_problem import load_actors
    from rigid_contact_initialization import place
    from oriented_two_bone import reach_pose
    from elbow_swivel import local_transforms
    from native_finger_motion import palm_geometry
    from shared_palm_meeting import measure
    from triangle_crossing import audit
    from convex_partner_surface import penetration
    source, baseline, output = [Path(p).resolve() for p in (source, baseline, output)]
    if output.exists(): raise ValueError('Fresh rig-pose diagnostic required')
    sr, sq = read(source/'result.json'), read(source/'request.json')
    if sr['status'] != 'complete' or not sr['passing_hand_screens'] or not sq.get('contact_regions') or sq['pose_source'] != 'animated':
        raise ValueError('Completed animated contact-region screen required')
    files = dict(sq['inputs']); files[str(source/'result.json')] = sha256(source/'result.json')
    for name, digest in sr['outputs'].items():
        path = (source/name).resolve()
        if path.parent != source: raise ValueError('Escaping source output')
        files[str(path)] = digest
    for name, digest in sq['implementation'].items():
        path = source/'implementation'/name
        if path.resolve().parent != source/'implementation': raise ValueError('Escaping method archive')
        files[str(path)] = digest
    def bound(path):
        if files.get(str(path)) != sha256(path): raise ValueError('Unbound evidence: '+str(path))
        return read(path)
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Changed input: '+path)
    br = bound(baseline/'result.json'); trials = bound(baseline/'trials.json')
    original = bound(baseline/'request.json'); donor = Path(sq['source']); dq = bound(donor/'request.json')
    trial = next(t for t in trials if t['folder'] == br['selected'])
    if Path(original['prepared_request']).parent != Path(sq['prepared']): raise ValueError('Original rig reference mismatch')
    prepared, actors = load_actors(sq['prepared']); event = sq['event_time_s']; contact = sq['selected_contact']; target = sq['target']
    rigs = []; references = []; chosen_worlds = []; selections = []
    output.mkdir(); (output/'implementation').mkdir(); methods = {}
    for name in sorted(set(sq['implementation']) | {'oriented_two_bone.py', 'two_bone_waypoint.py', 'study_palm_region_rig_pose.py'}):
        methods[name] = sha256(ROOT/'scripts'/name); shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    save(output/'request.json', dict(at=now(), source=str(source), baseline=str(baseline), inputs=files, implementation=methods,
        target=target, selected_contact=contact, contact_regions=sq['contact_regions'], region_vertices=sq['region_vertices'],
        event_time_s=event, twists_degrees=list(range(0, 360, 15)), swivels_degrees=list(range(-180, 181, 15)),
        policy='Independent wrist twist and two-bone elbow swivel search. Original source-reference pose angle limits stay fixed; only three arm local rotations may change. Rank feasible actor poses by summed squared original arm angles. Complete inter-actor mesh audit follows selection. This is a single-pose kinematic diagnostic, without native export, temporal or self-collision approval.',
        full_interval_geometry_audited=False, new_authored_condition=True, quality_approved=False))
    for i, (actor, ref_entry) in enumerate(zip(actors, trial['actors'])):
        path = donor/f'candidate-{i}.glb'; reference = baseline/br['selected']/ref_entry['path']
        for p in (path, reference):
            if files.get(str(p)) != sha256(p): raise ValueError('Unbound rig')
        rig, ref = RigAsset.load(path), RigAsset.load(reference); rigs.append(rig); references.append(ref)
        world = AnimationSampler(rig.document, rig.binary, 0).sample(event)
        ref_world = AnimationSampler(ref.document, ref.binary, 0).sample(event)
        source_local, ref_local = local_transforms(world, rig.parents), local_transforms(ref_world, ref.parents)
        layout = dq['actors'][i]; chain = layout['nodes'][:3]; wrist = chain[-1]
        item = contact['effector'] if i == 0 else contact['target']; vertex = item['surface_vertex']
        stage_points = rig.vertices(world)@actor['rotation'].T+actor['translation']; center = stage_points[vertex]
        support = sq['contact_regions'][i]['selected']['support_normal']; rows = []; best = None
        for twist in range(0, 360, 15):
            _, r, t = place(stage_points[[vertex]], center, support, target['centers_m'][i], target['normals'][i], twist)
            desired_position = actor['rotation'].T@(r@(actor['rotation']@world[wrist, :3, 3]+actor['translation'])+t-actor['translation'])
            desired_rotation = actor['rotation'].T@r@actor['rotation']@world[wrist, :3, :3]
            for swivel in range(-180, 181, 15):
                try:
                    candidate, local = reach_pose(world, rig.parents, *chain, desired_position, desired_rotation, np.deg2rad(swivel))
                except ValueError as exc:
                    rows.append(dict(twist=twist, swivel=swivel, reachable=False, reason=str(exc))); continue
                nodes = layout['nodes']; angles = np.rad2deg(Rotation.from_matrix(ref_local[nodes, :3, :3].transpose(0, 2, 1)@local[nodes, :3, :3]).magnitude())
                passed = bool(np.all(angles <= np.asarray(layout['original_budgets_degrees'])+1e-4))
                score = float(np.sum(angles[:3]**2))
                row = dict(twist=twist, swivel=swivel, reachable=True, original_pose_angles_degrees=angles.tolist(), original_pose_limits_pass=passed, arm_score=score)
                rows.append(row)
                if passed and (best is None or score < best['arm_score']):
                    frozen = [n for n in range(len(world)) if n not in chain]
                    np.testing.assert_allclose(local[frozen], source_local[frozen], rtol=0, atol=1e-9)
                    np.testing.assert_allclose(local[:, :3, 3], source_local[:, :3, 3], rtol=0, atol=1e-9)
                    best = row; best_world = candidate.copy()
        save(output/f'actor-{i}-search.json', rows)
        print(dict(actor=i, candidates=len(rows), within_pose_limits=sum(r.get('original_pose_limits_pass', False) for r in rows), selected=best), flush=True)
        selections.append(best)
        if best is not None: chosen_worlds.append(best_world)
    geometry_pass = False; contact_result = None
    if len(chosen_worlds) == 2:
        positions = [r.vertices(w)@a['rotation'].T+a['translation'] for r, w, a in zip(rigs, chosen_worlds, actors)]
        centers = []; normals = []
        for i, (p, actor) in enumerate(zip(positions, actors)):
            item = contact['effector'] if i == 0 else contact['target']; vertex = item['surface_vertex']
            patch = actor['faces'][np.any(actor['faces'] == vertex, axis=1)]
            c, n = palm_geometry(p, patch, vertex); centers.append(c); normals.append(n)
        contact_result = measure(centers, normals, target)
        surface = audit(positions[0], actors[0]['faces'], positions[1], actors[1]['faces'])
        depths = [penetration(positions[a], positions[b], actors[b]['faces'], tolerance_m=1e-8) for a, b in [(0, 1), (1, 0)]]
        geometry_pass = (not any(v for k, v in surface['counts'].items() if k != 'disjoint')
            and not any(surface['degenerate_faces']) and max(d['max_depth_m'] for d in depths) <= 1e-8)
        save(output/'geometry.json', dict(contact=contact_result, surface=surface, depths=depths, inter_actor_pose_screen_pass=geometry_pass))
        np.savez_compressed(output/'pose.npz', actor0=chosen_worlds[0], actor1=chosen_worlds[1])
        np.savez_compressed(output/'best-geometry.npz', left=positions[0], right=positions[1],
            left_faces=np.asarray(sq['region_faces'][0]), right_faces=np.asarray(sq['region_faces'][1]))
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Input changed during study')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Method changed during study')
    save(output/'result.json', dict(at=now(), status='complete', selections=selections, contact=contact_result,
        inter_actor_pose_screen_pass=bool(geometry_pass), original_pose_limits_pass=len(chosen_worlds) == 2,
        outputs={p.name: sha256(p) for p in output.iterdir() if p.is_file()}, native_animation_exported=False,
        full_interval_geometry_audited=False, selected_for_studio=False, quality_approved=False))


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'baseline', 'output'): parser.add_argument(name, type=Path)
    args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(args.source, args.baseline, args.output)
