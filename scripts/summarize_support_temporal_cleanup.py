"""Account for the full frozen cleanup population and inherited failures."""
import argparse
from pathlib import Path
from strep import read, save, sha256, now
from audit_authoring_intent import check_files


def run(study, output):
    protocol, complete = read(study/'protocol.json'), read(study/'completion.json')
    if complete['protocol_sha256'] != sha256(study/'protocol.json'):
        raise ValueError('Completed protocol changed')
    check_files(study, complete['files'])
    if complete['engine_verification_sha256'] != sha256(study/'engine/verification.json'):
        raise ValueError('Completed engine evidence changed')
    if [c['id'] for c in protocol['cases']] != [r['id'] for r in complete['rows']]:
        raise ValueError('Population changed')
    rows = []
    for case, result in zip(protocol['cases'], complete['rows']):
        row = {k: result[k] for k in ('id', 'family', 'action', 'rig', 'status')}
        if result['status'] in ('unfinished_source', 'failed'):
            row['reason'] = result.get('error', 'Source unfinished in frozen snapshot')
            rows.append(row)
            continue
        folder = study/case['id']
        check_files(folder, case['files'])
        if sha256(result['selected']) != result['selected_sha256']:
            raise ValueError('Selected output changed')
        trace = read(folder/'original-traces.json')
        raw = next(t for t in trace['variants'] if t['variant'] == 'input')
        before = next(t for t in trace['variants'] if t['variant'] == 'candidate')
        if result['status'] == 'candidate_preserved':
            chosen = [a for a in result['attempts'] if a['accepted']]
            if len(chosen) != 1 or chosen[0]['path'] != result['selected']:
                raise ValueError('Ambiguous accepted selection')
            audit_path = Path(result['selected']).with_suffix('.json')
            if sha256(audit_path) != chosen[0]['audit_sha256']:
                raise ValueError('Selected audit changed')
            audit = read(audit_path)
            if not audit['all_checks_passed'] or audit['root']['candidate_sha256'] != result['selected_sha256']:
                raise ValueError('Selected audit does not pass or match output')
            root = audit['root']
            row.update(root_peak_before_m_s2=root['root_peak_before_m_s2'],
                root_peak_after_m_s2=root['root_peak_after_m_s2'],
                root_energy_reduction_percent=100*(1-root['energy_after']/root['energy_before']),
                floor_before_m=root['source_floor_depth_m'], floor_after_m=root['candidate_floor_depth_m'],
                feet={f['side']: dict(before=f['support_peak_before_m_s'], after=f['support_peak_after_m_s'],
                    guarded_speed_excess_m_s=f['guarded_speed_excess_m_s']) for f in audit['feet']})
        elif result['status'] == 'input_retained':
            if result['selected_sha256'] != sha256(folder/'candidate/character.glb'):
                raise ValueError('Retained input changed')
            proof = read(folder/'original-verification.json')['metrics']['candidate']
            floor = max(proof['floor_depth_max_m'], proof['half_frame_floor_depth_max_m'])
            row.update(root_peak_before_m_s2=before['root_acceleration_max_m_s2'],
                root_peak_after_m_s2=before['root_acceleration_max_m_s2'], root_energy_reduction_percent=0.,
                floor_before_m=floor, floor_after_m=floor,
                feet={side: dict(before=f['predicted_support_max_m_s'], after=f['predicted_support_max_m_s'],
                    guarded_speed_excess_m_s=0.) for side, f in before['feet'].items()})
        else:
            raise ValueError('Unknown outcome')
        row['raw_root_peak_m_s2'] = raw['root_acceleration_max_m_s2']
        row['root_peak_still_above_raw_reporting_bin'] = row['root_peak_after_m_s2'] > row['raw_root_peak_m_s2']+.0036
        row['foot_peaks_still_above_raw_reporting_bin'] = [side for side, f in row['feet'].items()
            if f['after'] is not None and raw['feet'][side]['predicted_support_max_m_s'] is not None
            and f['after'] > raw['feet'][side]['predicted_support_max_m_s']+.001]
        rows.append(row)
    output.mkdir(parents=True, exist_ok=False)
    counts = {status: sum(r['status'] == status for r in rows) for status in
              ('candidate_preserved', 'input_retained', 'failed', 'unfinished_source')}
    summary = dict(at=now(), study=str(study), study_completion_sha256=sha256(study/'completion.json'),
        planned=len(rows), counts=counts, rows=rows, engine_actor_frames=complete['engine_actor_frames'],
        quality_approved=False, implementation_sha256=sha256(__file__),
        scope='Complete fixed development population accounting. Root/foot raw comparison bins are diagnostic; '
        'numerical candidate retention does not approve semantics or repair inherited quality failures.')
    save(output/'summary.json', summary)
    lines = ['# Support temporal cleanup results', '',
        f"{counts['candidate_preserved']} candidates retained; {counts['input_retained']} inputs retained; "
        f"{counts['failed']} failed; {counts['unfinished_source']} unfinished source rows. "
        f"{complete['engine_actor_frames']} actual Godot actor-frames. No quality approval.", '',
        '| Action / rig | Outcome | Root energy reduction | Root peak before → after (m/s²) |',
        '|---|---|---:|---:|']
    for r in rows:
        if 'root_energy_reduction_percent' in r:
            metrics = f"{r['root_energy_reduction_percent']:.3f}% | {r['root_peak_before_m_s2']:.4f} → {r['root_peak_after_m_s2']:.4f}"
        else: metrics = '— | —'
        lines.append(f"| {r['action']} / {r['rig']} | {r['status']} | {metrics} |")
    (output/'comparison.md').write_text('\n'.join(lines)+'\n', encoding='utf8')
    print(counts, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); run(args.study.resolve(), args.output.resolve())
