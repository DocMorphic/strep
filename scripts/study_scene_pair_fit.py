"""Fit a prepared two-actor scene, retaining exported failures and mesh evidence."""
import argparse
from pathlib import Path
import shutil
import time
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now
from scene_pair_problem import load_actors, ScenePairProblem
from build_guarded_pair_witnesses import query
from convex_partner_surface import penetration
from coupled_pair_proposal import solve
from rig_clip_import import AnimationSampler
from rig_asset import RigAsset
from paired_temporal_neighbor import rotation_channels

METHODS = ['study_scene_pair_fit.py', 'scene_pair_problem.py', 'timed_rotation_edit.py',
    'build_guarded_pair_witnesses.py', 'convex_partner_surface.py', 'coupled_pair_proposal.py',
    'coupled_surface_norms.py', 'paired_surface_witness.py', 'paired_approach_basis.py',
    'paired_guarded_temporal.py', 'paired_temporal_neighbor.py', 'rig_clip_import.py', 'rig_asset.py',
    'gltf_tools.py', 'conic_root_descent.py', 'strep.py']


def source_samples(actors, output):
    rows = []
    for index, stamp in enumerate(actors[0]['model'].times):
        points = [a['rig'].vertices(a['model'].source_world[index])@a['rotation'].T+a['translation'] for a in actors]
        directions = [dict(source=s, target=t, **query(points[s], points[t], actors[t]['faces'])) for s, t in [(0, 1), (1, 0)]]
        row = dict(sample=index, time_s=float(stamp), directions=directions,
                   floor_depth_m=[max(0., -float(p[:, 1].min())) for p in points])
        rows.append(row); save(output/f'sample-{index:03d}.json', row)
        save(output.parent/'progress.json', dict(status='source_geometry', completed=index+1, total=len(actors[0]['model'].times)))
        if (index+1) % 10 == 0:
            print(dict(status='source_geometry', completed=index+1), flush=True)
    return rows


def exported_motion(problem, controls, folder):
    folder.mkdir(); records = []; worlds = []
    for index, (actor, part) in enumerate(zip(problem.actors, problem.split(controls))):
        model = actor['model']; path = folder/f'actor-{index}.glb'
        model.export(part, path); rig = RigAsset.load(path); sampler = AnimationSampler(rig.document, rig.binary, 0)
        world = np.array([sampler.sample(t) for t in model.times]); worlds.append(world)
        rates, _ = actor['rates'].values(world); excess = np.linalg.norm(rates, axis=1)-actor['rates'].radii
        original = rotation_channels(model.document, model.binary); edited = rotation_channels(rig.document, rig.binary)
        max_edit = 0.; frozen_keys = 0
        for node, (_, clock, q) in original.items():
            np.testing.assert_array_equal(edited[node][1], clock)
            entry = next((e for e in model.entries if e['node'] == node), None)
            frozen = np.arange(len(clock)) if entry is None else np.setdiff1d(np.arange(len(clock)), entry['ids'])
            np.testing.assert_array_equal(edited[node][2][frozen], q[frozen]); frozen_keys += len(frozen)
            max_edit = max(max_edit, float(np.rad2deg((Rotation.from_quat(q).inv()*Rotation.from_quat(edited[node][2])).magnitude()).max()))
        # Independently decode the complete timeline, including exact protected points.
        clock = np.unique(np.r_[np.linspace(0, sampler.duration, int(np.ceil(sampler.duration*120))+1), model.protected.ravel(), model.window])
        frozen = (clock <= model.window[0]) | (clock >= model.window[1])
        for start, end in model.protected:
            frozen |= (clock >= start) & (clock <= end)
        source = AnimationSampler(model.document, model.binary, 0)
        error = max((float(np.abs(sampler.sample(t)-source.sample(t)).max()) for t in clock[frozen]), default=0.)
        records.append(dict(actor=actor['name'], path=path.name, sha256=sha256(path), maximum_edit_degrees=max_edit,
            rate_rows=len(excess), rate_failures=int((excess > 1e-5).sum()), maximum_rate_excess=float(max(0., excess.max(initial=0))),
            unchanged_quaternion_keys=frozen_keys, protected_pose_samples=int(frozen.sum()), maximum_protected_pose_error=error,
            preserved=bool(error <= 1e-12 and max_edit <= model.limit_degrees+1e-4)))
    surface = problem.surface_rows(worlds)
    original_gaps = np.concatenate([[r['gap_m'] for row in problem.samples for r in row['directions'][s]['records']] for s in [0, 1]])
    inside = original_gaps < 0
    return records, worlds, dict(maximum_cap_excess_m=float(np.maximum(-surface['gaps']-surface['depth_caps'], 0).max(initial=0)),
        maximum_bound_distance_excess_m=float(np.maximum(np.linalg.norm(surface['surface_vectors'][inside], axis=1)-surface['depth_caps'][inside], 0).max(initial=0)))


