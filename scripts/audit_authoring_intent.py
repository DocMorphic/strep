"""Read-only, frozen-population audit of Studio edits and their authored targets.

Dynamics are observations, never a veto on intentional animation changes.
This does not fit motion or turn old job statuses into quality approval.
"""
import argparse
import ast
import copy
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation, Slerp
from threadpoolctl import threadpool_limits
from strep import read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_transition import localize
from target_rig_contact import validate as validate_contacts
from hand_posture import validate as validate_posture

KINDS = {'contact_edit': ('transfer', 'corrected', 'contact-spec.json'),
         'joint_edit': ('input', 'transfer', 'joint-edit.json'),
         'posture_edit': ('input', 'transfer', 'hand-posture.json')}


def check_files(base, files):
    for name, digest in files.items():
        if sha256(base/name) != digest:
            raise ValueError('Frozen input changed: '+name)


def dependencies():
    root = Path(__file__).parent
    pending = [Path(__file__).name]
    found = set()
    while pending:
        name = pending.pop()
        if name in found:
            continue
        found.add(name)
        for node in ast.walk(ast.parse((root/name).read_text(encoding='utf-8-sig'))):
            modules = ([node.module] if isinstance(node, ast.ImportFrom) else
                       [a.name for a in node.names] if isinstance(node, ast.Import) else [])
            for module in modules:
                candidate = (module or '').split('.')[0]+'.py'
                if (root/candidate).is_file():
                    pending.append(candidate)
    return sorted(found)


def prepare(jobs, output):
    if output.exists():
        raise ValueError('Preserve previous audit')
    cases = []
    for file in sorted(jobs.glob('*/result.json')):
        result = read(file)
        if result.get('kind') not in KINDS:
            continue
        folder = file.parent
        if read(folder/'pipeline.json')['status'] != 'complete':
            continue
        before, after, recipe = KINDS[result['kind']]
        names = ['result.json', 'request.json', 'pipeline.json', recipe,
                 before+'/character.glb', after+'/character.glb']
        names += [p.relative_to(folder).as_posix() for p in
                  [folder/before/'report.json', folder/after/'report.json',
                   folder/'input/contact-spec.json', folder/'contact-spec.json'] if p.exists()]
        cases.append(dict(id=folder.name, kind=result['kind'], source=before,
                          candidate=after, recipe=recipe,
                          files={n: sha256(folder/n) for n in sorted(set(names))}))
    if not cases:
        raise ValueError('No completed authoring jobs')
    output.mkdir(parents=True)
    (output/'implementation').mkdir()
    implementation = {}
    for name in dependencies():
        path = Path(__file__).parent/name
        shutil.copyfile(path, output/'implementation'/name)
        implementation[name] = sha256(path)
    save(output/'request.json', dict(schema='strep-authoring-intent-audit-v1', at=now(),
         jobs=str(jobs.resolve()), cases=cases, implementation=implementation,
         scope='All completed contact, joint and posture edits present at preparation. Development jobs, not held-out motions. No solver or quality gate changes.'))
    print('Prepared', len(cases), 'jobs', flush=True)


def stats(values):
    values = np.asarray(values)
    if not values.size or not np.isfinite(values).all():
        raise ValueError('Empty or nonfinite measurement')
    return dict(max=float(values.max()), p95=float(np.percentile(values, 95)))


def rotation_error(a, b):
    relative = np.swapaxes(a, -1, -2)@b
    return np.degrees(Rotation.from_matrix(relative.reshape(-1, 3, 3)).magnitude()).reshape(relative.shape[:-2])


def same_rig(a, b):
    if a.parents != b.parents or a.joints != b.joints or len(a.primitives) != len(b.primitives):
        raise ValueError('Rig topology changed')
    if not np.array_equal(a.inverse, b.inverse):
        raise ValueError('Inverse bind matrices changed')
    for first, second in zip(a.primitives, b.primitives):
        if set(first) != set(second) or any(not np.array_equal(first[k], second[k]) for k in first):
            raise ValueError('Mesh geometry or skin changed')


def decode(path, frames, fps):
    rig = RigAsset.load(path)
    sampler = AnimationSampler(rig.document, rig.binary, 0)
    if frames < 3 or fps != 30 or abs(sampler.duration-(frames-1)/fps) > 1e-5:
        raise ValueError('Complete source/candidate clock mismatch')
    world = np.array([sampler.sample(float(np.float32(f/fps))) for f in range(frames)])
    if not np.isfinite(world).all():
        raise ValueError('Nonfinite decoded transform')
    return rig, world, localize(world, rig.parents)


