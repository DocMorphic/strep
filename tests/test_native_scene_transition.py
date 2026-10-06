"""Shared scene clocks, retained trim failures and exact source-bound replay."""
from pathlib import Path
import sys,copy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'scripts')]
import native_scene_transition as assembly
import native_rig_transition as transition
import native_transition_root_support as root_support
import action_worker_lock as locks
from native_scene_contacts import SceneContacts
from native_scene_game_tracks import crossed
from test_native_rig_transition import fixture as actor_fixture
from strep import read,save,sha256


def fixture(root,asset=None,moving=False):
    path,r=actor_fixture(root/'asset',asset=asset,moving=moving);out=root/'transition';transition.run(path,out)
    p=transition.Problem(r,path.parent);bindings=[]
    for side in range(2):
        actors={n:dict(glb=str(p.path),sha256=sha256(p.path),animation_index=r['animation_indices'][side],
            placement=dict(translation_m=[0,0,0] if n=='A' else [2,0,0],rotation_xyzw=[0,0,0,1])) for n in ('A','B')}
        # Numerical point correspondences are explicit, not inferred hands/feet.
        patch=r['supports'][0];ref=patch['vertices'];point=patch['points_m']
        contacts=[dict(id='ground',actor='A',vertices=ref,reduction='individual',target=dict(space='world',points_m=point),mode='hold',interval_s=[.1,.6],limits=patch['limits']),
            dict(id='partner',actor='A',vertices=ref,reduction='individual',target=dict(space='actor',actor='B',vertices=ref,reduction='individual'),mode='touch',interval_s=[float(r['cuts_s'][side])]*2,limits=dict(position_m=.002)),
            dict(id='object',actor='A',vertices=ref,reduction='individual',target=dict(space='object',object='box',points_m=[[.1,0,0]]),mode='touch',interval_s=[float(r['cuts_s'][side])]*2,limits=dict(position_m=.002))]
        times=[float(t) for t in np.array([0,.2,.4,.8],dtype='<f4')]
        keys=[dict(time_s=t,translation_m=[.1*t+.1*side,2,0],rotation_xyzw=Rotation.from_euler('z',10*t+4*side,degrees=True).as_quat().tolist()) for t in times]
        spec=dict(schema='strep-native-scene-contacts-v1',duration_s=times[-1],actors=actors,objects=dict(box=dict(geometry=dict(schema='strep-object-geometry-v1',shape='box',size_m=[.2,.2,.2]),keyframes=keys)),contacts=contacts)
        sp=root/('scene-'+str(side)+'.json');save(sp,spec)
        markers=[dict(id=name,name=name,actor=actor,time_s=float(time),confirmed=True) for name,actor,time in [('initial','A',0),('boundary','A',r['cuts_s'][side]),('reaction','B',r['cuts_s'][side]),('outside','A',.6 if side==0 else .1),('terminal','B',times[-1])]]
        gp=root/('game-'+str(side)+'.json');save(gp,dict(schema='strep-native-scene-game-tracks-v1',actors={n:dict(root_node=r['root_node']) for n in actors},markers=markers))
        bindings.append(dict(scene=dict(path=str(sp),sha256=sha256(sp)),game_tracks=dict(path=str(gp),sha256=sha256(gp))))
    recipe=dict(schema=assembly.SCHEMA,sources=bindings,actors={n:dict(kind='transition',folder=str(out),result_sha256=sha256(out/'result.json')) for n in ('A','B')},
        bridge=dict(contacts=[dict(id='bridge-ground',actor='A',vertices=ref,reduction='individual',target=dict(space='world',points_m=point),mode='hold',interval_s=[p.start,p.end],limits=patch['limits'])],
            markers=[dict(id='bridge-review',name='review-contact',actor='A',time_s=(p.start+p.end)/2,confirmed=False)]),
        object_limits=dict(curve_control_rotation_degrees=170,position_error_m=1e-5,basis_error=1e-5,linear_boundary_jump_m_s=.1,angular_boundary_jump_degrees_s=2,acceleration_m_s2=20),
        floor=None,maximum_timestamp_rounding_s=1e-6,maximum_pose_vertex_queries=1000000)
    rp=root/'assembly.json';save(rp,recipe);return rp,recipe