def exported_geometry(problem, worlds, folder):
    rows = []
    for source in problem.samples:
        sample = source['sample']; points = [a['rig'].vertices(w[sample])@a['rotation'].T+a['translation'] for a, w in zip(problem.actors, worlds)]
        directions = [penetration(points[s], points[t], problem.actors[t]['faces']) for s, t in [(0, 1), (1, 0)]]
        start = max(d['maximum_depth_m'] for d in source['directions']); depth = max(d['max_depth_m'] for d in directions)
        floors = [max(0., -float(p[:, 1].min())) for p in points]
        rows.append(dict(sample=sample, time_s=source['time_s'], directions=directions, source_depth_m=start, candidate_depth_m=depth,
            cap_excess_m=max(0., depth-max(.005, start)), floor_depth_m=floors,
            floor_increase_m=max(f-s for f, s in zip(floors, source['floor_depth_m']))))
        save(folder/'geometry.json', rows)
        if (sample+1) % 10 == 0:
            print(dict(status='candidate_geometry', completed=sample+1), flush=True)
    return dict(samples=len(rows), fresh_directional_queries=2*len(rows), source_peak_m=max(r['source_depth_m'] for r in rows),
        candidate_peak_m=max(r['candidate_depth_m'] for r in rows), source_failed_times=sum(r['source_depth_m'] > .005 for r in rows),
        candidate_failed_times=sum(r['candidate_depth_m'] > .005 for r in rows), maximum_cap_excess_m=max(r['cap_excess_m'] for r in rows),
        maximum_floor_increase_m=max(r['floor_increase_m'] for r in rows), geometry_sha256=sha256(folder/'geometry.json'))


