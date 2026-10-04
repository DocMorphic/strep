"""Observable object rotation, saved clocks and unchanged character evidence."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_geometry import closed_fixture,policy
from native_scene_contacts import SceneContacts
from native_object_correspondence_fit import SCHEMA,fit_points,request_for,proposal,run,saved_keys
from native_object_hold_fit import proposal as two_point_proposal,audit_bounds
from engine_contact_sampling import frame_populations
from strep import save,read,sha256


def fixture(tmp_path,*,grouped=False):
    source,path,spec=closed_fixture(tmp_path);scene=SceneContacts(spec,tmp_path);actor=scene.actors['A']
    node=actor['rig'].primitives[0]['node'];vertices=[4,5,7]
    grips=np.array([[-.2,-.2,-.2],[-.2,-.2,.2],[-.2,.2,.2]])
    times=np.unique(np.r_[actor['sampler'].channels[0][2],.8,.9,1.]);keys=[]
    for t in times:
        center=actor['rig'].vertices(actor['sampler'].sample(float(t))).mean(0)+[.4,0,0]
        angle=1. if .8<=t<=1. else 0.
        if t==.9:angle=-1.
        if .8<=t<=1.:center[1]+=.002
        keys.append(dict(time_s=float(t),translation_m=center.tolist(),rotation_xyzw=Rotation.from_euler('z',angle,degrees=True).as_quat().tolist()))
    spec['objects']={'item':dict(geometry=dict(schema='strep-object-geometry-v1',shape='box',size_m=[.4,.4,.4]),keyframes=keys)}
    groups=[(vertices,grips)] if grouped else [([v],[p]) for v,p in zip(vertices,grips)]
    spec['contacts']=[dict(id=f'grip-{i}',actor='A',vertices=[[node,0,v] for v in vs],reduction='individual',
        target=dict(space='object',object='item',points_m=np.asarray(ps).tolist()),mode='hold',interval_s=[.8,1.],
        limits=dict(position_m=.005,relative_speed_m_s=.005)) for i,(vs,ps) in enumerate(groups)]
    save(path,spec);scene=SceneContacts(spec,tmp_path)
    value=dict(schema=SCHEMA,contacts_sha256=sha256(path),object='item',contact_ids=[c['id'] for c in spec['contacts']],
        edit_window_s=[.6,1.2],maximum_translation_m=.01,maximum_rotation_degrees=2.,maximum_keys=3601,maximum_correspondences=3)
    return source,path,spec,scene,value


def test_proper_fit_recovers_translation_rotation_and_matches_scipy():
    local=np.array([[0.,0,0],[.2,0,0],[0,.1,0],[.03,.01,.04]])
    expected=Rotation.from_euler('xyz',[77,-22,151],degrees=True);shift=np.array([4.,-2,3])
    observed=expected.apply(local)+shift
    p,r,error=fit_points(local,observed)
    np.testing.assert_allclose(p,shift,atol=1e-14);np.testing.assert_allclose(r,expected.as_matrix(),atol=1e-14)
    assert error.max()<1e-14 and np.linalg.det(r)==pytest.approx(1)
    noisy=observed.copy();noisy[-1]+=[.003,-.002,.001]
    p,r,error=fit_points(local,noisy)
    oracle,_=Rotation.align_vectors(noisy-noisy.mean(0),local-local.mean(0))
    np.testing.assert_allclose(r,oracle.as_matrix(),atol=1e-13)
    np.testing.assert_allclose(error,np.linalg.norm(local@r.T+p-noisy,axis=1),atol=1e-15)
    assert error.max()>.0001


def test_reflection_does_not_become_a_rigid_exact_fit():
    local=np.array([[0.,0,0],[1.,0,0],[0,2.,0],[0,0,3.]])
    observed=local.copy();observed[:,0]*=-1
    _,r,error=fit_points(local,observed)
    assert np.linalg.det(r)==pytest.approx(1.) and error.max()>.1


def test_noncollinear_sets_with_degenerate_cross_covariance_reject():
    local=np.array([[1.,0,0],[-1.,0,0],[0,1.,0],[0,-1.,0]])
    observed=np.array([[1.,1,0],[1.,-1,0],[-1.,0,0],[-1.,0,0]])
    with pytest.raises(ValueError,match='covariance is degenerate'):fit_points(local,observed)


@pytest.mark.parametrize('fault',['two','collinear_local','collinear_observed','nonfinite','shape'])
def test_unobservable_or_invalid_geometry_rejects(fault):
    local=np.array([[0.,0,0],[1.,0,0],[0,1.,0]]);observed=local.copy()
    if fault=='two':local=local[:2];observed=observed[:2]
    if fault=='collinear_local':local[2]=[2,0,0]
    if fault=='collinear_observed':observed[2]=[2,0,0]
    if fault=='nonfinite':local[0,0]=np.nan
    if fault=='shape':observed=observed[:2]
    with pytest.raises(ValueError):fit_points(local,observed)


@pytest.mark.parametrize('grouped',[False,True])
def test_saved_multi_point_fit_removes_twist_failure_and_preserves_full_clocks(tmp_path,grouped):
    source,path,spec,scene,value=fixture(tmp_path,grouped=grouped);original=sha256(source)
    before,_=scene.evaluate();assert not before['passed']
    keys,arrays,layout=proposal(scene,value,sha256(path));derived=copy.deepcopy(spec)
    derived['objects']['item']['keyframes']=saved_keys(keys,spec,value);candidate=SceneContacts(derived,tmp_path)
    after,_=candidate.evaluate();assert after['passed']
    assert len(layout)==3 and arrays['observed_world_points'].shape[1:]==(3,3)
    # The GLB's Float32 cube coordinates differ from decimal grip points by nanometres.
    assert arrays['least_squares_point_errors_m'].max()<1e-8
    assert audit_bounds(scene,candidate,value,arrays['times_s'])['passed'] and sha256(source)==original
    for population in frame_populations([.8,1.]):assert np.isin(population['times_s'],arrays['times_s']).all()
    assert derived['actors']==spec['actors'] and derived['contacts']==spec['contacts']
    if not grouped:
        old=copy.deepcopy(value);old.pop('maximum_correspondences');old.update(schema='strep-native-object-hold-fit-v1',contact_ids=old['contact_ids'][:2])
        old_keys,_=two_point_proposal(scene,old,sha256(path));two=copy.deepcopy(spec);two['objects']['item']['keyframes']=old_keys
        legacy,_=SceneContacts(two,tmp_path).evaluate();assert not legacy['passed']
        assert legacy['contacts'][2]['maximum_position_error_m']>.006


@pytest.mark.parametrize('fault',['schema','binding','extra','duplicate','missing','wrong_object','interval','window','budget','key_budget','bool_budget','target_duplicate','collinear'])
def test_explicit_contracts_and_complete_populations_reject(tmp_path,fault):
    _,path,_,scene,value=fixture(tmp_path)
    if fault=='schema':value['schema']='strep-native-object-hold-fit-v1'
    if fault=='binding':value['contacts_sha256']='0'*64
    if fault=='extra':value['guess_hands']=True
    if fault=='duplicate':value['contact_ids']=['grip-0']*3
    if fault=='missing':value['contact_ids'][0]='unknown'
    if fault=='wrong_object':scene.rows[0]['authored']['target']['space']='world'
    if fault=='interval':scene.rows[0]['authored']['interval_s']=[.9,1.]
    if fault=='window':value['edit_window_s']=[.8,1.2]
    if fault=='budget':value['maximum_correspondences']=2
    if fault=='key_budget':value['maximum_keys']=2
    if fault=='bool_budget':value['maximum_correspondences']=True
    if fault=='target_duplicate':scene.rows[2]['target_ids']=scene.rows[1]['target_ids'].copy()
    if fault=='collinear':scene.rows[2]['target_ids']=scene.rows[1]['target_ids']*2-scene.rows[0]['target_ids']
    with pytest.raises(ValueError):proposal(scene,value,sha256(path))


def test_full_run_keeps_failure_decisions_separate_and_snapshots_all_actors(tmp_path):
    source,path,spec,scene,value=fixture(tmp_path);rp=tmp_path/'request.json';save(rp,value)
    pp=tmp_path/'policy.json';save(pp,policy(path));folder=tmp_path/'multi-fit'
    result=run(path,rp,pp,folder)
    assert result['actor_bytes_unchanged'] and result['original_selected'] and result['correspondences']==3
    assert result['all_contact_conditions_pass'] and result['bounds']['passed'] and result['sampled_geometry_conditions_pass']
    assert not result['quality_approved'] and not result['release_approved'] and not result['training_admitted']
    assert result['geometry_samples']>=result['keys'] and sha256(source)==spec['actors']['A']['sha256']
    assert read(folder/'proposal-contacts.json')['contacts']==spec['contacts']
    for name,digest in result['files_sha256'].items():assert sha256(folder/name)==digest
    for name,digest in result['implementation_sha256'].items():assert sha256(folder/'implementation'/name)==digest
    geometry=read(folder/'geometry-audit.json')
    assert geometry['observation_receipt_sha256']==sha256(folder/'geometry-observations.npz.receipt.json')
    with pytest.raises(ValueError,match='Fresh'):run(path,rp,pp,folder)


def test_centroid_is_one_correspondence_and_does_not_duplicate_its_weight(tmp_path):
    _,path,spec,_,value=fixture(tmp_path)
    spec['contacts'][0]['vertices'].append(spec['contacts'][1]['vertices'][0])
    spec['contacts'][0]['reduction']='centroid'
    spec['contacts'][0]['target']['points_m']=[[-.2,-.2,0.]]
    save(path,spec);value['contacts_sha256']=sha256(path);scene=SceneContacts(spec,tmp_path)
    keys,arrays,layout=proposal(scene,value,sha256(path))
    assert len(layout)==3 and arrays['observed_world_points'].shape[1]==3
    entry=scene.rows[0];expected=scene.actor_points('A',entry['ids'],arrays['hold_times_s']).mean(axis=1)
    np.testing.assert_array_equal(arrays['observed_world_points'][:,0],expected)
    spec['objects']['item']['keyframes']=keys
    assert SceneContacts(spec,tmp_path).evaluate()[0]['passed']


def test_correspondences_query_each_named_actor_with_its_placement(tmp_path):
    _,path,spec,_,value=fixture(tmp_path)
    spec['actors']['B']=copy.deepcopy(spec['actors']['A'])
    spec['actors']['B']['placement']['translation_m']=[0.,0.,2.]
    spec['contacts'][2]['actor']='B'
    save(path,spec);value['contacts_sha256']=sha256(path);scene=SceneContacts(spec,tmp_path)
    _,arrays,_=proposal(scene,value,sha256(path))
    expected=scene.actor_points('B',scene.rows[2]['ids'],arrays['hold_times_s'])[:,0]
    np.testing.assert_array_equal(arrays['observed_world_points'][:,2],expected)
    assert arrays['least_squares_point_errors_m'].max()>.5


def test_saved_contact_success_cannot_hide_an_original_relative_bound_failure(tmp_path):
    source,path,_,_,value=fixture(tmp_path);value['maximum_rotation_degrees']=.00001
    rp=tmp_path/'request.json';save(rp,value);pp=tmp_path/'policy.json';save(pp,policy(path))
    folder=tmp_path/'bounded-failure';result=run(path,rp,pp,folder)
    assert result['all_contact_conditions_pass'] and not result['bounds']['passed']
    assert not result['sampled_constraints_pass'] and result['original_selected']
    assert not result['quality_approved'] and read(folder/'pipeline.json')['status']=='complete'
    assert sha256(source)==read(folder/'source-contacts.json')['actors']['A']['sha256']


def test_degenerate_observed_fit_retains_failure_archive(tmp_path,monkeypatch):
    source,path,_,_,value=fixture(tmp_path)
    rp=tmp_path/'request.json';save(rp,value);pp=tmp_path/'policy.json';save(pp,policy(path))
    folder=tmp_path/'degenerate';original=sha256(source)
    def collapsed(self,actor,ids,times):return np.zeros((len(times),len(ids),3))
    monkeypatch.setattr(SceneContacts,'actor_points',collapsed)
    with pytest.raises(ValueError,match='Unobservable object fit at time'):run(path,rp,pp,folder)
    assert read(folder/'pipeline.json')['status']=='failed'
    assert (folder/'source-contacts.json').is_file() and (folder/'implementation').is_dir()
    assert sha256(folder/'input/actor-0.glb')==sha256(source)==original
    assert not (folder/'result.json').exists()


def test_unselected_contact_and_undeformed_object_remain_separate_failure_gates(tmp_path):
    _,path,spec,scene,value=fixture(tmp_path)
    spec['contacts'].append(dict(id='unselected-touch',actor='A',vertices=spec['contacts'][0]['vertices'],
        reduction='individual',target=dict(space='world',points_m=[[10.,10.,10.]]),mode='touch',interval_s=[0.,0.],limits=dict(position_m=.005)))
    actor=scene.actors['A'];center=actor['rig'].vertices(actor['sampler'].sample(.9)).mean(0)
    spec['objects']['unmodified']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.05),
        keyframes=[dict(time_s=0.,translation_m=center.tolist(),rotation_xyzw=[0.,0.,0.,1.])])
    save(path,spec);value['contacts_sha256']=sha256(path);rp=tmp_path/'request.json';save(rp,value)
    pp=tmp_path/'policy.json';save(pp,policy(path));folder=tmp_path/'independent-failures';result=run(path,rp,pp,folder)
    rows=read(folder/'contact-audit.json')['contacts']
    assert all(r['passed'] for r in rows[:3]) and not rows[-1]['passed']
    assert result['bounds']['passed'] and not result['all_contact_conditions_pass']
    assert not result['sampled_geometry_conditions_pass'] and not result['sampled_constraints_pass']
    assert read(folder/'proposal-contacts.json')['objects']['unmodified']==spec['objects']['unmodified']
    geometry=read(folder/'geometry-audit.json')
    assert all(len(s['actor_objects'])==2 for s in geometry['samples'])
    assert any(r['containment']['status']=='inside' for s in geometry['samples'] for r in s['actor_objects'] if r['object']=='unmodified')
