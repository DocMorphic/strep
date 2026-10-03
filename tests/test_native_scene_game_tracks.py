"""Exact native clocks and explicit intent; imported matrices here are test doubles."""
from pathlib import Path
import sys,copy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_game_tracks import validate,event_plan,export,crossed
from native_scene_contacts import SceneContacts
from native_engine_clock import clock_wire
from test_native_object_hold_fit import fixture
from strep import read,save,sha256


def setup(tmp_path):
    source,path,spec,scene,edit=fixture(tmp_path)
    for entry in spec['actors'].values():entry['glb']=str(source)
    scene=SceneContacts(spec,tmp_path)
    times=np.unique([0.,1/480,.8,1.,2.])
    request=dict(schema='strep-native-scene-game-tracks-v1',actors={name:dict(root_node=a['rig'].joints[0]) for name,a in scene.actors.items()},
        markers=[dict(id=i,name=i,actor='A',time_s=t,confirmed=confirmed) for i,t,confirmed in [('initial',0.,True),('fraction',1/480,True),('grasp',.8,True),('review',1.,False),('terminal',2.,True)]])
    report,_=scene.evaluate()
    worlds={name:np.array([a['sampler'].sample(t)[a['rig'].joints] for t in times]) for name,a in scene.actors.items()}
    return source,spec,scene,times,request,report,worlds


def test_full_root_reference_deltas_and_unnarrowed_intent_roundtrip(tmp_path):
    source,spec,scene,times,request,report,worlds=setup(tmp_path);before=sha256(source)
    out=tmp_path/'tracks';result=export(scene,request,times,worlds,report,out,source_spec=spec,portable_scene_sha256='a'*64,contact_report_sha256='b'*64)
    assert result['all_root_samples_pass'] and result['root_arrays_roundtrip_exact'] and sha256(source)==before
    assert result['contact_conditions_pass'] is False and result['dispatchable_gameplay_markers']==4
    roots=read(out/'root-motion.json');assert roots['application_mode']=='reference-only-motion-remains-embedded'
    assert roots['times_s']==times.tolist() and roots['source_interpolation_preserved_in_glb']
    for name,entry in roots['actors'].items():
        assert entry['character_glb_sha256']==before and entry['root_node']==request['actors'][name]['root_node']
        matrices=np.array(entry['world_matrices']);deltas=np.array(entry['initial_local_deltas'])
        np.testing.assert_allclose(matrices[0]@deltas,matrices,atol=1e-9,rtol=0)
    assert roots['actors']['B']['world_matrices'][0][0][3]-roots['actors']['A']['world_matrices'][0][0][3]==2
    contacts=read(out/'contacts.json');assert all(not c['runtime_dispatch_allowed'] for c in contacts['contacts'])
    assert [c['intent'] for c in contacts['contacts']]==spec['contacts']
    events=read(out/'events.json');assert events['clock']==clock_wire(times)
    assert not any(e['runtime_dispatch_allowed'] for e in events['events'] if e['kind']=='contact_intent')
    assert all(sha256(out/n)==h for n,h in result['files_sha256'].items())
    with pytest.raises(ValueError,match='Fresh'):export(scene,request,times,worlds,report,out,source_spec=spec,portable_scene_sha256='a'*64,contact_report_sha256='b'*64)


@pytest.mark.parametrize('fault',['missing-actor','extra-actor','bad-root','boolean-root','extra-root','duplicate-marker','off-clock','rounded-clock','boolean-time','unconfirmed-type','unknown-actor','extra-marker','unknown-schema','truncated-clock'])
def test_invalid_root_and_marker_choices_reject(tmp_path,fault):
    _,_,scene,times,r,_,_=setup(tmp_path)
    if fault=='missing-actor':r['actors'].pop('B')
    elif fault=='extra-actor':r['actors']['C']=r['actors']['A']
    elif fault=='bad-root':r['actors']['A']['root_node']=999
    elif fault=='boolean-root':r['actors']['A']['root_node']=True
    elif fault=='extra-root':r['actors']['A']['infer_anatomy']=True
    elif fault=='duplicate-marker':r['markers'][1]['id']=r['markers'][0]['id']
    elif fault=='off-clock':r['markers'][1]['time_s']=.123
    elif fault=='rounded-clock':r['markers'][1]['time_s']=float('0.00208333333333333')
    elif fault=='boolean-time':r['markers'][1]['time_s']=True
    elif fault=='unconfirmed-type':r['markers'][1]['confirmed']=1
    elif fault=='unknown-actor':r['markers'][1]['actor']='C'
    elif fault=='extra-marker':r['markers'][1]['contact_means_grasp']=True
    elif fault=='unknown-schema':r['schema']='old'
    else:times=times[:-1]
    with pytest.raises(ValueError):validate(r,scene,times)


