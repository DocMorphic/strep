import copy
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_engine_clock import clock_wire
from scene_prop_ownership import compile_plan,consistent_pose


def fixture():
    times=np.array([0.,.2,.6,1.,1.305,2.])
    entries=[('grab','A',1),('other','B',1),('partial','A',2),('giver','A',3),('receiver','B',3),('drop','B',4)]
    events=[dict(id=id,name=id,actor=actor,kind='gameplay_intent',sample_index=i,timing_confirmed=True,runtime_dispatch_allowed=True) for id,actor,i in entries]
    document=dict(schema='strep-native-scene-game-events-v1',clock=clock_wire(times),events=events)
    grips={n:dict(actor=a) for n,a in [('AL','A'),('AR','A'),('BL','B'),('BR','B')]}
    commands=[dict(event_id=e,object=o,grip=g,action=a) for e,o,g,a in [
        ('grab','P','AL','acquire'),('grab','P','AR','acquire'),('other','Q','BR','acquire'),
        ('partial','P','AL','release'),('giver','P','AR','release'),('receiver','P','BL','acquire'),
        ('drop','P','BL','release'),('drop','Q','BR','release')]]
    return document,grips,commands


def test_all_hands_objects_partial_release_atomic_handoff_and_final_release():
    doc,grips,commands=fixture();before=copy.deepcopy((doc,grips,commands));p=compile_plan(doc,['P','Q'],grips,commands)
    assert (doc,grips,commands)==before and p['clock']==doc['clock']
    assert p['groups'][0]['transitions'][0]['after']==['AL','AR']
    assert p['groups'][1]['transitions'][0]['after']==['AR'] and not p['groups'][1]['transitions'][0]['last_grip_released']
    handoff=p['groups'][2]['transitions'][0]
    assert handoff['before']==['AR'] and handoff['after']==['BL'] and handoff['mode']=='held' and not handoff['last_grip_released']
    assert all(t['last_grip_released'] and t['mode']=='released' for t in p['groups'][3]['transitions'])
    assert p['groups'][3]['time_s']==1.305
    reversed_plan=compile_plan(doc,['Q','P'],grips,list(reversed(commands)))
    assert reversed_plan==p
    assert all(p[k] is False for k in ('ownership_verified','physics_verified','quality_approved','release_approved'))


def test_one_hand_can_transfer_objects_atomically_without_transient_double_ownership():
    doc,grips,_=fixture()
    commands=[dict(event_id=e,object=o,grip='AL',action=a) for e,o,a in [('grab','P','acquire'),('partial','P','release'),('partial','Q','acquire')]]
    p=compile_plan(doc,['P','Q'],grips,commands)
    assert p['groups'][1]['transitions'][0]['after']==[] and p['groups'][1]['transitions'][1]['after']==['AL']


@pytest.mark.parametrize('fault',['contact','unconfirmed','dispatch','actor','duplicate','contradiction','release-unowned','acquire-owned','double-prop','unknown-object','unknown-grip','extra','bool-index','clock-count','clock-byte','source-order','event-duplicate','grip-extra','pose-bool','pose-large','pose-nan'])
def test_invalid_intent_clock_ownership_and_limits_reject(fault):
    doc,grips,commands=fixture();options={}
    if fault=='contact':doc['events'][0].update(kind='contact_intent',runtime_dispatch_allowed=False)
    elif fault=='unconfirmed':doc['events'][0].update(timing_confirmed=False,runtime_dispatch_allowed=False)
    elif fault=='dispatch':doc['events'][0]['runtime_dispatch_allowed']=False
    elif fault=='actor':grips['AL']['actor']='B'
    elif fault=='duplicate':commands.append(copy.deepcopy(commands[0]))
    elif fault=='contradiction':commands.append(dict(commands[0],action='release'))
    elif fault=='release-unowned':commands[0]['action']='release'
    elif fault=='acquire-owned':commands[3]['action']='acquire'
    elif fault=='double-prop':commands.append(dict(commands[0],object='Q'))
    elif fault=='unknown-object':commands[0]['object']='ghost'
    elif fault=='unknown-grip':commands[0]['grip']='ghost'
    elif fault=='extra':commands[0]['guess_action']=True
    elif fault=='bool-index':doc['events'][0]['sample_index']=True
    elif fault=='clock-count':doc['clock']['count']+=1
    elif fault=='clock-byte':doc['clock']['bytes_hex']='00'
    elif fault=='source-order':doc['events'].reverse()
    elif fault=='event-duplicate':doc['events'].append(copy.deepcopy(doc['events'][-1]))
    elif fault=='grip-extra':grips['AL']['infer_anatomy']=True
    elif fault=='pose-bool':options['position_tolerance_m']=True
    elif fault=='pose-large':options['rotation_tolerance_rad']=.011
    elif fault=='pose-nan':options['position_tolerance_m']=float('nan')
    with pytest.raises(ValueError):compile_plan(doc,['P','Q'],grips,commands,**options)