def run(prepared, output):
    prepared, output = Path(prepared).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Fresh output directory required; preserve previous attempts')
    record, actors = load_actors(prepared); output.mkdir(); implementation = output/'implementation'; implementation.mkdir()
    for name in METHODS:
        shutil.copyfile(ROOT/'scripts'/name, implementation/name)
    inputs = {str(prepared/'request.json'): sha256(prepared/'request.json'), str(prepared/'state.json'): sha256(prepared/'state.json')}
    inputs.update({str(a['source']): sha256(a['source']) for a in actors})
    scene = prepared/record['scene_snapshot']['path']; inputs[str(scene)] = sha256(scene)
    bootstrap = ROOT/'reports/conic-solver-bootstrap-v1.json'; inputs[str(bootstrap)] = sha256(bootstrap)
    request = dict(at=now(), prepared_request=str(prepared/'request.json'), inputs=inputs,
        implementation={n: sha256(implementation/n) for n in METHODS}, trust_degrees=.1, factors=[1., .5, .25, .125, .0625],
        motion_tolerance=1e-5, surface_tolerance_m=1e-6, minimum_peak_improvement_m=1e-6,
        scope='One scene-derived coupled step. Complete source/candidate vertex-depth queries at the declared 120 Hz local clock, with up to 64 fitting witnesses per direction/time. No continuous collision, full-clip dynamics or naturalness certification.', quality_approved=False)
    save(output/'request.json', request); began = time.monotonic(); (output/'source').mkdir()
    samples = source_samples(actors, output/'source'); problem = ScenePairProblem(actors, samples)
    save(output/'source-index.json', {p.name: sha256(p) for p in sorted((output/'source').glob('sample-*.json'))})
    zero = np.zeros(problem.size); save(output/'progress.json', dict(status='linearizing'))
    linear = problem.linearize(zero); np.savez_compressed(output/'linearization.npz', **linear)
    extracted = np.concatenate([[r['gap_m'] for row in samples for r in row['directions'][s]['records']] for s in [0, 1]])
    np.testing.assert_allclose(linear['gaps'], extracted, atol=1e-8, rtol=0)
    # Check every row's derivative along an independent combined direction.
    direction = np.random.default_rng(1409).normal(size=problem.size)*1e-6
    worlds = [a['model'].world(p) for a, p in zip(actors, problem.split(direction))]
    moved = problem.surface_rows(worlds); derivative_error = float(np.abs(moved['gaps']-(linear['gaps']+linear['gap_jacobian']@direction)).max())
    if derivative_error > 1e-9:
        raise ValueError('Coupled scene directional derivative failed')
    inside = linear['gaps'] < 0
    step, solver = solve(**{k: linear[k] for k in ['gaps', 'gap_jacobian', 'depth_caps']},
        vectors=np.concatenate([linear['vectors'], linear['surface_vectors'][inside]]),
        jacobians=np.concatenate([linear['jacobians'], linear['surface_jacobians'][inside]]),
        radii=np.r_[linear['radii'], linear['depth_caps'][inside]], trust=np.deg2rad(request['trust_degrees']),
        norm_tolerances=np.r_[np.where(linear['kinds'] == 'edit', 1e-8, 1e-6), np.full(inside.sum(), 1e-8)])
    save(output/'solver.json', dict(solver=solver, step=None if step is None else step.tolist(), derivative_error=derivative_error))
    print(dict(status='solved', **solver), flush=True); trials = []; selected = None
    if step is not None:
        for index, factor in enumerate(request['factors']):
            folder = output/f'trial-{index}'; controls = step*factor
            records, worlds, bound = exported_motion(problem, controls, folder)
            reasons = []
            if any(r['rate_failures'] for r in records): reasons.append('exported_motion')
            if any(not r['preserved'] for r in records): reasons.append('preservation_or_budget')
            if max(bound.values()) > 1e-6: reasons.append('retained_surface_bounds')
            geometry = None
            if not reasons:
                geometry = exported_geometry(problem, worlds, folder)
                if geometry['maximum_cap_excess_m'] > 1e-6: reasons.append('fresh_surface_caps')
                if geometry['maximum_floor_increase_m'] > 1e-6: reasons.append('floor_regression')
                if geometry['source_peak_m']-geometry['candidate_peak_m'] < 1e-6: reasons.append('no_peak_improvement')
            trial = dict(factor=factor, controls=controls.tolist(), actors=records, bound=bound, geometry=geometry,
                         accepted_local_step=not reasons, reasons=reasons, quality_approved=False)
            save(folder/'review.json', trial); trials.append(dict(folder=folder.name, **trial)); save(output/'trials.json', trials)
            print(dict(factor=factor, reasons=reasons, geometry=geometry), flush=True)
            if not reasons:
                selected = folder.name; break
    cases = []
    for index, actor in enumerate(actors):
        for label, path in [('input', actor['source'])]+([(selected, output/selected/f'actor-{index}.glb')] if selected else []):
            target = output/f'{label}-actor-{index}.glb'; shutil.copyfile(path, target)
            duration = AnimationSampler(actor['rig'].document, actor['rig'].binary, 0).duration
            cases.append(dict(id=label+'-'+actor['name'], path=target.name, sha256=sha256(target), frames=int(round(duration*30))+1, fps=30, sample_by_time=True))
    save(output/'manifest.json', dict(cases=cases, quality_approved=False))
    for path, digest in inputs.items():
        if sha256(path) != digest: raise ValueError('Input changed during fitting')
    for name, digest in request['implementation'].items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Method changed during fitting')
    save(output/'result.json', dict(at=now(), status='complete', request_sha256=sha256(output/'request.json'),
        source_index_sha256=sha256(output/'source-index.json'), linearization_sha256=sha256(output/'linearization.npz'),
        solver_sha256=sha256(output/'solver.json'), manifest_sha256=sha256(output/'manifest.json'),
        trials_sha256=sha256(output/'trials.json') if trials else None, selected=selected, trials=len(trials),
        surface_rows=len(linear['gaps']), norm_rows=len(linear['radii']), elapsed_seconds=time.monotonic()-began, quality_approved=False))
    save(output/'progress.json', dict(status='complete')); print(dict(status='complete', selected=selected), flush=True)


if __name__ == '__main__':
    from threadpoolctl import threadpool_limits
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('prepared', type=Path); p.add_argument('output', type=Path); a = p.parse_args()
    with threadpool_limits(limits=1):
        run(a.prepared, a.output)
