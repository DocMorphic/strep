"""Deadlines preserve native time bits and reject unrepresentable prop changes."""
import copy,math,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_prop_physics_timing import first_tick,timing,enforce,MAX_TICK
from native_engine_clock import clock_wire
from scene_prop_ownership import compile_plan
from strep import read,save,sha256


def plan(times,objects=('P',)):
    times=np.asarray(times,dtype=float)
    events=[dict(id='event'+str(i),name='event'+str(i),actor='A',kind='gameplay_intent',sample_index=i,timing_confirmed=True,runtime_dispatch_allowed=True) for i in range(1,len(times)-1)]
    doc=dict(schema='strep-native-scene-game-events-v1',clock=clock_wire(times),events=events)
    grips={n:dict(actor='A') for n in objects}
    commands=[dict(event_id=e['id'],object=objects[(i//2)%len(objects)],grip=objects[(i//2)%len(objects)],action='acquire' if i%2==0 else 'release') for i,e in enumerate(events)]
    return compile_plan(doc,list(objects),grips,commands)


@pytest.mark.parametrize('rate',[60,120,240])
def test_tick_predicate_matches_complete_grid_at_keys_and_both_neighboring_ulps(rate):
    grid=np.arange(2049,dtype=float)/rate
    for k in range(2048):
        for t in (grid[k],np.nextafter(grid[k],math.inf),np.nextafter(grid[k],-math.inf)):
            if t<0:continue
            assert first_tick(float(t),rate)==int(np.searchsorted(grid,t,side='left'))


@pytest.mark.parametrize('value,rate',[(True,60),(-1,60),(float('nan'),60),(float('inf'),60),(1,True),(1,30),(MAX_TICK/60+1,60)])
def test_invalid_or_unbounded_tick_rejects(value,rate):
    with pytest.raises(ValueError):first_tick(value,rate)


def test_exact_deadline_is_distinct_from_full_step_permission_and_never_rounds_source():
    p=plan([0.,1/480,1.,2.]);before=copy.deepcopy(p)
    exact=timing(p,60,0.);loose=timing(p,60,.02)
    assert not exact['contract_satisfied'] and loose['contract_satisfied']
    with pytest.raises(ValueError,match='14.5833333 ms'):enforce(exact)
    triples=np.frombuffer(bytes.fromhex(loose['application_clock']['bytes_hex']),dtype='<f8').reshape(-1,3)
    assert triples[0,0]==1/480 and triples[0,1]==1/60 and triples[0,2]==1/60-1/480
    assert p==before and not loose['quality_approved'] and not loose['release_approved']


def test_ulp_after_a_grid_time_cannot_claim_exact_timing_using_rounded_product():
    rate=60;time=float(np.nextafter(1.,math.inf));p=plan([0.,time,2.])
    assert first_tick(time,rate)==61
    report=timing(p,rate,0.)
    assert not report['within_requested_delay'] and not report['contract_satisfied']


def test_distinct_groups_for_same_prop_on_one_tick_are_not_simultaneously_applied():
    p=plan([0.,.001,.002,1.]);r=timing(p,60,1/60)
    assert r['within_requested_delay'] and not r['distinct_prop_boundaries'] and not r['contract_satisfied']
    assert r['collapsed_prop_transactions']==[dict(object='P',tick=1,first_group=0,later_group=1)]
    with pytest.raises(ValueError,match='collapse'):enforce(r)


def test_different_props_can_share_one_boundary_and_atomic_same_source_groups_stay_one():
    p=plan([0.,.001,.1001,.101,.2,1.],('P','Q'))
    # Separate prop changes at .1001 and .101 have the same 60 Hz boundary.
    r=timing(p,60,1/60)
    assert r['contract_satisfied'] and r['groups'][1]['tick']==r['groups'][2]['tick']
    from study_scene_prop_ownership import fixture
    _,multi=fixture();r=timing(multi,60,1/60)
    assert any(row['objects']==['P','Q'] for row in r['groups']) and r['distinct_prop_boundaries']


@pytest.mark.parametrize('cap',[None,True,-1,float('nan'),float('inf'),10**1000,'0'])
def test_explicit_invalid_limit_is_not_defaulted(cap):
    with pytest.raises(ValueError):timing(plan([0.,.2,.6,1.]),60,cap)


@pytest.mark.parametrize('fault',['clock','count','index','order','prop','duplicate-prop','empty'])
def test_complete_source_population_and_indices_are_required(fault):
    p=plan([0.,.2,.6,1.])
    if fault=='clock':p['clock']['bytes_hex']='00'
    elif fault=='count':p['clock']['count']=True
    elif fault=='index':p['groups'][0]['sample_index']=True
    elif fault=='order':p['groups'].reverse()
    elif fault=='prop':p['groups'][0]['transitions'][0]['object']='ghost'
    elif fault=='duplicate-prop':p['groups'][0]['transitions']*=2
    else:p['groups']=[]
    with pytest.raises(ValueError):timing(p,60,1/60)


def test_public_package_rejects_impossible_contract_and_preserves_failed_request(tmp_path):
    from test_native_scene_runtime import fixture
    from test_scene_prop_runtime import request_for
    from scene_prop_runtime import package
    _,source,_,_,scene,_,_,_=fixture(tmp_path);request=request_for(source,scene)
    request['commands'][0]['event_id']='marker:fraction';request['maximum_application_delay_s']=0.
    path=tmp_path/'request.json';save(path,request);before=source.read_bytes(),path.read_bytes()
    with pytest.raises(ValueError,match='exceeds requested'):package(source,path,tmp_path/'failed')
    assert not (tmp_path/'failed/prop-runtime-assets.zip').exists()
    assert read(tmp_path/'failed/pipeline.json')['status']=='failed' and before==(source.read_bytes(),path.read_bytes())


def test_editable_capture_preserves_and_independently_reconstructs_authored_timing(tmp_path):
    import scene_prop_bake as bake
    from test_scene_prop_bake import setup,trace,request
    from scene_prop_runtime import package
    _,source,scene,events,r,_,clock,poses=setup(tmp_path)
    r['maximum_application_delay_s']=.007
    path=tmp_path/'timed-request.json';save(path,r);exported=tmp_path/'timed-runtime'
    package(source,path,exported);runtime=exported/'prop-runtime-assets.zip'
    compiled=bake.load_package(runtime,tmp_path/'timed-capture')[2]
    actual=trace(scene,events,compiled,clock,poses,'a'*64)
    audit,_=bake.audit_capture(actual,compiled,scene,events,request(runtime),'a'*64)
    assert audit['physical_timing']==compiled['physical_timing']
    assert audit['maximum_application_delay_s']<=.007 and not audit['exact_physical_event_timing_pass']
    audit['physical_timing']['quality_approved']=True
    assert compiled['physical_timing']['quality_approved'] is False
    bad=copy.deepcopy(compiled);bad['physical_timing']['application_clock']['bytes_hex']='00'
    with pytest.raises(ValueError,match='Declared physical timing'):
        bake.audit_capture(actual,bad,scene,events,request(runtime),'a'*64)


@pytest.mark.parametrize('cap',[0.,.016])
def test_source_bound_studio_preview_reports_failure_and_worker_enforces_same_contract(tmp_path,monkeypatch,cap):
    from test_studio_scene_prop_runtime import setup
    import studio_scene_prop_runtime as studio
    payload,_=setup(tmp_path,monkeypatch);payload['request']['commands'][0]['event_id']='marker:fraction'
    payload['request'].update(physics_fps=60,maximum_application_delay_s=cap)
    before=copy.deepcopy(payload);preview=studio.timing_preview(payload)
    assert preview['physical_timing']['contract_satisfied']==(cap>0) and payload==before
    if cap==0:
        with pytest.raises(ValueError,match='exceeds requested'):studio.validate_request(payload)
    else:
        folder=studio.folder_for('timed');studio.prepare(payload,folder);studio.run(folder)
        assert studio.manifest('timed')['status']=='complete'
        r=read(folder/'runtime/project/ownership-v1/prop-runtime.json')
        assert r['physical_timing']==preview['physical_timing']


@pytest.mark.parametrize('fault',['host','origin','type','size','worker','valid'])
def test_new_preview_route_reuses_local_origin_body_budget_and_worker_exclusion(tmp_path,monkeypatch,fault):
    from test_studio_scene_prop_runtime import setup
    from test_studio_native_scene import handler
    from types import SimpleNamespace
    import action_studio_server as server
    payload,_=setup(tmp_path,monkeypatch);payload['request']['maximum_application_delay_s']=0.
    h=handler(payload,'/api/scene-prop-runtime-timing')
    monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    if fault=='host':h.headers['Host']='example.test'
    elif fault=='origin':h.headers['Origin']='https://example.test'
    elif fault=='type':h.headers['Content-Type']='text/plain'
    elif fault=='size':h.headers['Content-Length']='1048577'
    elif fault=='worker':h.server.worker=SimpleNamespace(poll=lambda:None)
    h.do_POST();assert h.responses[-1][0]==dict(host=403,origin=403,type=415,size=400,worker=409,valid=200)[fault]