@pytest.fixture(scope='module')
def study(tmp_path_factory):
    root=tmp_path_factory.mktemp('scene-transition');patch=pytest.MonkeyPatch();patch.setattr(locks,'ROOT',root)
    path,recipe=fixture(root);out=root/'assembled';result=assembly.run(path,out)
    yield root,path,recipe,out,result
    patch.undo()


def test_all_participants_objects_contacts_events_and_roots_share_one_clock(study):
    root,path,recipe,out,result=study;assert assembly.verify(out)==result
    assert result['checks']['actor_transition_conditions'] and result['checks']['objects']
    assert not result['checks']['contacts'] and not result['all_declared_samples_pass']
    assert result['objects']['box']['maximum_position_error_m']<1e-5 and result['objects']['box']['maximum_basis_error']<1e-5
    assert all(result[k] is False for k in transition.FALSE_FLAGS) and result['original_selected']
    spec=read(out/'scene.json');scene=SceneContacts(spec,out);roots=read(out/'roots.json');events=read(out/'events.json')
    assert set(spec['actors'])=={'A','B'} and set(spec['objects'])=={'box'} and roots['times_s'][-1]==result['duration_s']
    assert set(roots['actors'])==set(spec['actors']) and all(e['time_s'] in roots['times_s'] for e in events['events'])
    for name,entry in roots['actors'].items():
        w=np.array(entry['world_matrices']);d=np.array(entry['initial_local_deltas']);np.testing.assert_allclose(w[0]@d,w,rtol=0,atol=1e-9)
        assert entry['animation_index']==spec['actors'][name]['animation_index'] and len(scene.actors[name]['rig'].document['animations'])==4
        assert sha256(out/spec['actors'][name]['glb'])==sha256(root/'transition/character.glb')
    assert np.array(roots['actors']['B']['world_matrices'])[0,0,3]-np.array(roots['actors']['A']['world_matrices'])[0,0,3]==2
    contact=read(out/'contacts.json');by_id={c['intent']['id']:c for c in contact['contacts']}
    assert by_id['bridge_bridge-ground']['measurement']['passed']
    assert not by_id['first_partner']['measurement']['passed'] and not by_id['second_object']['measurement']['passed']
    assert all(not c['runtime_dispatch_allowed'] for c in contact['contacts'])
    assert not crossed(events,None,result['duration_s'])
    assert result['object_refinement']['box']['rounds']>=1 and result['object_refinement']['box']['final_keys']>result['object_refinement']['box']['initial_keys']
    assert result['floor_conditions_available'] is False and result['full_scene_collision_verified'] is False


def test_trim_dispositions_preserve_every_source_annotation_and_reset_confirmations(study):
    _,_,_,out,r=study;rows=r['timeline_mapping'];assert len(rows)==16
    assert len([c for c in rows if c['kind']=='contact'])==6
    markers=[c for c in rows if c['kind']=='marker'];assert len(markers)==10
    assert {m['source_id'] for m in markers if m['disposition']=='dropped'}=={'outside','initial','terminal'}
    assert all(m['source_confirmed'] for m in markers if m['disposition']=='retained-confirmation-reset')
    game=read(out/'game-tracks-request.json');assert all(m['confirmed'] is False for m in game['markers'])
    first=next(c for c in rows if c['kind']=='contact' and c['source_id']=='ground' and c['side']==0)
    second=next(c for c in rows if c['kind']=='contact' and c['source_id']=='ground' and c['side']==1)
    assert first['disposition']==second['disposition']=='clipped' and first['output_interval_s'][1]==r['bridge_interval_s'][0] and second['output_interval_s'][0]==r['bridge_interval_s'][1]
    for side,time in enumerate(r['bridge_interval_s']):
        matched=[m for m in game['markers'] if m['time_s']==time];assert {m['actor'] for m in matched}=={'A','B'}
    assert max(c['rounding_s'] for c in r['timestamp_mapping'])<=1e-6


