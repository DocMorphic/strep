"""Audit discrete triangle crossings in retained two-actor exported scenes."""
import argparse
import itertools
from pathlib import Path
import shutil
import time
import traceback
import numpy as np
import psutil
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset, array
from rig_clip_import import AnimationSampler
from triangle_crossing import audit


def run(source, scenes, frames, output):
    source, output = source.resolve(), output.resolve()
    if output.exists():
        raise ValueError('Preserve previous audit')
    if len(set(scenes)) != len(scenes) or not scenes:
        raise ValueError('Distinct scenes required')
    if len(set(frames)) != len(frames) or not frames or not np.isfinite(frames).all():
        raise ValueError('Distinct finite frames required')
    manifest = read(source / 'manifest.json')
    inputs = {str(source / 'manifest.json'): sha256(source / 'manifest.json')}
    prepared = []
    for scene_file in scenes:
        path = (source / scene_file).resolve()
        if not path.is_relative_to(source) or path.relative_to(source).as_posix() not in manifest['assets']:
            raise ValueError('Scene is not in the export manifest')
        if sha256(path) != manifest['assets'][path.relative_to(source).as_posix()]['sha256']:
            raise ValueError('Scene hash changed')
        inputs[str(path)] = sha256(path)
        scene = read(path)['scene']
        if len(scene['actors']) != 2 or any(f < 0 or f > scene['frame_count']-1 for f in frames):
            raise ValueError('Expected two actors and in-range samples')
        actors = []
        for label, entry in scene['actors'].items():
            glb = (source / entry['preview_glb']).resolve()
            if not glb.is_relative_to(source) or sha256(glb) != manifest['assets'][glb.relative_to(source).as_posix()]['sha256']:
                raise ValueError('Exported actor changed')
            inputs[str(glb)] = sha256(glb)
            rig = RigAsset.load(glb)
            if len(rig.primitives) != 1:
                raise ValueError('This diagnostic adapter requires one mesh primitive per actor')
            primitive = rig.primitives[0]
            mesh_index = rig.document['nodes'][primitive['node']]['mesh']
            primitive_data = rig.document['meshes'][mesh_index]['primitives'][primitive['primitive']]
            if primitive_data.get('mode', 4) != 4:
                raise ValueError('Triangle primitives required')
            faces = array(rig.document, rig.binary, primitive_data['indices']).reshape(-1, 3)
            sampler = AnimationSampler(rig.document, rig.binary, 0)
            actors.append((label, rig, sampler, faces,
                           Rotation.from_quat(entry['transform']['rotation_xyzw']).as_matrix(),
                           np.asarray(entry['transform']['translation_m'])))
        prepared.append((scene_file, scene, actors))
    output.mkdir(parents=True)
    (output / 'implementation').mkdir()
    names = ['audit_triangle_scene.py', 'triangle_crossing.py', 'rig_asset.py', 'rig_clip_import.py', 'gltf_tools.py', 'strep.py']
    for name in names:
        shutil.copyfile(ROOT / 'scripts' / name, output / 'implementation' / name)
    owner = psutil.Process()
    request = dict(at=now(), pid=owner.pid, created=owner.create_time(), source=str(source),
                   scenes=scenes, frames=frames, inputs=inputs, tolerance_m=1e-8,
                   implementation={n: sha256(output / 'implementation' / n) for n in names},
                   quality_approved=False, scope='Fixed decoded development samples. Supplementary surface crossing diagnostic; no optimizer, export modification or full-clock/continuous/self-collision/quality certification.')
    save(output / 'request.json', request)

    def phase(status, **details):
        save(output / 'pipeline.json', dict(at=now(), status=status, quality_approved=False, **details))
        print(status, details, flush=True)

    rows = []
    try:
        with threadpool_limits(limits=1):
            for scene_file, scene, actors in prepared:
                for frame in frames:
                    start = time.perf_counter()
                    values = [(label, rig.vertices(sampler.sample(float(np.float32(frame/scene['fps'])))) @ rot.T + shift, faces)
                              for label, rig, sampler, faces, rot, shift in actors]
                    a, b = values
                    phase('geometry', scene=scene_file, frame=frame)
                    result = audit(a[1], a[2], b[1], b[2], request['tolerance_m'])
                    name = f'sample-{len(rows):03d}.json'
                    save(output / name, dict(scene=scene_file, frame=frame, actors=[a[0],b[0]], **result))
                    rows.append(dict(scene=scene_file, frame=frame, counts=result['counts'],
                                     candidate_pairs=result['candidate_pairs'], degenerate_face_counts=[len(x) for x in result['degenerate_faces']],
                                     seconds=time.perf_counter()-start, sample=name, sample_sha256=sha256(output / name)))
                    save(output / 'summary.json', dict(rows=rows, quality_approved=False))
        for name, digest in inputs.items():
            if sha256(name) != digest:
                raise ValueError('Input changed during audit')
        for name, digest in request['implementation'].items():
            if sha256(ROOT / 'scripts' / name) != digest or sha256(output / 'implementation' / name) != digest:
                raise ValueError('Implementation changed during audit')
        save(output / 'completion.json', dict(at=now(), samples=len(rows), planned_samples=len(scenes)*len(frames),
                                              summary_sha256=sha256(output/'summary.json'), quality_approved=False))
        phase('complete')
    except BaseException as exc:
        phase('failed', error=str(exc), traceback=traceback.format_exc())
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--scenes', nargs='+', required=True)
    parser.add_argument('--frames', nargs='+', type=float, required=True)
    args = parser.parse_args()
    run(args.source, args.scenes, args.frames, args.output)
