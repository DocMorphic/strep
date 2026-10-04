"""Explain fixed-surface object-only conflicts from a completed imported audit."""
import argparse
from pathlib import Path
import shutil

import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT, read, save, sha256, now
from native_object_scene_surface import METHODS as AUDIT_METHODS, SCHEMA as AUDIT_SCHEMA, _bound_scene
from rigid_normal_spread import bound

SCHEMA = 'strep-rigid-contact-preflight-v1'
METHODS = AUDIT_METHODS + ('rigid_normal_spread.py', 'rigid_contact_preflight.py')
MODES = ('native-authoring', 'default-import')
# A conservative floating comparison reserve for rejection, not a change to
# the authored contact limit and not a formal interval arithmetic certificate.
COMPARISON_RESERVE_DEGREES = 1e-8


def analyze(spec, policy, observations, mode):
    """Retain every contact/time/point; only object normals share a rigid frame."""
    if mode not in MODES:
        raise ValueError('Choose an explicit imported observation mode')
    rows = spec.get('contacts')
    if not isinstance(rows, list) or not rows:
        raise ValueError('Complete authored contact population required')
    names = [r.get('id') for r in rows]
    if any(not isinstance(n, str) or not n for n in names) or len(set(names)) != len(names):
        raise ValueError('Distinct named contacts required')
    if set(policy.get('contacts', {})) != set(names):
        raise ValueError('Policy must cover every authored contact')
    limit = policy['limits']['maximum_opposition_error_degrees']
    if type(limit) not in (int, float) or not np.isfinite(limit) or not 0 <= limit <= 90:
        raise ValueError('Explicit authored opposition limit required')
    groups = {}; not_applicable = []; complete_samples = complete_points = 0
    for i, row in enumerate(rows):
        vertices = row['vertices']; reduction = row['reduction']
        if not isinstance(row.get('actor'), str) or not row['actor']:
            raise ValueError('Named source actor required')
        if (reduction not in ('individual', 'centroid') or not isinstance(vertices, list) or not vertices
                or any(not isinstance(v, list) or len(v) != 3 or any(type(x) is not int or x < 0 for x in v) for v in vertices)):
            raise ValueError('Explicit source vertex references and reduction required')
        count = 1 if reduction == 'centroid' else len(vertices)
        prefix = f'{mode}_contact_{i}_'
        clock = np.asarray(observations[prefix + 'times_s'])
        source = np.asarray(observations[prefix + 'source_normals_world'])
        available = np.asarray(observations[prefix + 'normal_available'])
        if (clock.ndim != 1 or not 1 <= len(clock) <= 20000 or not np.isfinite(clock).all()
                or np.any(np.diff(clock) <= 0) or source.shape != (len(clock), count, 3)
                or not np.isfinite(source).all() or available.shape != (len(clock), count)
                or available.dtype != bool):
            raise ValueError('Complete ordered clock, point normals and availability required')
        if np.any(abs(np.linalg.norm(source[available], axis=1) - 1) > 1e-8):
            raise ValueError('Available source normals must be unit directions')
        complete_samples += len(clock); complete_points += len(clock) * count
        target = row['target']
        if target['space'] != 'object':
            not_applicable.append(dict(contact=row['id'], target_space=target['space'], samples=len(clock), points=count,
                reason='This fixed rigid-object test does not cover world or deforming partner targets.'))
            continue
        name = target['object']
        if name not in spec['objects']:
            raise ValueError('Declared rigid target object required')
        declaration = policy['contacts'][row['id']]['target_normal']
        local = np.asarray(declaration.get('normals'), float)
        if (declaration['space'] != 'object' or local.shape != (count, 3) or not np.isfinite(local).all()
                or np.any(abs(np.linalg.norm(local, axis=1) - 1) > 1e-8)):
            raise ValueError('Complete unit target normals in one object-local frame required')
        identities = [dict(contact=row['id'], actor=row['actor'], point=k, reduction=reduction,
            source_vertices=vertices if reduction == 'centroid' else [vertices[k]]) for k in range(count)]
        groups.setdefault(name, []).append(dict(clock=clock, source=source, available=available, local=local, identities=identities))
    objects = []; incompatible = unknown = 0
    for name, contacts in groups.items():
        # Exact original clocks: do not round, interpolate, intersect clocks or
        # let non-overlapping declarations spuriously constrain one another.
        times = np.unique(np.concatenate([c['clock'] for c in contacts]))
        if len(times) > 20000:
            raise ValueError('Complete object clock exceeds 20000 times; no truncation')
        frames = []
        indices = [{float(t): i for i, t in enumerate(c['clock'])} for c in contacts]
        for time in times:
            source = []; target = []; available = []; identities = []
            for c, index in zip(contacts, indices):
                if float(time) not in index:
                    continue
                j = index[float(time)]
                source.extend(c['source'][j]); target.extend(c['local']); available.extend(c['available'][j]); identities.extend(c['identities'])
            if len(identities) > 256:
                raise ValueError('Complete active population exceeds 256 points; no truncation')
            frame = dict(time_s=float(time), active_points=len(identities), unavailable_points=int(np.count_nonzero(np.logical_not(available))),
                point_identities=identities, lower_bound_degrees=None, witness=None)
            if not all(available):
                frame['status'] = 'unknown_normal_unavailable'; unknown += 1
            else:
                report, values = bound(np.asarray(source)[None], target, limit)
                lower = report['maximum_necessary_error_degrees']
                frame['lower_bound_degrees'] = lower
                rejected = lower > limit + COMPARISON_RESERVE_DEGREES
                frame['status'] = 'incompatible_fixed_surfaces' if rejected else 'not_ruled_out'
                if len(identities) > 1:
                    a, b = values['witness_pairs'][0]
                    frame['witness'] = dict(points=[identities[a], identities[b]],
                        source_pair_degrees=float(values['source_pair_degrees'][0]),
                        target_pair_degrees=float(values['target_pair_degrees'][0]))
                incompatible += int(rejected)
            frames.append(frame)
        conflicts = [f for f in frames if f['status'] == 'incompatible_fixed_surfaces']
        objects.append(dict(object=name, samples=len(frames), incompatible_samples=len(conflicts),
            unknown_samples=sum(f['status'] == 'unknown_normal_unavailable' for f in frames), frames=frames,
            worst_conflict=max(conflicts, key=lambda f: f['lower_bound_degrees']) if conflicts else None))
    status = ('incompatible_fixed_surfaces' if incompatible else 'unknown_normal_unavailable' if unknown
              else 'not_ruled_out' if objects else 'not_applicable')
    return dict(schema=SCHEMA, status=status, mode=mode, authored_maximum_error_degrees=limit,
        comparison_reserve_degrees=COMPARISON_RESERVE_DEGREES, contacts=len(rows), contact_samples=complete_samples,
        point_normal_observations=complete_points, objects=objects, not_applicable_contacts=not_applicable,
        incompatible_object_times=incompatible, unknown_object_times=unknown,
        correction_scope='object_only_with_measured_source_surfaces_and_authored_local_target_normals_fixed',
        object_rotation_budget_relaxed_for_necessary_bound=True, source_or_target_edits_ruled_out=False,
        rotation_feasibility_proven=False, formal_interval_certificate=False, continuous_time_certified=False,
        original_selected=True, quality_approved=False, release_approved=False,
        guidance=('Review contact regions and authored normals, or plan a body/hand correction and remeasure it. '
            'An object-only refit cannot remove a reported spread conflict with these inputs fixed. '
            'No conflict found is not proof of feasible motion. Missing normals remain unknown; no point is dropped. '
            'World and partner contacts require separate checks.'))


