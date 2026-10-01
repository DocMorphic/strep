"""Recompute event contact from observed engine joints using original CPU skin."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset, array
from rig_clip_import import AnimationSampler
from native_finger_motion import palm_geometry
from shared_palm_meeting import measure


def run(engine_audit, output):
    engine_audit, output = Path(engine_audit).resolve(), Path(output).resolve()
    if output.exists() or output.parent != ROOT/'reports': raise ValueError('Fresh immediate reports folder required')
    q, result = read(engine_audit/'request.json'), read(engine_audit/'result.json')
    if result['status'] != 'complete': raise ValueError('Completed observations required, including failing audits')
    files = dict(q['inputs'])
    for name, digest in result['outputs'].items():
        path = (engine_audit/name).resolve()
        if not path.is_relative_to(engine_audit): raise ValueError('Escaping engine evidence')
        if str(path) in files and files[str(path)] != digest: raise ValueError('Conflicting evidence')
        files[str(path)] = digest
    for name in ('request.json', 'result.json'):
        files[str(engine_audit/name)] = sha256(engine_audit/name)
    def bound(path):
        path = Path(path).resolve()
        if files.get(str(path)) != sha256(path): raise ValueError('Unbound contact input')
        return read(path)
    def unchanged():
        for path, digest in files.items():
            if sha256(path) != digest: raise ValueError('Changed contact evidence')
    unchanged()
    study = Path(q['study']); intent = bound(study/'request.json')
    pose = intent; seen = set()
    while 'baseline' not in pose:
        path = Path(pose['source'])/'request.json'
        if path in seen or len(seen) >= 32: raise ValueError('Invalid provenance chain')
        seen.add(path); pose = bound(path)
    region = bound(Path(pose['source'])/'request.json'); prepared = bound(Path(region['prepared'])/'request.json')
    if list(prepared['actors']) != ['A', 'B']: raise ValueError('Paired A/B development fixture required')
    observed = bound(engine_audit/'engine-output.json')['cases']
    if len(observed) != 2 or len(q['cases']) != 2: raise ValueError('Two distinct engine participants required')
    centers, normals, source_centers, source_normals, errors = [], [], [], [], []
    for i, name in enumerate(('A', 'B')):
        case, actual = q['cases'][i], observed[i]
        if case['id'] != actual['id']: raise ValueError('Engine participant mismatch')
        path = Path(case['path']); rig = RigAsset.load(path)
        if files.get(str(path)) != sha256(path): raise ValueError('Unbound engine clip')
        sampler = AnimationSampler(rig.document, rig.binary, 0)
        source = sampler.sample(intent['event_time_s']); world = source.copy()
        names = [rig.document['nodes'][n].get('name') for n in rig.joints]
        if len(actual['bone_names']) != len(names) or set(actual['bone_names']) != set(names): raise ValueError('Joint mapping differs')
        index = case['sample_times_s'].index(intent['event_time_s']); frame = actual['frames'][index]
        transforms = np.asarray(frame['bones'], float)
        if transforms.shape != (len(names), 4, 3) or not np.isfinite(transforms).all(): raise ValueError('Invalid observed engine pose')
        for engine_index, bone in enumerate(actual['bone_names']):
            node = rig.joints[names.index(bone)]
            world[node, :3, :3] = transforms[engine_index, :3].T
            world[node, :3, 3] = transforms[engine_index, 3]
        placement = prepared['actors'][name]['placement']; rotation = Rotation.from_quat(placement['rotation_xyzw']).as_matrix()
        translation = np.asarray(placement['translation_m'])
        points = rig.vertices(world)@rotation.T+translation
        original = rig.vertices(source)@rotation.T+translation
        vertex = intent['selected_contact']['effector' if i == 0 else 'target']['surface_vertex']
        if len(rig.primitives) != 1: raise ValueError('Contact diagnostic requires one skinned primitive')
        primitive = rig.primitives[0]
        mesh = rig.document['meshes'][rig.document['nodes'][primitive['node']]['mesh']]['primitives'][primitive['primitive']]
        faces = array(rig.document, rig.binary, mesh['indices']).reshape(-1, 3)
        faces = faces[np.any(faces == vertex, axis=1)]
        center, normal = palm_geometry(points, faces, vertex); before, before_normal = palm_geometry(original, faces, vertex)
        centers.append(center); normals.append(normal); source_centers.append(before); source_normals.append(before_normal)
        errors.append(dict(actor=name, requested_time_s=intent['event_time_s'], actual_time_s=frame['actual_time_s'],
            maximum_original_cpu_skin_vertex_error_m=float(np.linalg.norm(points-original, axis=1).max()),
            anchor_displacement_m=float(np.linalg.norm(center-before))))
    output.mkdir(); archive = output/'implementation'; archive.mkdir()
    for filename in ('diagnose_native_engine_contact.py', 'rig_asset.py', 'rig_clip_import.py', 'gltf_tools.py', 'strep.py', 'native_finger_motion.py', 'shared_palm_meeting.py'):
        path = ROOT/'scripts'/filename; target = archive/filename; shutil.copyfile(path, target); files[str(target)] = sha256(target)
    save(output/'request.json', dict(at=now(), engine_audit=str(engine_audit), inputs=files))
    engine_contact = measure(centers, normals, intent['target']); source_contact = measure(source_centers, source_normals, intent['target'])
    save(output/'contact.json', dict(engine_driven_original_cpu_skin=engine_contact, source_original_cpu_skin=source_contact, actors=errors))
    unchanged()
    save(output/'result.json', dict(at=now(), status='complete', contact_target_pass=engine_contact['contact_target_pass'],
        outputs={p.relative_to(output).as_posix(): sha256(p) for p in output.rglob('*') if p.is_file()},
        scope='Observed Godot world joints drive original full-weight CPU skin and authored stage placements at the fractional contact. This does not validate imported Godot mesh skin weights/inverse binds, GPU skin, collisions, continuous clearance or realism.',
        gpu_skin_verified=False, collision_verified=False, quality_approved=False, selected_for_studio=False))
    print(dict(contact=engine_contact, actors=errors), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('engine_audit', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); run(args.engine_audit, args.output)
