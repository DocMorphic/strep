"""Sweep hand-shape azimuth with exact authored markers, before rig fitting."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now


def run(source, prepared_folder, output, contact_id, pose_source='animated'):
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from scene_pair_problem import load_actors
    from native_finger_motion import palm_geometry
    from shared_palm_meeting import measure
    from hand_contact_plane import hand_region
    from rigid_contact_initialization import place, summarize
    from triangle_crossing import audit
    from convex_partner_surface import penetration
    if pose_source not in ('animated', 'rest'): raise ValueError('Explicit animated or rest hand shape required')
    source, prepared_folder, output = [Path(p).resolve() for p in (source, prepared_folder, output)]
    if output.exists(): raise ValueError('Fresh diagnostic output required')
    result, request = read(source/'result.json'), read(source/'request.json')
    if result['status'] != 'complete' or not result['contact_target_pass']:
        raise ValueError('Completed authored contact study required')
    files = dict(request['inputs']); files[str(source/'result.json')] = sha256(source/'result.json')
    for name, digest in result['outputs'].items():
        path = (source/name).resolve()
        if path.parent != source: raise ValueError('Escaping source output')
        files[str(path)] = digest
    for name, digest in request['implementation'].items():
        path = (source/'implementation'/name).resolve()
        if path.parent != source/'implementation': raise ValueError('Escaping method archive')
        files[str(path)] = digest
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Changed source evidence: '+path)
    if files.get(str(prepared_folder/'request.json')) != sha256(prepared_folder/'request.json'):
        raise ValueError('Prepared request not bound by source')
    prepared, actors = load_actors(prepared_folder)
    scene_path = prepared_folder/prepared['scene_snapshot']['path']
    if files.get(str(scene_path)) != sha256(scene_path): raise ValueError('Scene not bound by source')
    contact = next(c for c in read(scene_path)['scene']['contacts'] if c['id'] == contact_id)
    if [a['name'] for a in actors] != [contact['actor'], contact['target']['actor']]:
        raise ValueError('Contact actor order must match source')
    event, target = request['event_time_s'], request['target']
    points = []; patches = []; regions = []; faces = []; centers = []; normals = []
    for i, actor in enumerate(actors):
        path = source/f'candidate-{i}.glb'
        if files.get(str(path)) != sha256(path): raise ValueError('Unbound candidate')
        rig = RigAsset.load(path); sampler = AnimationSampler(rig.document, rig.binary, 0)
        world = sampler.sample(event) if pose_source == 'animated' else rig.reference
        p = rig.vertices(world)@actor['rotation'].T+actor['translation']; points.append(p)
        item = contact['effector'] if i == 0 else contact['target']; vertex = item['surface_vertex']
        patch = actor['faces'][np.any(actor['faces'] == vertex, axis=1)]
        c, n = palm_geometry(p, patch, vertex); centers.append(c); normals.append(n); patches.append(patch)
        hand = next(j for j in rig.joints if rig.document['nodes'][j]['name'] == item['joint'])
        primitive = rig.primitives[0]
        ids, face_ids = hand_region(rig.parents, hand, np.asarray(rig.joints)[primitive['joints']], primitive['weights'], actor['faces'])
        np.testing.assert_array_equal(ids, request['actors'][i]['vertices'])
        np.testing.assert_array_equal(face_ids, request['actors'][i]['triangles'])
        regions.append(ids); faces.append(actor['faces'][face_ids])
    output.mkdir(); (output/'implementation').mkdir(); methods = {}
    for name in sorted(set(request['implementation']) | {'rigid_contact_initialization.py', 'study_rigid_contact_initialization.py'}):
        methods[name] = sha256(ROOT/'scripts'/name); shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    angles = list(range(0, 360, 15))
    save(output/'request.json', dict(at=now(), source=str(source), prepared=str(prepared_folder), inputs=files,
        implementation=methods, contact_id=contact_id, event_time_s=event, target=target, twists_degrees=angles, pose_source=pose_source,
        original_centers_m=np.asarray(centers).tolist(), original_normals=np.asarray(normals).tolist(),
        region_vertices=[v.tolist() for v in regions], region_faces=[f.tolist() for f in faces],
        policy='Rigidly align each source hand anchor and normal exactly, keep actor A twist zero, sweep actor B. Triangle tests cover both hand regions; directional containment checks every region vertex against the complete closed partner mesh under the same rigid transform. This is a geometry screen with relaxed rig reachability, original angle and temporal constraints, not an animation export or an infeasibility proof.',
        rig_feasibility_verified=False, diagnostic_only=True, quality_approved=False))
    rows = []; best_key = None
    for angle in angles:
        moved = []; transforms = []; measured_c = []; measured_n = []
        for i in range(2):
            p, r, t = place(points[i], centers[i], normals[i], target['centers_m'][i], target['normals'][i], angle if i else 0.)
            moved.append(p); transforms.append(dict(rotation=r.tolist(), translation_m=t.tolist()))
            item = contact['effector'] if i == 0 else contact['target']
            c, n = palm_geometry(p, patches[i], item['surface_vertex']); measured_c.append(c); measured_n.append(n)
        contact_check = measure(measured_c, measured_n, target)
        if not contact_check['contact_target_pass']: raise ValueError('Rigid placement lost exact contact')
        surface = audit(moved[0], faces[0], moved[1], faces[1])
        depths = [penetration(moved[a][regions[a]], moved[b], actors[b]['faces'], tolerance_m=1e-8) for a, b in [(0, 1), (1, 0)]]
        summary = summarize(surface, depths)
        row = dict(twist_degrees=angle, transforms=transforms, contact=contact_check, **summary)
        save(output/f'geometry-{angle:03d}.json', dict(surface=surface, directional_depths=depths, **row))
        rows.append(row); save(output/'sweep.json', rows)
        key = (not summary['sampled_hand_screen_pass'], summary['proper_crossings']+summary['unresolved_pairs'], summary['maximum_vertex_depth_m'])
        if best_key is None or key < best_key:
            best_key = key; best = row
            np.savez_compressed(output/'best-geometry.npz', left=moved[0], right=moved[1], left_faces=faces[0], right_faces=faces[1])
        print(dict(phase='rigid_contact_sweep', angle=angle, **summary), flush=True)
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Input changed during study')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Method changed during study')
    save(output/'result.json', dict(at=now(), status='complete', outputs={p.name: sha256(p) for p in output.iterdir() if p.is_file()},
        trials=len(rows), passing_hand_screens=sum(r['sampled_hand_screen_pass'] for r in rows), best=best,
        rig_feasibility_verified=False, selected_for_studio=False, diagnostic_only=True, quality_approved=False))


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'prepared', 'output'): parser.add_argument(name, type=Path)
    parser.add_argument('--contact', required=True)
    parser.add_argument('--pose-source', choices=['animated', 'rest'], default='animated'); args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(args.source, args.prepared, args.output, args.contact, args.pose_source)