def describe(report):
    if report['status'] == 'incompatible_fixed_surfaces':
        worst = max((o['worst_conflict'] for o in report['objects'] if o['worst_conflict']), key=lambda f: f['lower_bound_degrees'])
        ids = [p['contact'] + ':' + str(p['point']) for p in worst['witness']['points']]
        return (f"Object-only correction conflicts at {report['incompatible_object_times']} sampled object times. "
            f"At {worst['time_s']:.9g} s, {ids[0]} and {ids[1]} require a maximum opposition error "
            f"of at least {worst['lower_bound_degrees']:.6f} degrees; the authored limit is "
            f"{report['authored_maximum_error_degrees']:.6f} degrees. " + report['guidance'])
    return f"Fixed-surface object test: {report['status']}. " + report['guidance']


def run(audit_folder, output, mode='native-authoring'):
    audit_folder, output = Path(audit_folder).resolve(), Path(output).resolve()
    if mode not in MODES:
        raise ValueError('Choose an explicit imported observation mode')
    if output.exists() or output.is_relative_to(audit_folder):
        raise ValueError('Fresh preflight output outside the imported audit required')
    with worker_lock(), threadpool_limits(limits=1):
        result = read(audit_folder / 'result.json'); request = read(audit_folder / 'request.json')
        if (read(audit_folder / 'pipeline.json')['status'] != 'complete' or result['status'] != 'complete'
                or result['schema'] != AUDIT_SCHEMA or request['schema'] != AUDIT_SCHEMA):
            raise ValueError('Completed imported surface audit required')
        if output.is_relative_to(Path(request['bound_scene']).resolve()):
            raise ValueError('Preflight output must preserve the original bounded scene')
        if request['implementation_sha256'] != result['implementation_sha256']:
            raise ValueError('Imported audit method receipts differ')
        if set(result['implementation_sha256']) != set(AUDIT_METHODS):
            raise ValueError('Complete imported audit methods required')
        for name, digest in result['implementation_sha256'].items():
            if sha256(ROOT / 'scripts' / name) != digest or sha256(audit_folder / 'implementation' / name) != digest:
                raise ValueError('Imported audit method changed')
        inventory = {p.relative_to(audit_folder).as_posix() for p in audit_folder.rglob('*') if p.is_file()}
        if inventory != set(result['files_sha256']) | {'result.json', 'pipeline.json'}:
            raise ValueError('Complete imported audit inventory required')
        for name, digest in result['files_sha256'].items():
            path = (audit_folder / name).resolve()
            if not path.is_relative_to(audit_folder) or sha256(path) != digest:
                raise ValueError('Imported audit file changed or escaped output')
        if request['inputs_sha256'] != result['inputs_sha256']:
            raise ValueError('Imported audit input receipts differ')
        for path, digest in result['inputs_sha256'].items():
            if sha256(path) != digest:
                raise ValueError('Imported audit input changed')
        base_request, base_result, scene, *_ = _bound_scene(Path(request['bound_scene']))
        if (not result['original_selected'] or result['quality_approved'] is not False or result['release_approved'] is not False
                or not result['actual_imported_observations_used'] or result['loaded_skin_weights_normalized'] is not False
                or result['original_sampled_scene_conditions_pass'] != base_result['bounded_scene_conditions_pass']):
            raise ValueError('Unapproved original-retained imported observations required')
        policy = read(audit_folder / 'surface-policy.json')
        from native_surface_contact import policy_for
        digest = sha256(base_request['contacts'])
        if digest != request['contacts_sha256']:
            raise ValueError('Original contact declarations changed')
        policy_for(policy, scene, digest)
        methods = {n: sha256(ROOT / 'scripts' / n) for n in METHODS}
        inputs = {str(audit_folder / n): sha256(audit_folder / n) for n in ('result.json', 'request.json', 'pipeline.json', 'observations.npz', 'surface-policy.json')}
        inputs[str(Path(base_request['contacts']))] = digest
        with np.load(audit_folder / 'observations.npz', allow_pickle=False) as arrays:
            report = analyze(read(base_request['contacts']), policy, arrays, mode)
        for path, original in inputs.items():
            if sha256(path) != original:
                raise ValueError('Preflight input changed')
        for name, original in methods.items():
            if sha256(ROOT / 'scripts' / name) != original:
                raise ValueError('Preflight method changed')
        output.mkdir(); (output / 'implementation').mkdir()
        for name in METHODS:
            shutil.copyfile(ROOT / 'scripts' / name, output / 'implementation' / name)
            if sha256(output / 'implementation' / name) != methods[name]:
                raise ValueError('Archived preflight method differs')
        save(output / 'request.json', dict(schema=SCHEMA, at=now(), imported_audit=str(audit_folder), mode=mode,
            inputs_sha256=inputs, implementation_sha256=methods))
        report.update(at=now(), inputs_sha256=inputs, implementation_sha256=methods,
            geometry_queries_rerun=False, engine_launched=False, source_asset_edited=False,
            files_sha256={p.relative_to(output).as_posix(): sha256(p) for p in output.rglob('*') if p.is_file()})
        for path, original in inputs.items():
            if sha256(path) != original:
                raise ValueError('Preflight input changed during output publication')
        save(output / 'result.json', report)
        return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('imported_audit', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--mode', choices=MODES, default='native-authoring')
    args = parser.parse_args()
    print(describe(run(args.imported_audit, args.output, args.mode)))
