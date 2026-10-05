"""Finite local-control response experiment; never selects a retained clip.

Predict both signed coordinate stencils on all original contact/rate clocks.
Independently export/decode the baseline and up to two diagnostic candidates.
No collision, engine, anatomical, training or human-quality approval is granted.
"""
import argparse
from pathlib import Path
import shutil
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT, read, save, sha256, now
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from native_scene_fit import SceneProblem, METHODS as FIT_METHODS
from cached_contact_norms import CachedContactNorms
from cumulative_coupled_contacts import conditions
from native_contact_norms import row_regression

METHODS = sorted(set(FIT_METHODS) | {'native_contact_mask_probe.py',
    'cached_contact_norms.py', 'cumulative_coupled_contacts.py'})


def stencils(baseline, indices, step):
    baseline = np.asarray(baseline, float)
    if (baseline.ndim != 1 or not len(baseline) or not np.isfinite(baseline).all()
            or np.any(abs(baseline) > 1)):
        raise ValueError('Finite baseline within original normalized boxes required')
    if (not isinstance(indices, list) or not 1 <= len(indices) <= 24
            or any(type(i) is not int or not 0 <= i < len(baseline) for i in indices)
            or len(set(indices)) != len(indices)):
        raise ValueError('Choose 1-24 distinct explicit existing control indices')
    if type(step) not in (int, float) or not np.isfinite(step) or not 1e-6 <= step <= .005:
        raise ValueError('Explicit normalized stencil step from 1e-6 to .005 required')
    if any(abs(baseline[i]) + step > 1 for i in indices):
        raise ValueError('Both exact signed stencil steps must fit original boxes')
    result = []
    for index in indices:
        for sign in (-1, 1):
            value = baseline.copy(); value[index] += sign * step
            result.append((index, sign, value))
    return result


def run(contacts_path, permissions_path, surface_policy_path, baseline_path, output, *, indices, step):
    paths = [Path(p).resolve() for p in (contacts_path, permissions_path, surface_policy_path, baseline_path)]
    contacts_path, permissions_path, surface_policy_path, baseline_path = paths
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Fresh probe output required')
    if baseline_path.stat().st_size > 1024**2 or any(p.stat().st_size > 8*1024**2 for p in paths[:3]):
        raise ValueError('Probe input exceeds explicit complete-file budget')
    x = np.load(baseline_path, allow_pickle=False)
    proposals = stencils(x, indices, step)
    with worker_lock(), threadpool_limits(limits=1):
        inputs = {str(p): sha256(p) for p in paths}
        scene = SceneContacts(read(contacts_path), contacts_path.parent)
        inputs.update(scene.inputs)
        edits = SceneEdits(read(permissions_path), scene, inputs[str(contacts_path)],
                           rotation_storage_policy='source-scale')
        x = edits.controls(x)
        implementation = {n: sha256(ROOT/'scripts'/n) for n in METHODS}
        output.mkdir(); (output/'implementation').mkdir()
        for name in METHODS:
            shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
        save(output/'request.json', dict(schema='strep-native-contact-mask-probe-v1', at=now(),
            inputs_sha256=inputs, implementation_sha256=implementation,
            indices=indices, step=step, predicted_probes=len(proposals), maximum_decoded_candidates=2,
            rotation_storage_policy='source-scale', maximum_norm_rows=50000,
            original_selected=True, original_caps_and_contact_limits_preserved=True))
        print('Building original source caps and complete contact clocks', flush=True)
        problem = SceneProblem(scene, edits)
        contact = CachedContactNorms(problem, read(surface_policy_path), inputs[str(contacts_path)],
                                     maximum_rows=50000)
        protected = problem.protected_rows

        def measured(value, folder, *, decoded):
            folder.mkdir()
            static = {}; files = {}
            if decoded:
                for name in edits.actors:
                    path = folder/(name+'.glb'); edits.export(name, value, path)
                    static[name] = edits.audit(name, path, scene.actors[name]['animation_index'])
                    if not static[name]['passed']:
                        raise ValueError('Decoded probe violates unchanged static/track audit')
                    files[name] = path
                native, worlds = problem.decoded(files, value)
            else:
                worlds = problem.worlds(value); native = problem.constraints(value, worlds)
            surface = contact.residual(worlds)
            np.savez_compressed(folder/'conditions.npz', controls=value, native=native, surface=surface)
            report = dict(**conditions(native, surface), protected_rows=protected,
                protected_failed_rows=int((native[:protected] > 0).sum()),
                point_failed_rows=int((native[protected:] > 0).sum()),
                native_rows=len(native), surface_rows=len(surface), independently_decoded=decoded,
                static_audits=static, actor_sha256={n: sha256(p) for n, p in files.items()},
                conditions_sha256=sha256(folder/'conditions.npz'))
            save(folder/'result.json', report)
            return report, surface

        base, base_surface = measured(x, output/'baseline', decoded=True)
        predicted = []
        for k, (index, sign, value) in enumerate(proposals):
            report, surface = measured(value, output/('predicted-'+str(k)), decoded=False)
            report.update(probe=k, index=index, sign=sign,
                surface_regressed_rows=int((row_regression(base_surface, surface) > 0).sum()))
            predicted.append(report)
            save(output/'progress.json', dict(at=now(), predicted=predicted, original_selected=True))
            print('Predicted', k, index, sign, report['contact_score'],
                  'protected failures', report['protected_failed_rows'], flush=True)
        best = min(range(len(predicted)), key=lambda k: tuple(predicted[k]['contact_score']))
        selected = [best]
        eligible = [k for k, r in enumerate(predicted) if r['native_pass']]
        if eligible:
            feasible_best = min(eligible, key=lambda k: tuple(predicted[k]['contact_score']))
            if feasible_best != best:
                selected.append(feasible_best)
        decoded_reports = []
        for k in selected:
            report, surface = measured(proposals[k][2], output/('decoded-'+str(k)), decoded=True)
            report.update(probe=k, index=proposals[k][0], sign=proposals[k][1],
                surface_regressed_rows=int((row_regression(base_surface, surface) > 0).sum()))
            decoded_reports.append(report)
            print('Decoded', k, report['contact_score'], 'protected failures', report['protected_failed_rows'], flush=True)
        scene.check_inputs()
        if any(sha256(p) != h for p, h in inputs.items()) or any(sha256(ROOT/'scripts'/n) != h for n, h in implementation.items()):
            raise ValueError('Original probe inputs or methods changed during study')
        result = dict(schema='strep-native-contact-mask-probe-result-v1', at=now(), status='complete',
            baseline=base, predicted=predicted, decoded=decoded_reports,
            motion_samples=len(problem.times), contact_samples=sum(len(r['times']) for r in problem.rows),
            native_caps_rebuilt_from_candidate=False, unselected_controls_frozen=True,
            request_sha256=sha256(output/'request.json'), original_selected=True,
            collision_verified=False, engine_executed=False, anatomical_review_pending=True,
            quality_approved=False, training_admitted=False, release_approved=False,
            scope='Finite local response only. Complete original clocks and sampled caps; no full mesh/engine check, optimization or retained motion.')
        save(output/'result.json', result)
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('contacts', 'permissions', 'surface_policy', 'baseline', 'output'):
        parser.add_argument('--'+name.replace('_', '-'), required=True)
    parser.add_argument('--indices', required=True, type=int, nargs='+')
    parser.add_argument('--step', required=True, type=float)
    args = parser.parse_args()
    run(args.contacts, args.permissions, args.surface_policy, args.baseline, args.output,
        indices=args.indices, step=args.step)
