"""Freeze both first-seed rigs for the clipped-start comparison."""
import argparse
import os
from pathlib import Path
import shutil
import traceback
import psutil
from strep import ROOT,read,save,sha256,now


def run(output):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Preserve earlier temporal comparison')
    cases=[dict(id='motion-006-rig-01',source=str(ROOT/'reports/support-temporal-v1/motion-006-rig-01')),
           dict(id='motion-006-rig-02',source=str(ROOT/'reports/support-temporal-v1/motion-006-rig-02'))]
    names=set()
    for case in cases:
        source=Path(case['source'])
        if read(source/'pipeline.json')['status']!='complete':raise ValueError('Incomplete endpoint initializer')
        case['request_sha256']=sha256(source/'request.json');case['completion_sha256']=sha256(source/'completion.json')
        for name,digest in read(source/'request.json')['implementation'].items():
            if sha256(source/'implementation'/name)!=digest or sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Source implementation changed')
            names.add(name)
    names.update(['run_support_start_pair.py','study_support_start.py','support_clip_start.py','relax_support_start.py'])
    output.mkdir();(output/'implementation').mkdir()
    for name in sorted(names):shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    request=dict(at=now(),pid=os.getpid(),created=psutil.Process().create_time(),cases=cases,
        start_policies=['same_start_weights','retain_start_support'],initializer_method='curvature_10',window_frames_inclusive=[0,11],sweeps=6,
        implementation={n:sha256(output/'implementation'/n) for n in sorted(names)},quality_approved=False,
        scope='First declared development seed on both rigs, initialized with the lower tested nonzero curvature setting10. Same six-sweep budget for unchanged-weight control and generated clipped-start ramp removal. Preserve the prior interior and endpoint corrections and every failed candidate; no held-out optimality or realism claim.')
    save(output/'request.json',request)
    data=dict(rows=[dict(case=c['id'],status='pending') for c in cases],quality_approved=False);save(output/'results.json',data)
    def phase(status,**kwargs):
        save(output/'pipeline.json',dict(status=status,at=now(),quality_approved=False,**kwargs));print(status,kwargs,flush=True)
    try:
        from study_support_start import run as study
        for case,row in zip(cases,data['rows']):
            source=Path(case['source'])
            if sha256(source/'request.json')!=case['request_sha256'] or sha256(source/'completion.json')!=case['completion_sha256']:
                raise ValueError('Frozen initializer changed')
            for name,digest in request['implementation'].items():
                if sha256(output/'implementation'/name)!=digest or sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Frozen temporal implementation changed: '+name)
            folder=output/case['id'];row.update(status='running',folder=str(folder));save(output/'results.json',data);phase('running_case',case=case['id'])
            try:
                study(source,folder)
                completion=read(folder/'completion.json')
                if completion['engine_actor_frames']!=600:raise ValueError('Incomplete four-clip engine evidence')
                row.update(status='complete',completion_sha256=sha256(folder/'completion.json'),engine_actor_frames=600)
            except Exception as exc:
                row.update(status='failed',error=str(exc),traceback=traceback.format_exc())
            save(output/'results.json',data)
        phase('complete' if all(r['status']=='complete' for r in data['rows']) else 'complete_with_failures')
        save(output/'completion.json',dict(at=now(),results_sha256=sha256(output/'results.json'),quality_approved=False))
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();run(a.output)
