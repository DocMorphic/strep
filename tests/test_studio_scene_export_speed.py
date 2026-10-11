"""Current export intent, strict recipes, retained bounds and source archives."""
from pathlib import Path
import copy,sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_native_scene as studio
import studio_native_scene_game as game
from native_scene_export_speed import promote,policy,methods
from native_contact_revision import validate,apply
from strep import save,read,sha256
from test_studio_native_scene import setup


def speed_draft(tmp_path,monkeypatch):
    draft,source,resolver=setup(tmp_path,monkeypatch,edit=False)
    from rig_asset import RigAsset
    from native_support_clock import NativeSupportSampler
    rig=RigAsset.load(source);sampler=NativeSupportSampler(rig.document,rig.binary,0)
    node=next(c[0] for c in sampler.channels if c[1]=='rotation')
    return promote(draft,[dict(actor='A',node=node,maximum_degrees_per_second=0)]),source,resolver


def test_current_export_policy_is_immutable_and_archived_without_correction_history(tmp_path,monkeypatch):
    draft,source,resolver=speed_draft(tmp_path,monkeypatch);before=copy.deepcopy(draft)
    folder=studio.folder_for('speed');prepared=studio.prepare(draft,folder,resolver)
    assert draft==before and prepared['rotation_speed_requested']
    assert set(methods())<=set(prepared['implementation_sha256']) and prepared['correction_lineage'] is None
    assert read(folder/'recipe.json')['schema']=='strep-native-scene-authoring-job-v2'
    assert read(folder/'rotation-speed-policy.json')==policy(draft,sha256(folder/'contacts.json'))
    assert studio.frozen(folder)==prepared
    from native_scene_contacts import SceneContacts
    scene=SceneContacts(read(folder/'contacts.json'),folder)
    assert set(methods())<=set(game.source_method_names(scene,folder))
    assert not prepared['quality_approved']


@pytest.mark.parametrize('fault',['empty','negative','boolean','duplicate','actor','node','unknown','bad-schema'])
def test_invalid_current_limits_reject_before_job_outputs(tmp_path,monkeypatch,fault):
    draft,_,resolver=speed_draft(tmp_path,monkeypatch);tracks=draft['rotation_speed_limits']
    if fault=='empty':tracks.clear()
    elif fault=='negative':tracks[0]['maximum_degrees_per_second']=-1
    elif fault=='boolean':tracks[0]['maximum_degrees_per_second']=True
    elif fault=='duplicate':tracks.append(copy.deepcopy(tracks[0]))
    elif fault=='actor':tracks[0]['actor']='missing'
    elif fault=='node':tracks[0]['node']=999
    elif fault=='unknown':tracks[0]['acceptance_allowance']=1
    else:draft['schema']='unknown'
    folder=studio.folder_for('invalid')
    with pytest.raises((ValueError,KeyError)):studio.prepare(draft,folder,resolver)
    assert not folder.exists()


def test_rebound_current_policy_receipts_cannot_change_author_intent(tmp_path,monkeypatch):
    draft,_,resolver=speed_draft(tmp_path,monkeypatch);folder=studio.folder_for('changed');studio.prepare(draft,folder,resolver)
    value=read(folder/'rotation-speed-policy.json');value['tracks'][0]['maximum_degrees_per_second']=1;save(folder/'rotation-speed-policy.json',value)
    prepared=read(folder/'prepared.json');prepared['files_sha256']['rotation-speed-policy.json']=sha256(folder/'rotation-speed-policy.json');save(folder/'prepared.json',prepared)
    with pytest.raises(ValueError,match='limits changed'):studio.frozen(folder)


def test_promoted_new_limits_preserve_other_current_actor_limits():
    draft=dict(schema='strep-studio-native-scene-v2',scene={},geometry={},object_edit=None,
        rotation_speed_limits=[dict(actor='A',node=3,maximum_degrees_per_second=20),dict(actor='B',node=5,maximum_degrees_per_second=0)])
    result=promote(draft,[dict(actor='A',node=3,maximum_degrees_per_second=40)])
    assert result['rotation_speed_limits']==[dict(actor='A',node=3,maximum_degrees_per_second=40),draft['rotation_speed_limits'][1]]
    assert draft['rotation_speed_limits'][0]['maximum_degrees_per_second']==20


def test_promote_rejects_duplicate_proposed_and_existing_limits():
    track=dict(actor='A',node=3,maximum_degrees_per_second=20)
    with pytest.raises(ValueError,match='Duplicate'):promote(dict(schema='strep-studio-native-scene-v1'),[track,track])
    with pytest.raises(ValueError,match='Duplicate'):
        promote(dict(schema='strep-studio-native-scene-v2',rotation_speed_limits=[track,track]),[track])


