"""Exact complete-input reuse matches fresh whole-scene geometry decisions."""
from pathlib import Path
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_geometry_cache as cache
import native_scene_geometry as geometry
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from strep import read,save,sha256
from test_native_scene_geometry import closed_fixture,policy


def setup(tmp_path,*,partner=False,inside=False,second_object=False,second_plane=False):
    source,path,spec=closed_fixture(tmp_path)
    if partner:
        spec['actors']['B']=copy.deepcopy(spec['actors']['A']);spec['actors']['B']['placement']['translation_m']=[5.,0.,0.]
    center=[10.,0.,0.]
    if inside:
        scene=SceneContacts(spec,tmp_path);actor=scene.actors['A'];center=actor['rig'].vertices(actor['sampler'].sample(1.)).mean(0).tolist()
    spec['objects']['ball']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.05),
        keyframes=[dict(time_s=0.,translation_m=center,rotation_xyzw=[0.,0.,0.,1.])])
    if second_object:
        spec['objects']['another']=copy.deepcopy(spec['objects']['ball']);spec['objects']['another']['keyframes'][0]['translation_m'][0]+=1.
    save(path,spec);p=policy(path,planes=dict(floor=dict(normal_world=[0.,1.,0.],offset_m=-3.)))
    p['clock']['times_s']=[0.,.25,.5,.75,1.,1.25,1.5,1.75,2.]
    if second_plane:p['planes']['wall']=dict(normal_world=[1.,0.,0.],offset_m=-20.)
    policy_path=tmp_path/'geometry-policy.json';save(policy_path,p)
    output=tmp_path/'donor';result=cache.evaluate_to_cache(path,policy_path,output)
    return source,path,spec,p,policy_path,output,result


def compare(path,spec,p,output):
    expected,arrays=geometry.evaluate(SceneContacts(spec,path.parent),p,sha256(path))
    actual=read(output/'geometry.json');assert actual==expected
    with np.load(output/'observations.npz',allow_pickle=False) as a:
        for key,value in arrays.items():np.testing.assert_array_equal(a[key],value)
        assert len(a['times_s'])==len(actual['samples'])
    assert not actual['quality_approved'] and not actual['release_approved']


def candidate(tmp_path,path,spec):
    scene=SceneContacts(spec,tmp_path);digest=sha256(path)
    permissions=dict(schema='strep-native-scene-edit-v1',contacts_sha256=digest,actors=dict(A=dict(window_s=[.6,1.4],protected_s=[],knots_s=[.6,1.,1.4],
        tracks=[dict(node=3,path='rotation',maximum_change=5.)],maximum_joint_displacement_m=.02)))
    edits=SceneEdits(permissions,scene,digest);x=edits.initial.copy();x[0]=.01
    out=tmp_path/'candidate.glb';edits.export('A',x,out)
    proposed=copy.deepcopy(spec);proposed['actors']['A'].update(glb=out.name,sha256=sha256(out))
    target=tmp_path/'candidate-contacts.json';save(target,proposed)
    return target,proposed


def test_identical_complete_inputs_reuse_every_time_and_numeric_array_without_queries(tmp_path,monkeypatch):
    _,path,spec,p,pp,donor,_=setup(tmp_path);d=cache.Donor(donor)
    # Equal inputs require zero new collision queries, not merely fewer queries.
    original=geometry.evaluate
    monkeypatch.setattr(geometry,'evaluate',lambda *a,**k:pytest.fail('Unchanged samples must use complete donor evidence'))
    out=tmp_path/'identical';result=cache.evaluate_to_cache(path,pp,out,donor=d)
    assert result['reused_samples']==9 and result['fresh_samples']==0 and result['complete_samples']==9
    monkeypatch.setattr(geometry,'evaluate',original);compare(path,spec,p,out)


@pytest.mark.parametrize('partner',[False,True])
def test_native_edit_reuses_only_exact_unchanged_frames_and_keeps_every_condition(tmp_path,partner):
    _,path,spec,p,pp,donor,_=setup(tmp_path,partner=partner);target,proposed=candidate(tmp_path,path,spec)
    new_policy=copy.deepcopy(p);new_policy['contacts_sha256']=sha256(target);new_path=tmp_path/'new-policy.json';save(new_path,new_policy)
    out=tmp_path/'mixed';result=cache.evaluate_to_cache(target,new_path,out,donor=cache.Donor(donor))
    assert 0<result['reused_samples']<9 and result['fresh_samples']+result['reused_samples']==9
    assert result['fresh_samples']>=3 # Exact endpoint queries remain mandatory for a fresh subset.
    assert {v['kind'] for v in read(out/'reuse.json')['samples']}=={'fresh','reused-exact-full-inputs'}
    compare(target,proposed,new_policy,out)


