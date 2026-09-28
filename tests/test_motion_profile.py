import copy
import hashlib
import json
import sys
import threading
import urllib.request
import urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from motion_profile import default_profile,brief,resolved_segments,validate
from action_requests import validate_batch,validate_request,conditioning_texts,request_digest,timeline


def request():
    return dict(id='reach-and-bow',label='Reach and bow',segments=[dict(prompt='A person reaches upward with both hands.',duration_s=3),dict(prompt='The person bows to the audience.',duration_s=2)],seeds=[41],scene_requirements=[])


def profiled():
    r=request();p=default_profile();p['training']='Parkour';p['stats']=[p['stats'][0],p['stats'][-1]];p['stats'][0]['value']=85;r['motion_profile']=p;return r


def batch(r):return dict(schema_version=1,requests=[r])


def test_legacy_requests_and_digest_are_unchanged():
    r=request();b=batch(r)
    assert request_digest(b)==hashlib.sha256(json.dumps(b,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    assert brief(r) is None and resolved_segments(r)==r['segments']
    assert 'conditioning_prompt' not in timeline(r)[0]


def test_profile_applies_to_every_arbitrary_action_and_retains_original():
    r=profiled();original=copy.deepcopy(r);validate_request(r);result=brief(r)
    assert r==original
    assert len(result['segments'])==2
    assert all('Quick, precise changes of direction.' in s['conditioning_prompt'] for s in result['segments'])
    assert result['unmapped_stats']==[dict(id='endurance',label='Endurance',value=50)]
    assert result['response_validated'] is False
    assert result['segments'][0]['original_prompt']==r['segments'][0]['prompt']
    assert timeline(r)[-1]['end_frame_exclusive']==150
    from kimodo.sanitize import sanitize_texts
    assert conditioning_texts(batch(r))==sorted(set(sanitize_texts([s['prompt'] for s in resolved_segments(r)])))


def test_rule_boundaries_custom_stats_and_cache_invalidation():
    r=profiled();r['motion_profile']['stats'][0].update(id='focus',label='Focus',levels=['Tentative motion.','Controlled motion.','Decisive motion.'])
    texts=[]
    for value in [0,33,34,66,67,100]:
        r['motion_profile']['stats'][0]['value']=value;texts.append(brief(r)['description'])
    assert texts[0]==texts[1] and texts[2]==texts[3] and texts[4]==texts[5] and len(set(texts))==3
    changed=copy.deepcopy(r);changed['motion_profile']['stats'][0]['levels'][2]='Sustained confident motion.'
    assert request_digest(batch(r))!=request_digest(batch(changed))
    assert conditioning_texts(batch(r))!=conditioning_texts(batch(changed))
    changed=copy.deepcopy(r);changed['motion_profile']['stats'][1]['value']=90
    assert conditioning_texts(batch(r))==conditioning_texts(batch(changed))
    assert request_digest(batch(r))!=request_digest(batch(changed))


@pytest.mark.parametrize('patch',[{'value':True},{'value':101},{'levels':['a']},{'levels':['a','','c']},{'id':'../oops'},{'ignored':'x'}])
def test_invalid_stats_fail_before_generation(patch):
    r=profiled();r['motion_profile']['stats'][0].update(patch)
    with pytest.raises(ValueError):validate_batch(batch(r))


def test_duplicate_stats_and_oversized_resolved_text_rejected():
    r=profiled();r['motion_profile']['stats'].append(copy.deepcopy(r['motion_profile']['stats'][0]))
    with pytest.raises(ValueError):validate_request(r)
    r=profiled();r['segments'][0]['prompt']='a'*999
    with pytest.raises(ValueError,match='Resolved'):validate_request(r)


def test_profile_cache_rejects_changed_effective_description(tmp_path,monkeypatch):
    import torch
    from safetensors.torch import save_file
    import action_encoder
    from strep import save,sha256
    r=profiled();b=batch(r);texts=conditioning_texts(b);entries={}
    for i,text in enumerate(texts):
        name=str(i)+'.safetensors';save_file({'features':torch.full((1,1,4096),float(i))},str(tmp_path/name));entries[text]=dict(file=name,sha256=sha256(tmp_path/name))
    monkeypatch.setattr(action_encoder,'source_check',lambda:'pin');monkeypatch.setattr(action_encoder,'revisions',lambda:{'encoder':'pin'})
    save(tmp_path/'manifest.json',dict(status='complete',request_sha256=request_digest(b),kimodo_commit='pin',encoder_revisions={'encoder':'pin'},entries=entries))
    encoder=action_encoder.ActionEncoder(tmp_path,b);features,lengths=encoder(texts)
    assert features.shape==(2,1,4096) and lengths==[1,1]
    r['motion_profile']['training']='Ballet'
    with pytest.raises(ValueError,match='provenance'):action_encoder.ActionEncoder(tmp_path,b)


def test_read_only_brief_endpoint_works_while_generation_busy(monkeypatch):
    import action_studio_server as server_module
    monkeypatch.setattr(server_module,'worker_busy',lambda:True)
    server=ThreadingHTTPServer(('127.0.0.1',0),server_module.Handler)
    host='127.0.0.1:'+str(server.server_port);server.allowed_hosts={host};server.worker=None;server.job_lock=threading.Lock()
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    try:
        def post(origin):
            return urllib.request.urlopen(urllib.request.Request('http://'+host+'/api/motion-brief',data=json.dumps(profiled()).encode(),headers={'Content-Type':'application/json','Origin':origin}))
        with post('http://'+host) as response:assert json.load(response)['motion_brief']['segments'][0]['conditioning_prompt']==resolved_segments(profiled())[0]['prompt']
        with pytest.raises(urllib.error.HTTPError) as error:post('http://example.com')
        assert error.value.code==403
        with urllib.request.urlopen('http://'+host+'/api/motion-profile-template') as response:validate(json.load(response))
    finally:server.shutdown();server.server_close();worker.join()
