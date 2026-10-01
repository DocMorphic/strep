"""Standalone native support edits with preserved inputs and source-rate gates."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler as AnimationSampler
from native_support_spec import validate
from native_support_path import propose
from native_leg_floor import foot_region
from paired_approach_basis import BoundSkin
from contact_rate_path import ProjectedSkin
from elbow_swivel import descendants
from native_engine_clock import audit_clock
from paired_temporal_neighbor import rotation_channels
from sampled_motion_caps import features, measures, SampledMotionCaps
from absolute_rate_peaks import compare

SOURCE_DIR = Path(__file__).resolve().parent


def describe(source, output):
    """Expose actual joint identities/clocks for an explicit authored mapping."""
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Choose a fresh metadata file')
    digest = sha256(source); rig = RigAsset.load(source)
    if sha256(source) != digest: raise ValueError('Source changed during native description')
    if len(rig.document.get('animations', [])) != 1: raise ValueError('One chosen native animation required')
    reader = AnimationSampler(rig.document, rig.binary, 0); clocks = []; ids = {}; tracks = {}
    for node, path, times, values, mode in reader.channels:
        if path != 'rotation': continue
        clock = tuple(float(t) for t in times)
        if clock not in ids:
            ids[clock] = str(len(clocks)); clocks.append(dict(id=ids[clock], times_s=list(clock)))
        tracks[node] = dict(rotation_clock=ids[clock], interpolation=mode)
    record = dict(glb_sha256=digest, animation_index=0, duration_s=reader.duration,
        primitive_count=len(rig.primitives), clocks=clocks,
        joints=[dict(node=n, name=rig.document['nodes'][n].get('name'), parent=rig.parents[n], **tracks.get(n, {})) for n in rig.joints],
        scope='Explicitly choose the root and thigh/knee/foot roles; no anatomical mapping inferred', quality_approved=False)
    if sha256(source) != digest: raise ValueError('Source changed during native description')
    save(output, record); return record


def run(source, spec_path, output, *, joint_rates=False, joint_evaluations=80, joint_swivel=False):
    if type(joint_rates) is not bool: raise ValueError('Explicit joint-rate mode required')
    if type(joint_evaluations) is not int or not 1 <= joint_evaluations <= 2000 or not joint_rates and joint_evaluations != 80: raise ValueError('Joint-search budget requires joint-rate mode and 1–2000 evaluations')
    if type(joint_swivel) is not bool or joint_swivel and not joint_rates: raise ValueError('Knee-plane search requires joint-rate mode')
    propose_solver = propose
    if joint_rates:
        from native_support_rates import propose as joint_propose
        if joint_swivel:
            from native_support_swivel import propose as joint_propose
        from functools import partial
        propose_solver = partial(joint_propose, maximum_evaluations=joint_evaluations)
    source, spec_path, output = [Path(p).resolve() for p in (source, spec_path, output)]
    if output.exists() or output.parent != ROOT/'reports': raise ValueError('Fresh immediate reports output required')
    inputs = {str(p): sha256(p) for p in (source, spec_path)}
    rig = RigAsset.load(source); reader = AnimationSampler(rig.document, rig.binary, 0)
    if len(rig.document.get('animations', [])) != 1: raise ValueError('One chosen native animation required')
    spec = read(spec_path); mapping, rows = validate(spec, rig, reader, inputs[str(source)])
    uniform = np.arange(int(np.floor(reader.duration*120))+1)/120
    if len(uniform) < 3: raise ValueError('Clip too short for the 120Hz rate audit')
    declared = uniform.tolist()+[t for r in rows for t in r['stance_s']+r['edit_s']]
    times = audit_clock(reader.duration, [c[2] for c in reader.channels], declared, rows[0]['stance_s'][0])
    raw = np.array([reader.sample(float(t)) for t in times]); positions = np.searchsorted(times, uniform)
    caps = SampledMotionCaps(features(raw[positions], rig.joints), uniform, np.linspace(0., uniform[-1], 5))
    source_rates = measures(features(raw[positions], rig.joints), caps.dt)
    for p, digest in inputs.items():
        if sha256(p) != digest: raise ValueError('Support input changed during preparation')
    output.mkdir(); archive = output/'implementation'; archive.mkdir(); methods = {}
    names = {Path(__file__).name, 'native_support_path.py', 'native_support_spec.py', 'native_support_clock.py',
             'native_leg_smoothing.py', 'native_leg_floor.py', 'contact_rate_path.py',
             'rig_asset.py', 'rig_clip_import.py', 'paired_approach_basis.py',
             'paired_temporal_neighbor.py', 'elbow_swivel.py', 'two_bone_waypoint.py',
             'paired_guarded_temporal.py', 'gltf_tools.py', 'strep.py', 'sampled_motion_caps.py',
             'native_engine_clock.py', 'absolute_rate_peaks.py'}
    if joint_rates: names |= {'native_support_rates.py', 'timed_rotation_edit.py'}
    if joint_swivel: names.add('native_support_swivel.py')
    for name in sorted(names):
        p = SOURCE_DIR/name; methods[name] = sha256(p); shutil.copyfile(p, archive/name)
    save(output/'request.json', dict(at=now(), spec=spec, inputs=inputs, implementation=methods,
        joint_search_maximum_evaluations=joint_evaluations if joint_rates else None,
        proposal_method='joint_support_source_rate_swivel_search' if joint_swivel else 'joint_support_source_rate_search' if joint_rates else 'bounded_bend_smoothing',
        joint_swivel_limit_degrees=5. if joint_swivel else None,
        source_rate_reference='Selected input clip, full uniform 120Hz samples and four equal time bins; not a replacement for independent benchmark caps',
        rate_tolerance=caps.tolerance, excluded_derivative_tail_s=reader.duration-float(uniform[-1]),
        quality_approved=False))
    shutil.copyfile(source, output/'input.glb'); save(output/'pipeline.json', dict(status='processing'))
    nodes = sorted({n for r in rows for n in r['chain']}); old_channels = rotation_channels(rig.document, rig.binary)
    skin = BoundSkin(rig); trials = []; accepted = []
    source_supports = []
    for r in rows:
        region = foot_region(skin, rig.parents, r['chain'][-1])
        minimum = ProjectedSkin(skin, region, r['up'], r['offset']).evaluate(raw).min(axis=1)
        stance = (times >= r['stance_s'][0])&(times <= r['stance_s'][1])
        source_supports.append(dict(id=r['id'], minimum_height_m=float(minimum[stance].min()),
            maximum_lowest_height_m=float(minimum[stance].max()),
            passed=bool(minimum[stance].min() >= -1e-8 and minimum[stance].max() <= r['maximum_height'])))
    already_satisfied = all(s['passed'] for s in source_supports)
    try:
        for trial, (tau, mu) in enumerate(( (.05, .5), (.05, 5.), (.15, .5), (.15, 5.) )):
            path = output/f'trial-{trial}.glb'; report = dict(trial=trial, acceleration_time_s=tau, reference_weight_per_s2=mu)
            try:
                proposal = propose_solver(rig, reader, rows, path, tau, mu)
                exported = RigAsset.load(path); current = AnimationSampler(exported.document, exported.binary, 0)
                new_channels = rotation_channels(exported.document, exported.binary)
                assert len(current.channels) == len(reader.channels) and current.duration == reader.duration
                for old, new in zip(reader.channels, current.channels):
                    assert old[:2] == new[:2] and old[4] == new[4]; np.testing.assert_array_equal(old[2], new[2])
                    if old[1] != 'rotation' or old[0] not in nodes: np.testing.assert_array_equal(old[3], new[3])
                world = np.array([current.sample(float(t)) for t in times]); affected = np.zeros(len(rig.parents), bool)
                for r in rows: affected |= descendants(rig.parents, r['chain'][0])
                np.testing.assert_array_equal(world[:, ~affected], raw[:, ~affected])
                supports = []
                for r in rows:
                    region = foot_region(skin, rig.parents, r['chain'][-1]); projected = ProjectedSkin(skin, region, r['up'], r['offset'])
                    minimum = projected.evaluate(world).min(axis=1)
                    stance = (times >= r['stance_s'][0])&(times <= r['stance_s'][1])
                    branch = descendants(rig.parents, r['chain'][0])
                    free = np.ones(len(times), bool)
                    for interval in rows:
                        if interval['foot'] == r['foot']:
                            free &= (times <= interval['edit_s'][0])|(times >= interval['edit_s'][1])
                    np.testing.assert_array_equal(world[free][:, branch], raw[free][:, branch])
                    # Audit angles only in this interval; other disjoint edits can
                    # have their own tighter/looser bound on the same chain.
                    a, b = r['edit_keys']; angles = [float(np.rad2deg((Rotation.from_quat(old_channels[n][2][a:b+1]).inv()*Rotation.from_quat(new_channels[n][2][a:b+1])).magnitude()).max()) for n in r['chain']]
                    d = world[:, r['chain'][-1], :3, 3]-raw[:, r['chain'][-1], :3, 3]
                    in_edit = (times >= r['edit_s'][0])&(times <= r['edit_s'][1])
                    displacement = float(np.linalg.norm(d[in_edit], axis=1).max())
                    stamps = times[stance]; heights = minimum[stance]
                    audit_name = f"trial-{trial}-support-{r['id']}.json"
                    save(output/audit_name, dict(id=r['id'], times_s=stamps.tolist(), lowest_heights_m=heights.tolist()))
                    supports.append(dict(id=r['id'], samples=int(stance.sum()),
                        audit=audit_name, minimum_time_s=float(stamps[heights.argmin()]),
                        maximum_gap_time_s=float(stamps[heights.argmax()]),
                        minimum_height_m=float(minimum[stance].min()), maximum_lowest_height_m=float(minimum[stance].max()),
                        maximum_local_angles_degrees=angles, maximum_ankle_displacement_m=displacement,
                        outside_edit_world_exact=True,
                        passed=bool(minimum[stance].min() >= -1e-8 and minimum[stance].max() <= r['maximum_height']
                                    and max(angles) <= r['angle']+1e-4 and displacement <= r['displacement']+1e-7)))
                values = measures(features(world[positions], rig.joints), caps.dt)
                failed = [int(np.count_nonzero(v-c-caps.tolerance > 0)) for v, c in zip(values, caps.caps)]
                report.update(status='complete', sha256=sha256(path), proposal=proposal, supports=supports,
                              source_rate_failed_rows=failed, source_rates_pass=not any(failed),
                              support_samples_pass=all(s['passed'] for s in supports),
                              absolute_peak_comparison=compare(source_rates, values))
                if report['source_rates_pass'] and report['support_samples_pass']: accepted.append(trial)
            except ValueError as error:
                report.update(status='rejected', reason=str(error))
            trials.append(report); save(output/f'trial-{trial}.json', report)
            print({k: report[k] for k in ('trial', 'status', 'source_rate_failed_rows', 'reason') if k in report}, flush=True)
        selected = accepted[0] if accepted and not already_satisfied else None
        output_support_pass = already_satisfied or selected is not None
        shutil.copyfile(source if selected is None else output/f'trial-{selected}.glb', output/'candidate.glb')
        save(output/'support-events.json', dict(source='Explicit authored stance intervals, not measured contact force',
            target_clip_sha256=sha256(output/'candidate.glb'),
            constraint_status='satisfied_at_samples' if output_support_pass else 'unverified_on_retained_input',
            intervals=[dict(id=r['id'], foot=r['foot'], start_s=r['stance_s'][0], end_s=r['stance_s'][1]) for r in rows], quality_approved=False))
        save(output/'root-motion.json', dict(node=spec['root_node'], times_s=times.tolist(),
            positions_m=raw[:, spec['root_node'], :3, 3].tolist(),
            rotations_xyzw=Rotation.from_matrix(raw[:, spec['root_node'], :3, :3]).as_quat().tolist(),
            source_world_pose_unchanged=True,
            scope='Audit samples from unchanged source root; native source animation tracks remain in GLB'))
        for p, digest in inputs.items():
            if sha256(p) != digest: raise ValueError('Support source changed during fitting')
        if sha256(output/'input.glb') != inputs[str(source)]: raise ValueError('Frozen support input changed')
        if any(sha256(SOURCE_DIR/n) != d for n, d in methods.items()): raise ValueError('Support method changed during fitting')
        result = dict(at=now(), status='complete', selected_trial=selected, retained_input=selected is None,
            input_already_satisfied=already_satisfied, source_supports=source_supports,
            output_support_samples_pass=output_support_pass,
            retention_reason=('input_already_satisfies_support' if already_satisfied else 'no_proposal_satisfies_all_bounds') if selected is None else None,
            candidate_sha256=sha256(output/'candidate.glb'), trials=trials,
            continuous_collision_certified=False, self_collision_checked=False, engine_import_verified=False,
            human_review_submitted=False, quality_approved=False)
        result['outputs'] = {p.name: sha256(p) for p in output.iterdir() if p.is_file() and p.name != 'pipeline.json'}
        save(output/'result.json', result); save(output/'pipeline.json', dict(status='complete'))
        return result
    except Exception as error:
        save(output/'pipeline.json', dict(status='failed', reason=str(error))); raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    for name in ('spec', 'output'): parser.add_argument(name, type=Path, nargs='?')
    parser.add_argument('--describe', type=Path, help='Save joint identities and exact clocks instead of fitting')
    parser.add_argument('--joint-rates', action='store_true', help='Experimental simultaneous sampled support/source-rate search')
    parser.add_argument('--joint-evaluations', type=int, default=80, help='1–2000 evaluations per experimental joint-rate trial')
    parser.add_argument('--joint-swivel', action='store_true', help='Add bounded knee-plane freedom to joint-rate search')
    args = parser.parse_args()
    if args.describe is not None:
        if args.spec is not None or args.output is not None or args.joint_rates or args.joint_evaluations != 80 or args.joint_swivel: parser.error('Description does not use a support draft or fit output')
        describe(args.source, args.describe)
    else:
        if args.spec is None or args.output is None: parser.error('Support draft and fresh fit output required')
        from action_worker_lock import worker_lock
        from threadpoolctl import threadpool_limits
        with worker_lock(), threadpool_limits(limits=1): run(args.source, args.spec, args.output, joint_rates=args.joint_rates, joint_evaluations=args.joint_evaluations, joint_swivel=args.joint_swivel)
