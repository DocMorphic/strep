"""Saved two-grip object trajectories retain actor bytes and original contracts."""
from pathlib import Path
import sys,copy,subprocess
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_geometry import closed_fixture,policy
from native_scene_contacts import SceneContacts
from native_object_hold_fit import request_for,proposal,run,audit_bounds
from engine_contact_sampling import frame_populations
from strep import save,read,sha256


def fixture(tmp_path,shape='sphere'):
    source,path,spec=closed_fixture(tmp_path);spec['actors']['B']=copy.deepcopy(spec['actors']['A'])
    spec['actors']['B']['placement']['translation_m']=[2.,0,0]
    scene=SceneContacts(spec,tmp_path);actor=scene.actors['A'];node=actor['rig'].primitives[0]['node']
    geo=dict(schema='strep-object-geometry-v1',shape=shape,
        **({'radius_m':.8} if shape=='sphere' else ({'size_m':[1.6,.2,.2]} if shape=='box' else {'radius_m':.8,'height_m':.2})))
    keys=[]
    for t,offset in [(0.,0.),(.8,.003),(.9,-.003),(1.,.003),(2.,0.)]:
        center=actor['rig'].vertices(actor['sampler'].sample(t))[4]+[.8,offset,0.]
        keys.append(dict(time_s=t,translation_m=center.tolist(),rotation_xyzw=[0,0,0,1]))
    spec['objects']={'item':dict(geometry=geo,keyframes=keys)}
    spec['contacts']=[dict(id=name,actor=a,vertices=[[node,0,v]],reduction='individual',
        target=dict(space='object',object='item',points_m=[[x,0.,0.]]),mode='hold',interval_s=[.8,1.],
        limits=dict(position_m=.005,relative_speed_m_s=.005))
        for name,a,v,x in [('left-grip','A',4,-.8),('right-grip','B',0,.8)]]
    save(path,spec);digest=sha256(path);scene=SceneContacts(spec,tmp_path)
    request=dict(schema='strep-native-object-hold-fit-v1',contacts_sha256=digest,object='item',
        contact_ids=['left-grip','right-grip'],edit_window_s=[.6,1.2],maximum_translation_m=.01,
        maximum_rotation_degrees=2.,maximum_keys=3601)
    return source,path,spec,scene,request


@pytest.mark.parametrize('shape',['sphere','box','cylinder'])
def test_complete_frame_clock_and_saved_interpolation_repair_both_grips(tmp_path,shape):
    source,path,spec,scene,request=fixture(tmp_path,shape);before,_=scene.evaluate();assert not before['passed']
    original=sha256(source);keys,arrays=proposal(scene,request,sha256(path))
    candidate=copy.deepcopy(spec);candidate['objects']['item']['keyframes']=keys
    derived=SceneContacts(candidate,tmp_path);after,_=derived.evaluate()
    assert after['passed'] and sha256(source)==original
    assert candidate['actors']==spec['actors']
    for population in frame_populations([.8,1.]):assert np.isin(population['times_s'],arrays['times_s']).all()
    assert len(keys)<=request['maximum_keys'] and np.all(np.diff(arrays['times_s'])>0)
    assert audit_bounds(scene,derived,request,np.unique(np.r_[arrays['times_s'],np.linspace(0,2,61)]))['passed']


@pytest.mark.parametrize('fault',['binding','extra','object','duplicate','unknown','window','translation-bool','rotation-large','key-bool','interval','multiple'])
def test_invalid_object_fit_requests_reject(tmp_path,fault):
    _,path,_,scene,value=fixture(tmp_path)
    if fault=='binding':value['contacts_sha256']='0'*64
    if fault=='extra':value['guess_actions']=True
    if fault=='object':value['object']='missing'
    if fault=='duplicate':value['contact_ids']=['left-grip']*2
    if fault=='unknown':value['contact_ids'][0]='missing'
    if fault=='window':value['edit_window_s']=[.8,1.2]
    if fault=='translation-bool':value['maximum_translation_m']=True
    if fault=='rotation-large':value['maximum_rotation_degrees']=46.
    if fault=='key-bool':value['maximum_keys']=True
    if fault=='interval':scene.rows[1]['authored']['interval_s']=[.81,1.]
    if fault=='multiple':scene.rows[0]['ids']=np.repeat(scene.rows[0]['ids'],2)
    with pytest.raises(ValueError):request_for(scene,value,sha256(path))


def test_key_budget_rejects_complete_population_without_truncation(tmp_path):
    _,path,_,scene,request=fixture(tmp_path);request['maximum_keys']=2
    with pytest.raises(ValueError,match='resource budget'):proposal(scene,request,sha256(path))


def test_pose_bound_failure_is_visible_and_source_actor_is_unchanged(tmp_path):
    source,path,spec,scene,request=fixture(tmp_path);keys,arrays=proposal(scene,request,sha256(path))
    request['maximum_translation_m']=.0001;candidate=copy.deepcopy(spec);candidate['objects']['item']['keyframes']=keys
    audit=audit_bounds(scene,SceneContacts(candidate,tmp_path),request,arrays['times_s'])
    assert not audit['passed'] and audit['maximum_translation_m']>.002
    assert sha256(source)==spec['actors']['A']['sha256']


def test_full_run_snapshots_contacts_bounds_and_all_geometry_clocks(tmp_path):
    source,path,spec,scene,request=fixture(tmp_path);rp=tmp_path/'request.json';save(rp,request)
    pp=tmp_path/'policy.json';save(pp,policy(path));out=tmp_path/'fit';result=run(path,rp,pp,out)
    assert result['sampled_constraints_pass'] and result['actor_bytes_unchanged'] and result['original_selected']
    assert result['geometry_samples']>=result['keys'] and result['keys']>5
    assert not result['quality_approved'] and not result['release_approved'] and not result['training_admitted']
    for n,snapshot in result['actor_snapshots'].items():assert sha256(out/snapshot['path'])==spec['actors'][n]['sha256']
    candidate=read(out/'proposal-contacts.json');assert candidate['objects']['item']['keyframes'][0]==spec['objects']['item']['keyframes'][0]
    assert candidate['objects']['item']['keyframes'][-1]==spec['objects']['item']['keyframes'][-1]
    assert read(out/'pipeline.json')['status']=='complete'
    assert all(sha256(out/'implementation'/n)==h for n,h in result['implementation_sha256'].items())
    with pytest.raises(ValueError,match='Fresh'):run(path,rp,pp,out)


def test_rigid_point_kernel_import_does_not_load_model_dependencies():
    code="import sys;sys.path.insert(0,'scripts');from two_hand_rigidity import fit_two_grips;assert 'torch' not in sys.modules;assert 'scene_constraints' not in sys.modules;assert 'build_soma_preview' not in sys.modules"
    result=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
