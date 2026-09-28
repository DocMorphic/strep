"""Read-only, hash-verified snapshot of a live or finished transfer study."""
import argparse
from collections import Counter
from pathlib import Path

from strep import read, save, sha256, now
from breadth_transfer_study import validate


def analyze(folder):
    folder = Path(folder).resolve()
    spec = validate(folder)
    data = read(folder / 'results.json')  # One coherent, atomically written snapshot.
    motions = {m['id']: m for m in spec['motions']}
    expected = {m['id'] + '-' + r['id'] for m in spec['motions'] for r in spec['rigs']}
    rows = data['rows']
    if len(rows) != len(expected) or {r['id'] for r in rows} != expected:
        raise ValueError('Missing, duplicate or unexpected transfer denominator')
    verified_files = 0
    for row in rows:
        if row['status'] != 'complete':
            continue
        take = folder / 'takes' / row['id']
        for name, digest in row['files'].items():
            path = (take / name).resolve()
            if not path.is_relative_to(take) or sha256(path) != digest:
                raise ValueError('Changed or invalid transfer artifact: ' + row['id'] + '/' + name)
            verified_files += 1
        if row['files'].get('character.glb') != row['result']['glb_sha256']:
            raise ValueError('Transfer mesh hash mismatch')
    engine_ids = set()
    maximum_position = maximum_basis = 0.0
    for group in data['engine_groups']:
        if group['status'] != 'complete':
            continue
        proof = read(folder / 'engine-groups' / group['motion'] / 'audit' / 'verification.json')
        if proof['checks'] != group['checks']:
            raise ValueError('Engine evidence differs from result snapshot')
        motion = motions[group['motion']]
        required = {motion['id'] + '-native': motion['native_glb_sha256']}
        required.update({r['id']: r['result']['glb_sha256'] for r in rows
                         if r['motion'] == motion['id'] and r['status'] == 'complete'})
        checks = proof['checks']
        if len(checks) != len(required) or {c['id'] for c in checks} != required.keys():
            raise ValueError('Engine clip population differs from available transfers')
        for check in checks:
            if check['id'] in engine_ids or check['source_sha256'] != required[check['id']]:
                raise ValueError('Duplicate or changed engine input')
            if check['frames'] != motion['frames'] or check['max_position_error_m'] > 1e-4 or check['max_basis_element_error'] > 1e-4:
                raise ValueError('Engine verification outside frozen tolerances')
            engine_ids.add(check['id'])
            maximum_position = max(maximum_position, check['max_position_error_m'])
            maximum_basis = max(maximum_basis, check['max_basis_element_error'])
    summaries = []
    for rig in spec['rigs']:
        selected = [r for r in rows if r['rig'] == rig['id']]
        completed = [r for r in selected if r['status'] == 'complete']
        eligible = [r for r in completed if motions[r['motion']]['flat_floor_screen_applicable']]
        combinations = Counter()
        for row in eligible:
            native = motions[row['motion']]['native_mesh_depth_m'] <= spec['floor_screen_m']
            target = row['result']['target_mesh_floor_depth_max_m'] <= spec['floor_screen_m']
            combinations[f'native_{"pass" if native else "fail"}_target_{"pass" if target else "fail"}'] += 1
        hovering = [r['predicted_support_foot_region_hover_max_m'] for r in eligible
                    if r.get('predicted_support_foot_region_hover_max_m') is not None]
        summaries.append(dict(rig=rig['id'], label=rig['label'], family=rig['family'],
            planned=len(selected), statuses=dict(Counter(r['status'] for r in selected)),
            completed_floor_eligible=len(eligible), completed_floor_inapplicable=len(completed)-len(eligible),
            floor_combinations=dict(combinations),
            predicted_support_hover_measured=len(hovering),
            predicted_support_hover_max_m=max(hovering) if hovering else None))
    return dict(observed_at=now(), protocol_sha256=sha256(folder / 'protocol.json'),
        result_snapshot=data, planned_transfers=len(rows), statuses=dict(Counter(r['status'] for r in rows)),
        verified_transfer_files=verified_files, planned_engine_clips=spec['planned_engine_clips'],
        verified_engine_clips=len(engine_ids), engine_position_error_max_m=maximum_position if engine_ids else None,
        engine_basis_error_max=maximum_basis if engine_ids else None, rigs=summaries,
        quality_approved=False, human_review=None,
        limitations=['Snapshot of available completed work; pending and failed outcomes remain in denominator.',
                    'Foot region hover uses model-predicted support, not confirmed ground contact.',
                    'Zero hover can coexist with penetration and does not indicate good support.',
                    'Engine transform validity does not verify motion semantics, physical correctness or GPU skinning.',
                    'Existing three assets share two rig families; these are development results, not held-out release evidence.'])


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('folder', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise ValueError('Preserve earlier diagnostic snapshots; choose a new output path')
    result = analyze(args.folder)
    save(args.output, result)
    print({k: result[k] for k in ['statuses', 'verified_transfer_files', 'verified_engine_clips', 'rigs']})
