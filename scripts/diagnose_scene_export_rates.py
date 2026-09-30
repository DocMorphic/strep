"""Separate affine, nonlinear, float32-key and decoder effects on motion limits."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now
from diagnose_scene_pair_limits import load_bound_study
from scene_pair_problem import load_actors
from angular_motion_rows import AngularMotionRows
from timed_rotation_edit import sampled_rotations
from paired_guarded_temporal import world_from_local
from rig_clip_import import AnimationSampler
from gltf_tools import read_glb


def rounded_world(model, controls):
    """Use float32 export keys with the fitter's batch sampler, before GLB replay."""
    local = model.local.copy(); keys = model.quaternions(controls, quantize=True)
    for entry in model.entries:
        node = entry['node']
        local[:, node, :3, :3] = sampled_rotations(entry['clock'], keys[node], model.times)*model.scales[node][:, None, :]
    return world_from_local(local, model.parents)


def stages_summary(stages, radii, kinds, tolerance=1e-5):
    """Compare the same immutable row population at every evaluation stage."""
    radii, kinds = np.asarray(radii), np.asarray(kinds)
    if radii.ndim != 1 or kinds.shape != radii.shape or not np.isfinite(radii).all() or np.any(radii < 0):
        raise ValueError('Finite nonnegative row caps and matching kinds required')
    if not np.isfinite(tolerance) or tolerance < 0 or not stages:
        raise ValueError('Stages and finite nonnegative tolerance required')
    summaries = {}; previous = None
    for name, value in stages.items():
        value = np.asarray(value)
        if value.shape != (len(radii), 3) or not np.isfinite(value).all():
            raise ValueError('Matching finite row vectors required')
        excess = np.linalg.norm(value, axis=1)-radii; groups = {}
        for kind in np.unique(kinds):
            mask = kinds == kind
            groups[str(kind)] = dict(rows=int(mask.sum()), failures=int((excess[mask] > tolerance).sum()),
                maximum_excess=float(max(0., excess[mask].max())),
                maximum_vector_change_from_previous=None if previous is None else float(np.linalg.norm((value-previous)[mask], axis=1).max()))
        summaries[name] = groups; previous = value
    return summaries


