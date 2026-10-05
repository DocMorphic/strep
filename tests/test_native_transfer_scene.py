"""Independent generated rig/scene fixtures; no anatomy or quality evidence."""
import copy
from pathlib import Path
import shutil
import sys

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_transfer_scene as scene_bridge
import native_rig_transfer as transfer
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from native_support_clock import NativeSupportSampler
from native_support_skin import NativeSupportSkin
from gltf_tools import append_accessor,write_glb,local_matrix
from rig_asset import RigAsset
from strep import read,save,sha256
from test_native_rig_transfer import fixture


def stationary(path,profile):
    rig=RigAsset.load(path);doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
    for channel in doc['animations'][0]['channels']:
        sampler=doc['animations'][0]['samplers'][channel['sampler']];node=channel['target']['node'];kind=channel['target']['path']
        from rig_asset import array
        times=array(doc,binary,sampler['input'])*.1
        value=doc['nodes'][node][kind]
        sampler['input']=append_accessor(doc,binary,times,'SCALAR')
        sampler['output']=append_accessor(doc,binary,np.repeat([value],len(times),axis=0),'VEC4' if kind=='rotation' else 'VEC3')
    write_glb(path,doc,binary);p=read(profile);p['character_sha256']=sha256(path);save(profile,p)


def patch(rig,role):
    skin=NativeSupportSkin(rig);node=next(i for i,n in enumerate(rig.document['nodes']) if n.get('name','').endswith('_'+role))
    return skin.vertex_references[np.flatnonzero(skin.nodes[:,0]==node)].tolist()


def moving_root(path,profile):
    rig=RigAsset.load(path);doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
    from rig_asset import array
    channel=next(c for c in doc['animations'][0]['channels'] if c['target']['path']=='translation')
    sampler=doc['animations'][0]['samplers'][channel['sampler']];node=channel['target']['node'];times=array(doc,binary,sampler['input'])
    shift=np.outer(times/times[-1],[.04,.005,-.015]);parent=rig.parents[node]
    values=np.asarray(doc['nodes'][node]['translation'])+shift@rig.reference[parent,:3,:3]
    sampler['output']=append_accessor(doc,binary,values,'VEC3');write_glb(path,doc,binary)
    p=read(profile);p['character_sha256']=sha256(path);save(profile,p)