def test_contact_patch_revision_cannot_change_export_limits(tmp_path,monkeypatch):
    draft,_,_=speed_draft(tmp_path,monkeypatch);row=draft['scene']['contacts'][0]
    refs=list(reversed(row['vertices']))
    if refs==row['vertices']:refs=[refs[0][:2]+[refs[0][2]+1]]
    edit=dict(id=row['id'],source=dict(glb_sha256=draft['scene']['actors'][row['actor']]['sha256'],vertices=refs,reduction=row['reduction']),partner=None)
    changed=apply(draft,[edit]);changed['contact_revision']=dict(schema='strep-native-contact-revision-v1',baseline=draft,edits=[edit])
    assert validate(changed)[0]['rotation_speed_limits']==draft['rotation_speed_limits']
    changed['rotation_speed_limits'][0]['maximum_degrees_per_second']=30
    with pytest.raises(ValueError):validate(changed)


@pytest.mark.parametrize('passed',[True,False])
def test_object_edit_rebinds_limits_and_preserves_speed_failures(tmp_path,monkeypatch,passed):
    import native_scene_authoring_job as job
    import native_engine_rotation_speed as speed
    import native_scene_export_speed as export
    from native_scene_contacts import SceneContacts
    from test_native_scene_authoring_job import authored,mocked
    recipe,_,contacts,geometry,engine,edit=authored(tmp_path,edit=True)
    scene=SceneContacts(read(contacts),tmp_path)
    node=next(c[0] for c in scene.actors['A']['sampler'].channels if c[1]=='rotation')
    limits=[dict(actor='A',node=node,maximum_degrees_per_second=0)]
    original=dict(schema='strep-native-rotation-speed-policy-v1',contacts_sha256=sha256(contacts),tracks=limits)
    speed_path=tmp_path/'speed.json';save(speed_path,original);new_recipe=tmp_path/'v2.json'
    job.plan(contacts,geometry,engine,new_recipe,edit,rotation_speed_policy=speed_path)
    out=tmp_path/'job';calls=mocked(monkeypatch,out);fit=job.fit_run;actors=job.actor_run
    def changed_fit(*args):
        result=fit(*args);folder=args[-1];spec=read(folder/'proposal-contacts.json')
        first=next(iter(spec['objects'].values()))['keyframes'][0]
        first['translation_m'][0]+=.01;save(folder/'proposal-contacts.json',spec)
        value=read(folder/'geometry-policy.json');value['contacts_sha256']=sha256(folder/'proposal-contacts.json');save(folder/'geometry-policy.json',value)
        result['proposal_contacts_sha256']=sha256(folder/'proposal-contacts.json');save(folder/'result.json',result);return result
    def resources(path,folder,**kwargs):
        result=actors(path,folder,**kwargs);resource=folder/'A-animation.res';resource.write_bytes(b'explicit mocked export resource')
        result['animation_resources_sha256']={'A':sha256(resource)};save(folder/'result.json',result);return result
    def measured(path,policy_path,folder,**kwargs):
        assert path==out/'object-edit/proposal-contacts.json'
        assert read(policy_path)==dict(original,contacts_sha256=sha256(path)) and sha256(path)!=sha256(contacts)
        assert kwargs['animation_resources']=={'A':out/'actors-engine/A-animation.res'}
        folder.mkdir();calls.append('rotation-speed-engine')
        result=dict(status='complete',rotation_speed_conditions_pass=passed,source_pose_conditions_pass=True,all_sampled_conditions_pass=passed)
        save(folder/'result.json',result);return result
    def replay(path,policy_path,producer,folder):
        folder.mkdir();calls.append('rotation-speed-replay');result=dict(status='complete');save(folder/'result.json',result);return result
    monkeypatch.setattr(job,'fit_run',changed_fit);monkeypatch.setattr(job,'actor_run',resources)
    monkeypatch.setattr(speed,'run',measured);monkeypatch.setattr(export,'replay_export',replay)
    result=job.run(new_recipe,out)
    assert read(speed_path)==original and result['combined_conditions_pass']
    assert result['rotation_speed_conditions_pass'] is result['sampled_conditions_pass'] is passed
    assert calls.index('rotation-speed-engine')==calls.index('actors-engine')+1
    assert calls.index('rotation-speed-replay')==calls.index('rotation-speed-engine')+1
    assert not result['quality_approved']