def test_pose_consistency_uses_all_grips_and_never_averages_or_selects_a_good_subset():
    a=np.eye(4);a[:3,3]=[1,2,3];b=a.copy();b[:3,3]+=[.0005,0,0]
    p,r=consistent_pose({'right':b,'left':a})
    assert np.array_equal(p,a) and r['primary']=='left' and set(r['grips'])=={'left','right'}
    assert r['grips']['right']['position_m']==pytest.approx(.0005)
    b[0,3]+=.001
    with pytest.raises(ValueError,match='incompatible'):consistent_pose({'right':b,'left':a})
    b=a.copy();b[:3,:3]=Rotation.from_rotvec([0,.002,0]).as_matrix()
    with pytest.raises(ValueError,match='incompatible'):consistent_pose({'right':b,'left':a})


@pytest.mark.parametrize('fault',['scale','reflection','nonfinite','last-row','empty','bool-limit','large-limit'])
def test_pose_provider_guards(fault):
    a=np.eye(4);poses={'left':a};options={}
    if fault=='scale':a[0,0]=2
    elif fault=='reflection':a[0,0]=-1
    elif fault=='nonfinite':a[0,3]=float('nan')
    elif fault=='last-row':a[3,0]=1
    elif fault=='empty':poses={}
    elif fault=='bool-limit':options['position_tolerance_m']=True
    elif fault=='large-limit':options['rotation_tolerance_rad']=.02
    with pytest.raises(ValueError):consistent_pose(poses,**options)


def test_native_float32_key_and_fractional_times_keep_exact_binary_identity():
    doc,grips,commands=fixture();times=np.array([0.,float(np.float32(.2)),.6000000000000001,1.,1.305,2.]);doc['clock']=clock_wire(times)
    for e in doc['events']:e['time_s']=999 # Descriptive JSON is not authoritative.
    p=compile_plan(doc,['P','Q'],grips,commands)
    assert p['groups'][0]['time_s']==times[1] and p['groups'][1]['time_s']==times[2]
    assert p['clock']==clock_wire(times)


def test_independent_engine_reference_and_native_column_layout():
    from study_scene_prop_ownership import reference,observed_matrix
    p=reference('P',1.);q=reference('Q',1.)
    np.testing.assert_allclose(p[:3,3],[-.38,1.58,0],atol=1e-12)
    np.testing.assert_allclose(q[:3,3],[.38,1.58,0],atol=1e-12)
    columns=np.vstack([p[:3,:3].T,p[:3,3]])
    np.testing.assert_array_equal(observed_matrix(columns),p)
    with pytest.raises(ValueError):observed_matrix(p)


def test_source_bound_compiler_cli_preserves_inputs_and_refuses_overwrite(tmp_path):
    import hashlib,json,subprocess
    doc,grips,commands=fixture();event=tmp_path/'events.json';request=tmp_path/'request.json';output=tmp_path/'ownership.json'
    event.write_text(json.dumps(doc),encoding='utf8');request.write_text(json.dumps(dict(schema='strep-scene-prop-ownership-request-v1',objects=['P','Q'],grips=grips,commands=commands)),encoding='utf8')
    before=(event.read_bytes(),request.read_bytes())
    cli=[sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/scene_prop_ownership.py'),'--events',str(event),'--request',str(request),'--output',str(output)]
    run=subprocess.run(cli,capture_output=True,text=True);assert run.returncode==0,run.stderr
    result=json.loads(output.read_text());assert result['source_events_file_sha256']==hashlib.sha256(before[0]).hexdigest() and result['ownership_request_file_sha256']==hashlib.sha256(before[1]).hexdigest()
    saved=output.read_bytes();run=subprocess.run(cli,capture_output=True,text=True)
    assert run.returncode!=0 and output.read_bytes()==saved and (event.read_bytes(),request.read_bytes())==before