@pytest.mark.parametrize('fault',['placement','shape','object-pose','plane','limit','topology','tiny-vertex'])
def test_changed_query_inputs_never_reuse_unrelated_matching_actor_poses(tmp_path,fault):
    source,path,spec,p,pp,donor,_=setup(tmp_path)
    proposed=copy.deepcopy(spec);new_policy=copy.deepcopy(p)
    if fault=='placement':proposed['actors']['A']['placement']['translation_m'][0]+=.001
    if fault=='shape':proposed['objects']['ball']['geometry']['radius_m']=.06
    if fault=='object-pose':proposed['objects']['ball']['keyframes'][0]['translation_m'][0]+=.001
    if fault=='plane':new_policy['planes']['floor']['offset_m']-=.01
    if fault=='limit':new_policy['limits']['penetration_m']=.004
    if fault=='tiny-vertex':
        from gltf_tools import write_glb,append_accessor
        from rig_asset import RigAsset
        rig=RigAsset.load(source);doc=copy.deepcopy(rig.document);data=bytearray(rig.binary)
        points=rig.primitives[0]['positions'].astype(np.float32).copy();points[0,0]=np.nextafter(points[0,0],np.float32(np.inf))
        doc['meshes'][0]['primitives'][0]['attributes']['POSITION']=append_accessor(doc,data,points,'VEC3')
        changed=tmp_path/'one-ulp.glb';write_glb(changed,doc,data);proposed['actors']['A'].update(glb=changed.name,sha256=sha256(changed))
    if fault=='topology':
        from gltf_tools import write_glb
        from rig_asset import RigAsset,array
        rig=RigAsset.load(source);doc=copy.deepcopy(rig.document)
        # Reverse the primitive's index triples without changing vertex data.
        primitive=doc['meshes'][0]['primitives'][0];indices=array(doc,rig.binary,primitive['indices']).copy().reshape(-1,3)[:,::-1].ravel()
        # Write an explicit unsigned replacement accessor.
        data=bytearray(rig.binary)
        while len(data)%4:data.append(0)
        values=indices.astype('<u2');doc['bufferViews'].append(dict(buffer=0,byteOffset=len(data),byteLength=values.nbytes));data.extend(values.tobytes())
        doc['accessors'].append(dict(bufferView=len(doc['bufferViews'])-1,componentType=5123,count=len(values),type='SCALAR'))
        primitive['indices']=len(doc['accessors'])-1;changed=tmp_path/'reversed.glb';write_glb(changed,doc,data)
        proposed['actors']['A'].update(glb=changed.name,sha256=sha256(changed))
    target=tmp_path/'different-contacts.json';save(target,proposed);new_policy['contacts_sha256']=sha256(target)
    new_path=tmp_path/'different-policy.json';save(new_path,new_policy);out=tmp_path/'different'
    result=cache.evaluate_to_cache(target,new_path,out,donor=cache.Donor(donor))
    assert result['reused_samples']==0 and result['fresh_samples']==9
    compare(target,proposed,new_policy,out)


def test_additional_declared_clock_is_queried_without_thinning_other_samples(tmp_path):
    _,path,spec,p,pp,donor,_=setup(tmp_path);new=copy.deepcopy(p);new['clock']['times_s']=sorted(p['clock']['times_s']+[.125])
    added=tmp_path/'added-policy.json';save(added,new);out=tmp_path/'added'
    result=cache.evaluate_to_cache(path,added,out,donor=cache.Donor(donor))
    assert result['complete_samples']==10 and result['fresh_samples']==3 and result['reused_samples']==7
    compare(path,spec,new,out)


def test_local_moving_object_change_requeries_only_its_actual_changed_full_inputs(tmp_path):
    _,path,spec,p,_,folder,_=setup(tmp_path);proposed=copy.deepcopy(spec)
    proposed['objects']['ball']['keyframes']=[dict(time_s=float(t),translation_m=[10.+(.01 if t==1. else 0.),0.,0.],
        rotation_xyzw=[0.,0.,0.,1.]) for t in np.linspace(0.,2.,11)]
    target=tmp_path/'moving-object.json';save(target,proposed);new=copy.deepcopy(p);new['contacts_sha256']=sha256(target)
    pp=tmp_path/'moving-policy.json';save(pp,new);out=tmp_path/'moving'
    result=cache.evaluate_to_cache(target,pp,out,donor=cache.Donor(folder))
    assert 0<result['reused_samples']<9 and result['fresh_samples']+result['reused_samples']==9
    compare(target,proposed,new,out)


@pytest.mark.parametrize('order',['objects','planes'])
def test_reordered_scene_conditions_preserve_the_new_complete_population_order(tmp_path,order):
    _,path,spec,p,_,folder,_=setup(tmp_path,second_object=order=='objects',second_plane=order=='planes')
    proposed=copy.deepcopy(spec);new=copy.deepcopy(p)
    if order=='objects':proposed['objects']=dict(reversed(list(proposed['objects'].items())))
    else:new['planes']=dict(reversed(list(new['planes'].items())))
    target=tmp_path/'reordered-contacts.json';save(target,proposed);new['contacts_sha256']=sha256(target)
    pp=tmp_path/'reordered-policy.json';save(pp,new);out=tmp_path/'reordered'
    cache.evaluate_to_cache(target,pp,out,donor=cache.Donor(folder))
    compare(target,proposed,new,out)


