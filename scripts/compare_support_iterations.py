"""Compare complete support studies that differ only in finite iteration budget."""
import argparse
from collections import Counter
from pathlib import Path

from strep import read, save, sha256, now
from compare_midpoint_support import verified, trial_counts


def match_protocols(before, after):
    variable = {'at', 'scope', 'implementation', 'steps_per_block'}
    if {k:v for k,v in before.items() if k not in variable} != {
        k:v for k,v in after.items() if k not in variable
    }:
        raise ValueError('Source population, physical limits or solver protocol differs')
    a,b = before['steps_per_block'],after['steps_per_block']
    if type(a) is not int or type(b) is not int or not 1 <= a < b <= 30:
        raise ValueError('Expected increasing finite step budgets')
    if not before.get('midpoint_constraints') or not after.get('midpoint_constraints'):
        raise ValueError('Both studies must retain midpoint constraints')
    changed = sorted(k for k in set(before['implementation']) | set(after['implementation'])
                     if before['implementation'].get(k) != after['implementation'].get(k))
    if changed not in ([], ['study_coupled_support.py']):
        raise ValueError('Solver or validator implementation changed')
    return changed


def selected_metrics(audit, result):
    accepted = result['status'] == 'candidate_preserved'
    if result['status'] not in ('candidate_preserved','input_retained'):
        raise ValueError('Failed cases have no comparable candidate metrics')
    if accepted and (not audit['passed'] or not all(audit['checks'].values()) or
                     result['selected_sha256'] != audit['candidate_sha256']):
        raise ValueError('Selected candidate lacks matching successful audit')
    if not accepted and result['selected_sha256'] != audit['source_sha256']:
        raise ValueError('Retained input identity differs')
    energy = audit['foot_speed_excess_energy_after' if accepted else 'foot_speed_excess_energy_before']
    feet = [dict(side=f['side'],raw_target_m_s=f['raw_peak_target_m_s'],
                 selected_peak_m_s=f['support_peak_after_m_s' if accepted else 'support_peak_before_m_s'])
            for f in audit['feet']]
    remaining = [f['side'] for f in feet if f['selected_peak_m_s'] is not None and
                 f['raw_target_m_s'] is not None and f['selected_peak_m_s'] > f['raw_target_m_s']+.001]
    return dict(selected_energy=energy,feet=feet,remaining_peak_regressions=remaining,
                candidate_checks_against_common_input=audit['checks'])


def compare(before, after, output, comparison_kind='iterations'):
    if output.exists():raise ValueError('Preserve prior comparison')
    for folder in [before,after]:
        if read(folder/'pipeline.json')['status']!='complete':raise ValueError('Wait for terminal studies')
    bp,bc=verified(before);ap,ac=verified(after)
    from support_comparison_protocol import match_studies
    changed=match_studies(bp,ap,comparison_kind)
    preparation=read(after/'matched-preparation.json')
    if preparation['before_protocol_sha256']!=sha256(before/'protocol.json') or preparation['after_protocol_sha256']!=sha256(after/'protocol.json'):
        raise ValueError('Prepared comparison does not bind these protocols')
    rows=[]
    for case,old,new in zip(ap['cases'],bc['rows'],ac['rows']):
        row={k:case[k] for k in ['id','family','action','rig']}
        row.update(before_status=old['status'],after_status=new['status'])
        if not case['eligible']:
            row['outcome']='not_targeted';rows.append(row);continue
        if 'failed' in (old['status'],new['status']):
            row.update(outcome='failed_case',before_error=old.get('error'),after_error=new.get('error'))
            rows.append(row);continue
        if read(before/case['id']/'selection.json')!=read(after/case['id']/'selection.json'):
            raise ValueError('Selected editing windows differ')
        metrics=[];audits=[]
        for folder,result in [(before,old),(after,new)]:
            path=folder/case['id']/'audit.json';audit=read(path)
            if sha256(path)!=result['audit_sha256']:raise ValueError('Audit identity changed')
            if sha256(result['selected'])!=result['selected_sha256']:raise ValueError('Selected motion changed')
            item=selected_metrics(audit,result)
            item['attempts']=trial_counts(folder/case['id']/'solver.json')
            metrics.append(item);audits.append(audit)
        if audits[0]['source_sha256']!=audits[1]['source_sha256'] or abs(audits[0]['foot_speed_excess_energy_before']-audits[1]['foot_speed_excess_energy_before'])>1e-12:
            raise ValueError('Common input measurements differ')
        foot_changes=[]
        if [f['side'] for f in metrics[0]['feet']]!=[f['side'] for f in metrics[1]['feet']]:raise ValueError('Foot populations differ')
        for a,b in zip(metrics[0]['feet'],metrics[1]['feet']):
            if a['raw_target_m_s']!=b['raw_target_m_s']:raise ValueError('Raw reference changed')
            delta=None if a['selected_peak_m_s'] is None or b['selected_peak_m_s'] is None else b['selected_peak_m_s']-a['selected_peak_m_s']
            foot_changes.append(dict(side=a['side'],peak_delta_m_s=delta))
        delta=metrics[1]['selected_energy']-metrics[0]['selected_energy']
        row.update(before=metrics[0],after=metrics[1],energy_delta=delta,foot_peak_changes=foot_changes,
                   outcome='improved' if delta < -1e-9 else 'worse' if delta > 1e-9 else 'unchanged')
        rows.append(row)
    counts=dict(Counter(r['outcome'] for r in rows))
    output.mkdir(parents=True)
    save(output/'comparison.json',dict(at=now(),before=str(before),after=str(after),rows=rows,counts=counts,
        before_completion_sha256=sha256(before/'completion.json'),after_completion_sha256=sha256(after/'completion.json'),
        matched_preparation_sha256=sha256(after/'matched-preparation.json'),changed_implementation=changed,
        comparison_kind=comparison_kind,fraction_schedules=[bp.get('fractions'),ap.get('fractions')],
        protocol_matcher_sha256=sha256(Path(__file__).with_name('support_comparison_protocol.py')),
        step_budgets=[bp['steps_per_block'],ap['steps_per_block']],engine_actor_frames=[bc['engine_actor_frames'],ac['engine_actor_frames']],
        implementation_sha256=sha256(__file__),quality_approved=False,
        scope='Matched development comparison with all population rows retained. Selected metrics exclude rejected proposals. '
              'Candidate checks compare with the common input, not the other selected output. '
              'Objective reduction does not guarantee per-frame or quarter-frame non-regression, contact correctness or naturalness.'))
    title='additional support-correction iterations' if comparison_kind=='iterations' else 'extended support-correction backtracking'
    lines=['# Effect of '+title,'',str(counts),'',
           '| Case | Outcome | Energy delta | Remaining raw-relative peak regressions |','|---|---|---:|---|']
    for r in rows:
        delta=f"{r['energy_delta']:.9f}" if 'energy_delta' in r else '—'
        remaining=', '.join(r['after']['remaining_peak_regressions']) or 'none in reporting bin' if 'after' in r else '—'
        lines.append(f"| {r['id']} | {r['outcome']} | {delta} | {remaining} |")
    lines+=['','Negative energy delta is an improvement on this objective only. Numerical results do not supply human review.']
    (output/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(counts)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['before','after','output']:p.add_argument(name,type=Path)
    p.add_argument('--comparison-kind',choices=['iterations','backtracking'],default='iterations')
    a=p.parse_args();compare(a.before.resolve(),a.after.resolve(),a.output.resolve(),a.comparison_kind)
