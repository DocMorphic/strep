"""Separate exported-geometry and engine audit of authored-root candidates."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from threadpoolctl import threadpool_limits
from strep import read, save, sha256, now
from rig_asset import RigAsset, array
from rig_clip_import import AnimationSampler
from audit_authoring_intent import check_files, same_rig
from run_godot_rig_import import run as import_engine


def samples(path, frames):
    rig = RigAsset.load(path)
    sampler = AnimationSampler(rig.document, rig.binary, 0)
    if abs(sampler.duration-(frames-1)/30) > 1e-5:
        raise ValueError('Unexpected clip duration')
    transforms = np.asarray([sampler.sample(float(np.float32(i/60))) for i in range(frames*2-1)])
    return rig, transforms


def preserved_channels(source, candidate, root):
    a, b = source.document['animations'][0], candidate.document['animations'][0]
    if len(a['channels']) != len(b['channels']):
        return False
    for x, y in zip(a['channels'], b['channels']):
        if x['target'] != y['target']:
            return False
        first, second = a['samplers'][x['sampler']], b['samplers'][y['sampler']]
        if first.get('interpolation', 'LINEAR') != second.get('interpolation', 'LINEAR'):
            return False
        keys = ['input'] if x['target'] == dict(node=root, path='translation') else ['input', 'output']
        for key in keys:
            if not np.array_equal(array(source.document, source.binary, first[key]), array(candidate.document, candidate.binary, second[key])):
                return False
    return True


def inspect(source, candidate, original, recipe, frames, policy):
    rig, before = samples(source, frames)
    other, after = samples(candidate, frames)
    _, raw = samples(original, frames)
    same_rig(rig, other)
    spec = read(recipe)
    if sha256(original) != spec['glb_sha256'] or (spec['frames'], spec['fps']) != (frames, 30):
        raise ValueError('Original authored recipe clock/binding changed')
    root = spec['root_node']
    positions = before[::2, root, :3, 3]
    new_positions = after[::2, root, :3, 3]
    edit = new_positions-raw[::2, root, :3, 3]
    delta = new_positions-positions
    a0 = np.linalg.norm(np.diff(positions, n=2, axis=0), axis=1)*900
    a1 = np.linalg.norm(np.diff(new_positions, n=2, axis=0), axis=1)*900
    points0 = np.array([rig.vertices(w) for w in before])
    points1 = np.array([other.vertices(w) for w in after])
    floor_delta = float(np.max(np.clip(-points1[:, :, 1], 0, None)-np.clip(-points0[:, :, 1], 0, None)))
    contacts = []
    for c in spec['contacts']:
        ids = spec['patches'][c['patch']]['vertices']
        start, end = c['start_frame'], c['end_frame_exclusive']
        old = np.mean(points0[2*start:2*end:2, ids], axis=1)
        new = np.mean(points1[2*start:2*end:2, ids], axis=1)
        error0, error1 = [np.linalg.norm(t-c['target_position_m'], axis=1) for t in (old, new)]
        edge0, edge1 = [np.linalg.norm(np.diff(t, axis=0), axis=1) for t in (old, new)]
        contacts.append(dict(patch=c['patch'], error_excess_m=float((error1-error0).max()),
            edge_excess_m=float((edge1-edge0).max()) if len(edge1) else 0.,
            error_before_m=float(error0.max()), error_after_m=float(error1.max())))
    eps, lim = policy['position_tolerance_m'], spec['limits']
    checks = dict(channels=preserved_channels(rig, other, root),
        world_rotations_exact=bool(np.array_equal(before[:, :, :3, :3], after[:, :, :3, :3])),
        root_horizontal=float(np.max(np.linalg.norm(edit[:, [0, 2]], axis=1))) <= lim['root_horizontal_m']+eps,
        root_vertical=float(np.max(np.abs(edit[:, 1]))) <= lim['root_vertical_m']+eps,
        root_edit_step=float(np.max(np.linalg.norm(np.diff(edit, axis=0), axis=1))) <= lim['root_step_m']+2*eps,
        root_radius=float(np.max(np.linalg.norm(delta, axis=1))) <= policy['root_correction_radius_m']+eps,
        endpoints=float(np.max(np.abs(delta[[0, 1, -2, -1]]))) <= eps,
        root_acceleration=float(np.max(a1-a0)) <= policy['acceleration_tolerance_m_s2'],
        floor=floor_delta <= eps,
        targets=all(c['error_excess_m'] <= eps for c in contacts),
        contact_edges=all(c['edge_excess_m'] <= eps for c in contacts),
        objective=float(a1@a1) < float(a0@a0)-max(policy['minimum_energy_improvement'],
            policy.get('minimum_relative_energy_improvement',0.)*float(a0@a0)))
    patch_dynamics = []
    if policy.get('preserve_patch_acceleration', False):
        for name, patch in spec['patches'].items():
            ids = patch['vertices']
            old_centers, new_centers = [p[::2, ids].mean(axis=1) for p in (points0, points1)]
            old_acc, new_acc = [np.linalg.norm((p[2:]-2*p[1:-1]+p[:-2])*900, axis=1) for p in (old_centers, new_centers)]
            patch_dynamics.append(dict(patch=name, source_peak_m_s2=float(old_acc.max()), candidate_peak_m_s2=float(new_acc.max()),
                source_p95_m_s2=float(np.percentile(old_acc, 95)), candidate_p95_m_s2=float(np.percentile(new_acc, 95)),
                frame_cap_excess_m_s2=float(np.max(new_acc-old_acc))))
        checks['whole_clip_patch_acceleration'] = all(p['frame_cap_excess_m_s2'] <= policy['acceleration_tolerance_m_s2'] for p in patch_dynamics)
    return dict(checks={k: bool(v) for k, v in checks.items()}, all_checks_passed=all(checks.values()),
        source_sha256=sha256(source), candidate_sha256=sha256(candidate),
        root_peak_before_m_s2=float(a0.max()), root_peak_after_m_s2=float(a1.max()),
        root_p95_before_m_s2=float(np.percentile(a0, 95)), root_p95_after_m_s2=float(np.percentile(a1, 95)),
        energy_before=float(a0@a0), energy_after=float(a1@a1), floor_cap_excess_m=floor_delta,
        source_floor_depth_m=float(np.maximum(-points0[:, :, 1], 0).max()),
        candidate_floor_depth_m=float(np.maximum(-points1[:, :, 1], 0).max()),
        contacts=contacts, patch_dynamics=patch_dynamics, quality_approved=False)


def run(study, output):
    if output.exists():
        raise ValueError('Preserve previous verification')
    request, complete = read(study/'request.json'), read(study/'completion.json')
    if complete['request_sha256'] != sha256(study/'request.json'):
        raise ValueError('Protocol changed')
    check_files(study, complete['files'])
    if [c['id'] for c in request['cases']] != [r['id'] for r in complete['rows']]:
        raise ValueError('Population changed')
    output.mkdir(parents=True)
    rows, engine_cases = [], []
    with threadpool_limits(limits=1):
        for case, result in zip(request['cases'], complete['rows']):
            folder = Path(request['jobs'])/case['id']
            check_files(folder, case['files'])
            old = read(folder/'result.json')
            frames = old['frames']
            source = folder/case['candidate']/'character.glb'
            record = dict(id=case['id'], status=result['status'],
                          original_status={k: old.get(k) for k in ('correction_status', 'joint_edit_status', 'human_approved')})
            selected = source
            if result['status'] == 'candidate_preserved':
                selected = Path(result['selected'])
                if selected.resolve().parent != (study/case['id']).resolve() or sha256(selected) != result['selected_sha256']:
                    raise ValueError('Selected candidate binding changed')
                audit = inspect(source, selected, folder/case['source']/'character.glb', folder/'contact-spec.json', frames, request['policy'])
                record['audit'] = audit
                if not audit['all_checks_passed']:
                    raise ValueError('Selected candidate failed independent preservation: '+case['id'])
            elif result['status'] not in ('no_accepted_candidate', 'no_solver_proposal', 'fixed_body_noop', 'failed'):
                raise ValueError('Unknown selection state')
            if result['status'] != 'failed':
                engine_cases.append(dict(id=case['id'], path=str(selected), sha256=sha256(selected), frames=frames, fps=30, sample_by_time=True))
            rows.append(record)
            save(output/(case['id']+'.json'), record)
            print(case['id'], result['status'], flush=True)
    save(output/'manifest.json', dict(cases=engine_cases))
    import_engine(output, output/'engine')
    engine = read(output/'engine/verification.json')
    if [r['id'] for r in engine['checks']] != [r['id'] for r in engine_cases]:
        raise ValueError('Engine population mismatch')
    check_files(study, complete['files'])
    save(output/'completion.json', dict(at=now(), study_completion_sha256=sha256(study/'completion.json'),
        implementation_sha256=sha256(__file__), engine_verification_sha256=sha256(output/'engine/verification.json'),
        cases=rows, engine_actor_frames=sum(c['frames'] for c in engine_cases),
        preserved_candidates=sum(r['status']=='candidate_preserved' for r in rows),
        quality_approved=False, scope='Separate exported key/midpoint geometry, channel, target and root audit plus all-frame Godot import of selected outcomes. Inherited failures and original statuses remain.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    run(args.study.resolve(), args.output.resolve())
