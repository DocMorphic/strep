"""Matched release-weight ablation on all four already completed support cases."""
import argparse
from pathlib import Path
import shutil
import traceback
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from support_release_hold import hold_until_release
from support_release_metrics import measure
from support_release_clip import run as fit
from verify_breadth_contact import verify
from support_velocity_traces import run as trace
from run_godot_rig_import import run as engine
from study_whole_support_breadth import check_engine


def compare(prior,proof,old_trace,new_trace,dynamics):
    checks={};values={}
    for side in ['Left','Right']:
        old=next(r for r in old_trace['variants'] if r['variant']=='candidate')['feet'][side]
        raw,new=[next(r for r in new_trace['variants'] if r['variant']==v)['feet'][side] for v in ['input','candidate']]
        checks[side+'_support_max_no_worse']=new['predicted_support_max_m_s']<=old['predicted_support_max_m_s']+1e-6
        checks[side+'_support_max_raw_cap']=new['predicted_support_max_m_s']<=max(.05,raw['predicted_support_max_m_s'])+1e-6
        checks[side+'_support_p95_no_worse']=new['predicted_support_p95_m_s']<=old['predicted_support_p95_m_s']+1e-6
        checks[side+'_hover_no_worse']=proof['metrics']['candidate']['feet'][side]['predicted_support_hover_max_m']<=max(.01,prior['metrics']['candidate']['feet'][side]['predicted_support_hover_max_m'])+1e-7
        tracks=[dynamics[v]['feet'][side] for v in ['input','prior','candidate']]
        checks[side+'_global_acceleration_no_worse']=tracks[2]['global_acceleration_max_m_s2']<=max(t['global_acceleration_max_m_s2'] for t in tracks[:2])+1e-5
        if any(len(t['releases'])!=len(tracks[0]['releases']) for t in tracks):raise ValueError('Release population differs')
        release=[]
        for a,b,c in zip(*[t['releases'] for t in tracks]):
            if a['release_frame']!=b['release_frame'] or a['release_frame']!=c['release_frame']:raise ValueError('Release clock differs')
            release.append(c['acceleration_max_m_s2']<=max(a['acceleration_max_m_s2'],b['acceleration_max_m_s2'])+1e-5)
        checks[side+'_every_release_acceleration_no_worse']=all(release)
        values[side]=dict(raw_max_m_s=raw['predicted_support_max_m_s'],prior_max_m_s=old['predicted_support_max_m_s'],candidate_max_m_s=new['predicted_support_max_m_s'],release_count=len(release),release_acceleration_regressions=sum(not v for v in release))
    a=prior['metrics']['candidate'];b=proof['metrics']['candidate'];raw=proof['metrics']['input']
    checks['floor_no_worse_than_prior_or_5mm']=max(b['floor_depth_max_m'],b['half_frame_floor_depth_max_m'])<=max(.005,a['floor_depth_max_m'],a['half_frame_floor_depth_max_m'])+1e-7
    for key in ['root_acceleration_max_m_s2','local_rotation_step_max_degrees']:
        checks[key+'_no_worse']=b[key]<=max(a[key],raw[key])+1e-5
    checks['decoded_hard_limits_pass']=proof['bounds_and_preservation_passed']
    return dict(checks=checks,passes_development_screen=all(checks.values()),feet=values,quality_approved=False,
        scope='Frozen numerical ablation screen. Passing cannot approve semantics, contact labels, anatomy or animator quality.')


def prepare(summary,wait_for,output):
    summary,wait_for,output=[Path(p).resolve() for p in (summary,wait_for,output)]
    snapshot=read(summary/'summary.json');study=Path(snapshot['study']);protocol=read(study/'protocol.json')
    if sha256(study/'protocol.json')!=snapshot['protocol_sha256']:raise ValueError('Study protocol changed')
    completed=[r['id'] for r in snapshot['rows'] if r['status']=='complete']
    if len(completed)!=4:raise ValueError('Declared ablation requires exact four-completed-case snapshot')
    # First examine the largest observed support-speed failure, then the dance.
    order=['motion-036-rig-02','motion-011-rig-01','motion-036-rig-01','motion-036-rig-03']
    if set(completed)!=set(order):raise ValueError('Declared development population differs')
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir();cases=[];diagnostic=[]
    for identifier in order:
        folder=study/'takes'/identifier;case=next(c for c in protocol['cases'] if c['id']==identifier)
        if read(folder/'pipeline.json')['status']!='complete':raise ValueError('Prior fit incomplete')
        request=read(folder/'request.json');spec=read(folder/'spec.json');hold_until_release(request['support'],spec['frames'])
        inputs={str(folder/name):sha256(folder/name) for name in ['request.json','spec.json','verification.json','traces.json','fit-summary.json','input/character.glb','input/report.json','candidate/character.glb','candidate/report.json']}
        inputs.update({str(Path(case['source'])/name):digest for name,digest in case['files'].items()})
        cases.append(dict(id=identifier,prior=str(folder),source=case['source'],frames=case['motion']['frames'],inputs=inputs))
        traces=read(folder/'traces.json')['variants']
        for side in ['Left','Right']:
            a,b=[r['feet'][side] for r in traces];f=b['peak_step_end_frame'];w=request['support']['guides'][side]['weights']
            diagnostic.append(dict(case=identifier,side=side,peak_step_end_frame=f,raw_speed_at_candidate_peak_m_s=a['horizontal_speed_m_s'][f-1],
                candidate_peak_speed_m_s=b['predicted_support_max_m_s'],draft_weights=w[f-1:f+1],
                is_release_tail=any(i['side']==side and i['end_frame_exclusive']==f+1 for i in request['support']['intervals'])))
    names=sorted(set(protocol['implementation'])|{'study_support_release.py','support_release_hold.py','support_release_clip.py','support_release_metrics.py','study_whole_support_breadth.py'})
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    owner=read(wait_for/'request.json')
    request=dict(at=now(),source_protocol=str(study/'protocol.json'),source_protocol_sha256=sha256(study/'protocol.json'),
        summary=str(summary/'summary.json'),summary_sha256=sha256(summary/'summary.json'),cases=cases,
        wait_for=dict(folder=str(wait_for),pid=owner['pid'],created=owner['created'],request_sha256=sha256(wait_for/'request.json')),
        implementation={n:sha256(output/'implementation'/n) for n in names},resources=protocol['resources'],
        sweeps=6,support_weight=40.,curvature_weight=10.,initialization='Same zero edits on raw transfer',
        planned_engine_actor_frames=3*sum(c['frames'] for c in cases),quality_approved=False,
        acceptance='No increase over prior in predicted-support max/p95; max also <=max(0.05m/s,raw). Hover <=max(10mm,prior); floor <=max(5mm,prior). Root acceleration, local rotation step, global foot acceleration and every release-window acceleration <=max(raw,prior). Decoded hard limits and actual engine import. Numerical development only, no human/release approval.')
    save(output/'request.json',request);save(output/'release-diagnostic.json',dict(rows=diagnostic,input_snapshots={c['id']:c['inputs'] for c in cases},quality_approved=False))
    save(output/'results.json',dict(rows=[dict(id=c['id'],status='pending') for c in cases],quality_approved=False))
    save(output/'pipeline.json',dict(at=now(),status='prepared',quality_approved=False))