def test_forward_dispatch_preserves_shared_times_skips_and_pauses(tmp_path):
    _,_,scene,times,r,report,_=setup(tmp_path)
    r['markers'].append(dict(id='same-time',name='reaction',actor='B',time_s=.8,confirmed=True))
    plan,_=event_plan(scene,r,times,report)
    whole=crossed(plan,None,2);step=[];previous=None
    for time in times:
        step.extend(crossed(plan,previous,float(time)));assert crossed(plan,float(time),float(time))==[];previous=float(time)
    assert step==whole and len(whole)==5 and [e['actor'] for e in whole if e['time_s']==.8]==['A','B']
    assert crossed(plan,None,0)[0]['id']=='marker:initial'
    assert not any(e['id']=='marker:review' for e in whole)
    with pytest.raises(ValueError,match='Rewind'):crossed(plan,1,.8)
    for value in [-1,np.nan,np.inf,3,True]:
        with pytest.raises(ValueError):crossed(plan,0,value)


def test_failed_imported_root_samples_remain_visible(tmp_path):
    _,spec,scene,times,r,report,worlds=setup(tmp_path);worlds['A'][1,0,0,3]+=.02
    result=export(scene,r,times,worlds,report,tmp_path/'bad',source_spec=spec,portable_scene_sha256='a'*64,contact_report_sha256='b'*64)
    assert not result['all_root_samples_pass'] and result['root_comparisons']['A']['maximum_position_error_m']>.019
    assert not result['quality_approved'] and not result['release_approved'] and result['original_selected']


def test_contact_pass_never_confirms_gameplay_intent(tmp_path):
    _,_,scene,times,r,report,_=setup(tmp_path)
    for row in report['contacts']:row['passed']=True
    report['passed']=True;plan,contacts=event_plan(scene,r,times,report)
    assert all(not e['runtime_dispatch_allowed'] and not e['timing_confirmed'] for e in plan['events'] if e['kind']=='contact_intent')
    assert all(not c['runtime_dispatch_allowed'] for c in contacts['contacts'])


def test_other_root_joints_rotated_placement_and_reordered_choices(tmp_path):
    _,spec,scene,times,r,report,worlds=setup(tmp_path)
    from scipy.spatial.transform import Rotation
    spec['actors']['B']['placement']['rotation_xyzw']=Rotation.from_euler('y',73,degrees=True).as_quat().tolist()
    scene=SceneContacts(spec,tmp_path)
    nodes={name:a['rig'].joints[-1] for name,a in scene.actors.items()}
    r['actors']={name:dict(root_node=nodes[name]) for name in reversed(list(scene.actors))}
    report,_=scene.evaluate();out=tmp_path/'rotated'
    result=export(scene,r,times,worlds,report,out,source_spec=spec,portable_scene_sha256='a'*64,contact_report_sha256='b'*64)
    assert result['all_root_samples_pass']
    roots=read(out/'root-motion.json');placement=np.eye(4);placement[:3,:3]=scene.actors['B']['placement'][1];placement[:3,3]=scene.actors['B']['placement'][0]
    expected=placement@scene.actors['B']['sampler'].sample(float(times[1]))[nodes['B']]
    np.testing.assert_array_equal(roots['actors']['B']['world_matrices'][1],expected)
    assert roots['actors']['A']['array_prefix']=='actor_0' and roots['actors']['B']['array_prefix']=='actor_1'
