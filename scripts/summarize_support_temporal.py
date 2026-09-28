"""Verify completed matched temporal cases and report all declared outcomes."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from strep import read,save,sha256,now


def run(study,output):
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Preserve prior temporal summary')
    request=read(study/'request.json');raw=(study/'results.json').read_bytes();data=json.loads(raw)
    if [r['case'] for r in data['rows']]!=[c['id'] for c in request['cases']]:raise ValueError('Declared population changed')
    files={};rows=[]
    def verify(path,digest=None):
        path=Path(path);actual=sha256(path)
        if digest is not None and actual!=digest:raise ValueError('Changed evidence: '+str(path))
        files[str(path)]=actual
    for name,digest in request['implementation'].items():verify(study/'implementation'/name,digest)
    for status in data['rows']:
        if status['status']!='complete':continue
        folder=Path(status['folder']);completion=read(folder/'completion.json');recipe=read(folder/'request.json')
        verify(folder/'completion.json',status['completion_sha256'])
        verify(folder/'results.json',completion['results_sha256']);verify(folder/'traces.json',completion['traces_sha256'])
        verify(folder/'engine/audit/verification.json',completion['engine_sha256']);verify(folder/'request.json')
        source=Path(recipe['source'])
        for name,digest in recipe['source_hashes'].items():verify(source/name,digest)
        parent=read(source/'verification.json');spec=read(source/'spec.json')
        result=read(folder/'results.json')['rows'];traces=read(folder/'traces.json')['variants']
        engine=read(folder/'engine/audit/verification.json')['checks']
        methods=[v[0] for v in recipe['variants']]
        if [r['variant'] for r in result]!=methods or [t['variant'] for t in traces]!=['raw','parent_correction',*methods]:
            raise ValueError('Missing or changed method population')
        if [c['id'] for c in engine]!=['raw','parent_correction',*methods] or any(c['frames']!=spec['frames'] for c in engine):
            raise ValueError('Incomplete engine coverage')
        if recipe['first_editable_frame']!=36 or recipe['last_editable_frame']!=69 or recipe['sweeps']!=6 or recipe['variants']!=[['curvature_0',0.],['curvature_10',10.],['curvature_30',30.]]:
            raise ValueError('Different declared temporal comparison')
        metrics={'raw':parent['metrics']['input'],'parent_correction':parent['metrics']['candidate']}
        for r in result:
            p=folder/r['variant'];verification=read(p/'verification.json')
            if verification!=r['verification'] or not verification['bounds_and_preservation_passed'] or r['decoded_outside_window_max_error']>1e-5:
                raise ValueError('Candidate preservation evidence changed or failed')
            if read(p/'spec.json')!=spec:raise ValueError('Original edit/specification limits changed')
            verify(p/'verification.json');verify(p/'candidate/character.glb',verification['candidate_sha256'])
            metrics[r['variant']]=verification['metrics']['candidate']
        variants=[]
        for trace,check in zip(traces,engine):
            name=trace['variant'];path=source/'input/character.glb' if name=='raw' else source/'candidate/character.glb' if name=='parent_correction' else folder/name/'candidate/character.glb'
            verify(path,trace['source_sha256'])
            if check['source_sha256']!=trace['source_sha256']:raise ValueError('Engine checks different payload')
            m=metrics[name];acc=np.asarray(trace['root_acceleration_magnitude_m_s2'])
            if acc.shape!=(spec['frames']-2,) or not np.isfinite(acc).all() or abs(acc.max()-m['root_acceleration_max_m_s2'])>1e-8:
                raise ValueError('Root acceleration trace disagrees with independent verifier')
            variants.append(dict(method=name,root_acceleration_max_m_s2=float(acc.max()),root_peak_frame=int(acc.argmax())+1,
                floor_max_m=max(m['floor_depth_max_m'],m['half_frame_floor_depth_max_m']),
                feet={s:dict(p95_m_s=f['support_p95_m_s'],max_m_s=f['support_max_m_s'],last_step_m_s=f['last_step_m_s'],
                    hover_max_m=m['feet'][s]['predicted_support_hover_max_m']) for s,f in trace['feet'].items()}))
        rows.append(dict(case=status['case'],variants=variants,engine_actor_frames=sum(c['frames'] for c in engine),quality_approved=False))
    output.mkdir();(output/'results-snapshot.json').write_bytes(raw)
    summary=dict(at=now(),study=str(study),request_sha256=sha256(study/'request.json'),captured_results_sha256=hashlib.sha256(raw).hexdigest(),
        population=data['rows'],rows=rows,completed_cases=len(rows),planned_cases=len(request['cases']),verified_files=files,
        summarizer_sha256=sha256(__file__),quality_approved=False,
        scope='Matched first-seed development comparison. All declared methods, including failures and regressions, retained. Actual export/engine evidence and frame-window preservation do not establish physical balance, anatomy, semantics or animator quality.')
    save(output/'summary.json',summary)
    lines=['# Root-correction smoothness comparison','',f"{len(rows)} / {len(request['cases'])} cases complete. No quality approval.",'',
        '| Case | Method | Root acceleration max (m/s²) | Peak frame | Floor max (mm) | Left/right support p95 (m/s) |',
        '|---|---|---:|---:|---:|---|']
    for row in rows:
        for v in row['variants']:
            speed='/'.join('missing' if v['feet'][s]['p95_m_s'] is None else f"{v['feet'][s]['p95_m_s']:.6f}" for s in ['Left','Right'])
            lines.append(f"| {row['case']} | {v['method']} | {v['root_acceleration_max_m_s2']:.5f} | {v['root_peak_frame']} | {v['floor_max_m']*1000:.5f} | {speed} |")
    lines+=['',summary['scope']];(output/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(dict(completed_cases=len(rows),planned_cases=len(request['cases'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.study,a.output)