def test_object_bridge_preserves_source_motion_and_uses_independent_hermite_translation(study):
    _,path,recipe,out,_=study;p=assembly.Problem(recipe,path.parent);scene=SceneContacts(read(out/'scene.json'),out)
    for time in (.13,.33,p.start,p.end,.83,1.1):
        actual,r=scene.object_poses('box',[time]);expected=p.expected_object('box',[time]);np.testing.assert_allclose(actual,expected[:,:3,3],atol=1e-5,rtol=0);np.testing.assert_allclose(r,expected[:,:3,:3],atol=1e-5,rtol=0)
    t=(p.start+p.end)/2;d=p.bridge_duration;a=p.object_curves['box'];u=.5
    expected=(2*u**3-3*u**2+1)*a.a[0,:3,3]+(u**3-2*u**2+u)*d*a.va[0]+(-2*u**3+3*u**2)*a.b[0,:3,3]+(u**3-u**2)*d*a.vb[0]
    np.testing.assert_allclose(p.expected_object('box',[t])[0,:3,3],expected,atol=1e-14,rtol=0)


@pytest.mark.parametrize('fault',['schema','extra','budget-bool','budget-small','rounding-bool','rounding-zero','missing-partner','bad-binding','bridge-outside','bridge-confirmed'])
def test_invalid_or_incomplete_requests_reject_without_output(study,tmp_path,fault):
    _,_,recipe,_,_=study;p=copy.deepcopy(recipe)
    if fault=='schema':p['schema']='old'
    elif fault=='extra':p['infer_attachment']=True
    elif fault=='budget-bool':p['maximum_pose_vertex_queries']=True
    elif fault=='budget-small':p['maximum_pose_vertex_queries']=1
    elif fault=='rounding-bool':p['maximum_timestamp_rounding_s']=False
    elif fault=='rounding-zero':p['maximum_timestamp_rounding_s']=0
    elif fault=='missing-partner':p['actors'].pop('B')
    elif fault=='bad-binding':p['actors']['B']['result_sha256']='0'*64
    elif fault=='bridge-outside':p['bridge']['markers'][0]['time_s']=0
    else:p['bridge']['markers'][0]['confirmed']=True
    path=tmp_path/'recipe.json';save(path,p);out=tmp_path/'out'
    with pytest.raises(ValueError):assembly.run(path,out)
    assert not out.exists()


@pytest.mark.parametrize('fault',['approval','typed-flag','mapping','object-keys','marker-confirmation','root-reference','contact-intent','array','snapshot','snapshot-path','method','actor'])
def test_rehashed_scene_tracks_arrays_bindings_and_decisions_cannot_forge_a_result(study,fault):
    _,_,_,out,_=study;modified={p:p.read_bytes() for p in (out/'result.json',out/'completion.json')}
    def edit(name,fn):
        p=out/name;modified.setdefault(p,p.read_bytes());v=read(p);fn(v);save(p,v)
    try:
        if fault=='approval':edit('result.json',lambda v:v.update(quality_approved=True))
        elif fault=='typed-flag':edit('result.json',lambda v:v.update(original_selected=1))
        elif fault=='mapping':edit('result.json',lambda v:v['timeline_mapping'].pop())
        elif fault=='object-keys':edit('scene.json',lambda v:v['objects']['box']['keyframes'][1]['translation_m'].__setitem__(0,99))
        elif fault=='marker-confirmation':edit('events.json',lambda v:v['events'][0].update(runtime_dispatch_allowed=True))
        elif fault=='root-reference':edit('roots.json',lambda v:v['actors']['B']['world_matrices'][0][0].__setitem__(3,99))
        elif fault=='contact-intent':edit('contacts.json',lambda v:v['contacts'][0].update(runtime_dispatch_allowed=True))
        elif fault=='snapshot-path':
            edit('prepared.json',lambda v:v['inputs'][next(iter(v['inputs']))].update(path=next(iter(v['inputs']))))
            edit('result.json',lambda v:v.update(prepared_sha256=sha256(out/'prepared.json')))
        else:
            name={'array':'contact-observations.npz','snapshot':'input/0.json','method':'implementation/native_scene_transition.py','actor':'actors/A.glb'}[fault]
            p=out/name;modified[p]=p.read_bytes()
            if fault=='array':
                with np.load(p,allow_pickle=False) as stored:arrays={n:stored[n].copy() for n in stored.files}
                first=next(iter(arrays));arrays[first].flat[0]+=1;np.savez_compressed(p,**arrays)
            else:p.write_bytes(p.read_bytes()+b'changed')
        r=read(out/'result.json');r['files_sha256']={n:sha256(out/n) for n in r['files_sha256']};save(out/'result.json',r);save(out/'completion.json',dict(result_sha256=sha256(out/'result.json')))
        with pytest.raises(ValueError):assembly.verify(out)
    finally:
        for p,data in modified.items():p.write_bytes(data)