def joint_targets(recipe, worlds):
    rows = []
    for goal in recipe['goals']:
        f, n = goal['frame'], goal['node']
        target = Rotation.from_quat(goal['rotation_xyzw']).as_matrix()
        row = dict(frame=f, node=n)
        for label, world in worlds.items():
            row[label] = dict(position_error_m=float(np.linalg.norm(world[f, n, :3, 3]-goal['position_m'])),
                              orientation_error_degrees=float(rotation_error(world[f, n, :3, :3], target)))
        rows.append(row)
    return rows


def posture_expected(local, recipe):
    """Independent quaternion interpolation of the recorded attack/hold/release."""
    expected = local.copy()
    weights = {}
    frames = np.arange(len(local))
    for pose in recipe['poses']:
        a, b, c, d = (pose[k] for k in ('start_frame', 'full_start_frame', 'full_end_frame', 'end_frame'))
        u = np.minimum(np.clip((frames-a)/(b-a), 0, 1), np.clip((d-frames)/(d-c), 0, 1))
        w = (3*u*u-2*u*u*u)*pose['strength']
        weights[pose['id']] = w
        for target in pose['targets']:
            n = target['node']
            for f in np.flatnonzero(w):
                endpoints = Rotation.from_quat([Rotation.from_matrix(local[f, n, :3, :3]).as_quat(), target['rotation_xyzw']])
                expected[f, n, :3, :3] = Slerp([0, 1], endpoints)(float(w[f])).as_matrix()
    return expected, weights


def contact_targets(spec, rigs, worlds, source_hash, frames, fps):
    if spec['glb_sha256'] != source_hash or (spec['frames'], spec['fps']) != (frames, fps):
        raise ValueError('Authored contact target binding/clock mismatch')
    validate_contacts(spec, rigs['source'])
    rows = []
    for index, contact in enumerate(spec['contacts']):
        a, b = contact['start_frame'], contact['end_frame_exclusive']
        ids = spec['patches'][contact['patch']]['vertices']
        row = dict(index=index, **contact)
        for label, world in worlds.items():
            track = np.array([rigs[label].vertices(world[f])[ids].mean(axis=0) for f in range(a, b)])
            error = np.linalg.norm(track-contact['target_position_m'], axis=1)
            row[label] = dict(error_m=stats(error), failed_frames=int(np.sum(error > spec['screen']['contact_error_m'])),
                              worst_frame=int(a+error.argmax()))
        rows.append(row)
    return dict(screen=spec['screen'], intervals=rows, scope='Original authored world centroid targets at integer samples; not contact inference or continuous geometry validation.')


