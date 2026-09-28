"""Fresh GLB envelope and release audit, independent of optimizer caches."""
import argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from verify_rig_clearance import localize
from support_release_metrics import release_windows
from study_whole_support_breadth import check_engine


def run(folder, output):
    if output.exists():
        raise ValueError('Preserve existing audit')
    done = read(folder/'completion.json'); request = read(folder/'request.json')
    if read(folder/'pipeline.json')['status'] != 'complete' or done['request_sha256'] != sha256(folder/'request.json'):
        raise ValueError('Complete unchanged trial required')
    for name, digest in done['files'].items():
        if sha256(folder/name) != digest: raise ValueError('Completed output changed: '+name)
    for path, digest in request['inputs'].items():
        if sha256(path) != digest: raise ValueError('Frozen input changed: '+path)
    for name, digest in request['implementation'].items():
        if sha256(folder/'implementation'/name) != digest: raise ValueError('Frozen implementation changed')
    spec = read(folder/'take/spec.json'); count, fps = spec['frames'], spec['fps']; root = spec['root_node']
    fit = read(folder/'take/fit-summary.json'); held = Path(request['held'])
    parameters = np.load(folder/'take/parameters.npz', allow_pickle=False)
    np.testing.assert_array_equal(parameters['parameters'][:, fit['protected_columns']], parameters['initial'][:, fit['protected_columns']])
    rows, decoded = [], {}
    for variant, path in [('held', held/'candidate/character.glb'), ('candidate', folder/'take/candidate/character.glb')]:
        rig = RigAsset.load(path); sampler = AnimationSampler(rig.document, rig.binary, 0)
        world = np.array([sampler.sample(float(np.float32(f/fps))) for f in range(count)])
        surfaces = np.array([rig.vertices(pose) for pose in world])
        local = localize(world, rig.parents)
        centers = np.stack([surfaces[:, patch['vertices']].mean(axis=1) for patch in spec['patches'].values()], axis=1)
        heights = np.stack([surfaces[:, patch['vertices'], 1].min(axis=1) for patch in spec['patches'].values()], axis=1)
        floor = max(0., -float(surfaces[:, :, 1].min()))
        half_floor = max(max(0., -float(rig.vertices(sampler.sample((f+.5)/fps))[:, 1].min())) for f in range(count-1))
        acceleration = np.linalg.norm(np.diff(centers, n=2, axis=0)*fps**2, axis=2)
        speed = np.linalg.norm(np.diff(centers[:, :, [0, 2]], axis=0)*fps, axis=2)
        delta = local[:-1, :, :3, :3].transpose(0, 1, 3, 2)@local[1:, :, :3, :3]
        rotation_peak = float(np.degrees(Rotation.from_matrix(delta.reshape(-1, 3, 3)).magnitude()).max())
        decoded[variant] = dict(world=world, local=local, centers=centers, heights=heights, acceleration=acceleration, speed=speed)
        rows.append(dict(variant=variant, source_sha256=sha256(path), integer_floor_m=floor,
            half_frame_floor_m=half_floor, rotation_peak_degrees=rotation_peak,
            root_acceleration_m_s2=float(np.linalg.norm(np.diff(world[:, root, :3, 3], n=2, axis=0)*fps**2, axis=1).max())))
    old, new = decoded['held'], decoded['candidate']
    source_root_error = float(np.abs(np.diff(new['world'][:, root, :3, 3]-old['world'][:, root, :3, 3], n=2, axis=0)*fps**2).max())
    protected_error = (float(np.abs(new['local'][:, request['protected_nodes'], :3, :3]-old['local'][:, request['protected_nodes'], :3, :3]).max())
                       if request['protected_nodes'] else 0.)
    # Separate serialization tolerances from the unchanged development screen.
    acceleration_excess = float(np.maximum(0, new['acceleration']-fit['safety_caps_m_s2']).max())
    steps = np.asarray(fit['support_steps'], bool)
    speed_excess = float(np.maximum(0, new['speed']-fit['support_speed_caps_m_s'])[steps].max())
    active = np.zeros((count, len(spec['patches'])), bool)
    annotations = read(held/'input/contacts.json')
    for index, side in enumerate(spec['patches']):
        for interval in annotations['intervals']:
            if interval['joint'] in (side+'Foot', side+'ToeBase'):
                active[interval['start_frame']:interval['end_frame_exclusive'], index] = True
    hover_excess = float(np.maximum(0, new['heights']-fit['hover_caps_m'])[active].max())
    caps = read(held/'release-dynamics.json'); support = read(held/'request.json')['support']; events = []
    for side_index, side in enumerate(spec['patches']):
        intervals = [r for r in support['intervals'] if r['side'] == side]
        actual = [release_windows(decoded[v]['centers'][:, side_index], intervals, fps) for v in ['held', 'candidate']]
        baselines = [caps[v]['feet'][side]['releases'] for v in ['input', 'prior']]
        if len({len(r) for r in baselines+[a['releases'] for a in actual]}) != 1:
            raise ValueError('Release population differs')
        for raw, prior, held_event, candidate in zip(*baselines, *[a['releases'] for a in actual]):
            if len({r['release_frame'] for r in [raw, prior, held_event, candidate]}) != 1:
                raise ValueError('Release clock differs')
            cap = max(raw['acceleration_max_m_s2'], prior['acceleration_max_m_s2'])+1e-5
            events.append(dict(side=side, release_frame=candidate['release_frame'], limit_m_s2=cap,
                held_m_s2=held_event['acceleration_max_m_s2'], candidate_m_s2=candidate['acceleration_max_m_s2'],
                held_passed=held_event['acceleration_max_m_s2'] <= cap, candidate_passed=candidate['acceleration_max_m_s2'] <= cap))
    checks = dict(frozen_acceleration_envelopes=acceleration_excess <= 1e-4,
        frozen_support_speed_envelopes=speed_excess <= 1e-6, frozen_hover_envelopes=hover_excess <= 1e-6,
        held_root_acceleration_preserved=source_root_error <= 1e-4, protected_joint_preserved=protected_error <= 1e-6,
        floor_all_integer_and_half_frames=max(rows[1]['integer_floor_m'], rows[1]['half_frame_floor_m']) <= .005+1e-7,
        local_rotation_peak_preserved=rows[1]['rotation_peak_degrees'] <= rows[0]['rotation_peak_degrees']+1e-4,
        no_new_release_failures=all(not e['held_passed'] or e['candidate_passed'] for e in events))
    engine_cases = read(folder/'engine/manifest.json')['cases']
    frames = check_engine(read(folder/'engine/audit/verification.json'), engine_cases)
    if frames != 3*count: raise ValueError('Incomplete engine population')
    for item in engine_cases:
        if sha256(item['path']) != item['sha256']: raise ValueError('Engine input changed')
    full = read(folder/'take/comparison.json')
    for side in spec['patches']:
        if sum(not e['candidate_passed'] for e in events if e['side'] == side) != full['feet'][side]['release_acceleration_regressions']:
            raise ValueError('Fresh release count differs from full comparison')
    save(output, dict(at=now(), completion_sha256=sha256(folder/'completion.json'), implementation_sha256=sha256(__file__),
        rows=rows, events=events, envelope_checks=checks, engine_actor_frames=frames,
        acceleration_envelope_excess_m_s2=acceleration_excess, support_speed_excess_m_s=speed_excess,
        hover_excess_m=hover_excess, held_root_acceleration_error_m_s2=source_root_error, protected_joint_matrix_error=protected_error,
        failed_full_checks=[name for name, passed in full['checks'].items() if not passed],
        quality_approved=False, scope='Fresh decoded all integer/half-frame surfaces, frozen envelopes, releases, protected tracks and engine bindings. Independent animator/semantic validation remains missing.'))
    print(dict(envelope_checks=checks, full_failures=[name for name, passed in full['checks'].items() if not passed], engine_frames=frames))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('folder', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); run(args.folder.resolve(), args.output.resolve())