@pytest.mark.parametrize('condition',['object-rate','whole-floor','static-object','world-only'])
def test_real_declared_failures_and_static_or_actor_only_bridge_variants(study,tmp_path,condition):
    _,_,recipe,_,_=study;p=copy.deepcopy(recipe)
    if condition=='object-rate':p['object_limits']['linear_boundary_jump_m_s']=0
    elif condition=='whole-floor':p['floor']=dict(height_m=10,maximum_penetration_m=1e-5)
    elif condition=='static-object':
        for i,binding in enumerate(p['sources']):
            spec=read(binding['scene']['path']);spec['objects']['box']['keyframes']=[spec['objects']['box']['keyframes'][0]]
            sp=tmp_path/(str(i)+'.json');save(sp,spec);binding['scene']=dict(path=str(sp),sha256=sha256(sp))
    else:
        for i,binding in enumerate(p['sources']):
            spec=read(binding['scene']['path']);spec['objects']={};spec['contacts']=[c for c in spec['contacts'] if c['target']['space']=='world']
            sp=tmp_path/(str(i)+'.json');save(sp,spec);binding['scene']=dict(path=str(sp),sha256=sha256(sp))
    path=tmp_path/'recipe.json';save(path,p);out=tmp_path/'out';r=assembly.run(path,out)
    assert assembly.verify(out)==r and not r['quality_approved']
    if condition=='object-rate':assert not r['checks']['objects'] and not r['all_declared_samples_pass']
    elif condition=='whole-floor':assert not r['checks']['floor'] and r['floor_maximum_penetration_m']>1 and not r['all_declared_samples_pass']
    elif condition=='static-object':assert r['checks']['objects'] and not r['checks']['contacts']
    else:assert r['all_declared_samples_pass'] and r['objects']=={} and not r['floor_conditions_available']


def test_completed_root_support_variant_carries_exact_corrected_animation_into_scene(tmp_path,monkeypatch):
    monkeypatch.setattr(locks,'ROOT',tmp_path);path,recipe=fixture(tmp_path,moving=True)
    source=tmp_path/'transition';source_result=read(source/'result.json')
    original=transition.Problem(read(source/'recipe.json'),read(source/'prepared.json')['recipe_base'])
    rp=tmp_path/'root-support.json';save(rp,dict(schema=root_support.SCHEMA,source=dict(folder=str(source),result_sha256=sha256(source/'result.json')),
        label='repaired shared transition',window_s=[.25,float(original.times[abs(original.times-.9).argmin()])],maximum_root_translation_change_m=.08,maximum_joint_displacement_m=.08,maximum_pose_vertex_queries=1000000))
    fit=tmp_path/'fit';fixed=root_support.run(rp,fit);assert fixed['all_declared_samples_pass'] and not source_result['all_declared_samples_pass']
    recipe['actors']={n:dict(kind='root-support',folder=str(fit),result_sha256=sha256(fit/'result.json')) for n in recipe['actors']};save(path,recipe)
    out=tmp_path/'out';r=assembly.run(path,out);spec=read(out/'scene.json')
    assert r['checks']['actor_transition_conditions'] and all(a['animation_index']==4 for a in spec['actors'].values())
    assert all(sha256(out/a['glb'])==sha256(fit/'character.glb') for a in spec['actors'].values())
    assert not r['checks']['contacts'] and not r['all_declared_samples_pass'] and not r['quality_approved']
