"""Fixed development grid; rank serialized stance proposals, retaining failures."""
import numpy as np
from scipy.spatial.transform import Rotation
from native_leg_smoothing import corridor, smooth, lifts, rate_score
from native_leg_floor import lift_pose, export_rotations
from sampled_motion_caps import features, measures
from absolute_rate_peaks import compare
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from paired_temporal_neighbor import rotation_channels
from strep import save, sha256


def select(rig, reader, chains, projections, channels, key_times, up,
           audit_times, uniform, caps, output, actor):
    source_keys = np.array([reader.sample(float(t)) for t in key_times])
    heights = [p.evaluate(source_keys).min(axis=1) for p in projections]
    boxes = [corridor(source_keys, rig.parents, chain, height, up=up)
             for chain, height in zip(chains, heights)]
    moving = []
    from elbow_swivel import descendants
    for chain in chains:
        moving.extend(np.flatnonzero(descendants(rig.parents, chain[0])).tolist())
    columns = np.flatnonzero(np.isin(rig.joints, moving))
    raw = np.array([reader.sample(float(t)) for t in uniform])
    source_rates = measures(features(raw, rig.joints), caps.dt)
    nodes = [n for chain in chains for n in chain]
    grid = [(None, None)]+[(tau, mu) for tau in (.05, .15, .35) for mu in (.05, .5, 5.)]
    rows = []; viable = []
    for trial, (tau, mu) in enumerate(grid):
        row = dict(trial=trial, acceleration_time_s=tau, reference_weight_per_s2=mu,
                   control=tau is None, status='processing')
        path = output/f'grid-{actor}-{trial:02d}.glb'
        try:
            reports = []; amounts = []
            for box in boxes:
                if tau is None:
                    amounts.append(box['lower_lift']); reports.append(dict(control=True))
                else:
                    bend, report = smooth(key_times, box['lower'], box['upper'],
                                          acceleration_time=tau, reference_weight=mu)
                    amounts.append(lifts(box, bend)); reports.append(report)
            values = {n: channels[n][2].copy() for n in nodes}; corrections = []
            for key, time in enumerate(key_times):
                world = source_keys[key].copy(); feet = []
                for chain, height, amount in zip(chains, heights, amounts):
                    world, local, report = lift_pose(world, rig.parents, chain, float(height[key]),
                        clearance=float(height[key]+amount[key]), up=up)
                    report.update(source_minimum_height_m=float(height[key]),
                                  foot=rig.document['nodes'][chain[-1]]['name'])
                    feet.append(report)
                    if report['lift_m']:
                        for node, quat in zip(chain, Rotation.from_matrix(local[chain, :3, :3]).as_quat()):
                            values[node][key] = quat if quat@channels[node][2][key] >= 0 else -quat
                corrections.append(dict(time_s=float(time), feet=feet))
            export_rotations(rig.document, rig.binary, values, path)
            exported = RigAsset.load(path); current = AnimationSampler(exported.document, exported.binary, 0)
            decoded = rotation_channels(exported.document, exported.binary)
            angles = [float(np.rad2deg((Rotation.from_quat(channels[n][2]).inv()*Rotation.from_quat(decoded[n][2])).magnitude()).max()) for n in nodes]
            if max(angles) > 45.+1e-4:
                raise ValueError('Serialized source-relative leg edit exceeds angle bound')
            world = np.array([current.sample(float(t)) for t in audit_times])
            stance = []
            for projection in projections:
                minimum = projection.evaluate(world).min(axis=1)
                stance.append(dict(minimum_height_m=float(minimum.min()),
                                   maximum_lowest_height_m=float(minimum.max()),
                                   floor_depth_m=max(0., -float(minimum.min())),
                                   stance_samples_pass=bool(minimum.min() >= -1e-8 and minimum.max() <= .005)))
            rates = measures(features(world[np.searchsorted(audit_times, uniform)], rig.joints), caps.dt)
            score = rate_score(rates, caps.caps, columns, caps.tolerance)
            peak = compare(source_rates, rates)
            failed = [int(np.count_nonzero(v-c-caps.tolerance > 0)) for v, c in zip(rates, caps.caps)]
            row.update(status='complete', path=path.name, sha256=sha256(path), optimizer=reports,
                       decoded_leg_angles_degrees=angles, stance=stance,
                       stance_samples_pass=all(s['stance_samples_pass'] for s in stance),
                       diagnostic=score, original_motion_failed_rows=failed,
                       absolute_peak_comparison=peak)
            if row['stance_samples_pass']:
                viable.append((score['score'], trial, values, corrections))
        except ValueError as error:
            row.update(status='rejected', reason=str(error))
        rows.append(row)
        save(output/f'grid-{actor}-{trial:02d}.json', row)
        print(dict(phase='native_leg_grid', actor=actor, trial=trial, status=row['status'],
                   stance_samples_pass=row.get('stance_samples_pass'),
                   score=row.get('diagnostic', {}).get('score'), reason=row.get('reason')), flush=True)
    if not viable:
        raise ValueError('No serialized proposal satisfies the sampled stance corridor')
    score, trial, values, corrections = min(viable, key=lambda v: (v[0], v[1]))
    summary = dict(actor=actor, selected_trial=trial, score=score, candidates=rows,
                   policy='Minimum fixed-grid diagnostic leg-only excess among sampled stance-feasible candidates, including minimal-lift control. Original caps, contact and geometry gates remain unchanged.',
                   sampled_stance_maximum_lowest_height_m=.005,
                   source_clock_and_motion_caps_unchanged=True, quality_approved=False)
    save(output/f'actor-{actor}-grid.json', summary)
    return values, corrections, summary
