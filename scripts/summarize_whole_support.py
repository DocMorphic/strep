"""Account for every declared whole-support input, including failures and pending work."""
import argparse
from pathlib import Path
import copy
from strep import ROOT,read,save,sha256,now


def population(cases,rows):
    expected=[c['id'] for c in cases];actual=[r['id'] for r in rows]
    if len(set(actual))!=len(actual) or set(actual)!=set(expected):
        raise ValueError('Missing, duplicate or undeclared study rows')
    allowed={'pending','running','verified_pending_engine','complete','failed'}
    if any(r['status'] not in allowed for r in rows):raise ValueError('Unknown study row status')
    return dict(planned=len(expected),complete=sum(r['status']=='complete' for r in rows),
        failed=sum(r['status']=='failed' for r in rows),pending=sum(r['status'] not in {'complete','failed'} for r in rows))


def metric_row(proof,traces):
    result={}
    for version in ['input','candidate']:
        m=proof['metrics'][version];t=next(v for v in traces['variants'] if v['variant']==version)
        if abs(t['root_acceleration_max_m_s2']-m['root_acceleration_max_m_s2'])>1e-7:
            raise ValueError('Trace/verification acceleration mismatch')
        feet={}
        for side,f in m['feet'].items():
            trace=t['feet'][side]
            if trace['predicted_support_p95_m_s']!=f['predicted_support_speed_p95_m_s']:
                raise ValueError('Trace/verification support percentile mismatch')
            feet[side]=dict(p95_m_s=f['predicted_support_speed_p95_m_s'],max_m_s=trace['predicted_support_max_m_s'],
                peak_step_end_frame=trace['peak_step_end_frame'],hover_max_m=f['predicted_support_hover_max_m'],
                predicted_support_steps=f['predicted_support_steps'],anchor_error_max_m=f['drafted_anchor_error_max_m'])
        result[version]=dict(floor_max_m=max(m['floor_depth_max_m'],m['half_frame_floor_depth_max_m']),
            root_acceleration_max_m_s2=m['root_acceleration_max_m_s2'],root_peak_frame=t['root_peak_frame'],
            local_rotation_step_max_degrees=m['local_rotation_step_max_degrees'],feet=feet)
    return result


def run(study,output,allow_partial=False):
    from study_whole_support_breadth import validate,check_engine
    study,output=[Path(p).resolve() for p in [study,output]]
    if output.exists():raise ValueError('Preserve earlier summary')
    p=validate(study);state=read(study/'pipeline.json');data=read(study/'results.json')
    counts=population(p['cases'],data['rows']);terminal=state['status'] in ['complete','complete_with_failures','failed']
    if not terminal and not allow_partial:raise ValueError('Study still running; partial summary must be explicit')
    if state['status']=='complete' and counts['complete']!=counts['planned']:raise ValueError('False complete status')
    if state['status'] in ['complete','complete_with_failures']:
        if read(study/'completion.json')['results_sha256']!=sha256(study/'results.json'):raise ValueError('Completion evidence changed')
    rows=[];total=0
    for case in p['cases']:
        row=copy.deepcopy(next(r for r in data['rows'] if r['id']==case['id']));folder=study/'takes'/case['id']
        entry=dict(id=case['id'],family=case['motion']['family'],action=case['motion']['case'],rig=case['rig'],seed=case['motion']['seed'],status=row['status'])
        for key in ['error','engine_error']:
            if key in row:entry[key]=row[key]
        if row['status']=='complete':
            for name,key in [('verification.json','verification_sha256'),('traces.json','traces_sha256')]:
                if sha256(folder/name)!=row[key]:raise ValueError('Candidate evidence changed: '+case['id'])
            proof=read(folder/'verification.json');traces=read(folder/'traces.json')
            if proof!=row['verification'] or not proof['bounds_and_preservation_passed']:raise ValueError('Candidate verification mismatch')
            for version,key in [('input','source_sha256'),('candidate','candidate_sha256')]:
                digest=sha256(folder/version/'character.glb')
                if digest!=proof[key] or digest!=next(t for t in traces['variants'] if t['variant']==version)['source_sha256']:
                    raise ValueError('Export/trace source mismatch')
            if proof['source_sha256']!=case['files']['character.glb']:raise ValueError('Wrong baseline')
            group=next(g for g in data['engine_groups'] if g['case']==case['id']);engine=study/'engine-groups'/case['id']
            if group['status']!='complete' or sha256(engine/'audit/verification.json')!=group['proof_sha256']:
                raise ValueError('Engine evidence incomplete/changed')
            eproof=read(engine/'audit/verification.json');checks=read(engine/'manifest.json')['cases']
            if eproof!=group['proof'] or len(checks)!=2:raise ValueError('Wrong engine population')
            expected=[proof['source_sha256'],proof['candidate_sha256']]
            if [c['sha256'] for c in checks]!=expected or any(c['frames']!=case['motion']['frames'] for c in checks):raise ValueError('Wrong engine sources/clock')
            frames=check_engine(eproof,checks);total+=frames
            entry.update(metrics=metric_row(proof,traces),engine_actor_frames=frames,
                verification_sha256=row['verification_sha256'],traces_sha256=row['traces_sha256'],engine_sha256=group['proof_sha256'])
        rows.append(entry)
    output.mkdir(parents=True);save(output/'captured-results.json',data)
    summary=dict(at=now(),study=str(study),protocol_sha256=sha256(study/'protocol.json'),population=counts,
        pipeline=state,partial=not terminal,rows=rows,engine_actor_frames_on_complete_inputs=total,
        planned_engine_actor_frames=p['planned_engine_actor_frames'],excluded_context_cases=p['excluded_context_cases'],
        captured_results_sha256=sha256(output/'captured-results.json'),summarizer_sha256=sha256(__file__),quality_approved=False,
        scope='Full declared development population. Pending/failed cases remain in denominators; no automatic quality, semantic, physical or held-out acceptance.')
    save(output/'summary.json',summary)
    lines=['# Whole-clip support correction: development comparison','',f"{counts['complete']}/{counts['planned']} complete; {counts['failed']} failed; {counts['pending']} pending.",'',
        'Numbers are raw → candidate. Predicted contact labels are unconfirmed. All declared inputs are listed.','',
        '| Action | Rig | Status | Floor max (mm) | Root acceleration max (m/s²) | Support speed max L/R (m/s) |',
        '|---|---|---|---:|---:|---|']
    def number(v):return 'missing' if v is None else f'{v:.4f}'
    for row in rows:
        floor=acc=speed='—'
        if 'metrics' in row:
            a,b=[row['metrics'][v] for v in ['input','candidate']]
            floor=f"{a['floor_max_m']*1000:.3f} → {b['floor_max_m']*1000:.3f}"
            acc=f"{a['root_acceleration_max_m_s2']:.3f} → {b['root_acceleration_max_m_s2']:.3f}"
            speed='; '.join(f"{s}: {number(a['feet'][s]['max_m_s'])} → {number(b['feet'][s]['max_m_s'])}" for s in ['Left','Right'])
        lines.append(f"| {row['action']} | {row['rig']} | {row['status']} | {floor} | {acc} | {speed} |")
    lines+=['','Swimming, stairs, object and partner cases are retained as context-dependent exclusions from this floor-only study. Other project studies must assess them.','',
        'This comparison is development evidence. Review action correctness, intended pivots/slides, physical plausibility and cleanup time independently.']
    (output/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);p.add_argument('--allow-partial',action='store_true');a=p.parse_args()
    print(run(a.study,a.output,a.allow_partial)['population'])
