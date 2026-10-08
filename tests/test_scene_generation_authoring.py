"""In-memory authoring/handler checks: no HTTP server, model or pose queries."""
import copy
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_studio_server as server
import scene_generation_guides as guides
from test_scene_generation_guides import fixture_scene,fixture_plan
from motion_profile import default_profile


def payload():
    scene=fixture_scene();plan=fixture_plan()
    for name in plan:
        plan[name]['motion_profile']=default_profile()
        plan[name]['motion_profile']['style']='Springy' if name=='A' else 'Deliberate'
    return dict(scene=scene,actor_plan=plan)


def handler(value):
    raw=json.dumps(value).encode('utf-8');h=object.__new__(server.Handler)
    h.path='/api/scene-generation-plan'
    h.headers={'Host':'127.0.0.1:8768','Origin':'http://127.0.0.1:8768','Content-Type':'application/json','Content-Length':str(len(raw))}
    h.server=SimpleNamespace(allowed_hosts={'127.0.0.1:8768'})
    h.rfile=io.BytesIO(raw);h.responses=[];h.respond=lambda code,data:h.responses.append((code,data))
    return h


def test_actor_plan_preview_preserves_profiles_and_full_clock():
    data=payload();original=copy.deepcopy(data);result=guides.authoring_preview(data)
    assert data==original and result['plan']==guides.audit_plan(data['scene'],data['actor_plan'])
    assert all(a['complete_target_frames']==list(range(120)) for a in result['plan']['actors'].values())
    assert result['source_pose_geometry_checked'] is result['generated_motion_checked'] is False
    assert len(result['input_sha256'])==64 and len(result['implementation_sha256'])==7
    changed=copy.deepcopy(data);changed['actor_plan']['B']['motion_profile']['stats'][-1]['value']=80
    assert guides.authoring_preview(changed)['input_sha256']!=result['input_sha256']


@pytest.mark.parametrize('fault',['fields','missing_actor','fps','seeds','duration','profile','budget','missing_partner','missing_object','source_actor','nonfinite'])
def test_invalid_drafts_rejected(fault):
    data=payload()
    if fault=='fields':data['auto_generate']=True
    if fault=='missing_actor':data['actor_plan'].pop('B')
    if fault=='fps':data['scene']['fps']=60
    if fault=='seeds':data['actor_plan']['B']['seeds']=[17,29]
    if fault=='duration':data['actor_plan']['A']['segments'][0]['duration_s']=3
    if fault=='profile':data['actor_plan']['A']['motion_profile']=None
    if fault=='budget':data['actor_plan']['A']['guide_plan']['maximum_frames']=1
    if fault=='missing_partner':data['scene']['contacts'][0]['target']['actor']='missing'
    if fault=='missing_object':data['scene']['contacts'][0]['target']=dict(space='object',object='missing')
    if fault=='source_actor':data['scene']['contacts'][0]['actor']='missing'
    if fault=='nonfinite':data['scene']['objects']={'unused':dict(value=float('nan'))}
    with pytest.raises(ValueError):guides.authoring_preview(data)


def test_single_actor_object_plan_can_be_previewed_without_loading_geometry():
    data=payload();data['scene']['actors'].pop('B');data['actor_plan'].pop('B')
    data['scene']['objects']={'parcel':dict(type='box')}
    data['scene']['contacts'][0]['target']=dict(space='object',object='parcel')
    result=guides.authoring_preview(data)
    assert list(result['plan']['actors'])==['A'] and result['source_pose_geometry_checked'] is False


def test_preview_retains_failed_contact_intent_and_exact_conflict_witness():
    from test_scene_contact_consistency import scene
    data=payload();data['scene']=scene();data['actor_plan'].pop('B')
    result=guides.authoring_preview(data)
    assert result['contact_consistency']['conflicting_pairs']==[[0,1]]
    assert result['contact_consistency']['overlapping_pairs'][0]['overlap_frames']==[50,90]
    assert result['quality_approved'] is result['release_approved'] is False


def test_changed_methods_rejected_during_preview(monkeypatch):
    original=guides.sha256;calls={}
    def changed(path):
        key=str(path);calls[key]=calls.get(key,0)+1
        return original(path) if calls[key]==1 else '0'*64
    monkeypatch.setattr(guides,'sha256',changed)
    with pytest.raises(ValueError,match='methods changed'):guides.authoring_preview(payload())


@pytest.mark.parametrize('fault,code',[('valid',200),('host',403),('origin',403),('type',415),('size',400),('profile',400)])
def test_offline_route_gates_and_no_worker_dispatch(monkeypatch,fault,code):
    def unexpected(*a,**k):raise AssertionError('Planning touched a worker or asset')
    monkeypatch.setattr(server,'worker_busy',unexpected)
    monkeypatch.setattr(server.subprocess,'Popen',unexpected)
    monkeypatch.setattr(server,'external_pair_fit_busy',unexpected)
    data=payload()
    if fault=='profile':data['actor_plan']['B']['motion_profile']=None
    h=handler(data)
    if fault=='host':h.headers['Host']='example.test'
    if fault=='origin':h.headers['Origin']='https://example.test'
    if fault=='type':h.headers['Content-Type']='text/plain'
    if fault=='size':h.headers['Content-Length']='1048577'
    h.do_POST();assert h.responses[-1][0]==code


def test_editor_module_has_exact_allowlisted_route():
    assert server.allowed_file('/scene-generation-plan.js')==server.ROOT/'scripts/scene-generation-plan.js'
    assert server.allowed_file('/scene-generation-plan.js/../secrets.json') is None
