"""Compare completed midpoint-proposal and endpoint-only development studies."""
import argparse
from pathlib import Path
from collections import Counter
from strep import read, save, sha256, now
from audit_authoring_intent import check_files
from study_whole_support_breadth import check_engine


def verified(study):
    protocol, completion = read(study/'protocol.json'), read(study/'completion.json')
    if completion['protocol_sha256'] != sha256(study/'protocol.json'):
        raise ValueError('Completed study protocol changed')
    check_files(study, completion['files'])
    check_files(study/'implementation', protocol['implementation'])
    if [c['id'] for c in protocol['cases']] != [r['id'] for r in completion['rows']]:
        raise ValueError('Completion population differs from protocol')
    if sha256(study/'engine/verification.json') != completion['engine_verification_sha256']:
        raise ValueError('Engine proof changed')
    count = check_engine(read(study/'engine/verification.json'), read(study/'manifest.json')['cases'])
    if count != completion['engine_actor_frames']:
        raise ValueError('Engine count differs from completion')
    return protocol, completion


def trial_counts(path):
    counts = Counter()
    for block in read(path)['blocks']:
        for step in block['solver']['history']:
            for attempt in step['attempts']:
                counts['solver_'+attempt['status']] += 1
                for trial in attempt.get('trials', []):
                    counts['proposals'] += 1
                    counts['accepted'] += int(trial['accepted'])
                    counts['midpoint_guard_veto'] += int(trial['midpoint_excess_m'] is not None and not trial['midpoint_pass'])
                    counts['midpoint_proposal_row_veto'] += int(trial['margins'].get('midpoint_floor', 0) < -1e-9)
    return dict(counts)


def compare(before, after, output):
    bp, bc = verified(before); ap, ac = verified(after)
    if bp.get('midpoint_constraints', False) or not ap.get('midpoint_constraints', False):
        raise ValueError('Expected endpoint-only then midpoint-constrained studies')
    for key in ('cases', 'summary_sha256', 'steps_per_block', 'trusts', 'blocks_per_case', 'frames_per_block', 'fractions', 'solver_bootstrap_sha256'):
        if bp[key] != ap[key]: raise ValueError('Unmatched comparison: '+key)
    rows = []
    for case, old, new in zip(ap['cases'], bc['rows'], ac['rows']):
        row = dict(id=case['id'], family=case['family'], action=case['action'], rig=case['rig'],
                   before_status=old['status'], after_status=new['status'])
        if case['eligible']:
            if read(before/case['id']/'selection.json') != read(after/case['id']/'selection.json'):
                raise ValueError('Selected blocks differ')
            metrics = []
            for study, item in ((before, old), (after, new)):
                audit = read(study/case['id']/'audit.json')
                if sha256(study/case['id']/'audit.json') != item['audit_sha256']:
                    raise ValueError('Audit differs from completion')
                accepted = item['status'] == 'candidate_preserved'
                if accepted and not all(audit['checks'].values()): raise ValueError('Invalid accepted candidate')
                metrics.append(dict(status=item['status'],
                    input_energy=audit['foot_speed_excess_energy_before'],
                    selected_energy=audit['foot_speed_excess_energy_after' if accepted else 'foot_speed_excess_energy_before'],
                    checks=audit['checks'], attempts=trial_counts(study/case['id']/'solver.json'),
                    feet=[dict(side=f['side'], raw_peak_target_m_s=f['raw_peak_target_m_s'],
                        selected_peak_m_s=f['support_peak_after_m_s' if accepted else 'support_peak_before_m_s']) for f in audit['feet']]))
            if abs(metrics[0]['input_energy']-metrics[1]['input_energy']) > 1e-12:
                raise ValueError('Input measurements differ')
            delta = metrics[1]['selected_energy']-metrics[0]['selected_energy']
            row.update(before=metrics[0], after=metrics[1], energy_delta=delta,
                outcome='improved' if delta < -1e-9 else 'worse' if delta > 1e-9 else 'unchanged')
        rows.append(row)
    counts = dict(Counter(row.get('outcome', 'not_targeted_or_unfinished') for row in rows))
    output.mkdir(parents=True, exist_ok=False)
    save(output/'comparison.json', dict(at=now(), before=str(before), after=str(after),
        before_completion_sha256=sha256(before/'completion.json'), after_completion_sha256=sha256(after/'completion.json'),
        matched_inputs_and_parameters=True, rows=rows, counts=counts,
        engine_actor_frames=[bc['engine_actor_frames'], ac['engine_actor_frames']],
        implementation_sha256=sha256(__file__), quality_approved=False,
        scope='Matched development comparison; objective improvement is not contact correctness or animator approval.'))
    lines = ['# Effect of explicit midpoint floor constraints', '', str(counts), '',
             '| Case | Previous | Midpoint | Selected speed-excess energy delta |', '|---|---|---|---:|']
    for row in rows:
        delta = f"{row['energy_delta']:.9f}" if 'energy_delta' in row else 'n/a'
        lines.append(f"| {row['id']} | {row['before_status']} | {row['after_status']} | {delta} |")
    lines += ['', 'Negative delta is better on this objective only. All unchanged and worsened outcomes remain included. No release promotion.']
    (output/'comparison.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(counts)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('before', 'after', 'output'): parser.add_argument(name, type=Path)
    args = parser.parse_args()
    compare(args.before.resolve(), args.after.resolve(), args.output.resolve())