def scene_fixture(root,*,size=1.,helpers=False,source_gap=0.,both=False,moving=False):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    a,ap=fixture(root,'actor',axes=23);stationary(a,ap)
    b,bp=fixture(root,'replacement',axes=-31,optional=not helpers,helpers=helpers,reverse=True,size=size,animated=False)
    partner,pp=fixture(root,'partner',axes=9,optional=False,reverse=True);stationary(partner,pp)
    if moving:moving_root(a,ap);moving_root(partner,pp)
    rigs=[RigAsset.load(a),RigAsset.load(b),RigAsset.load(partner)];reader=NativeSupportSampler(rigs[0].document,rigs[0].binary,0)
    foot=patch(rigs[0],'LeftFoot');hand=patch(rigs[0],'LeftHand');other=patch(rigs[2],'RightHand')
    skin=NativeSupportSkin(rigs[0]);table={tuple(r):i for i,r in enumerate(skin.vertex_references)}
    posed=rigs[0].vertices(reader.sample(0.));hand_points=posed[[table[tuple(r)] for r in hand]];foot_points=posed[[table[tuple(r)] for r in foot]]
    partner_skin=NativeSupportSkin(rigs[2]);ids={tuple(r):i for i,r in enumerate(partner_skin.vertex_references)}
    p_reader=NativeSupportSampler(rigs[2].document,rigs[2].binary,0)
    other_points=rigs[2].vertices(p_reader.sample(0.))[[ids[tuple(r)] for r in other]]
    placement=(hand_points[0]-other_points[0]).tolist()
    pose=dict(translation_m=[0,0,0],rotation_xyzw=[0,0,0,1])
    spec=dict(schema='strep-native-scene-contacts-v1',duration_s=reader.duration,actors=dict(
        A=dict(glb=a.name,sha256=sha256(a),animation_index=0,placement=copy.deepcopy(pose)),
        B=dict(glb=partner.name,sha256=sha256(partner),animation_index=0,placement={**pose,'translation_m':placement})),objects={},contacts=[])
    grip=hand_points.mean(0);center=grip+[0,0,.1]
    spec['objects']['box']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='box',size_m=[.2,.2,.2]),
        keyframes=[dict(time_s=0.,translation_m=center.tolist(),rotation_xyzw=[0,0,0,1])])
    limits=dict(position_m=.002,relative_speed_m_s=.002)
    def contact(name,actor,vertices,reduction,target):
        return dict(id=name,actor=actor,vertices=vertices,reduction=reduction,target=target,mode='hold',interval_s=[.02,.18],limits=copy.deepcopy(limits))
    spec['contacts']=[contact('foot', 'A',foot,'individual',dict(space='world',points_m=(foot_points+[source_gap,0,0]).tolist())),
        contact('box-grip','A',hand,'centroid',dict(space='object',object='box',points_m=[[0,0,-.1]])),
        contact('partner','A',hand,'individual',dict(space='actor',actor='B',vertices=other,reduction='individual')),
        contact('partner-initiated','B',other,'centroid',dict(space='actor',actor='A',vertices=hand,reduction='centroid'))]
    if moving:
        time=.0853725;world=rigs[0].vertices(reader.sample(time));points=world[[table[tuple(r)] for r in foot]]
        spec['contacts'][0].update(mode='touch',interval_s=[time,time],target=dict(space='world',points_m=points.tolist()),limits=dict(position_m=.002))
        spec['objects']['box']['keyframes']=[dict(time_s=t,translation_m=(center+np.array([.04,.005,-.015])*t/reader.duration).tolist(),rotation_xyzw=[0,0,0,1]) for t in (0.,reader.duration)]
    contacts=root/'scene.json';save(contacts,spec)
    candidate=root/'transfer';transfer.export(a,ap,b,bp,0,candidate,120)
    mapping=[dict(source=l,target=r) for role in ('LeftFoot','LeftHand') for l,r in zip(patch(rigs[0],role),patch(rigs[1],role))]
    recipe=dict(schema=scene_bridge.SCHEMA,contacts=dict(path=contacts.name,sha256=sha256(contacts)),
        transfers=dict(A=dict(candidate=dict(path=candidate.name,sha256=sha256(candidate/'report.json')),vertex_map=mapping)))
    if both:
        bp_glb,bp_profile=fixture(root,'partner-replacement',axes=-19,optional=False,size=size,animated=False)
        partner_transfer=root/'partner-transfer';transfer.export(partner,pp,bp_glb,bp_profile,0,partner_transfer,120)
        target=RigAsset.load(bp_glb);mapping=[dict(source=l,target=r) for l,r in zip(other,patch(target,'RightHand'))]
        recipe['transfers']['B']=dict(candidate=dict(path=partner_transfer.name,sha256=sha256(partner_transfer/'report.json')),vertex_map=mapping)
    path=root/'recipe.json';save(path,recipe);return path


@pytest.fixture(scope='module')
def studies(tmp_path_factory):
    root=tmp_path_factory.mktemp('transfer-scenes');result={}
    for name,kwargs in [('preserved',{}),('regressed',dict(size=1.3,helpers=True)),('failed-source',dict(source_gap=.01)),('both',dict(both=True)),
        ('moving',dict(moving=True)),('moving-regressed',dict(moving=True,size=1.3,helpers=True))]:
        recipe=scene_fixture(root/name,**kwargs);out=recipe.parent/'comparison';r=scene_bridge.run(recipe,out);result[name]=(recipe,out,r)
    return result


def test_retains_world_object_partner_and_incoming_partner_intent(studies):
    recipe,out,result=studies['preserved'];old=read(recipe.parent/'scene.json');new=read(out/'contacts.json')
    assert result['retention_samples_pass'] and all(r['retention_status']=='preserved' for r in result['contacts'])
    assert {r['target_space'] for r in result['contacts']}=={'world','object','actor'}
    assert new['objects']==old['objects'] and new['actors']['A']['placement']==old['actors']['A']['placement']
    assert new['actors']['A']['animation_index']==1 and old['actors']['A']['animation_index']==0
    for a,b in zip(old['contacts'],new['contacts']):
        assert all(a[k]==b[k] for k in ('id','actor','mode','interval_s','limits','reduction'))
        if a['target']['space']!='actor':assert a['target']==b['target']
    assert scene_bridge.verify(out,sha256(out/'result.json'))==result


