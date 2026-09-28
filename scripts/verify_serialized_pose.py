"""Compare the in-memory export evaluator with retained actual GLB exports."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from profile_support_surface import load
from sparse_support_surface import SparseSupportReferenceFitter
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from serialized_pose import SerializedPose


def run(output):
    if output.exists(): raise ValueError('Preserve prior proof')
    fixtures = [ROOT/'reports'/name/'take' for name in
        ['fixed-root-support-v1', 'fixed-root-support-rig02-v1', 'fixed-root-support-rig03-v1', 'guarded-release-v1']]
    output.mkdir(parents=True); (output/'implementation').mkdir()
    names = ['serialized_pose.py', 'verify_serialized_pose.py', 'rig_loop.py', 'rig_transition.py',
             'gltf_tools.py', 'rig_clip_import.py', 'target_rig_contact.py', 'rig_asset.py',
             'profile_support_surface.py', 'sparse_support_surface.py']
    for name in names: shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    paths = [folder/name for folder in fixtures for name in ['spec.json', 'request.json', 'input/character.glb', 'candidate/character.glb']]
    paths += [f/('parameters.npz' if f.parent.name == 'guarded-release-v1' else 'fit.npz') for f in fixtures]
    request = dict(at=now(), fixtures=[str(f) for f in fixtures], inputs={str(p): sha256(p) for p in paths},
        implementation={n: sha256(output/'implementation'/n) for n in names},
        acceptance='All node matrices <=1e-12, all skinned coordinates <=1e-12, foot acceleration norm difference <=1e-8 m/s2 versus actual retained GLB. All integer and half frames on four150-frame clips across three rigs. Not motion quality or arbitrary glTF support.', quality_approved=False)
    save(output/'request.json', request); rows = []
    with threadpool_limits(limits=1):
        for folder in fixtures:
            held = Path(read(folder.parent/'request.json')['held']) if folder.parent.name == 'guarded-release-v1' else folder
            fitter, _ = load(held, SparseSupportReferenceFitter)
            archive = np.load(folder/('parameters.npz' if folder.parent.name == 'guarded-release-v1' else 'fit.npz'), allow_pickle=False)
            parameters = archive['parameters']; spec = read(folder/'spec.json'); count = spec['frames']
            animated = {c['target']['node'] for c in fitter.rig.document['animations'][0]['channels']} | set(fitter.nodes)
            oracle = SerializedPose(fitter.rig, animated, spec['root_node'], count)
            original = [fitter.pose(f, x)[0] for f, x in enumerate(parameters)]
            rig = RigAsset.load(folder/'candidate/character.glb'); sampler = AnimationSampler(rig.document, rig.binary, 0)
            matrix_error = skin_error = 0.; centers = [[], []]
            for frame in range(count):
                expected = sampler.sample(float(np.float32(frame/30)))
                found = oracle.pose(original[frame])
                matrix_error = max(matrix_error, float(np.abs(expected-found).max()))
                actual_skin, predicted_skin = rig.vertices(expected), fitter.rig.vertices(found)
                skin_error = max(skin_error, float(np.abs(actual_skin-predicted_skin).max()))
                for stream, surface in zip(centers, [actual_skin, predicted_skin]):
                    stream.append([surface[p['vertices']].mean(axis=0) for p in spec['patches'].values()])
                if frame+1 < count:
                    expected = sampler.sample((frame+.5)/30)
                    found = oracle.half_pose(original[frame], original[frame+1], frame)
                    matrix_error = max(matrix_error, float(np.abs(expected-found).max()))
                    skin_error = max(skin_error, float(np.abs(rig.vertices(expected)-fitter.rig.vertices(found)).max()))
            acceleration = [np.linalg.norm(np.diff(np.asarray(c), n=2, axis=0)*900, axis=2) for c in centers]
            acceleration_error = float(np.abs(acceleration[0]-acceleration[1]).max())
            passed = matrix_error <= 1e-12 and skin_error <= 1e-12 and acceleration_error <= 1e-8
            row = dict(case=folder.parent.name, integer_frames=count, half_frames=count-1,
                max_matrix_error=matrix_error, max_skinned_coordinate_error_m=skin_error,
                max_acceleration_norm_error_m_s2=acceleration_error, passed=passed)
            rows.append(row); save(output/'results.json', dict(rows=rows)); print(row, flush=True)
            if not passed: raise ValueError('Serialized pose reproduction differs')
    for path, digest in request['inputs'].items():
        if sha256(path) != digest: raise ValueError('Input changed')
    save(output/'completion.json', dict(at=now(), request_sha256=sha256(output/'request.json'),
        results_sha256=sha256(output/'results.json'), integer_frames=sum(r['integer_frames'] for r in rows),
        half_frames=sum(r['half_frames'] for r in rows), passed=True, quality_approved=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('output', type=Path); args = parser.parse_args(); run(args.output.resolve())
