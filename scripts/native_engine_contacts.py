"""Headless imported-engine poses/bindings, CPU skin and fixed foot contacts.

This samples AnimationPlayer, not a renderer, physics solver or human review.
It deliberately does not call mesh bake APIs that retrieve GPU buffers.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import numpy as np
from scipy.spatial import cKDTree
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_support_spec import validate
from native_support_skin import NativeSupportSkin
from native_leg_floor import foot_region
from native_foot_plant import policy_rows
from native_contact_diagnostics import measure, patch_metrics
from contact_rate_path import ProjectedSkin


IDENTITY_TOLERANCE = 2e-6


def matrices(values):
    a = np.asarray(values, float)
    if a.shape[-2:] != (4, 3) or not np.isfinite(a).all():
        raise ValueError('Finite Godot basis columns and origin required')
    result = np.zeros(a.shape[:-2] + (4, 4))
    result[..., :3, :] = a.swapaxes(-1, -2)
    result[..., 3, 3] = 1
    return result


def clocks(row):
    start, end = row['stance_s']
    uniform = np.arange(int(np.floor(start*120)), int(np.ceil(end*120))+1)/120
    # Keep the original acceptance population exactly. Native keys are a
    # separate population: merging nearly coincident clocks distorts speed.
    regular = np.unique(np.r_[start, uniform[(uniform > start) & (uniform < end)], end])
    keys = np.asarray(row['clock'], float)
    native = np.unique(np.r_[start, keys[(keys > start) & (keys < end)], end])
    return {'stance_120hz': regular, 'native_keys': native}


def checked_clock(times, duration):
    a = np.asarray(times, float)
    if (a.ndim != 1 or len(a) < 2 or not np.isfinite(a).all()
            or np.any(np.diff(a) <= 0) or a[0] < 0 or a[-1] > duration):
        raise ValueError('Increasing finite engine clock within duration required')
    return a


def packed_weights(weights):
    """Expected Godot 4.7.2 unsigned-16 mesh encoding, for identity only.

    No normalization and no modification to source/candidate assets. The
    imported bindings must independently match this encoding before use.
    """
    a = np.asarray(weights, np.float32)
    if not np.isfinite(a).all() or np.any(a < 0) or np.any(a > 1):
        raise ValueError('Finite unit-range weights required')
    return (np.floor(a*np.float32(65535)).astype(np.uint16).astype(np.float32)/np.float32(65535)).astype(float)


def features(nodes, weights, points, bone_count, quantized=False):
    """Per-bone weight and weighted bind-space position, before animation.

    Equivalent duplicate influences accumulate. Slot order and exact duplicate
    vertices can change on import without changing the skin function.
    """
    nodes, weights, points = np.asarray(nodes), np.asarray(weights, float), np.asarray(points, float)
    if (nodes.ndim != 2 or weights.shape != nodes.shape or points.shape != nodes.shape+(4,)
            or nodes.dtype.kind not in 'iu' or nodes.min() < 0 or nodes.max() >= bone_count
            or not np.isfinite(weights).all() or not np.isfinite(points).all()
            or np.any(weights < 0) or np.any(weights.sum(axis=1) > 1+2e-6)
            or np.any(weights.sum(axis=1) < 1-2e-6-(nodes.shape[1]/65535 if quantized else 0))):
        raise ValueError('Valid normalized skin binding population required')
    result = np.zeros((len(nodes), bone_count, 4))
    for slot in range(nodes.shape[1]):
        np.add.at(result, (np.arange(len(nodes)), nodes[:, slot]), weights[:, slot, None]*points[:, slot])
    return result


def match_bindings(source_features, imported_features, tolerance=IDENTITY_TOLERANCE):
    """Match bind functions, never nearest posed geometry or vertex order."""
    a, b = np.asarray(source_features, float), np.asarray(imported_features, float)
    if (a.ndim != 3 or a.shape[1:] != b.shape[1:] or not len(a) or not len(b)
            or not np.isfinite(a).all() or not np.isfinite(b).all()):
        raise ValueError('Finite comparable source/imported bindings required')
    tree = cKDTree(b.sum(axis=1))
    # The coarse sum only locates candidates. Every per-bone component must
    # independently match; collisions in the sum cannot hide changed weights.
    radius = tolerance * a.shape[1] * 2
    indices, errors, duplicates = [], [], []
    for entry in a:
        choices = tree.query_ball_point(entry.sum(axis=0), radius)
        valid = [(float(np.max(np.abs(b[i]-entry))), i) for i in choices
                 if np.max(np.abs(b[i]-entry)) <= tolerance]
        if not valid:
            raise ValueError('Imported foot vertex lost or skin binding changed')
        error, index = min(valid)
        indices.append(index); errors.append(error); duplicates.append(len(valid))
    return np.asarray(indices), max(errors), duplicates


def imported_bindings(observed, names):
    if (len(observed['bone_names']) != len(names) or len(set(observed['bone_names'])) != len(names)
            or set(observed['bone_names']) != set(names)):
        raise ValueError('Explicit unchanged unique bone-name population required')
    name_index = {name: i for i, name in enumerate(names)}
    bone_map = np.array([name_index[name] for name in observed['bone_names']])
    bindings, refs = [], []
    for mesh in observed['meshes']:
        vertices = np.asarray(mesh['positions'], float)
        ids = np.asarray(mesh['bones'])
        weights = np.asarray(mesh['weights'], float)
        if (vertices.ndim != 2 or vertices.shape[1] != 3 or not len(vertices)
                or ids.ndim != 1 or ids.dtype.kind not in 'iu' or ids.size not in (len(vertices)*4, len(vertices)*8)
                or weights.shape != ids.shape or ids.min() < 0 or ids.max() >= len(mesh['binds'])):
            raise ValueError('Imported surface requires four or eight bone influences')
        ids = ids.reshape(len(vertices), -1); weights = weights.reshape(ids.shape)
        bind_bones = np.asarray([b['bone'] for b in mesh['binds']])
        if bind_bones.dtype.kind not in 'iu' or bind_bones.min() < 0 or bind_bones.max() >= len(bone_map):
            raise ValueError('Imported bind references invalid bones')
        inverse = matrices([b['pose'] for b in mesh['binds']])
        local = np.einsum('vkij,vj->vki', inverse[ids], np.c_[vertices, np.ones(len(vertices))])
        bindings.append(features(bone_map[bind_bones[ids]], weights, local, len(names), quantized=True))
        refs.extend([mesh['node'], mesh['surface'], v] for v in range(len(vertices)))
    if not bindings:
        raise ValueError('No imported skin surfaces')
    return np.concatenate(bindings), refs, bone_map


def imported_world(observed, times, bone_map):
    if len(observed['frames']) != len(times):
        raise ValueError('Missing engine samples')
    worlds = []
    mesh_names = {mesh['node'] for mesh in observed['meshes']}
    for time, frame in zip(times, observed['frames']):
        if (not np.isfinite([frame['requested_time_s'], frame['actual_time_s']]).all()
                or abs(frame['requested_time_s']-float(time)) > 4*abs(np.spacing(float(time)))
                or abs(frame['actual_time_s']-time) > 1e-9):
            raise ValueError('Engine sample clock differs from requested clock')
        world = matrices(frame['bones'])
        if world.shape != (len(bone_map), 4, 4):
            raise ValueError('Incomplete engine bone population')
        skeleton = matrices(frame['skeleton_world'])
        meshes = frame['mesh_world']
        if len(meshes) != len(mesh_names) or {m['node'] for m in meshes} != mesh_names:
            raise ValueError('Missing engine mesh transforms')
        # The CPU formula below requires the imported mesh to use skeleton
        # space. Reject a displaced instance rather than omit its transform.
        if any(np.max(np.abs(matrices(m['matrix'])-skeleton)) > 1e-7 for m in meshes):
            raise ValueError('Engine mesh and skeleton spaces differ; explicit mapping required')
        ordered = np.empty_like(world); ordered[bone_map] = world; worlds.append(ordered)
    return np.asarray(worlds)


def contact(points, anchor, row, times, patch, limit):
    result = patch_metrics(points, row['up'], row['offset'], times, patch)
    intervals = np.diff(times)
    movement = np.diff(points[:, patch], axis=0)
    movement -= (movement@row['up'])[..., None]*row['up']
    speeds = np.linalg.norm(movement, axis=2)/intervals[:, None]
    pair, vertex = np.unravel_index(speeds.argmax(), speeds.shape)
    result['minimum_velocity_interval_s'] = float(intervals.min())
    result['peak_speed_pair'] = dict(times_s=[float(times[pair]), float(times[pair+1])],
        interval_s=float(intervals[pair]), patch_vertex_index=int(patch[vertex]),
        tangential_distance_m=float(np.linalg.norm(movement[pair, vertex])))
    delta = points[:, patch]-anchor[patch]
    delta -= (delta@row['up'])[..., None]*row['up']
    result['maximum_patch_anchor_error_m'] = float(np.linalg.norm(delta, axis=2).max())
    result['limits'] = dict(anchor_m=limit['anchor'], speed_m_s=limit['speed'],
                          clearance_m=row['clearance'], maximum_gap_m=row['maximum_height'])
    result['contact_limits_pass'] = bool(result['maximum_patch_anchor_error_m'] <= limit['anchor']
        and result['maximum_patch_vertex_tangential_speed_m_s'] <= limit['speed']
        and result['minimum_region_height_m'] >= row['clearance']-1e-8
        and result['maximum_lowest_region_height_m'] <= row['maximum_height'])
    return result


def run(source, candidate, draft, policy, output, base=None, frame_sampling=False):
    if type(frame_sampling) is not bool:
        raise ValueError('Explicit frame sampling Boolean required')
    paths = [Path(p).resolve() for p in (source, candidate, draft, policy)]
    source, candidate, draft, policy = paths; output = Path(output).resolve()
    base = Path(base).resolve() if base is not None else source
    inputs = {str(p): sha256(p) for p in paths+[base]}
    rig = RigAsset.load(source); reader = NativeSupportSampler(rig.document, rig.binary, 0)
    spec = read(draft); _, rows = validate(spec, rig, reader, sha256(source))
    limits = policy_rows(read(policy), source, base, draft, rows)
    # Full native geometry/clock equality is independently checked before import.
    native = measure(source, candidate, spec)
    names = [rig.document['nodes'][node].get('name') for node in rig.joints]
    if any(not isinstance(n, str) or not n for n in names) or len(set(names)) != len(names):
        raise ValueError('Unique named source joints required')
    populations = {r['id']: clocks(r) for r in rows}
    groups = [t for c in populations.values() for t in c.values()]
    frame_populations = {}
    if frame_sampling:
        import engine_contact_sampling as sampling
        frame_populations = {r['id']: sampling.frame_populations(r['stance_s']) for r in rows}
        groups.extend(p['times_s'] for c in frame_populations.values() for p in c)
    times = checked_clock(np.unique(np.concatenate(groups)), reader.duration)
    output.mkdir(parents=True, exist_ok=False)
    project = output/'project'; project.mkdir()
    (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep engine contacts"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n', encoding='utf8')
    script = ROOT/'scripts/godot_contact_audit.gd'
    shutil.copyfile(script, project/'audit.gd')
    from native_review_support import method_names
    methods = {}; archive = output/'implementation'; archive.mkdir()
    for name in sorted(set(method_names()) | {'native_engine_contacts.py', 'engine_contact_sampling.py', 'native_contact_diagnostics.py', 'native_foot_plant.py', 'godot_contact_audit.gd', 'strep.py'}):
        path = ROOT/'scripts'/name; methods[str(path)] = sha256(path); shutil.copyfile(path, archive/name)
    cases = []
    for label, path in (('source', source), ('candidate', candidate)):
        shutil.copyfile(path, output/(label+'.glb'))
        cases.append(dict(id=label, path=str(output/(label+'.glb')), sample_times_s=times.tolist()))
    shutil.copyfile(draft, output/'draft.json'); shutil.copyfile(policy, output/'plant-policy.json')
    shutil.copyfile(base, output/'base.glb')
    request=dict(cases=cases, inputs_sha256=inputs, methods_sha256=methods)
    if frame_sampling:
        request.update(frame_sampling_contract=sampling.contract(),frame_sampling_contract_sha256=sampling.contract_sha256())
    save(output/'request.json', request)
    save(output/'pipeline.json', dict(status='processing', started_at=now()))
    engine = ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    try:
        with (output/'engine.log').open('w', encoding='utf8') as log:
            completed = subprocess.run([str(engine), '--headless', '--path', str(project), '--script', 'audit.gd', '--',
                str(output/'request.json'), str(output/'engine-output.json')], stdout=log, stderr=subprocess.STDOUT,
                timeout=300, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if completed.returncode:
            raise ValueError('Engine contact import failed; inspect engine.log')
        actual = read(output/'engine-output.json')
        if [c['id'] for c in actual['cases']] != ['source', 'candidate']:
            raise ValueError('Engine case population changed')
        if any(c['path'] != request['path'] for c, request in zip(actual['cases'], cases)):
            raise ValueError('Engine imported a different file')
        skin = NativeSupportSkin(rig)
        source_nodes = np.array([rig.joints.index(n) for n in skin.nodes.ravel()]).reshape(skin.nodes.shape)
        source_features = features(source_nodes, packed_weights(skin.weights), skin.points, len(names), quantized=True)
        observations = []
        for case in actual['cases']:
            bindings, refs, bone_map = imported_bindings(case, names)
            world = imported_world(case, times, bone_map)
            changed = RigAsset.load(candidate if case['id'] == 'candidate' else source)
            sampler = NativeSupportSampler(changed.document, changed.binary, 0)
            expected_world = np.array([sampler.sample(float(t))[rig.joints] for t in times])
            pose_error = float(np.abs(world-expected_world).max())
            if not np.isfinite(case['duration_s']) or abs(case['duration_s']-reader.duration) > 1e-6 or case['loop_mode'] != 0 or pose_error > 1e-4:
                raise ValueError('Engine duration, non-loop playback or joint poses differ')
            supports = []
            for row in rows:
                region = foot_region(skin, rig.parents, row['chain'][-1])
                matched, error, duplicates = match_bindings(source_features[region], bindings)
                imported_points = np.einsum('tbij,vbj->tvi', world[..., :3, :], bindings[matched])
                projections = [ProjectedSkin(skin, region, axis) for axis in np.eye(3)]
                source_anchor = np.stack([p.evaluate(np.array([reader.sample(row['stance_s'][0])]))[0] for p in projections], axis=1)
                heights = source_anchor@row['up']+row['offset']
                patch = np.flatnonzero(heights <= heights.min()+.003)
                expected_points = np.stack([p.evaluate(np.array([sampler.sample(float(t)) for t in times])) for p in projections], axis=2)
                measured = {}
                for label, clock in populations[row['id']].items():
                    index = np.searchsorted(times, clock)
                    measured[label] = dict(times_s=clock.tolist(),
                        engine=contact(imported_points[index], source_anchor, row, clock, patch, limits[row['id']]),
                        native=contact(expected_points[index], source_anchor, row, clock, patch, limits[row['id']]))
                support=dict(id=row['id'], populations=measured, source_region_vertex_references=skin.vertex_references[region].tolist(),
                    source_patch_indices=patch.tolist(), imported_region_vertex_references=[refs[i] for i in matched],
                    maximum_bind_identity_error=error, binding_matches_within_tolerance=duplicates,
                    maximum_engine_native_region_position_error_m=float(np.linalg.norm(imported_points-expected_points, axis=2).max()))
                if frame_sampling:
                    indices=np.flatnonzero((times>=row['stance_s'][0])&(times<=row['stance_s'][1]))
                    thresholds=dict(anchor_m=limits[row['id']]['anchor'],speed_m_s=limits[row['id']]['speed'],
                                    clearance_m=row['clearance'],maximum_gap_m=row['maximum_height'])
                    support['frame_sampling']=dict(engine=sampling.evaluate(imported_points,source_anchor,row['up'],row['offset'],patch,
                        indices,frame_populations[row['id']],times,thresholds),
                        native=sampling.evaluate(expected_points,source_anchor,row['up'],row['offset'],patch,
                        indices,frame_populations[row['id']],times,thresholds))
                supports.append(support)
            observation=dict(id=case['id'], samples=len(times), bones=len(names), imported_surfaces=len(case['meshes']),
                maximum_pose_element_error=pose_error, supports=supports,
                contact_samples_pass=all(s['populations']['stance_120hz']['engine']['contact_limits_pass'] for s in supports))
            if frame_sampling:
                observation['game_frame_contact_samples_pass']=all(s['frame_sampling']['engine']['passed'] for s in supports)
                observation['all_contact_populations_pass']=bool(observation['contact_samples_pass'] and observation['game_frame_contact_samples_pass'])
            observations.append(observation)
        if any(sha256(p) != h for p, h in {**inputs, **methods}.items()):
            raise ValueError('Engine audit inputs or methods changed')
        if any(sha256(archive/Path(p).name) != h for p, h in methods.items()):
            raise ValueError('Engine archived implementation differs')
        if any(sha256(c['path']) != sha256(p) for c,p in zip(cases,(source,candidate))):
            raise ValueError('Engine input snapshots differ')
        result = dict(schema='strep-native-engine-contacts-v2' if frame_sampling else 'strep-native-engine-contacts-v1', status='complete', created_at=now(), engine=actual['engine'],
            engine_executable_sha256=sha256(engine), inputs_sha256=inputs, methods_sha256=methods, cases=observations,
            engine_output_sha256=sha256(output/'engine-output.json'),
            original_native_diagnostics=native, bind_identity_tolerance=IDENTITY_TOLERANCE,
            binding_identity_weight_encoding='Float32 multiply by 65535, unsigned-16 truncation, Float32 divide by 65535; matched independently against imported binding functions. Native metrics retain original weights; engine metrics use imported weights without normalization.',
            velocity_intervals_filtered=False,
            scope='Actual headless AnimationPlayer world joint samples and imported vertex/bind/weight data, independent CPU linear skin reconstruction. Original 120Hz stance contact gate and separate native-key population. No GPU, physics, angular-cap, continuous-collision or human quality approval.',
            gpu_skin_verified=False, full_support_gates_verified=False, quality_approved=False, release_approved=False)
        if frame_sampling:
            result.update(frame_sampling_contract=sampling.contract(),frame_sampling_contract_sha256=sampling.contract_sha256(),
                          original_contact_population_replaced=False)
        save(output/'result.json', result); save(output/'pipeline.json', dict(status='complete')); return result
    except Exception as exc:
        save(output/'pipeline.json', dict(status='failed', error=str(exc))); raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'candidate', 'draft', 'policy', 'output'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--base', type=Path, help='Unchanged base asset bound by the policy; defaults to source')
    parser.add_argument('--frame-sampling', action='store_true', help='Also audit all fixed 30/60/120Hz quarter-phase populations; preserve original result')
    args = parser.parse_args()
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    with worker_lock(), threadpool_limits(limits=1):
        result = run(args.source, args.candidate, args.draft, args.policy, args.output, base=args.base, frame_sampling=args.frame_sampling)
        print([(c['id'], c['contact_samples_pass'], c.get('game_frame_contact_samples_pass')) for c in result['cases']])
