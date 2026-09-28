"""One preregistered actual-foot acceleration pilot, queued after held-support study."""
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
from support_acceleration_clip import run as fit
from study_support_release import compare
from verify_breadth_contact import verify
from support_velocity_traces import run as trace
from run_godot_rig_import import run as engine
from study_whole_support_breadth import check_engine


def prepare(output):
    output=Path(output).resolve()
    base=ROOT/'reports/support-release-hold-v1'
    original=read(base/'request.json')
    selected=next(c for c in original['cases'] if c['id']=='motion-036-rig-01')
    held=base/'takes'/selected['id']
    if read(held/'pipeline.json')['status']!='complete':raise ValueError('Pilot baseline incomplete')
    outcome=next(r for r in read(base/'results.json')['rows'] if r['id']==selected['id'])
    if outcome['status']!='complete':raise ValueError('Pilot validation incomplete')
    for name,digest in outcome['files'].items():
        if sha256(held/name)!=digest:raise ValueError('Changed retained baseline')
    proof=ROOT/'reports/support-acceleration-skin-proof-v1.json'
    proof_data=read(proof)
    if not proof_data['passed']:raise ValueError('Skin derivative proof missing')
    for path,digest in proof_data['implementation'].items():
        if sha256(path)!=digest:raise ValueError('Proof implementation changed')
    selected=dict(selected,baseline_dynamics=str(held/'release-dynamics.json'))
    selected['inputs']=dict(selected['inputs'])
    for name in ['release-dynamics.json','request.json','spec.json','comparison.json','candidate/character.glb']:
        selected['inputs'][str(held/name)]=sha256(held/name)
    selected['inputs'][str(proof)]=sha256(proof)
    owner=read(base/'runner.json')
    process=psutil.Process(owner['pid'])
    if abs(process.create_time()-owner['created'])>1e-3:raise ValueError('Dependency PID reused')
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    names=set(original['implementation'])|{'foot_acceleration.py','support_acceleration_fit.py',
        'relax_support_acceleration.py','support_acceleration_clip.py','study_support_acceleration.py',
        'verify_support_acceleration.py'}
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    request=dict(original,at=now(),cases=[selected],planned_engine_actor_frames=3*selected['frames'],
        implementation={n:sha256(output/'implementation'/n) for n in sorted(names)},
        wait_for=dict(folder=str(base),pid=owner['pid'],created=owner['created'],request_sha256=sha256(base/'request.json')),
        method='actual_foot_acceleration_excess',acceleration_weight=1.,
        scope='One development pilot on a measured release snap; no held-out quality or coverage claim.',
        baseline_caps='max(raw, original whole-support prior) acceleration per interior frame and foot plus1e-5m/s2; full3D centroid; soft penalty',
        budget='One 150-frame pilot, six sweeps, no weight sweep or extra iterations',
        chosen_reason='Backpedal rig01 has a right-foot release19 acceleration increase3.47 to7.45m/s2 with a6.84mm residual offset.',
        baseline_comparison='Original whole-support prior and raw, exactly the previous release screen. Also retain every-frame acceleration excess; held-support reference remains retained in inputs.')
    save(output/'request.json',request)
    save(output/'results.json',dict(rows=[dict(id=selected['id'],status='pending')],quality_approved=False))
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
        phase('waiting_for_exact_support_release_study');await_owner(dependency,'pid','created',Path(dependency['folder']),{'complete'})
        if sha256(Path(dependency['folder'])/'request.json')!=dependency['request_sha256']:raise ValueError('Dependency identity changed')
        data=read(output/'results.json');total=0
        with threadpool_limits(limits=1):
            for case,row in zip(request['cases'],data['rows']):
                validate();dest=output/'takes'/case['id'];prior=Path(case['prior']);row.update(status='running',started_at=now());save(output/'results.json',data);phase('fitting',case=case['id'])
                try:
                    fit(case['source'],dest,case['baseline_dynamics']);proof=verify(dest);new_trace=trace(dest);spec=read(dest/'spec.json');support=read(dest/'request.json')['support']
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
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','run']);p.add_argument('output',type=Path);a=p.parse_args()
    if a.command=='prepare':prepare(a.output)
    else:run(a.output)
