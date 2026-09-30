"""Compare affine fitting limits without exporting or approving any animation."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now
from coupled_pair_proposal import solve


KINDS = ('edit', 'speed', 'acceleration', 'angular_speed', 'angular_acceleration', 'surface_distance')


def constraint_population(linear):
    inside = linear['gaps'] < 0
    return dict(
        vectors=np.concatenate([linear['vectors'], linear['surface_vectors'][inside]]),
        jacobians=np.concatenate([linear['jacobians'], linear['surface_jacobians'][inside]]),
        radii=np.r_[linear['radii'], linear['depth_caps'][inside]],
        kinds=np.r_[linear['kinds'], np.full(inside.sum(), 'surface_distance')],
        tolerances=np.r_[np.where(linear['kinds'] == 'edit', 1e-8, 1e-6), np.full(inside.sum(), 1e-8)])


def trust_only_bound(gaps, jacobian, trust):
    """Necessary affine peak floor from independent 3-vector control balls.

    Each row is allowed its own best direction, ignoring every other constraint.
    This optimistic floor is not an achievable motion or a nonlinear certificate.
    """
    maximum_gain = trust*np.linalg.norm(jacobian.reshape(len(gaps), -1, 3), axis=2).sum(axis=1)
    floors = np.maximum(-gaps-maximum_gain, 0)
    limiting = int(np.argmax(floors))
    return dict(peak_floor_m=float(floors[limiting]), limiting_row=limiting,
                row_maximum_gain_m=float(maximum_gain[limiting]))


def original_checks(linear, population, step, trust):
    norms = np.linalg.norm(population['vectors']+np.einsum('nid,d->ni', population['jacobians'], step), axis=1)
    excess = norms-population['radii']
    groups = {}
    for kind in KINDS:
        mask = population['kinds'] == kind
        groups[kind] = dict(rows=int(mask.sum()), failures=int((excess[mask] > population['tolerances'][mask]).sum()),
            maximum_excess=float(max(0., excess[mask].max(initial=0))))
    gaps = linear['gaps']+linear['gap_jacobian']@step
    return dict(groups=groups, predicted_peak_m=float(np.maximum(-gaps, 0).max()),
        maximum_depth_cap_excess_m=float(np.maximum(-gaps-linear['depth_caps'], 0).max()),
        maximum_control_degrees=float(np.rad2deg(np.linalg.norm(step.reshape(-1, 3), axis=1).max())),
        original_trust_excess_radians=float(max(0., np.linalg.norm(step.reshape(-1, 3), axis=1).max()-trust)))


def load_bound_study(study):
    result = read(study/'result.json'); request = read(study/'request.json')
    if result['status'] != 'complete': raise ValueError('Completed immutable study required')
    files = {}
    for name in ['request.json', 'source-index.json', 'linearization.npz', 'solver.json']:
        key = name.split('.')[0].replace('-', '_')+'_sha256'
        if sha256(study/name) != result[key]: raise ValueError('Study evidence changed: '+name)
        files[str(study/name)] = result[key]
    files[str(study/'result.json')] = sha256(study/'result.json')
    for name, digest in read(study/'source-index.json').items():
        path = (study/'source'/name).resolve()
        if path.parent != (study/'source').resolve() or sha256(path) != digest:
            raise ValueError('Source witness changed')
        files[str(path)] = digest
    for name, digest in request['implementation'].items():
        path = (study/'implementation'/name).resolve()
        if path.parent != (study/'implementation').resolve() or sha256(path) != digest:
            raise ValueError('Study implementation snapshot changed')
        files[str(path)] = digest
    for name in ['coupled_pair_proposal.py', 'conic_root_descent.py']:
        if sha256(ROOT/'scripts'/name) != request['implementation'][name]:
            raise ValueError('Diagnostic solver differs from study')
    for name, digest in request['inputs'].items():
        if sha256(name) != digest: raise ValueError('Study input changed')
        files[name] = digest
    with np.load(study/'linearization.npz', allow_pickle=False) as data:
        linear = dict(data)
    return request, linear, files


def variants_for(profile):
    if profile == 'angular-limits':
        positional = ['speed', 'acceleration']; angular = ['angular_speed', 'angular_acceleration']
        specifications = [
            ('original', 1., [], True),
            ('tenfold_trust', 10., [], True),
            ('without_angular', 1., angular, True),
            ('without_positional', 1., positional, True),
            ('without_all_motion', 1., positional+angular, True),
            ('without_surface_distance', 1., ['surface_distance'], True),
            ('without_local_surface_caps', 1., ['surface_distance'], False),
            ('trust_and_edit_only', 1., positional+angular+['surface_distance'], False)]
        return [dict(name=n, trust_multiplier=t, omitted_norm_kinds=k, per_time_caps=c, regularizer=1e-4) for n,t,k,c in specifications]
    if profile == 'norms':
        specifications = [('original', 1., ()), ('double_trust', 2., ()), ('tenfold_trust', 10., ()),
            ('without_speed', 1., ('speed',)), ('without_acceleration', 1., ('acceleration',)),
            ('without_motion', 1., ('speed', 'acceleration')),
            ('without_surface_distance', 1., ('surface_distance',)),
            ('without_motion_or_surface_distance', 1., ('speed', 'acceleration', 'surface_distance'))]
        return [dict(name=n, trust_multiplier=t, omitted_norm_kinds=list(k), per_time_caps=True, regularizer=1e-4) for n, t, k in specifications]
    if profile == 'surface-caps':
        return [
            dict(name='original', omitted_norm_kinds=[], per_time_caps=True, regularizer=1e-4),
            dict(name='smaller_regularizer', omitted_norm_kinds=[], per_time_caps=True, regularizer=1e-8),
            dict(name='global_scalar_cap', omitted_norm_kinds=[], per_time_caps=False, regularizer=1e-4),
            dict(name='without_local_surface_caps', omitted_norm_kinds=['surface_distance'], per_time_caps=False, regularizer=1e-4),
            dict(name='trust_and_edit_only', omitted_norm_kinds=['surface_distance', 'speed', 'acceleration'], per_time_caps=False, regularizer=1e-4)]
    raise ValueError('Unknown diagnostic profile')


def run(study, output, profile='norms'):
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh diagnostic destination required')
    request, linear, files = load_bound_study(study)
    if profile == 'angular-limits' and not {'angular_speed','angular_acceleration'} <= set(linear['kinds']):
        raise ValueError('Matched angular constraint population required')
    original_trust = np.deg2rad(request['trust_degrees']); population = constraint_population(linear)
    variants = variants_for(profile)
    output.mkdir(); (output/'implementation').mkdir()
    methods = {}
    for name in ['diagnose_scene_pair_limits.py', 'coupled_pair_proposal.py', 'conic_root_descent.py', 'strep.py']:
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
        methods[name] = sha256(output/'implementation'/name)
    save(output/'request.json', dict(at=now(), study=str(study), inputs=files, implementation=methods,
        profile=profile, variants=variants,
        scope='Affine constraint ablation only. Omitted limits remain mandatory for real acceptance. No export, geometry approval or new motion.', quality_approved=False))
    rows = []
    for variant in variants:
        name, multiplier, omitted = variant['name'], variant.get('trust_multiplier', 1.), variant['omitted_norm_kinds']
        mask = ~np.isin(population['kinds'], omitted); trust = original_trust*multiplier
        # The global cap is redundant for a peak-improving solution. It deliberately
        # removes per-time protection only in this diagnostic, never in a clip fit.
        caps = linear['depth_caps'] if variant['per_time_caps'] else np.full_like(linear['depth_caps'], np.maximum(-linear['gaps'], 0).max())
        step, solver = solve(gaps=linear['gaps'], gap_jacobian=linear['gap_jacobian'], depth_caps=caps,
            **{k: population[k][mask] for k in ['vectors', 'jacobians', 'radii']},
            trust=trust, regularizer=variant['regularizer'], norm_tolerances=population['tolerances'][mask])
        row = dict(**variant, trust_degrees=float(np.rad2deg(trust)), solver=solver,
            trust_only_bound=trust_only_bound(linear['gaps'], linear['gap_jacobian'], trust),
            step=None if step is None else step.tolist(), original_checks=None if step is None else original_checks(linear, population, step, original_trust),
            quality_approved=False)
        if name == 'original':
            saved = read(study/'solver.json')['step']
            if step is None or saved is None: raise ValueError('Passing baseline required for matched comparison')
            row['baseline_maximum_control_difference_radians'] = float(np.abs(step-np.asarray(saved)).max())
            np.testing.assert_allclose(step, saved, atol=1e-10, rtol=0)
        rows.append(row); save(output/'variants.json', rows)
        print(dict(name=name, status=solver['status'], proposed=step is not None,
            predicted_peak_mm=solver['predicted_peak_m']*1000), flush=True)
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Input changed during diagnosis')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Diagnostic method changed')
    save(output/'result.json', dict(at=now(), status='complete', variants=len(rows),
        request_sha256=sha256(output/'request.json'), variants_sha256=sha256(output/'variants.json'), quality_approved=False))


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--profile', choices=['norms', 'surface-caps', 'angular-limits'], default='norms')
    args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(args.study, args.output, args.profile)
