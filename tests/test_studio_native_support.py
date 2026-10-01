"""Synthetic rig jobs exercise native draft isolation and actual HTTP routes."""
import copy
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_native_support import fixture
import studio_native_support as studio
import native_support_job as fitting
import rig_contact_authoring
import action_studio_server as server_module
from strep import read,save,sha256


@pytest.fixture
def setup(tmp_path,monkeypatch):
    source,rig,reader,spec=fixture(tmp_path)
    monkeypatch.setattr(studio,'ROOT',tmp_path)
    monkeypatch.setattr(fitting,'ROOT',tmp_path)
    monkeypatch.setattr(server_module,'ROOT',tmp_path)
    report=dict(root_node=0,mapping=dict(LeftLeg=1,LeftShin=2,LeftFoot=3))
    def bound(job,variant):
        if job!='parent' or variant!='transfer':raise ValueError('Choose an existing character result and version')
        return tmp_path,dict(label='Synthetic motion'),{},report,source
    monkeypatch.setattr(rig_contact_authoring,'source',bound)
    body=dict(source_job='parent',variant='transfer',spec=spec)
    return SimpleNamespace(root=tmp_path,source=source,spec=spec,body=body)


def test_metadata_uses_original_clock_and_explicit_saved_mapping(setup):
    data=studio.metadata('parent','transfer')
    assert data['glb_sha256']==sha256(setup.source)
    assert data['duration_s']==2. and len(data['clocks'])==1
    assert data['mapping']==dict(LeftLeg=1,LeftShin=2,LeftFoot=3)
    assert data['joints'][3]['name']=='ankle-Z' and data['quality_approved'] is False
    assert data['clocks'][0]['times_s'][3]!=.6 # original float32, not invented fps


@pytest.mark.parametrize('fault',['source','variant','hash','root','duration','clock_index','extra','unknown_spec'])
def test_studio_drafts_reject_misbound_or_invalid_inputs(setup,fault):
    body=copy.deepcopy(setup.body)
    if fault=='source':body['source_job']='../../weights'
    if fault=='variant':body['variant']='repeated'
    if fault=='hash':body['spec']['glb_sha256']='0'*64
    if fault=='root':body['spec']['root_node']=1
    if fault=='duration':body['spec']['duration_s']=3
    if fault=='clock_index':body['spec']['supports'][0]['edit_keys']=[1,99]
    if fault=='extra':body['path']=str(setup.source)
    if fault=='unknown_spec':body['spec']['screen']={}
    with pytest.raises(ValueError):studio.validate_request(body)


def completed(setup):
    folder=studio.folder_for('synthetic')
    studio.prepare(setup.body,folder);studio.run(folder)
    return folder,setup.root/'reports/native-support-fit-synthetic'


def test_actual_fit_preserves_failed_trials_and_bound_input(setup):
    digest=sha256(setup.source);folder,output=completed(setup)
    review=studio.manifest('synthetic')
    assert review['retained_input'] and not review['output_support_samples_pass']
    assert review['retention_reason']=='no_proposal_satisfies_all_bounds'
    assert review['versions'][0]['sha256']==review['versions'][1]['sha256']==digest==sha256(setup.source)
    assert len(review['versions'])==6 and all(v['trial']['source_rates_pass'] is False for v in review['versions'][2:])
    assert read(folder/'draft.json')==setup.spec
    assert sha256(output/'candidate.glb')==digest
    assert studio.listing()['jobs'][0]['review']['quality_approved'] is False
    for name in ['candidate.glb','input.glb','trial-0.glb','result.json','support-events.json','root-motion.json']:
        assert studio.served_file('native-support-jobs/synthetic/'+name)==output/name
    (output/'secret.json').write_text('{}')
    for name in ['secret.json','../source.glb','implementation/strep.py','supervisor.log']:
        assert studio.served_file('native-support-jobs/synthetic/'+name) is None