def test_different_proportions_keep_all_regressions_without_loosening_targets(studies):
    _,out,result=studies['regressed']
    assert result['source_contacts_pass'] and not result['candidate_contact_samples_pass'] and not result['retention_samples_pass']
    assert all(r['retention_status']=='regressed' for r in result['contacts'])
    assert max(r['maximum_candidate_position_error_m'] for r in result['contacts'])>.1
    assert all(result[k] is False for k in ('continuous_contact_certified','anatomical_reviewed','surface_orientation_verified',
        'collision_verified','engine_playback_verified','quality_approved','release_approved','contact_intent_revised'))
    assert result['status']=='complete' and (out/'observations.npz').is_file()


def test_preexisting_source_failure_is_separate_from_retention(studies):
    result=studies['failed-source'][2]
    assert not result['source_contacts_pass'] and not result['retention_samples_pass']
    assert result['contacts'][0]['retention_status']=='source_and_candidate_failed'
    assert all(r['retention_status']=='preserved' for r in result['contacts'][1:])


def test_transfer_both_partner_sides_and_relocated_output(studies,tmp_path):
    recipe,out,result=studies['both'];assert result['transfer_actors']==['A','B'] and result['retention_samples_pass']
    relocated=tmp_path/'portable';shutil.copytree(out,relocated)
    assert scene_bridge.verify(relocated,sha256(out/'result.json'))==result
    assert SceneContacts(read(relocated/'contacts.json'),relocated).evaluate()[0]['passed']


def test_common_native_and_quarter_positions_keep_complete_frame_speed_populations(studies):
    _,out,r=studies['preserved'];source=read(out/'source-audit.json');candidate=read(out/'candidate-audit.json')
    assert all(len(c['relative_speed_populations'])==12 for c in source['contacts']+candidate['contacts'])
    with np.load(out/'observations.npz',allow_pickle=False) as a:
        for i,c in enumerate(r['contacts']):
            times=a[f'contact_{i}_times_s'];assert times.dtype==np.dtype('float64') and len(times)==c['common_position_samples']
            assert times[0]==.02 and times[-1]==.18 and np.any(~np.isin(times,[.02,.18]))
            assert a[f'contact_{i}_candidate_effector_world_m'].shape==a[f'contact_{i}_source_effector_world_m'].shape


def test_existing_bounded_scene_editor_accepts_appended_clip_and_preserves_older_animation(studies,tmp_path):
    _,out,_=studies['regressed'];spec=read(out/'contacts.json');scene=SceneContacts(spec,out);rig=scene.actors['A']['rig']
    node=next(c[0] for c in scene.actors['A']['sampler'].channels if c[1]=='translation')
    permissions=dict(schema='strep-native-scene-edit-v1',contacts_sha256=sha256(out/'contacts.json'),actors=dict(A=dict(
        window_s=[0,scene.duration],protected_s=[],knots_s=[0,.1,scene.duration],maximum_joint_displacement_m=.01,
        tracks=[dict(node=node,path='translation',maximum_change=.005)])))
    edits=SceneEdits(permissions,scene,sha256(out/'contacts.json'));values=edits.initial.copy();values[0]=.1
    path=tmp_path/'bounded.glb';edits.export('A',values,path)
    checked=edits.audit('A',path,1);assert checked['passed'] and checked['native_clocks_frozen_keys_and_static_payloads_preserved']
    changed=RigAsset.load(path);assert changed.document['animations'][0]==rig.document['animations'][0]


def test_moving_box_and_partner_keep_exact_touch_and_surface_relative_speed_failures(studies):
    _,out,result=studies['moving'];assert result['retention_samples_pass']
    with np.load(out/'observations.npz',allow_pickle=False) as a:
        np.testing.assert_array_equal(a['contact_0_times_s'],[.0853725])
        assert np.linalg.norm(a['contact_1_candidate_effector_world_m'][-1]-a['contact_1_candidate_effector_world_m'][0])>.02
    failed=studies['moving-regressed'][2];assert failed['source_contacts_pass'] and not failed['retention_samples_pass']
    audit=read(studies['moving-regressed'][1]/'candidate-audit.json')
    assert not audit['contacts'][0]['relative_speed_populations']
    assert all(any(not p['passed'] and p['maximum_relative_speed_m_s']>.05 for p in r['relative_speed_populations']) for r in audit['contacts'][1:])


