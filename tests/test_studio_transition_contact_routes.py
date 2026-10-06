"""Real in-memory handler dispatch; no HTTP socket or running Studio required."""
import pytest
import io,json,threading
from types import SimpleNamespace
import studio_native_transition_contact_fit as provider
import action_studio_server as server
from test_studio_transition_fit_cache_routes import handler


def test_review_uses_new_provider_and_keeps_failed_checks(monkeypatch):
    value={'id':'job','status':'complete','checks':{'whole_scene_geometry':False},'release_approved':False}
    monkeypatch.setattr(provider,'manifest',lambda job:value)
    h=handler('/api/native-transition-contact-fit-review?id=job');h.do_GET()
    assert h.responses==[(200,value)]


@pytest.mark.parametrize('query',['','?id=','?id=a&id=b','?id=job&extra=','?extra=job'])
def test_exact_review_query_required_before_verification(monkeypatch,query):
    def forbidden(_):raise AssertionError('Invalid query reached verifier')
    monkeypatch.setattr(provider,'manifest',forbidden)
    h=handler('/api/native-transition-contact-fit-review'+query);h.do_GET()
    assert h.responses[0][0]==400


@pytest.mark.parametrize('host',['foreign.test:8768',None])
def test_new_review_retains_loopback_host_gate(monkeypatch,host):
    def forbidden(_):raise AssertionError('Invalid Host reached verifier')
    monkeypatch.setattr(provider,'manifest',forbidden)
    h=handler('/api/native-transition-contact-fit-review?id=job',host);h.do_GET()
    assert h.responses[0][0]==403


def test_download_streams_exact_allowlisted_bytes(monkeypatch,tmp_path):
    path=tmp_path/'bundle.zip';path.write_bytes(b'not-a-real-package-fixture')
    seen=[]
    def resolve(relative):seen.append(relative);return path
    monkeypatch.setattr(provider,'served_file',resolve)
    h=handler('/files/native-transition-contact-fit-jobs/job/candidate-bundle.zip');h.do_GET()
    assert h.statuses==[200] and h.wfile.getvalue()==path.read_bytes()
    assert seen==['native-transition-contact-fit-jobs/job/candidate-bundle.zip']


def test_rejected_download_never_streams_payload(monkeypatch):
    def reject(_):raise ValueError('unpublished')
    monkeypatch.setattr(provider,'served_file',reject)
    h=handler('/files/native-transition-contact-fit-jobs/job/private.json');h.do_GET()
    assert h.responses==[(400,{'error':'unpublished'})]


def post_handler(path,payload):
    h=handler(path);raw=json.dumps(payload).encode()
    h.headers.update({'Origin':'http://127.0.0.1:8768','Content-Type':'application/json','Content-Length':str(len(raw))})
    h.rfile=io.BytesIO(raw);h.server.job_lock=threading.Lock();h.server.worker=None
    return h


def test_catalog_dispatches_after_existing_post_gates(monkeypatch):
    value={'contacts':[],'original_selected':True};seen=[]
    monkeypatch.setattr(provider,'catalog',lambda payload:seen.append(payload) or value)
    h=post_handler('/api/native-transition-contact-fit-catalog',{'source':'fixture'});h.do_POST()
    assert h.responses==[(200,value)] and seen==[{'source':'fixture'}]


@pytest.mark.parametrize('gate',['host','origin','content'])
def test_invalid_post_origin_host_and_content_reject_before_catalog(monkeypatch,gate):
    def forbidden(_):raise AssertionError('Rejected POST reached catalog')
    monkeypatch.setattr(provider,'catalog',forbidden)
    h=post_handler('/api/native-transition-contact-fit-catalog',{})
    h.headers[{'host':'Host','origin':'Origin','content':'Content-Type'}[gate]]={'host':'foreign.test','origin':'http://foreign.test','content':'text/plain'}[gate]
    h.do_POST();assert h.responses[0][0] in (403,415)


def test_generate_dispatches_one_hidden_offline_worker_after_validation(monkeypatch,tmp_path):
    seen=[]
    monkeypatch.setattr(provider,'validate_request',lambda payload:seen.append(('validate',payload)))
    monkeypatch.setattr(provider,'folder_for',lambda job:tmp_path/job)
    def prepare(payload,folder):folder.mkdir();seen.append(('prepare',payload))
    monkeypatch.setattr(provider,'prepare',prepare)
    monkeypatch.setattr(server,'worker_busy',lambda:False);monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    monkeypatch.setattr(server,'offline_environment',lambda:{'HF_HUB_OFFLINE':'1'})
    def launch(argv,**kwargs):seen.append(('launch',argv,kwargs));return SimpleNamespace(poll=lambda:None)
    monkeypatch.setattr(server.subprocess,'Popen',launch)
    h=post_handler('/api/native-transition-contact-fits',{'fixture':True});h.do_POST()
    assert h.responses[0][0]==202 and [r[0] for r in seen]==['validate','prepare','launch']
    assert seen[-1][1][1].endswith('studio_native_transition_contact_fit.py')
    assert seen[-1][2]['env']=={'HF_HUB_OFFLINE':'1'} and 'creationflags' in seen[-1][2]


def test_busy_worker_rejects_before_preparing_a_new_job(monkeypatch):
    monkeypatch.setattr(provider,'validate_request',lambda payload:None)
    def forbidden(*args):raise AssertionError('Busy request created output')
    monkeypatch.setattr(provider,'prepare',forbidden);monkeypatch.setattr(server,'worker_busy',lambda:True)
    h=post_handler('/api/native-transition-contact-fits',{});h.do_POST();assert h.responses[0][0]==409