def test_failed_sampled_geometry_stays_failed_when_all_inputs_are_reused(tmp_path):
    _,path,spec,p,pp,donor,source=setup(tmp_path,inside=True);assert not source['sampled_conditions_pass']
    out=tmp_path/'failure-copy';result=cache.evaluate_to_cache(path,pp,out,donor=cache.Donor(donor))
    assert not result['sampled_conditions_pass'] and result['reused_samples']==9
    compare(path,spec,p,out)


@pytest.mark.parametrize('fault',['report','archive','input','runtime','method','reuse'])
def test_donor_tamper_or_mismatched_source_kernel_and_runtime_reject(tmp_path,monkeypatch,fault):
    source,_,_,_,_,folder,_=setup(tmp_path)
    if fault=='report':(folder/'geometry.json').write_bytes((folder/'geometry.json').read_bytes()+b' ')
    if fault=='archive':(folder/'observations.npz').write_bytes((folder/'observations.npz').read_bytes()+b'mutation')
    if fault=='reuse':(folder/'reuse.json').write_bytes((folder/'reuse.json').read_bytes()+b' ')
    if fault=='input':source.write_bytes(source.read_bytes()+b'mutation')
    if fault=='runtime':
        value=cache.runtime();value['numpy']='different';monkeypatch.setattr(cache,'runtime',lambda:value)
    if fault=='method':
        value=cache.methods();value['native_scene_geometry.py']='0'*64;monkeypatch.setattr(cache,'methods',lambda:value)
    with pytest.raises(ValueError):cache.Donor(folder)


def test_resource_overflow_cannot_leave_an_approvable_partial_cache(tmp_path):
    _,path,_,_,pp,_,_=setup(tmp_path);out=tmp_path/'overflow'
    with pytest.raises(ValueError):cache.evaluate_to_cache(path,pp,out,maximum_array_bytes=100)
    assert not (out/'result.json').exists()
    assert (out/'observations.npz.partial.receipt.json').exists()
    with pytest.raises((ValueError,OSError)):cache.Donor(out)


def test_total_logical_budget_never_discards_late_samples_to_fit(tmp_path):
    _,path,_,_,pp,_,_=setup(tmp_path);out=tmp_path/'total-overflow'
    with pytest.raises(ValueError,match='total logical'):cache.evaluate_to_cache(path,pp,out,maximum_logical_bytes=1024)
    assert not (out/'result.json').exists() and (out/'observations.npz.partial.receipt.json').exists()


@pytest.mark.parametrize('value',[True,0,1023,1024**4+1,float('nan')])
def test_invalid_total_budget_rejects_before_any_input_load(tmp_path,value):
    with pytest.raises(ValueError,match='budget'):cache.evaluate_to_cache(tmp_path/'missing.json',tmp_path/'missing-policy.json',tmp_path/'invalid',maximum_logical_bytes=value)


def test_mutating_loaded_donor_decisions_cannot_turn_cached_failures_into_passes(tmp_path):
    _,path,_,_,pp,folder,_=setup(tmp_path,inside=True);donor=cache.Donor(folder)
    donor.report['samples'][4]['passed']=True
    with pytest.raises(ValueError,match='metadata changed'):cache.evaluate_to_cache(path,pp,tmp_path/'tampered',donor=donor)


def test_run_records_complete_and_failed_states_with_one_worker_lock(tmp_path,monkeypatch):
    import action_worker_lock
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'local-lock')
    _,path,_,_,pp,donor,_=setup(tmp_path);out=tmp_path/'locked'
    result=cache.run(path,pp,out,donor_path=donor)
    assert result['reused_samples']==9 and read(out/'pipeline.json')['status']=='complete'
    failed=tmp_path/'failed'
    with pytest.raises(ValueError):cache.run(path,pp,failed,maximum_logical_bytes=1024)
    assert read(failed/'pipeline.json')['status']=='failed' and not (failed/'result.json').exists()
    with action_worker_lock.worker_lock():
        with pytest.raises(RuntimeError,match='Another local action job'):cache.run(path,pp,tmp_path/'busy')
    assert not (tmp_path/'busy').exists()


def test_vertex_inputs_changing_between_comparison_and_query_cannot_complete(tmp_path,monkeypatch):
    _,path,_,_,pp,_,_=setup(tmp_path);original=cache._vertices;calls=0
    def unstable(scene,name,time):
        nonlocal calls
        value=original(scene,name,time);calls+=1
        if calls>9:value[0,0]+=1e-12
        return value
    monkeypatch.setattr(cache,'_vertices',unstable);out=tmp_path/'unstable'
    with pytest.raises(ValueError,match='inputs changed'):cache.evaluate_to_cache(path,pp,out)
    assert not (out/'result.json').exists() and (out/'observations.npz.partial.receipt.json').exists()
