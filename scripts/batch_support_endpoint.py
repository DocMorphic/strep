"""Consume completed immutable parent cases; retain every planned outcome."""
import argparse
import os
from pathlib import Path
import shutil
import time
import traceback
import psutil
from strep import ROOT,read,save,sha256,now


def run(parent,first_result,output):
    parent,first_result,output=[Path(p).resolve() for p in [parent,first_result,output]]
    if output.exists():raise ValueError('Preserve prior batch')
    protocol=read(parent/'protocol.json');owner=read(parent/'runner.json')
    reused_request=read(first_result/'request.json')
    if read(first_result/'pipeline.json')['status']!='complete' or reused_request['source']!=str(parent/'takes'/protocol['cases'][0]['id']):
        raise ValueError('Reuse only the completed first declared case')
    names=sorted(set(reused_request['implementation'])|{'batch_support_endpoint.py'})
    for name,digest in reused_request['implementation'].items():
        if sha256(first_result/'implementation'/name)!=digest or sha256(ROOT/'scripts'/name)!=digest:
            raise ValueError('Endpoint method changed before batch: '+name)
    output.mkdir();(output/'implementation').mkdir()
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    request=dict(at=now(),pid=os.getpid(),created=psutil.Process().create_time(),parent=str(parent),
        parent_protocol_sha256=sha256(parent/'protocol.json'),parent_owner=owner,
        cases=[c['id'] for c in protocol['cases']],reused_first_case=str(first_result),
        reused_request_sha256=sha256(first_result/'request.json'),
        implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False,
        scope='Same ten declared five-seed/two-rig development inputs. Each completed parent gets both identical-budget tail continuations. Reuse the already-completed first case without rerunning it. Preserve all failed, missing and unchanged-policy cases. No held-out or human approval.')
    save(output/'request.json',request)
    data=dict(rows=[dict(case=c['id'],status='pending') for c in protocol['cases']],quality_approved=False)
    save(output/'results.json',data)
    def phase(status,**kwargs):
        save(output/'pipeline.json',dict(status=status,at=now(),quality_approved=False,**kwargs));print(status,kwargs,flush=True)
    def verify_implementation():
        if sha256(parent/'protocol.json')!=request['parent_protocol_sha256']:raise ValueError('Parent protocol changed')
        for name,digest in request['implementation'].items():
            if sha256(output/'implementation'/name)!=digest or sha256(ROOT/'scripts'/name)!=digest:
                raise ValueError('Frozen batch implementation changed: '+name)
    try:
        from study_support_endpoint import run as study
        for index,row in enumerate(data['rows']):
            case=row['case'];phase('waiting_for_parent_case',case=case)
            while True:
                snapshot=read(parent/'results.json');matches=[r for r in snapshot['rows'] if r['case']==case]
                if len(matches)!=1:raise ValueError('Missing/duplicate parent population member')
                current=matches[0]
                if current['status'] in ['complete','failed']:break
                try:
                    proc=psutil.Process(owner['pid'])
                    if proc.create_time()!=owner['created']:raise RuntimeError('Parent PID reused; inspect before continuing')
                    alive=proc.is_running()
                except psutil.NoSuchProcess:alive=False
                if not alive:
                    current=dict(status='failed',error='Parent ended before this case completed');break
                time.sleep(5)
            if current['status']=='failed':
                row.update(status='source_failed',error=current.get('error','Parent case failed'));save(output/'results.json',data);continue
            try:
                verify_implementation();source=parent/'takes'/case
                if read(source/'verification.json')!=current['verification']:
                    raise ValueError('Parent candidate evidence changed')
                if sha256(parent/'engine-groups'/case/'audit/verification.json')!=current['engine_sha256']:
                    raise ValueError('Parent engine evidence changed')
                folder=first_result if index==0 else output/'cases'/case
                if index:
                    folder.parent.mkdir(exist_ok=True);phase('running_case',case=case);study(source,folder)
                else:
                    if sha256(folder/'request.json')!=request['reused_request_sha256']:raise ValueError('Reused request changed')
                leaf_request=read(folder/'request.json');completion=read(folder/'completion.json')
                if leaf_request['source']!=str(source) or read(folder/'pipeline.json')['status']!='complete':raise ValueError('Incomplete/mismatched leaf')
                for name,digest in leaf_request['source_hashes'].items():
                    if sha256(source/name)!=digest:raise ValueError('Endpoint leaf source changed')
                for name,key in [('results.json','results_sha256'),('traces.json','traces_sha256'),('engine/audit/verification.json','engine_sha256')]:
                    if sha256(folder/name)!=completion[key]:raise ValueError('Endpoint leaf evidence changed')
                engine=read(folder/'engine/audit/verification.json')
                if len(engine['checks'])!=4 or sum(c['frames'] for c in engine['checks'])!=600:
                    raise ValueError('Incomplete endpoint engine population')
                row.update(status='complete',folder=str(folder),reused=index==0,request_sha256=sha256(folder/'request.json'),
                    completion_sha256=sha256(folder/'completion.json'),engine_actor_frames=600,finished_at=now())
            except Exception as exc:
                row.update(status='failed',error=str(exc),traceback=traceback.format_exc(),finished_at=now())
            save(output/'results.json',data)
        phase('complete' if all(r['status']=='complete' for r in data['rows']) else 'complete_with_failures')
        save(output/'completion.json',dict(at=now(),results_sha256=sha256(output/'results.json'),quality_approved=False))
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('first_result',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.parent,a.first_result,a.output)