@pytest.mark.parametrize('limit',['POSITION_QUERY_LIMIT','POINT_OBSERVATION_LIMIT'])
def test_whole_population_budget_rejects_before_animated_skin_queries(studies,monkeypatch,limit):
    _,out,_=studies['preserved'];original=SceneContacts(read(out/'source-contacts.json'),out);candidate=SceneContacts(read(out/'contacts.json'),out)
    monkeypatch.setattr(scene_bridge,limit,1)
    monkeypatch.setattr(SceneContacts,'actor_points',lambda *a,**kw:pytest.fail('Animated skin queried before complete budget rejection'))
    with pytest.raises(ValueError,match='no partial'):scene_bridge.evaluate(original,candidate)


@pytest.mark.parametrize('fault',['missing','extra','duplicate-source','duplicate-target','boolean','target-missing','wrong-source','wrong-clip','recipe-extra','report-hash'])
def test_invalid_correspondence_or_binding_rejects_before_output(studies,tmp_path,fault):
    original,_,_=studies['preserved'];recipe=read(original)
    recipe['contacts']['path']=str(original.parent/'scene.json');recipe['transfers']['A']['candidate']['path']=str(original.parent/'transfer')
    pairs=recipe['transfers']['A']['vertex_map']
    if fault=='missing':pairs.pop()
    elif fault=='extra':pairs.append(dict(source=[0,0,999],target=[0,0,999]))
    elif fault=='duplicate-source':pairs[1]['source']=pairs[0]['source']
    elif fault=='duplicate-target':pairs[1]['target']=pairs[0]['target']
    elif fault=='boolean':pairs[0]['source'][2]=False
    elif fault=='target-missing':pairs[0]['target'][2]=999
    elif fault in ('wrong-source','wrong-clip'):
        spec=read(original.parent/'scene.json')
        if fault=='wrong-source':spec['actors']['A']['sha256']='0'*64
        else:spec['actors']['A']['animation_index']=1
        scene=tmp_path/'scene.json';save(scene,spec)
        for actor in spec['actors'].values():actor['glb']=str(original.parent/actor['glb'])
        save(scene,spec);recipe['contacts']=dict(path=str(scene),sha256=sha256(scene))
    elif fault=='recipe-extra':recipe['quality_approved']=True
    else:recipe['transfers']['A']['candidate']['sha256']='0'*64
    path=tmp_path/'recipe.json';save(path,recipe);output=tmp_path/'invalid'
    with pytest.raises((ValueError,IndexError)):scene_bridge.run(path,output)
    assert not output.exists()


@pytest.mark.parametrize('fault',['limits','placement','object','point-map','observations','quality','typed-flag','old-clip','method','missing-file'])
def test_rehashed_completed_changes_reject_on_replay(studies,tmp_path,fault):
    _,original,_=studies['preserved'];out=tmp_path/'changed';shutil.copytree(original,out)
    if fault in ('limits','placement','object','point-map'):
        p=out/'contacts.json';v=read(p)
        if fault=='limits':v['contacts'][0]['limits']['position_m']=1.
        elif fault=='placement':v['actors']['A']['placement']['translation_m'][0]+=.01
        elif fault=='object':v['objects']['box']['keyframes'][0]['translation_m'][0]+=.01
        else:v['contacts'][0]['vertices'].reverse()
        save(p,v)
    elif fault=='observations':
        p=out/'observations.npz'
        with np.load(p,allow_pickle=False) as a:data={k:a[k].copy() for k in a.files}
        data['contact_0_candidate_effector_world_m'][0,0,0]+=.01;np.savez_compressed(p,**data)
    elif fault in ('quality','typed-flag'):
        r=read(out/'result.json');r['quality_approved']=True if fault=='quality' else 0;save(out/'result.json',r)
    elif fault=='old-clip':
        p=out/'actors/actor-0.glb';rig=RigAsset.load(p);doc=copy.deepcopy(rig.document);doc['animations'][0]['name']='changed';write_glb(p,doc,rig.binary)
    elif fault=='method':p=out/'implementation/native_transfer_scene.py';p.write_bytes(p.read_bytes()+b' changed')
    else:(out/'source-audit.json').unlink()
    r=read(out/'result.json')
    r['files_sha256']={n:sha256(out/n) for n in r['files_sha256'] if (out/n).is_file()};save(out/'result.json',r)
    with pytest.raises((ValueError,OSError)):scene_bridge.verify(out)