def run(study, output):
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh diagnostic output required')
    request, linear, files = load_bound_study(study)
    if request.get('angular_motion') is not True: raise ValueError('Angular-constrained generic fit required')
    result = read(study/'result.json'); trials_path = study/'trials.json'
    if sha256(trials_path) != result['trials_sha256']: raise ValueError('Trial evidence changed')
    files[str(trials_path)] = sha256(trials_path); trials = read(trials_path)
    methods = ['diagnose_scene_export_rates.py', 'diagnose_scene_pair_limits.py', 'scene_pair_problem.py',
        'angular_motion_rows.py', 'joint_angular_rates.py', 'timed_rotation_edit.py', 'paired_temporal_neighbor.py',
        'paired_guarded_temporal.py', 'rig_clip_import.py', 'rig_asset.py', 'gltf_tools.py', 'strep.py']
    for name in methods:
        if name in request['implementation'] and sha256(ROOT/'scripts'/name) != request['implementation'][name]:
            raise ValueError('Diagnostic dependency differs from study: '+name)
    _, actors = load_actors(Path(request['prepared_request']).parent)
    policies = [AngularMotionRows(a['model'], a['rig'].joints) for a in actors]
    # Rebuild row identities, not derivatives or caps. Original arrays are authoritative.
    positional_slices = []; cursor = 0
    for actor in actors:
        edits, _ = actor['model'].edit_rows(np.zeros(actor['model'].size)); cursor += len(edits)
        positional_slices.append(slice(cursor, cursor+len(actor['rates'].radii))); cursor += len(actor['rates'].radii)
    angular_slices = []
    for policy in policies:
        angular_slices.append(slice(cursor, cursor+len(policy.radii))); cursor += len(policy.radii)
    if cursor != len(linear['radii']): raise ValueError('Unexpected linearized row population')
    output.mkdir(); (output/'implementation').mkdir()
    for name in methods: shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    saved_methods = {n:sha256(output/'implementation'/n) for n in methods}
    protocol = dict(at=now(), study=str(study), inputs=files, implementation=saved_methods,
        tolerance=1e-5, scope='Diagnostic decomposition only; original limits unchanged, no geometry or release approval.', quality_approved=False)
    save(output/'request.json', protocol)
    reviews = []
    for trial in trials:
        control = np.asarray(trial['controls']); offset = 0; actor_records = []
        if control.shape != (sum(a['model'].size for a in actors),): raise ValueError('Control population differs')
        for index, (actor, policy, ps, ars) in enumerate(zip(actors, policies, positional_slices, angular_slices)):
            model = actor['model']; part = control[offset:offset+model.size]; offset += model.size
            ids = np.r_[np.arange(ps.start, ps.stop), np.arange(ars.start, ars.stop)]
            caps = np.r_[actor['rates'].radii, policy.radii]; kinds = np.r_[actor['rates'].kinds, policy.kinds]
            np.testing.assert_array_equal(caps, linear['radii'][ids]); np.testing.assert_array_equal(kinds, linear['kinds'][ids])
            values = lambda w: np.concatenate([actor['rates'].values(w)[0], policy.values(w)[0]])
            source = values(model.source_world); zero = values(model.world(np.zeros(model.size)))
            np.testing.assert_allclose(zero, linear['vectors'][ids], atol=1e-9, rtol=0)
            report = trial['actors'][index]; path = study/trial['folder']/report['path']
            if sha256(path) != report['sha256']: raise ValueError('Attempted export changed')
            files[str(path)] = report['sha256']
            regenerated = output/f"{trial['folder']}-actor-{index}.glb"; model.export(part, regenerated)
            if sha256(regenerated) != report['sha256']: raise ValueError('Controls do not reconstruct export')
            doc, binary = read_glb(path); sampler = AnimationSampler(doc, binary, 0)
            ideal = model.world(part); rounded = rounded_world(model, part)
            decoded = np.array([sampler.sample(t) for t in model.times])
            affine = linear['vectors'][ids]+np.einsum('nid,d->ni', linear['jacobians'][ids], control)
            stages = dict(source=source, zero_model=zero, affine=affine, nonlinear=values(ideal),
                rounded_keys=values(rounded), decoded=values(decoded))
            summary = stages_summary(stages, caps, kinds)
            positional = sum(summary['decoded'][k]['failures'] for k in ['speed', 'acceleration'])
            angular = sum(summary['decoded'][k]['failures'] for k in ['angular_speed', 'angular_acceleration'])
            if positional != report['rate_failures'] or angular != sum(v['exceeding_observations'] for v in trial['angular_rates'][index]['rates'].values()):
                raise ValueError('Diagnostic counts do not reproduce saved export review')
            worst = []
            for kind in np.unique(kinds):
                indices = np.flatnonzero(kinds == kind)
                excess = np.linalg.norm(stages['decoded'][indices], axis=1)-caps[indices]
                for row in indices[np.argsort(excess)[-5:][::-1]]:
                    worst.append(dict(kind=str(kind), row=int(row), cap=float(caps[row]),
                        excess={n:float(np.linalg.norm(v[row])-caps[row]) for n,v in stages.items()}))
            actor_records.append(dict(actor=actor['name'], stages=summary, worst_decoded_rows=worst,
                maximum_world_quantization_error=float(np.abs(rounded-ideal).max()),
                maximum_world_decoder_error=float(np.abs(decoded-rounded).max())))
        reviews.append(dict(factor=trial['factor'], actors=actor_records)); save(output/'diagnostics.json', reviews)
        print(dict(factor=trial['factor'], failures=[{n:sum(k['failures'] for k in a['stages'][n].values()) for n in ['affine', 'nonlinear', 'rounded_keys', 'decoded']} for a in actor_records]), flush=True)
    save(output/'request.json', protocol)
    for name,digest in files.items():
        if sha256(name) != digest: raise ValueError('Diagnostic evidence changed during run')
    for name,digest in saved_methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Diagnostic method changed during run')
    save(output/'result.json', dict(at=now(), status='complete', request_sha256=sha256(output/'request.json'),
        diagnostics_sha256=sha256(output/'diagnostics.json'), trials=len(reviews), quality_approved=False))


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('study', type=Path); p.add_argument('output', type=Path); a = p.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(a.study, a.output)
