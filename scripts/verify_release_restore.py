"""Fresh exported geometry checks including strict normalized feasibility."""
import argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_transition import localize
from verify_guarded_release import run as decoded_audit


def run(folder, output):
    if output.exists(): raise ValueError('Preserve prior audit')
    request = read(folder/'request.json'); frozen = read(folder/'freeze.json')
    for name, key in [('request.json', 'request_sha256'), ('envelope.json', 'envelope_sha256'), ('preflight.json', 'preflight_sha256')]:
        if sha256(folder/name) != frozen[key]: raise ValueError('Frozen protocol changed')
    if read(folder/'pipeline.json')['status'] != 'complete': raise ValueError('Completed trial required')
    output.mkdir(parents=True); decoded_audit(folder, output/'decoded.json')
    decoded = read(output/'decoded.json'); spec = read(folder/'take/spec.json'); envelope = read(folder/'envelope.json')
    proposal = Path(request['proposal']); archive = np.load(folder/'take/parameters.npz', allow_pickle=False)
    initial = np.load(proposal/'take/parameters.npz', allow_pickle=False)['parameters']
    np.testing.assert_array_equal(archive['initial'], initial)
    values = archive['parameters']; frames = request['frames']; untouched = [f for f in range(len(values)) if f not in frames]
    np.testing.assert_array_equal(values[untouched], initial[untouched]); np.testing.assert_array_equal(values[:, envelope['protected_columns']], initial[:, envelope['protected_columns']])
    solver = read(folder/'take/solver.json'); free = [i for i in range(values.shape[1]) if i not in envelope['protected_columns']]
    np.testing.assert_array_equal(values[np.ix_(frames, free)].ravel(), solver['final_coordinates'])
    change = float(np.abs(values-initial).max())
    if change > request['attempts']*request['trust']+1e-12: raise ValueError('Restoration exceeds cumulative step bound')
    rig = RigAsset.load(folder/'take/candidate/character.glb'); sampler = AnimationSampler(rig.document, rig.binary, 0)
    world = np.array([sampler.sample(float(np.float32(f/spec['fps']))) for f in range(spec['frames'])])
    surfaces = np.array([rig.vertices(w) for w in world]); local = localize(world, rig.parents)
    centers = np.stack([surfaces[:, p['vertices']].mean(axis=1) for p in spec['patches'].values()], axis=1)
    heights = np.stack([surfaces[:, p['vertices'], 1].min(axis=1) for p in spec['patches'].values()], axis=1)
    acceleration = np.diff(centers, n=2, axis=0)*spec['fps']**2; caps = np.asarray(envelope['safety_caps_m_s2'])
    acceleration_margin = (caps**2-np.sum(acceleration**2, axis=2))/np.maximum(caps**2, 1.)
    speed = np.diff(centers[:, :, [0, 2]], axis=0)*spec['fps']; caps = np.asarray(envelope['support_speed_caps_m_s'])
    mask = np.asarray(envelope['support_steps'], bool)
    speed_margin = ((caps**2-np.sum(speed**2, axis=2))/np.maximum(caps**2, .01**2))[mask]
    floor_margin = (surfaces[:, :, 1]+.005)/.005
    hover_margin = ((np.asarray(envelope['hover_caps_m'])-heights)/.01)[np.asarray(envelope['active_frames'], bool)]
    differences = np.diff(values, axis=0); edit_margins = []
    for column in range(0, values.shape[1], 3):
        radius = spec['limits']['root_step_m'] if column == 0 else np.radians(spec['limits']['joint_step_degrees'])
        edit_margins.extend(1-np.sum(differences[:, column:column+3]**2, axis=1)/radius**2)
    margins = dict(acceleration=float(acceleration_margin.min()), support_speed=float(speed_margin.min()),
        integer_floor=float(floor_margin.min()), hover=float(hover_margin.min()), adjacent_edits=float(min(edit_margins)))
    rotation = Rotation.from_matrix((local[:-1, :, :3, :3].transpose(0, 1, 3, 2)@local[1:, :, :3, :3]).reshape(-1, 3, 3)).magnitude().max()
    # Full-file half-frame and rotation checks retain their original exact
    # geometric thresholds; the normalized feasibility tolerance is unchanged.
    checks = {name: value >= -1e-8 for name, value in margins.items()}
    checks['half_frame_floor'] = decoded['rows'][1]['half_frame_floor_m'] <= .005
    checks['rotation_peak'] = bool(rotation <= envelope['rotation_cap_radians']+1e-10)
    target = request['target']; magnitude = np.linalg.norm(acceleration[np.asarray(target['centers'])-1, target['side_index']], axis=1)
    checks['target_exactly_satisfied'] = bool(magnitude.max() <= target['limit_m_s2'])
    old_rig = RigAsset.load(proposal/'take/candidate/character.glb'); old_sampler = AnimationSampler(old_rig.document, old_rig.binary, 0)
    outside_error = max(float(np.abs(world[f]-old_sampler.sample(float(np.float32(f/spec['fps'])))).max()) for f in untouched)
    checks['untouched_decoded_frames'] = outside_error <= 1e-12
    save(output/'completion.json', dict(at=now(), study_completion_sha256=sha256(folder/'completion.json'),
        decoded_audit_sha256=sha256(output/'decoded.json'), implementation_sha256=sha256(__file__), strict_checks=checks,
        strict_checks_passed=all(checks.values()), minimum_normalized_margins=margins,
        maximum_parameter_change=change, unchanged_frames=len(untouched), unchanged_decoded_matrix_max_error=outside_error,
        target_acceleration_max_m_s2=float(magnitude.max()), target_limit_m_s2=target['limit_m_s2'],
        original_full_checks_passed=not decoded['failed_full_checks'], engine_actor_frames=decoded['engine_actor_frames'],
        quality_approved=False, scope='Independent all-frame GLB skin/parameter constraints, original normalized tolerance, target release and preserved frames, plus original full comparison/engine proof. No optimizer-cache or relaxed-tolerance substitute.'))
    print(read(output/'completion.json'))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('folder', type=Path); p.add_argument('output', type=Path); a = p.parse_args(); run(a.folder.resolve(), a.output.resolve())