def audit_case(folder, case):
    check_files(folder, case['files'])
    result, request = read(folder/'result.json'), read(folder/'request.json')
    frames, fps, root = result['frames'], result['fps'], result['root_node']
    rigs, worlds, locals_ = {}, {}, {}
    hashes = {}
    for label, variant in [('source', case['source']), ('candidate', case['candidate'])]:
        path = folder/variant/'character.glb'
        hashes[label] = sha256(path)
        if hashes[label] != result['variants'][variant]['sha256']:
            raise ValueError('Result GLB binding mismatch')
        rigs[label], worlds[label], locals_[label] = decode(path, frames, fps)
    if hashes['source'] != request['input_glb_sha256']:
        raise ValueError('Edit parent binding mismatch')
    same_rig(rigs['source'], rigs['candidate'])
    if root not in rigs['source'].joints:
        raise ValueError('Invalid mapped root')
    recipe = read(folder/case['recipe'])
    kind = case['kind']
    if request['kind'] != kind or result['kind'] != kind:
        raise ValueError('Job kind mismatch')
    expected_hash = (request['authored_spec_sha256'] if kind == 'contact_edit' else
                     request['input_files']['joint-edit.json'] if kind == 'joint_edit' else request['posture_sha256'])
    if sha256(folder/case['recipe']) != expected_hash:
        raise ValueError('Authored recipe binding mismatch')
    targeted = set()
    intent = {}
    if kind == 'joint_edit':
        if recipe['glb_sha256'] != hashes['source']:
            raise ValueError('Joint target input changed')
        targeted = {g['node'] for g in recipe['goals']}
        intent['joint_targets'] = joint_targets(recipe, worlds)
    elif kind == 'posture_edit':
        targeted = set(validate_posture(recipe, rigs['source'], hashes['source']))
        if (recipe['frames'], recipe['fps']) != (frames, fps):
            raise ValueError('Posture clock mismatch')
        expected, weights = posture_expected(locals_['source'], recipe)
        selected = sorted(targeted)
        others = [n for n in range(len(rigs['source'].parents)) if n not in targeted]
        frozen = ~np.any(np.stack(list(weights.values())) > 0, axis=0)
        intent['posture'] = dict(target_nodes=selected,
            blended_target_error_degrees=stats(rotation_error(expected[:, selected, :3, :3], locals_['candidate'][:, selected, :3, :3])),
            unedited_local_max_matrix_error=float(np.abs(locals_['source'][:, others]-locals_['candidate'][:, others]).max()),
            frozen_world_max_matrix_error=float(np.abs(worlds['source'][frozen]-worlds['candidate'][frozen]).max()),
            translations_max_error_m=float(np.abs(locals_['source'][:, :, :3, 3]-locals_['candidate'][:, :, :3, 3]).max()))
    spec_path = folder/'contact-spec.json' if kind == 'contact_edit' else folder/'input/contact-spec.json'
    if spec_path.exists():
        spec = read(spec_path)
        # Retained input specs may name an ancestor version: preserve and report
        # that fact, without silently rebinding an unverified recipe.
        if spec['glb_sha256'] != hashes['source']:
            intent['contacts'] = dict(status='binding_mismatch', authored_sha256=spec['glb_sha256'], source_sha256=hashes['source'])
        else:
            intent['contacts'] = contact_targets(spec, rigs, worlds, hashes['source'], frames, fps)
    dynamics = []
    for n in rigs['source'].joints:
        row = dict(node=n, label=rigs['source'].document['nodes'][n].get('name', str(n)), directly_targeted=n in targeted)
        for label, local in locals_.items():
            row[label] = stats(rotation_error(local[:-1, n, :3, :3], local[1:, n, :3, :3]))
        row['peak_change_degrees_per_frame'] = row['candidate']['max']-row['source']['max']
        row['p95_change_degrees_per_frame'] = row['candidate']['p95']-row['source']['p95']
        dynamics.append(row)
    root_dynamics = {label: stats(np.linalg.norm(np.diff(world[:, root, :3, 3], n=2, axis=0)*fps**2, axis=1))
                     for label, world in worlds.items()}
    check_files(folder, case['files'])
    return dict(id=case['id'], kind=kind, status='measured', frames=frames, fps=fps, glb_sha256=hashes,
        original_status={key: result.get(key) for key in ('correction_status', 'joint_edit_status', 'human_approved')},
        intent=intent, joint_step_degrees=dynamics, root_acceleration_m_s2=root_dynamics,
        generic_research_chain_ready=False,
        integration_requirement='Carry authored targets and protected motion into correction constraints, then independently audit exported targets and original screens. Angular increases alone do not reject intentional edits.',
        quality_approved=False)


def run(output):
    request = read(output/'request.json')
    if (output/'completion.json').exists():
        raise ValueError('Preserve completed audit')
    check_files(Path(__file__).parent, request['implementation'])
    check_files(output/'implementation', request['implementation'])
    rows = []
    with threadpool_limits(limits=1):
        for case in request['cases']:
            try:
                row = audit_case(Path(request['jobs'])/case['id'], case)
            except Exception as error:
                row = dict(id=case['id'], kind=case['kind'], status='audit_failed', error=str(error), quality_approved=False)
            rows.append(row)
            save(output/(case['id']+'.json'), row)
            print(case['id'], row['status'], row.get('error', ''), flush=True)
    check_files(Path(__file__).parent, request['implementation'])
    save(output/'completion.json', dict(at=now(), request_sha256=sha256(output/'request.json'),
        population=len(rows), measured=sum(r['status']=='measured' for r in rows),
        failed=[r['id'] for r in rows if r['status']!='measured'],
        files={r['id']+'.json': sha256(output/(r['id']+'.json')) for r in rows}, quality_approved=False,
        scope='Fresh exported integer-frame measurements. All frozen jobs retained including failures. No new engine import, human evidence, physiological limits or quality promotion.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'run'])
    parser.add_argument('output', type=Path)
    parser.add_argument('--jobs', type=Path, default=Path('reports/rig-jobs'))
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.jobs.resolve(), args.output.resolve())
    else:
        run(args.output.resolve())
