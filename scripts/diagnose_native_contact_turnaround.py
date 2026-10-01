"""Read-only rate and contact-key velocity diagnosis of completed native exports."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now


def run(source, output):
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from paired_approach_basis import BoundSkin
    from sampled_motion_caps import SampledMotionCaps, features, measures
    from elbow_swivel import descendants
    from scene_pair_problem import load_actors
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh diagnostic directory required')
    q, result = read(source/'request.json'), read(source/'result.json')
    if result['status'] != 'complete': raise ValueError('Completed native export required')
    files = dict(q['inputs']); files[str(source/'result.json')] = sha256(source/'result.json')
    for name, digest in result['outputs'].items():
        path = (source/name).resolve()
        if path.parent != source: raise ValueError('Escaping output path')
        files[str(path)] = digest
    for name, digest in q['implementation'].items():
        path = (source/'implementation'/name).resolve()
        if path.parent != source/'implementation': raise ValueError('Escaping method path')
        files[str(path)] = digest
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Changed evidence')
    def bound(path):
        path = Path(path)
        if files.get(str(path)) != sha256(path): raise ValueError('Unbound input')
        return read(path)
    pose = q; seen = set()
    while 'baseline' not in pose:
        path = Path(pose['source'])/'request.json'
        if path in seen or len(seen) >= 32: raise ValueError('Invalid provenance chain')
        seen.add(path); pose = bound(path)
    region = bound(Path(pose['source'])/'request.json'); donor = bound(Path(region['source'])/'request.json')
    _, actors = load_actors(region['prepared'])
    baseline = Path(pose['baseline']); br = bound(baseline/'result.json')
    trial = next(t for t in bound(baseline/'trials.json') if t['folder'] == br['selected'])
    times = np.asarray(q['uniform_times_s']); raw = []; current = []; labels = []; affected = []; turns = []
    step = 1e-5
    for i, entry in enumerate(trial['actors']):
        paths = [baseline/br['selected']/entry['path'], source/f'candidate-{i}.glb']
        for path, rows in zip(paths, (raw, current)):
            if files.get(str(path)) != sha256(path): raise ValueError('Unbound animation')
            rig = RigAsset.load(path); reader = AnimationSampler(rig.document, rig.binary, 0)
            rows.append(features(np.array([reader.sample(t) for t in times]), rig.joints))
        root = donor['actors'][i]['nodes'][0]
        affected.extend(descendants(rig.parents, root)[rig.joints].tolist())
        labels.extend(dict(actor=i, node=n, name=rig.document['nodes'][n]['name']) for n in rig.joints)
        clock = next(c[2] for c in reader.channels if c[0] == root and c[1] == 'rotation')
        key = int(np.searchsorted(clock, q['event_time_s'], side='right')-1); time = float(clock[key])
        if not 0 < key < len(clock)-1 or min(time-float(clock[key-1]), float(clock[key+1])-time) <= step:
            raise ValueError('Interior native key with finite-difference support required')
        world = np.array([reader.sample(t) for t in (time-step, time, time+step)])
        vertex = (q['selected_contact']['effector'] if i == 0 else q['selected_contact']['target'])['surface_vertex']
        points = BoundSkin(rig).evaluate(world, np.arange(3), np.full(3, vertex))@actors[i]['rotation'].T+actors[i]['translation']
        velocities = np.diff(points, axis=0)/step
        turns.append(dict(actor=i, native_key=key, time_s=time, marker_vertex=vertex,
            stage_velocity_before_after_m_s=velocities.tolist(),
            outward_velocity_before_after_m_s=(velocities@np.asarray(q['target']['normals'][i])).tolist(),
            velocity_jump_m_s=float(np.linalg.norm(velocities[1]-velocities[0]))))
    def combine(rows): return {k: np.concatenate([r[k] for r in rows], axis=1) for k in ('positions', 'rotations')}
    caps = SampledMotionCaps(combine(raw), times, q['original_bins_s']); rows = []
    saved = bound(source/'decoded.json')['motion_rates']
    for kind, values, ceiling, order, old in zip(('position_speed', 'position_acceleration', 'angular_speed', 'angular_acceleration'), measures(combine(current), caps.dt), caps.caps, (1, 2, 1, 2), saved):
        excess = values-ceiling-caps.tolerance; t, j = np.unravel_index(excess.argmax(), excess.shape)
        stamps = times[1:-1] if kind == 'angular_acceleration' else (times[:-order]+times[order:])/2
        count = int(np.count_nonzero(excess > 0))
        if kind != old['kind'] or count != old['failed_rows'] or abs(float(excess.max())-old['maximum_excess']) > 1e-10:
            raise ValueError('Recomputed rates disagree with completed export')
        rows.append(dict(kind=kind, failed_rows=count, worst_joint=labels[j], time_s=float(stamps[t]),
            measured=float(values[t, j]), original_cap=float(ceiling[t, j]), maximum_excess=float(excess.max()),
            failing_rows_outside_edited_arm_subtrees=int(np.count_nonzero(excess[:, ~np.asarray(affected)] > 0))))
    output.mkdir(); (output/'implementation').mkdir(); methods = {}
    for name in sorted(set(q['implementation']) | {Path(__file__).name}):
        methods[name] = sha256(ROOT/'scripts'/name); shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    save(output/'request.json', dict(at=now(), source=str(source), inputs=files, implementation=methods,
        finite_difference_step_s=step, policy='Recompute original rate checks and estimate one-sided marker velocities at the native key immediately before contact. Read-only diagnosis, not a smoothness or infeasibility certificate.'))
    save(output/'diagnosis.json', dict(turnaround=turns, rates=rows, quality_approved=False))
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Evidence changed during diagnosis')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Method changed during diagnosis')
    save(output/'result.json', dict(at=now(), status='complete', outputs={p.name: sha256(p) for p in output.iterdir() if p.is_file()},
        animations_modified=False, quality_approved=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('source', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); run(args.source, args.output)