def run(output):
    output=Path(output).resolve();request=read(output/'request.json')
    if read(output/'pipeline.json')['status']!='prepared':raise ValueError('Preserve existing run')
    proc=psutil.Process();save(output/'runner.json',dict(pid=proc.pid,created=proc.create_time(),at=now()))
    def phase(status,**kw):save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**kw));print(status,kw,flush=True)
    def validate():
        for path,digest in [(request['source_protocol'],request['source_protocol_sha256']),(request['summary'],request['summary_sha256']),*request['resources'].items(),*[item for c in request['cases'] for item in c['inputs'].items()]]:
            if sha256(path)!=digest:raise ValueError('Input changed: '+str(path))
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:raise ValueError('Implementation changed: '+name)
    try:
        validate();dependency=request['wait_for']
        from audit_paired_guides import await_owner
        phase('waiting_for_exact_dynamic_witness_trial');await_owner(dependency,'pid','created',Path(dependency['folder']),{'complete_pending_export_and_full_geometry','complete_no_accepted_step'})
        if sha256(Path(dependency['folder'])/'request.json')!=dependency['request_sha256']:raise ValueError('Dependency identity changed')
        data=read(output/'results.json');total=0
        with threadpool_limits(limits=1):
            for case,row in zip(request['cases'],data['rows']):
                validate();dest=output/'takes'/case['id'];prior=Path(case['prior']);row.update(status='running',started_at=now());save(output/'results.json',data);phase('fitting',case=case['id'])
                try:
                    fit(case['source'],dest);proof=verify(dest);new_trace=trace(dest);spec=read(dest/'spec.json');support=read(dest/'request.json')['support']
                    phase('release_dynamics',case=case['id']);dynamics={v:measure(path,spec,support) for v,path in [('input',dest/'input/character.glb'),('prior',prior/'candidate/character.glb'),('candidate',dest/'candidate/character.glb')]}
                    save(dest/'release-dynamics.json',dynamics)
                    decision=compare(read(prior/'verification.json'),proof,read(prior/'traces.json'),new_trace,dynamics);save(dest/'comparison.json',decision)
                    group=output/'engine-groups'/case['id'];group.mkdir(parents=True)
                    checks=[dict(id=case['id']+'-'+v,path=str(path),sha256=sha256(path),frames=case['frames'],fps=30) for v,path in [('input',dest/'input/character.glb'),('prior',prior/'candidate/character.glb'),('candidate',dest/'candidate/character.glb')]]
                    save(group/'manifest.json',dict(cases=checks));phase('engine',case=case['id']);engine(group,group/'audit')
                    eproof=read(group/'audit/verification.json');frames=check_engine(eproof,checks);total+=frames
                    row.update(status='complete',decision=decision,engine_actor_frames=frames,files={name:sha256(dest/name) for name in ['verification.json','traces.json','release-dynamics.json','comparison.json','candidate/character.glb']},engine_verification_sha256=sha256(group/'audit/verification.json'))
                except Exception as exc:row.update(status='failed',error=str(exc),traceback=traceback.format_exc())
                row['finished_at']=now();save(output/'results.json',data)
        validate();failed=any(r['status']!='complete' for r in data['rows'])
        if not failed and total!=request['planned_engine_actor_frames']:raise ValueError('Engine population differs')
        save(output/'completion.json',dict(at=now(),results_sha256=sha256(output/'results.json'),engine_actor_frames=total,quality_approved=False))
        phase('complete_with_failures' if failed else 'complete')
    except BaseException as exc:phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','run']);p.add_argument('output',type=Path)
    p.add_argument('--summary',type=Path,default=ROOT/'reports/whole-support-breadth-interim-v4');p.add_argument('--wait-for',type=Path,default=ROOT/'reports/dynamic-witness-cuts-v1');a=p.parse_args()
    if a.command=='prepare':prepare(a.summary,a.wait_for,a.output)
    else:run(a.output)
