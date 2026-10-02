"""Studio opts into frozen decoded refinement without changing its drafts."""
from pathlib import Path
import sys,copy
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_studio_native_support import setup
from test_studio_support_preparation import rounded
import studio_native_support as studio
from strep import read,save,sha256


@pytest.mark.parametrize('choice',[1,0,'true',None,{},[]])
def test_refinement_choice_is_boolean_not_truthiness(setup,choice):
    body=copy.deepcopy(setup.body);body['sampled_support_repair']=choice
    with pytest.raises(ValueError,match='choice'):studio.validate_request(body)


def test_budget_and_paths_cannot_be_supplied_by_studio_clients(setup):
    for name in ('sampled_support_iterations','repair_from','source','output'):
        body=copy.deepcopy(setup.body);body[name]=8
        with pytest.raises(ValueError,match='draft required'):studio.validate_request(body)


def complete(setup,monkeypatch,prepared=False):
    body=rounded(setup,monkeypatch) if prepared else copy.deepcopy(setup.body)
    body['sampled_support_repair']=True;folder=studio.folder_for('refined')
    studio.prepare(body,folder);studio.run(folder)
    return folder,setup.root/'reports/native-support-fit-refined'


@pytest.mark.parametrize('prepared',[False,True])
def test_real_refinement_keeps_original_draft_and_bound_seeds(setup,monkeypatch,prepared):
    folder,fit=complete(setup,monkeypatch,prepared);review=studio.manifest('refined')
    assert review['refinement']==dict(iterations=8) and bool(review['preparation'])==prepared
    assert review['retained_input'] and not review['quality_approved'] and read(folder/'draft.json')==setup.spec
    assert len(review['versions'])==(11 if prepared else 10)
    assert len([v for v in review['versions'] if 'before refinement' in v['label']])==4
    for t in review['trials']:
        audit=studio.served_file(t['refinement']['audit_url'].removeprefix('/files/'))
        assert audit and read(audit)['iterations_limit']==8
        assert t['refinement']['sampled_support_pass']==t['support_samples_pass'] and not t['source_rates_pass']
    for v in review['versions']:
        p=studio.served_file(v['url'].removeprefix('/files/'));assert p and sha256(p)==v['sha256']


@pytest.mark.parametrize('fault',['seed','repair_audit','method'])
def test_changed_refinement_evidence_is_not_served(setup,monkeypatch,fault):
    folder,fit=complete(setup,monkeypatch)
    path={'seed':fit/'trial-0-support-seed.glb','repair_audit':fit/'trial-0-support-repair.json',
        'method':fit/'implementation/native_support_sampled_repair.py'}[fault]
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError):studio.manifest('refined')
    assert studio.served_file('native-support-jobs/refined/trial-0.glb') is None


def test_rebound_result_cannot_change_frozen_refinement_mode(setup,monkeypatch):
    folder,fit=complete(setup,monkeypatch);q=read(fit/'request.json');q['sampled_support_iterations']=1
    save(fit/'request.json',q);r=read(fit/'result.json');r['outputs']['request.json']=sha256(fit/'request.json');save(fit/'result.json',r)
    c=read(folder/'completion.json');c['result_sha256']=sha256(fit/'result.json');save(folder/'completion.json',c)
    with pytest.raises(ValueError,match='refinement mode'):studio.manifest('refined')


def test_old_request_without_new_flags_still_has_no_refinement_claim(setup):
    folder=studio.folder_for('legacy');studio.prepare(setup.body,folder)
    q=read(folder/'request.json');q.pop('sampled_support_repair');q.pop('sampled_support_iterations');save(folder/'request.json',q)
    receipt=read(folder/'prepared.json');receipt['request_sha256']=sha256(folder/'request.json');save(folder/'prepared.json',receipt)
    studio.run(folder);review=studio.manifest('legacy')
    assert review['refinement'] is None and len(review['versions'])==6


def test_http_flag_goes_to_real_worker_and_seeds_are_hash_bound(setup,monkeypatch):
    import json,threading
    from http.client import HTTPConnection
    from http.server import ThreadingHTTPServer
    from types import SimpleNamespace
    import action_studio_server as server_module
    body=copy.deepcopy(setup.body);body['sampled_support_repair']=True
    monkeypatch.setattr(server_module,'worker_busy',lambda:False);monkeypatch.setattr(server_module,'external_pair_fit_busy',lambda:False)
    def launch(args,**kwargs):
        studio.run(Path(args[2]));return SimpleNamespace(pid=99999999,poll=lambda:0)
    monkeypatch.setattr(server_module.subprocess,'Popen',launch)
    server=ThreadingHTTPServer(('127.0.0.1',0),server_module.Handler);host=f'127.0.0.1:{server.server_port}'
    server.allowed_hosts={host};server.worker=None;server.job_lock=threading.Lock()
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def request(method,path,data=None,origin=True):
        connection=HTTPConnection('127.0.0.1',server.server_port);headers={'Host':host,'Content-Type':'application/json'}
        if origin:headers['Origin']='http://'+host
        connection.request(method,path,json.dumps(data) if data is not None else None,headers)
        response=connection.getresponse();value=response.read();status=response.status;connection.close();return status,value
    try:
        assert request('POST','/api/native-support-edits',body,False)[0]==403
        status,data=request('POST','/api/native-support-edits',body);assert status==202;job=json.loads(data)['id']
        status,data=request('GET','/api/native-support-review?id='+job);assert status==200;review=json.loads(data)
        assert review['refinement']['iterations']==8 and review['retained_input']
        seed=next(v for v in review['versions'] if 'before refinement' in v['label'])
        status,data=request('GET',seed['url']);assert status==200
        from hashlib import sha256 as digest
        assert digest(data).hexdigest()==seed['sha256']
        assert request('GET',review['trials'][0]['refinement']['audit_url'])[0]==200
        assert request('GET',f'/files/native-support-jobs/{job}/implementation/native_support_sampled_repair.py')[0]==404
    finally:server.shutdown();server.server_close();thread.join()
