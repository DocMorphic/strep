"""All-seed endpoint comparison with source, bounds, engine and trace checks."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import traceback
import numpy as np
import psutil
from strep import ROOT,read,save,sha256,now
from summarize_breadth_contact import metrics
from support_clip_boundary import retain_end_support

METHODS=['same_weights_continuation','retain_end_support']
VARIANTS=['raw','parent_correction',*METHODS]


def trace_metrics(foot,frames,first):
    speed=np.asarray(foot['speed_m_s'],float);mask=foot['predicted_support_steps']
    if speed.shape!=(frames-1,) or len(mask)!=frames-1 or any(type(v) is not bool for v in mask):
        raise ValueError('Every speed and boolean support step is required')
    if not np.isfinite(speed).all() or np.any(speed<0) or not 1<=first<frames:
        raise ValueError('Invalid speed/window')
    selected=speed[np.asarray(mask)];tail=speed[first-1:];tail_selected=tail[np.asarray(mask)[first-1:]]
    result=dict(p95_m_s=float(np.percentile(selected,95)) if len(selected) else None,
                max_m_s=float(selected.max()) if len(selected) else None,last_step_m_s=float(speed[-1]),
                tail_max_m_s=float(tail.max()),tail_support_max_m_s=float(tail_selected.max()) if len(tail_selected) else None,
                support_steps=len(selected),tail_support_steps=len(tail_selected))
    for published,key in [('support_p95_m_s','p95_m_s'),('support_max_m_s','max_m_s'),('last_step_m_s','last_step_m_s')]:
        found,expected=foot[published],result[key]
        if (found is None)!=(expected is None) or (found is not None and (not np.isfinite(found) or abs(found-expected)>1e-10)):
            raise ValueError('Published trace summary disagrees with complete samples')
    return result


def leaf(status,case,verify):
    folder=Path(status['folder']);recipe=read(folder/'request.json');done=read(folder/'completion.json')
    verify(folder/'request.json',status['request_sha256']);verify(folder/'completion.json',status['completion_sha256'])
    if read(folder/'pipeline.json')['status']!='complete':raise ValueError('Incomplete endpoint leaf')
    for file,key in [('results.json','results_sha256'),('traces.json','traces_sha256'),('engine/audit/verification.json','engine_sha256')]:verify(folder/file,done[key])
    for name,digest in recipe['implementation'].items():verify(folder/'implementation'/name,digest)
    source=Path(recipe['source'])
    if source.name!=case['id']:raise ValueError('Mismatched source case')
    for name,digest in recipe['source_hashes'].items():verify(source/name,digest)
    parent=read(source/'verification.json');parent_request=read(source/'request.json');spec=read(source/'spec.json')
    if not parent['bounds_and_preservation_passed']:raise ValueError('Parent bounds failed')
    if recipe['variants']!=METHODS or recipe['first_editable_frame']!=spec['frames']-12 or recipe['sweeps']!=6 or recipe['max_nfev']!=spec['max_nfev']:
        raise ValueError('Matched endpoint protocol differs')
    if spec['frames']!=case['motion']['frames'] or parent['source_sha256']!=case['files']['character.glb']:
        raise ValueError('Parent input differs from declared population')
    results=read(folder/'results.json')['rows'];traces=read(folder/'traces.json')['variants'];engine=read(folder/'engine/audit/verification.json')['checks']
    if [r['variant'] for r in results]!=METHODS or [t['variant'] for t in traces]!=VARIANTS or [c['id'] for c in engine]!=VARIANTS:
        raise ValueError('Missing/duplicate/reordered methods')
    if any(c['frames']!=spec['frames'] for c in engine) or done['engine_actor_frames']!=sum(c['frames'] for c in engine) or status['engine_actor_frames']!=done['engine_actor_frames']:
        raise ValueError('Incomplete engine population')
    measured={'raw':parent['metrics']['input'],'parent_correction':parent['metrics']['candidate']}
    for row in results:
        variant=row['variant'];target=folder/variant;proof=read(target/'verification.json')
        if proof!=row['verification'] or not proof['bounds_and_preservation_passed'] or row['decoded_prefix_max_error']>1e-5:
            raise ValueError('Bounds or prefix preservation failed')
        if proof['source_sha256']!=parent['source_sha256'] or proof['metrics']['input']!=parent['metrics']['input']:
            raise ValueError('Different raw input verification')
        if read(target/'spec.json')!=spec:raise ValueError('Edit limits changed')
        wanted=copy.deepcopy(parent_request)
        if variant=='retain_end_support':wanted['support']=retain_end_support(wanted['support'],spec['frames'])
        wanted.update(method=variant,parent_correction_sha256=parent['candidate_sha256'],first_editable_frame=recipe['first_editable_frame'],max_sweeps=6)
        if read(target/'request.json')!=wanted:raise ValueError('Continuation changed more than the declared EOF policy')
        verify(target/'verification.json');verify(target/'request.json');verify(target/'candidate/character.glb',proof['candidate_sha256'])
        measured[variant]=proof['metrics']['candidate']
    variants=[]
    for trace,check in zip(traces,engine):
        name=trace['variant'];path=source/'input/character.glb' if name=='raw' else source/'candidate/character.glb' if name=='parent_correction' else folder/name/'candidate/character.glb'
        verify(path,trace['source_sha256'])
        if check['source_sha256']!=trace['source_sha256'] or set(trace['feet'])!={'Left','Right'}:raise ValueError('Trace/engine/feet mismatch')
        variants.append(dict(method=name,metrics=metrics(measured[name]),feet={s:trace_metrics(f,spec['frames'],recipe['first_editable_frame']) for s,f in trace['feet'].items()}))
    return dict(case=case['id'],rig=case['rig'],seed=case['motion']['seed'],variants=variants,engine_actor_frames=done['engine_actor_frames'],quality_approved=False)


def summarize(study,output):
    request=read(study/'request.json');parent=Path(request['parent']);protocol=read(parent/'protocol.json')
    files={}
    def verify(path,digest=None):
        path=Path(path);actual=sha256(path)
        if digest is not None and actual!=digest:raise ValueError('Changed evidence: '+str(path))
        files[str(path)]=actual
    verify(parent/'protocol.json',request['parent_protocol_sha256'])
    for name,digest in request['implementation'].items():verify(study/'implementation'/name,digest)
    raw=(study/'results.json').read_bytes();statuses=json.loads(raw)['rows']
    if request['cases']!=[c['id'] for c in protocol['cases']] or [r['case'] for r in statuses]!=request['cases'] or len(statuses)!=10:
        raise ValueError('Require the complete ten-case population')
    if read(study/'pipeline.json')['status'] not in ['complete','complete_with_failures']:raise ValueError('Batch is not terminal')
    verify(study/'results.json',read(study/'completion.json')['results_sha256'])
    rows=[]
    for status,case in zip(statuses,protocol['cases']):
        if status['status']=='complete':rows.append(leaf(status,case,verify))
        elif status['status'] not in ['failed','source_failed']:raise ValueError('Unfinished population member')
    save(output/'summary.json',dict(at=now(),planned_cases=10,completed_cases=len(rows),population=statuses,rows=rows,
         results_sha256=hashlib.sha256(raw).hexdigest(),request_sha256=sha256(study/'request.json'),verified_files=files,
         summarizer_sha256=sha256(__file__),quality_approved=False,
         scope='All five seeds and both rigs retained. Same initializer, edit limits and six-sweep twelve-frame tail; only EOF support policy differs. Complete speed traces and extrema verified. Predicted support remains unconfirmed; p95 does not hide reported maxima. No physical balance, action, held-out or animator approval.'))
    (output/'results-snapshot.json').write_bytes(raw)
    lines=['# Complete endpoint population','',f'{len(rows)} / 10 inputs have complete export/engine evidence. All statuses are retained.','',
           '| Case | Method | Support p95 max (m/s) | Support speed max (m/s) | Last step max (m/s) | Floor (mm) | Root acceleration (m/s²) |',
           '|---|---|---:|---:|---:|---:|---:|']
    def fmt(v):return 'missing' if v is None else f'{v:.6f}'
    for row in rows:
        for v in row['variants']:
            m=v['metrics'];speeds=[f['max_m_s'] for f in v['feet'].values()]
            lines.append('| '+' | '.join([row['case'],v['method'],fmt(m['support_speed_p95_max_m_s']),fmt(max(speeds) if all(s is not None for s in speeds) else None),fmt(max(f['last_step_m_s'] for f in v['feet'].values())),fmt(m['floor_m']*1000),fmt(m['root_acceleration_max_m_s2'])])+' |')
    lines+=['','Full per-foot tail maxima, support sample counts, hover, local rotation steps and every failure status remain in summary.json. No quality approval.']
    (output/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf8')


def run(study,output,wait=False):
    study,output=Path(study).resolve(),Path(output).resolve();output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    source=read(study/'request.json');proc=psutil.Process()
    names=['summarize_support_endpoints.py','summarize_breadth_contact.py','support_clip_boundary.py','audit_paired_guides.py','strep.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    request=dict(at=now(),pid=proc.pid,created=proc.create_time(),study=str(study),source_request_sha256=sha256(study/'request.json'),owner=dict(pid=source['pid'],created=source['created']),implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False)
    save(output/'request.json',request)
    def phase(status,**details):save(output/'pipeline.json',dict(status=status,at=now(),quality_approved=False,**details));print(status,flush=True)
    try:
        if wait:
            from audit_paired_guides import await_owner
            phase('waiting_for_exact_endpoint_owner');await_owner(request['owner'],'pid','created',study,{'complete','complete_with_failures'})
        if sha256(study/'request.json')!=request['source_request_sha256']:raise ValueError('Batch request changed')
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Summarizer dependency changed')
        phase('summarizing');summarize(study,output)
        save(output/'completion.json',dict(at=now(),summary_sha256=sha256(output/'summary.json'),quality_approved=False));phase('complete')
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);p.add_argument('--wait',action='store_true');a=p.parse_args();run(a.study,a.output,a.wait)
