"""Recorded Python bytes remain runnable while unrelated live source evolves."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import os
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import frozen_key_continuation as runtime
from strep import save,sha256,read

FLAGS=dict(original_selected=True,quality_approved=False,release_approved=False)


def fixture(tmp_path,monkeypatch):
    live=tmp_path/'scripts';live.mkdir();root=Path(runtime.__file__).parent
    for name in ('strep.py','action_worker_lock.py','frozen_key_continuation.py',*runtime.HELPERS):shutil.copyfile(root/name,live/name)
    reports=tmp_path/'reports';reports.mkdir();initial=reports/'initial';parent=reports/'parent';initial.mkdir();parent.mkdir()
    code={'strep.py':(root/'strep.py').read_bytes(),'action_worker_lock.py':(root/'action_worker_lock.py').read_bytes(),
        'motion_math.py':b'VALUE=7\n'}
    job=b'''from pathlib import Path
from strep import read,save
import action_worker_lock
from motion_math import VALUE
def run(recipe,output):
    with action_worker_lock.worker_lock():
        save(Path(output)/'request.json',{'recipe':read(recipe)})
        result={'value':VALUE,'lock_root':str(action_worker_lock.ROOT),'quality_approved':False}
        save(Path(output)/'result.json',result);return result
'''
    audit=b'''from pathlib import Path
from strep import save
import action_worker_lock
from motion_math import VALUE
def run(producer,output,rd,qd):
    with action_worker_lock.worker_lock():
        result={'value':VALUE,'producer_request_sha256':qd}
        save(Path(output)/'result.json',result);return result
'''
    for folder,payload in ((initial,code),(parent,dict(code,**{'native_key_continuation_job.py':job,'audit_native_key_continuation_job.py':audit}))):
        archive=folder/'implementation';archive.mkdir()
        for name,value in payload.items():(archive/name).write_bytes(value)
        save(folder/'request.json',dict(implementation_sha256={name:sha256(archive/name) for name in payload},source_bindings_sha256={}))
        save(folder/'result.json',{})
    oldrecipe=reports/'original-recipe.json';save(oldrecipe,dict(schema='strep-native-key-interval-restoration-v1',
        producer=dict(path=str(initial),result_sha256=sha256(initial/'result.json'),request_sha256=sha256(initial/'request.json'))))
    request=read(parent/'request.json');request.update(schema='strep-native-key-interval-restoration-v1',recipe=read(oldrecipe),
        source_bindings_sha256={str(oldrecipe):sha256(oldrecipe)},**FLAGS);save(parent/'request.json',request)
    save(parent/'result.json',dict(schema=request['schema'],status='complete',source_request_sha256=sha256(parent/'request.json'),**FLAGS))
    proof=reports/'proof.json';save(proof,dict(schema='strep-native-key-restoration-replay-v1',status='complete',
        producer_result_sha256=sha256(parent/'result.json'),producer_request_sha256=sha256(parent/'request.json'),retention_history_replayed=True,**FLAGS))
    recipe=reports/'recipe.json';save(recipe,dict(schema='strep-native-key-continuation-job-v1',parent=dict(path=str(parent),
        result_sha256=sha256(parent/'result.json'),request_sha256=sha256(parent/'request.json'),replay=str(proof),replay_sha256=sha256(proof))))
    monkeypatch.setattr(runtime,'ROOT',tmp_path)
    return recipe,initial,parent,live


def child(live,*args):
    return subprocess.run([sys.executable,str(live/'frozen_key_continuation.py'),*map(str,args)],capture_output=True,text=True,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=30)


def test_recorded_imports_survive_changed_live_source_and_share_project_lock(tmp_path,monkeypatch):
    recipe,initial,parent,live=fixture(tmp_path,monkeypatch);frozen=tmp_path/'reports/runtime';receipt=runtime.build(recipe,frozen)
    (live/'motion_math.py').write_text('VALUE=99\n');before={p:p.read_bytes() for p in parent.rglob('*') if p.is_file()}
    output=tmp_path/'reports/run';result=child(live,'run',frozen,output)
    assert result.returncode==0,result.stderr
    assert read(output/'result.json')['value']==7 and read(output/'result.json')['lock_root']==str(tmp_path)
    assert read(output/'frozen-runtime-execution.json')['runtime_sha256']==sha256(frozen/'runtime.json')
    assert not any((frozen/'scripts').rglob('*.pyc'))
    assert {p:p.read_bytes() for p in before}==before
    replay=tmp_path/'reports/replay';result=child(live,'audit',frozen,output,replay,'--expected-result-sha256','a'*64,'--expected-request-sha256','b'*64)
    assert result.returncode==0,result.stderr
    assert read(replay/'result.json')['value']==7 and read(replay/'frozen-runtime-execution.json')['auditor_executed']


@pytest.mark.parametrize('fault',['archive','conflict','parent','replay','approval','escape'])
def test_invalid_source_rejects_without_runtime(tmp_path,monkeypatch,fault):
    recipe,initial,parent,live=fixture(tmp_path,monkeypatch)
    if fault=='archive':(parent/'implementation/motion_math.py').write_text('VALUE=8\n')
    elif fault=='conflict':
        path=parent/'implementation/motion_math.py';path.write_text('VALUE=8\n');q=read(parent/'request.json');q['implementation_sha256']['motion_math.py']=sha256(path);save(parent/'request.json',q)
        r=read(parent/'result.json');r['source_request_sha256']=sha256(parent/'request.json');save(parent/'result.json',r)
        proof=tmp_path/'reports/proof.json';p=read(proof);p.update(producer_request_sha256=sha256(parent/'request.json'),producer_result_sha256=sha256(parent/'result.json'));save(proof,p)
        q=read(recipe);q['parent'].update(request_sha256=sha256(parent/'request.json'),result_sha256=sha256(parent/'result.json'),replay_sha256=sha256(proof));save(recipe,q)
    elif fault=='parent':(parent/'result.json').write_text('{}\n')
    elif fault=='replay':(tmp_path/'reports/proof.json').write_text('{}\n')
    elif fault=='approval':
        proof=tmp_path/'reports/proof.json';p=read(proof);p['quality_approved']=True;save(proof,p);q=read(recipe);q['parent']['replay_sha256']=sha256(proof);save(recipe,q)
    else:q=read(recipe);q['parent']['path']=str(tmp_path);save(recipe,q)
    frozen=tmp_path/'reports/runtime'
    with pytest.raises((ValueError,KeyError)):runtime.build(recipe,frozen)
    assert not frozen.exists()


@pytest.mark.parametrize('fault',['source','extra-source','package-source','native-module','bytecode','scope','bootstrap','input'])
def test_changed_runtime_cannot_execute(tmp_path,monkeypatch,fault):
    recipe,initial,parent,live=fixture(tmp_path,monkeypatch);frozen=tmp_path/'reports/runtime';runtime.build(recipe,frozen)
    if fault=='source':(frozen/'scripts/motion_math.py').write_text('VALUE=9\n')
    elif fault=='extra-source':(frozen/'scripts/extra.py').write_text('VALUE=9\n')
    elif fault=='package-source':
        path=frozen/'scripts/numpy';path.mkdir();(path/'__init__.py').write_text('VALUE=9\n')
    elif fault=='bytecode':(frozen/'scripts/strep.pyc').write_bytes(b'changed')
    elif fault=='native-module':(frozen/'scripts/numpy.pyd').write_bytes(b'changed')
    elif fault=='input':save(recipe,{})
    else:
        value=read(frozen/'runtime.json');value['quality_approved' if fault=='scope' else 'bootstrap_sha256']=True if fault=='scope' else '0'*64;save(frozen/'runtime.json',value)
    output=tmp_path/'reports/run';result=child(live,'run',frozen,output)
    assert result.returncode!=0 and not output.exists()


def test_frozen_worker_cannot_bypass_live_project_worker_lock(tmp_path,monkeypatch):
    import action_worker_lock
    recipe,initial,parent,live=fixture(tmp_path,monkeypatch);frozen=tmp_path/'reports/runtime';runtime.build(recipe,frozen)
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path)
    with action_worker_lock.worker_lock():
        result=child(live,'run',frozen,tmp_path/'reports/run')
    assert result.returncode!=0 and 'Another local action job is running' in result.stderr
    assert not (tmp_path/'reports/run').exists()


def test_audited_job_additional_recorded_methods_are_reconciled(tmp_path,monkeypatch):
    recipe,initial,parent,live=fixture(tmp_path,monkeypatch);target=tmp_path/'reports/later';target.mkdir();archive=target/'implementation';archive.mkdir()
    (archive/'additional_auditor.py').write_text('VALUE=12\n')
    save(target/'request.json',dict(schema='strep-native-key-continuation-job-v1',implementation_sha256={'additional_auditor.py':sha256(archive/'additional_auditor.py')},source_bindings_sha256={},**FLAGS))
    save(target/'result.json',dict(schema='strep-native-key-continuation-job-v1',status='complete',source_request_sha256=sha256(target/'request.json'),**FLAGS))
    rd,qd=sha256(target/'result.json'),sha256(target/'request.json');frozen=tmp_path/'reports/runtime'
    receipt=runtime.build(recipe,frozen,audit=(target,rd,qd))
    assert receipt['implementation_sha256']['additional_auditor.py']==sha256(archive/'additional_auditor.py')
    assert receipt['audit_producer']==dict(path=str(target),result_sha256=rd,request_sha256=qd)
    result=child(live,'audit',frozen,parent,tmp_path/'reports/rejected','--expected-result-sha256',rd,'--expected-request-sha256',qd)
    assert result.returncode!=0 and not (tmp_path/'reports/rejected').exists()


def test_external_runtime_digest_is_checked_before_execution(tmp_path,monkeypatch):
    recipe,initial,parent,live=fixture(tmp_path,monkeypatch);frozen=tmp_path/'reports/runtime';runtime.build(recipe,frozen)
    result=child(live,'run',frozen,tmp_path/'reports/rejected','--expected-runtime-sha256','0'*64)
    assert result.returncode!=0 and 'Trusted frozen runtime binding changed' in result.stderr
    assert not (tmp_path/'reports/rejected').exists()
