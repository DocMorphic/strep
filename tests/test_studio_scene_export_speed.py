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


def test_contact_patch_revision_cannot_change_export_limits(tmp_path,monkeypatch):
    draft,_,_=speed_draft(tmp_path,monkeypatch);row=draft['scene']['contacts'][0]
    refs=list(reversed(row['vertices']))
    if refs==row['vertices']:refs=refs+[refs[0][:2]+[refs[0][2]+1]]
    edit=dict(id=row['id'],source=dict(glb_sha256=draft['scene']['actors'][row['actor']]['sha256'],vertices=refs,reduction='centroid'),partner=None)
    # Keep the fixture's point correspondence unchanged while changing order.
    if row['reduction']!='centroid' and len(refs)!=1:edit['source']['reduction']=row['reduction']
    changed=apply(draft,[edit]);changed['contact_revision']=dict(schema='strep-native-contact-revision-v1',baseline=draft,edits=[edit])
    assert validate(changed)[0]['rotation_speed_limits']==draft['rotation_speed_limits']
    changed['rotation_speed_limits'][0]['maximum_degrees_per_second']=30
    with pytest.raises(ValueError):validate(changed)
