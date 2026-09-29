"""Verify the frozen population, selected exports and engine proof before reporting."""
import argparse
from collections import Counter
from pathlib import Path
from strep import read,save,sha256,now
from audit_authoring_intent import check_files


def run(study,output):
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Preserve earlier summary')
    request=read(study/'request.json');results=read(study/'results.json');done=read(study/'completion.json')
    if read(study/'pipeline.json')['status'] not in ['complete','complete_with_failures']:raise ValueError('Terminal study required')
    if done['request_sha256']!=sha256(study/'request.json') or done['results_sha256']!=sha256(study/'results.json') or done['engine_sha256']!=sha256(study/'engine/verification.json'):raise ValueError('Completion binding changed')
    if read(study/'freeze.json')['request_sha256']!=done['request_sha256']:raise ValueError('Freeze changed')
    cases=request['cases'];rows=results['rows']
    if len(cases)!=24 or len(set(c['id'] for c in cases))!=24 or [c['id'] for c in cases]!=[r['id'] for r in rows]:raise ValueError('Full population required')
    check_files(study/'implementation',request['implementation'])
    engine=read(study/'engine/verification.json')['checks'];manifest=read(study/'manifest.json')['cases']
    selected=[r for r in rows if r['status']!='failed']
    if [r['id'] for r in selected]!=[r['id'] for r in manifest] or [r['id'] for r in engine]!=[r['id'] for r in manifest]:raise ValueError('Engine denominator changed')
    records=[];frames=0
    for case,row in zip(cases,rows):
        folder=study/'takes'/case['id'];check_files(folder,case['files'])
        record={k:case[k] for k in ['id','action','family','rig','seed','frames']};record['status']=row['status']
        if row['status']=='failed':record['error']=row['error'];records.append(record);continue
        if row['status'] not in ['candidate_preserved','no_solver_proposal','no_accepted_candidate']:raise ValueError('Nonterminal row')
        path=Path(row['selected']).resolve()
        if not path.is_relative_to(folder.resolve()) or sha256(path)!=row['selected_sha256']:raise ValueError('Selected export changed')
        entry=next(e for e in engine if e['id']==row['id']);item=next(e for e in manifest if e['id']==row['id'])
        if entry['source_sha256']!=row['selected_sha256'] or item['sha256']!=row['selected_sha256'] or Path(item['path']).resolve()!=path or entry['frames']!=case['frames'] or item['frames']!=case['frames']:raise ValueError('Engine input changed')
        frames+=entry['frames'];record.update(original_peak_m_s2=case['original_root_peak_m_s2'],prior_peak_m_s2=case['prior_root_peak_m_s2'],selected_peak_m_s2=case['prior_root_peak_m_s2'],energy_reduction_fraction=0.)
        if row['status']=='candidate_preserved':
            attempts=read(folder/'attempts.json')
            if not attempts or len(attempts)!=row['attempts'] or attempts[-1]!=row['last_audit']:raise ValueError('Attempt record changed')
            selected_audit=attempts[-1];a=selected_audit['independent'];s=selected_audit['support'];v=selected_audit['verification']
            if not (selected_audit['accepted'] and a['all_checks_passed'] and all(a['checks'].values()) and s['passed'] and all(x['passed'] for x in s['rows']) and v['all_preservation_checks_passed'] and all(v['checks'].values()) and v['objective_improved']):raise ValueError('Selected outcome failed its guards')
            if a['candidate_sha256']!=row['selected_sha256'] or s['candidate_sha256']!=row['selected_sha256'] or v['glb_sha256']!=row['selected_sha256']:raise ValueError('Audit is for another output')
            if a['source_sha256']!=case['files']['candidate/character.glb'] or s['source_sha256']!=a['source_sha256']:raise ValueError('Wrong correction input')
            record.update(selected_peak_m_s2=a['root_peak_after_m_s2'],energy_reduction_fraction=1-a['energy_after']/a['energy_before'],support=s['rows'])
        elif path!= (folder/'candidate/character.glb').resolve():raise ValueError('Unaccepted proposal selected')
        record['original_root_peak_recovered']=record['selected_peak_m_s2']<=record['original_peak_m_s2']+request['policy']['acceleration_tolerance_m_s2']
        records.append(record)
    counts=dict(Counter(r['status'] for r in records))
    if frames!=done['engine_actor_frames'] or counts.get('candidate_preserved',0)!=done['selected_candidates'] or counts.get('failed',0)!=done['failed']:raise ValueError('Completion totals changed')
    output.mkdir(parents=True)
    summary=dict(at=now(),study_completion_sha256=sha256(study/'completion.json'),population=24,status_counts=counts,engine_actor_frames=frames,rows=records,quality_approved=False,
        original_root_peak_recovered=sum(r.get('original_root_peak_recovered',False) for r in records),scope='Development root cleanup; every case retained. Passing guards is neither broad motion-quality nor human approval.')
    save(output/'summary.json',summary)
    lines=['# Breadth root cleanup: complete development comparison','',f"24 cases; {counts}; {frames} engine actor-frames.",'','| Action | Rig | Outcome | Peak root acceleration: raw / prior / selected (m/s²) | Energy reduction |','|---|---|---|---:|---:|']
    for r in records:
        metrics=' / '.join(f"{r[k]:.4f}" for k in ['original_peak_m_s2','prior_peak_m_s2','selected_peak_m_s2']) if r['status']!='failed' else 'failed'
        lines.append(f"| {r['action']} | {r['rig']} | {r['status']} | {metrics} | {r.get('energy_reduction_fraction',0)*100:.2f}% |")
    lines+=['','Original refers to the raw transfer, prior to the whole-support candidate. No semantic, scene/partner, physical-balance or human-quality approval.']
    (output/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('study',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args();print(run(args.study,args.output)['status_counts'])
