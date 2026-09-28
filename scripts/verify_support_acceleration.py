"""Finite-difference proof on a retained real skinned rig; no motion export."""
import argparse
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from strep import read, save, sha256, now
from rig_asset import RigAsset
from target_rig_contact import baseline
from support_acceleration_fit import SupportAccelerationFitter
from foot_acceleration import acceleration_caps, foot_acceleration_pair, foot_acceleration_energy


def run(folder, output):
    folder, output = folder.resolve(), output.resolve()
    if output.exists(): raise ValueError('Preserve previous proof')
    spec, request = read(folder/'spec.json'), read(folder/'request.json')
    rig = RigAsset.load(folder/'input/character.glb')
    before, local = baseline(rig, spec['frames'])
    surface = np.array([rig.vertices(w) for w in before])
    dynamics = read(folder/'release-dynamics.json')
    tracks = {v: np.stack([dynamics[v]['feet'][side]['centroids_m'] for side in spec['patches']], axis=1)
              for v in ['input', 'prior']}
    caps = acceleration_caps(tracks['input'], tracks['prior'], spec['fps'])
    fitter = SupportAccelerationFitter(rig, spec, local, request['targets_m'], np.ones(len(local)),
        surface, guides=request['support']['guides'], support_weight=40.)
    parameters = np.load(folder/'fit.npz', allow_pickle=False)['parameters']
    fitter.initialize_dynamics(parameters, caps, 1.)
    rows = []
    rng = np.random.default_rng(9135)
    for frame in [0, 18, 19, 20, len(local)-1]:
        x = parameters[frame].copy()
        fitter.surface_jacobian(frame, x)
        centers = fitter._centroids.copy(); jac = fitter._centroid_jac.copy()
        r, j = foot_acceleration_pair(fitter.centroid_track, frame, centers, jac, caps, spec['fps'], 1.)
        original_track = fitter.centroid_track.copy()
        errors = []
        for _ in range(3):
            direction = rng.normal(size=len(x)); direction /= np.linalg.norm(direction)
            eps = 1e-6
            pairs = []
            for sign in [-1, 1]:
                fitter.surface_jacobian(frame, x+sign*eps*direction)
                pairs.append(foot_acceleration_pair(original_track, frame, fitter._centroids,
                    fitter._centroid_jac, caps, spec['fps'], 1.)[0])
            error = float(np.max(np.abs((pairs[1]-pairs[0])/(2*eps)-j@direction)))
            if error > 2e-4: raise ValueError('Actual skin derivative mismatch')
            errors.append(error)
        # Accept a value different from the last trial: catches a stale cache.
        fitter.accept_frame(frame, x)
        expected = fitter.centroids(rig.vertices(fitter.pose(frame, x)[0]))
        cache_error = float(np.max(np.abs(fitter.centroid_track[frame]-expected)))
        if cache_error > 1e-12: raise ValueError('Stale accepted centroid cache')
        fitter.centroid_track = original_track
        rows.append(dict(frame=frame,active_residuals=int(np.count_nonzero(r)),
                         max_directional_error=max(errors),accepted_cache_error_m=cache_error))
    inputs = {str(folder/n):sha256(folder/n) for n in ['spec.json','request.json','fit.npz','release-dynamics.json','input/character.glb']}
    implementation = {str(Path(__file__).parent/n):sha256(Path(__file__).parent/n) for n in
        ['foot_acceleration.py','support_acceleration_fit.py','relax_support_acceleration.py','support_acceleration_clip.py','verify_support_acceleration.py']}
    save(output, dict(at=now(),inputs=inputs,implementation=implementation,rows=rows,
        energy=foot_acceleration_energy(fitter.centroid_track,caps,spec['fps'],1.),
        passed=True,quality_approved=False,scope='Real skin derivative and cache proof only; no optimized clip or engine validation.'))
    print(dict(passed=True,frames=len(rows),max_error=max(r['max_directional_error'] for r in rows)))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    with threadpool_limits(limits=1): run(a.folder,a.output)
