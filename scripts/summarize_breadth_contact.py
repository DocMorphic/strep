"""Hash-verified paired metrics, retaining complete and unfinished populations."""
import argparse
import hashlib
import json
from pathlib import Path
from strep import read,save,sha256,now
from study_breadth_contact import validate


def metrics(value):
    speeds=[foot['predicted_support_speed_p95_m_s'] for foot in value['feet'].values()]
    hover=[foot['predicted_support_hover_max_m'] for foot in value['feet'].values()]
    complete=all(v is not None for v in speeds+hover)
    result=dict(floor_m=max(value['floor_depth_max_m'],value['half_frame_floor_depth_max_m']),
        support_speed_p95_max_m_s=max(speeds) if all(v is not None for v in speeds) else None,
        hover_max_m=max(hover) if all(v is not None for v in hover) else None,
        root_acceleration_max_m_s2=value['root_acceleration_max_m_s2'],local_rotation_step_max_degrees=value['local_rotation_step_max_degrees'])
    result['proposed_proxy_screens_passed']=bool(complete and result['floor_m']<=.01 and result['support_speed_p95_max_m_s']<=.05 and result['hover_max_m']<=.03)
    return result


def run(study,output):
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Preserve earlier interim snapshot')
    protocol=validate(study);raw=(study/'results.json').read_bytes();data=json.loads(raw);cases=[];files={}
    for case in protocol['cases']:
        rows=[r for r in data['rows'] if r['case']==case['id']]
        groups=[g for g in data['engine_groups'] if g['case']==case['id'] and g['status']=='complete']
        if len(rows)!=2 or any(r['status']!='complete' for r in rows) or len(groups)!=1:continue
        group=study/'engine-groups'/case['id'];engine=read(group/'audit/verification.json')
        if engine!=groups[0]['proof']:raise ValueError('Engine proof changed')
        verified={};digests={case['files']['character.glb']}
        for row in rows:
            folder=study/'takes'/row['id'];proof=read(folder/'verification.json')
            if proof!=row['verification'] or not proof['bounds_and_preservation_passed']:raise ValueError('Candidate proof changed')
            if sha256(folder/'candidate/character.glb')!=proof['candidate_sha256'] or proof['source_sha256']!=case['files']['character.glb']:raise ValueError('Candidate/input changed')
            digests.add(proof['candidate_sha256']);verified[row['method']]=proof
            files[str(folder/'verification.json')]=sha256(folder/'verification.json')
        if verified['clearance']['metrics']['input']!=verified['support']['metrics']['input']:raise ValueError('Paired input metrics differ')
        checks=engine['checks']
        if len(checks)!=3 or {c['source_sha256'] for c in checks}!=digests or any(c['frames']!=case['motion']['frames'] for c in checks):raise ValueError('Incomplete engine group')
        files[str(group/'audit/verification.json')]=sha256(group/'audit/verification.json')
        cases.append(dict(id=case['id'],seed=case['motion']['seed'],rig=case['rig'],input=metrics(verified['clearance']['metrics']['input']),
            clearance=metrics(verified['clearance']['metrics']['candidate']),support=metrics(verified['support']['metrics']['candidate']),
            engine_frames=sum(c['frames'] for c in checks)))
    complete=len(cases)==len(protocol['cases']) and read(study/'pipeline.json')['status']=='complete'
    output.mkdir();(output/'results-snapshot.json').write_bytes(raw)
    result=dict(at=now(),status='complete_population' if complete else 'interim_population',study=str(study),script_sha256=sha256(__file__),source_results_sha256=hashlib.sha256(raw).hexdigest(),
        protocol_sha256=sha256(study/'protocol.json'),verified_files=files,cases=cases,
        population=[{k:r[k] for k in ['id','case','method','status']} for r in data['rows']],
        complete_pairs=len(cases),planned_pairs=len(protocol['cases']),
        proposed_proxy_thresholds=dict(floor_m=.01,predicted_support_p95_m_s=.05,predicted_support_hover_m=.03),quality_approved=False,
        scope=('Complete declared development population, with both independently verified candidates and engine groups for every input. ' if complete else
               'All paired inputs with both independently verified candidates and complete engine groups in this captured snapshot. Unfinished cases remain in the population. ')+
              'Model-predicted support is unconfirmed; no anatomy, semantic, balance or animator approval. P95 screens can hide individual speed spikes; whole-motion approval requires more than these proxies.')
    save(output/'summary.json',result)
    lines=['# '+('Complete' if complete else 'Interim')+' contact-correction comparison','',
        f"{len(cases)} of {len(protocol['cases'])} paired inputs complete in this snapshot."+(' All planned inputs are included.' if complete else ' Remaining cases are not scored.'),'',
        '| Input | Method | Floor including halfway frames (mm) | Worst predicted-support p95 speed (m/s) | Predicted-support hover (mm) | Proposed proxy screens |',
        '|---|---|---:|---:|---:|---|']
    for case in cases:
        for method in ['input','clearance','support']:
            m=case[method];speed='missing' if m['support_speed_p95_max_m_s'] is None else f"{m['support_speed_p95_max_m_s']:.4f}"
            hover='missing' if m['hover_max_m'] is None else f"{m['hover_max_m']*1000:.3f}"
            lines.append(f"| {case['id']} | {method} | {m['floor_m']*1000:.3f} | {speed} | {hover} | {'pass' if m['proposed_proxy_screens_passed'] else 'fail'} |")
    lines.extend(['','Proxy thresholds: 10 mm floor depth, 0.05 m/s predicted-support speed, 30 mm predicted-support hover. Passing these proxies is not usable-motion approval. All edit/preservation bounds and three-clip engine groups were checked.','',result['scope']])
    (output/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');print({'complete_pairs':len(cases),'planned_pairs':len(protocol['cases']),'cases':cases})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.study,a.output)
