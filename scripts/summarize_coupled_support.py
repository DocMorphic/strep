"""Full-population accounting for a completed coupled support study."""
import argparse
from pathlib import Path
from strep import read, save, sha256, now
from audit_authoring_intent import check_files
from study_whole_support_breadth import check_engine


def run(study, output):
    complete, protocol = read(study/'completion.json'), read(study/'protocol.json')
    if complete['protocol_sha256'] != sha256(study/'protocol.json'):
        raise ValueError('Completed protocol changed')
    check_files(study, complete['files'])
    if [r['id'] for r in complete['rows']] != [c['id'] for c in protocol['cases']]:
        raise ValueError('Population changed')
    previous = Path(protocol['summary'])/'summary.json'
    if sha256(previous) != protocol['summary_sha256']:
        raise ValueError('Predecessor changed')
    if complete['engine_actor_frames']:
        if sha256(study/'engine/verification.json') != complete['engine_verification_sha256']:
            raise ValueError('Engine proof changed')
        actual = check_engine(read(study/'engine/verification.json'), read(study/'manifest.json')['cases'])
        if actual != complete['engine_actor_frames']: raise ValueError('Engine frame count changed')
    rows = []
    for case, result in zip(protocol['cases'], complete['rows']):
        row = {k: result[k] for k in ('id', 'family', 'action', 'rig', 'status')}
        if case['eligible']:
            folder = study/case['id']; check_files(folder/'base', case['files'])
            if sha256(result['selected']) != result['selected_sha256']:
                raise ValueError('Selected output changed')
            if result['status'] == 'failed': row['error'] = result['error']
            else:
                if sha256(folder/'audit.json') != result['audit_sha256']:
                    raise ValueError('Full-file audit changed')
                audit = read(folder/'audit.json'); accepted = result['status'] == 'candidate_preserved'
                if accepted and (not audit['passed'] or audit['candidate_sha256'] != result['selected_sha256']):
                    raise ValueError('Invalid candidate selection')
                if not accepted and result['selected_sha256'] != case['selected_sha256']:
                    raise ValueError('Input retention changed')
                before, after = audit['foot_speed_excess_energy_before'], audit['foot_speed_excess_energy_after']
                row.update(selected_excess_energy_reduction_percent=100*(1-after/before) if accepted and before else 0.,
                    candidate_checks=audit['checks'], feet=[], quality_approved=False)
                for foot in audit['feet']:
                    row['feet'].append(dict(side=foot['side'], before_m_s=foot['support_peak_before_m_s'],
                        selected_m_s=foot['support_peak_after_m_s'] if accepted else foot['support_peak_before_m_s'],
                        raw_target_m_s=foot['raw_peak_target_m_s']))
                row['remaining_peak_regressions'] = [f['side'] for f in row['feet'] if f['selected_m_s'] is not None and
                    f['raw_target_m_s'] is not None and f['selected_m_s'] > f['raw_target_m_s']+.001]
        rows.append(row)
    counts = {s: sum(r['status']==s for r in rows) for s in sorted({r['status'] for r in rows})}
    output.mkdir(parents=True, exist_ok=False)
    save(output/'summary.json', dict(at=now(), study=str(study), completion_sha256=sha256(study/'completion.json'),
        counts=counts, rows=rows, planned=len(rows), targeted=sum(c['eligible'] for c in protocol['cases']),
        engine_actor_frames=complete['engine_actor_frames'], implementation_sha256=sha256(__file__),
        quality_approved=False, scope='Full fixed development population; raw-peak comparison bins are diagnostics, not realism criteria.'))
    lines = ['# Coupled support correction results', '', str(counts), '',
        f"Actual Godot verification: {complete['engine_actor_frames']} actor-frames. No quality promotion.", '',
        '| Action / rig | Outcome | Selected speed-excess energy reduction | Remaining foot peak regressions |',
        '|---|---|---:|---|']
    for row in rows:
        metric = f"{row['selected_excess_energy_reduction_percent']:.3f}%" if 'selected_excess_energy_reduction_percent' in row else '—'
        remaining = ', '.join(row['remaining_peak_regressions']) or 'none in reporting bin' if 'remaining_peak_regressions' in row else '—'
        lines.append(f"| {row['action']} / {row['rig']} | {row['status']} | {metric} | {remaining} |")
    (output/'comparison.md').write_text('\n'.join(lines)+'\n', encoding='utf8')
    print(counts)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); run(args.study.resolve(), args.output.resolve())