@pytest.mark.parametrize('fault',['source_snapshot','draft','request','result','candidate','trial','support_audit'])
def test_changed_evidence_cannot_be_served_or_reviewed(setup,fault):
    folder,output=completed(setup)
    path={'source_snapshot':folder/'source.glb','draft':folder/'draft.json','request':folder/'request.json',
          'result':output/'result.json','candidate':output/'candidate.glb','trial':output/'trial-2.glb',
          'support_audit':output/'trial-0-support-left-stance.json'}[fault]
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError):studio.manifest('synthetic')
    assert studio.served_file('native-support-jobs/synthetic/candidate.glb') is None
    assert studio.listing()['jobs'][0]['status']=='failed'


def test_snapshot_does_not_follow_later_parent_mutation(setup):
    folder=studio.folder_for('synthetic');studio.prepare(setup.body,folder)
    setup.source.write_bytes(setup.source.read_bytes()+b' ')
    assert studio.frozen(folder)['source_sha256']==setup.spec['glb_sha256']
    studio.run(folder)
    assert studio.manifest('synthetic')['versions'][0]['sha256']==setup.spec['glb_sha256']


def test_failed_worker_is_terminal_and_raw_proposals_stay(setup,monkeypatch):
    folder=studio.folder_for('synthetic');studio.prepare(setup.body,folder)
    def fail(*args):
        out=args[2];out.mkdir();(out/'trial-0.glb').write_bytes(b'Failed synthetic attempt')
        raise ValueError('Synthetic worker failure')
    monkeypatch.setattr(fitting,'run',fail)
    with pytest.raises(ValueError,match='Synthetic worker failure'):studio.run(folder)
    assert studio.listing()['jobs'][0]['status']=='failed'
    assert (setup.root/'reports/native-support-fit-synthetic/trial-0.glb').is_file()


def test_unreachable_stance_keeps_all_reasons_even_without_glb_proposals(setup):
    body=copy.deepcopy(setup.body);body['spec']['supports'][0]['plane']['offset_m']=.8
    folder=studio.folder_for('unreachable');studio.prepare(body,folder);studio.run(folder)
    review=studio.manifest('unreachable')
    assert len(review['versions'])==2 and len(review['trials'])==4
    assert review['retained_input'] and not review['output_support_samples_pass']
    assert all(t['status']=='rejected' and 'unreachable' in t['reason'] for t in review['trials'])


def test_actual_http_submission_and_artifact_guards(setup,monkeypatch):
    monkeypatch.setattr(server_module,'worker_busy',lambda:False)
    monkeypatch.setattr(server_module,'external_pair_fit_busy',lambda:False)
    def launch(args,**kwargs):
        assert Path(args[1]).name=='studio_native_support.py'
        studio.run(Path(args[2]));return SimpleNamespace(pid=99999999,poll=lambda:0)
    monkeypatch.setattr(server_module.subprocess,'Popen',launch)
    server=ThreadingHTTPServer(('127.0.0.1',0),server_module.Handler)
    host=f'127.0.0.1:{server.server_port}';server.allowed_hosts={host};server.worker=None;server.job_lock=threading.Lock()
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def request(method,path,body=None,origin=True):
        connection=HTTPConnection('127.0.0.1',server.server_port)
        headers={'Host':host,'Content-Type':'application/json'}
        if origin:headers['Origin']='http://'+host
        connection.request(method,path,json.dumps(body) if body is not None else None,headers)
        response=connection.getresponse();raw=response.read();status=response.status;connection.close();return status,raw
    try:
        assert request('GET','/api/native-support-source?job=parent&variant=transfer')[0]==200
        assert request('GET','/api/native-support-source?job=parent&job=other&variant=transfer')[0]==400
        assert request('POST','/api/native-support-edits',setup.body,False)[0]==403
        status,raw=request('POST','/api/native-support-edits',setup.body);assert status==202
        job=json.loads(raw)['id']
        status,raw=request('GET','/api/native-support-review?id='+job);assert status==200
        review=json.loads(raw);assert review['retained_input'] and review['quality_approved'] is False
        assert request('GET',review['versions'][0]['url'])[1]==setup.source.read_bytes()
        assert request('GET',f'/files/native-support-jobs/{job}/implementation/strep.py')[0]==404
        assert request('GET','/api/native-support-jobs')[0]==200
        server.worker=SimpleNamespace(poll=lambda:None)
        assert request('POST','/api/native-support-edits',setup.body)[0]==409
    finally:server.shutdown();server.server_close();thread.join()
