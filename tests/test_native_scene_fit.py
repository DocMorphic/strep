"""Permissions, exact exports, original source rates and retained-input proposals."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_contacts import setup, object_target
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from native_scene_fit import SceneProblem, run
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from strep import save, read, sha256


def prepare(tmp_path, *, rotation=False):
    source,rig,reader,spec = setup(tmp_path,rotating=rotation)
    if not rotation:
        spec['contacts'][0]['target']['points_m'][0][1] += .002
        spec['contacts'][0]['limits'] = dict(position_m=.001,relative_speed_m_s=.005)
    contacts = tmp_path/'contacts.json'; save(contacts,spec)
    track = dict(node=3 if rotation else 0,path='rotation' if rotation else 'translation',maximum_change=5. if rotation else .02)
    permissions = dict(schema='strep-native-scene-edit-v1',contacts_sha256=sha256(contacts),actors=dict(A=dict(
        window_s=[0.,2.],protected_s=[],knots_s=[0.,.5,1.,1.5,2.],tracks=[track],maximum_joint_displacement_m=.02)))
    path=tmp_path/'permissions.json'; save(path,permissions)
    scene=SceneContacts(spec,tmp_path); edits=SceneEdits(permissions,scene,sha256(contacts))
    return source,spec,contacts,permissions,path,scene,edits


@pytest.mark.parametrize('fault',['binding','schema','actor','track-duplicate','node-bool','node-missing','path',
    'static','maximum-bool','maximum-large','window','knots','protected','displacement','extra','step'])
def test_invalid_permissions_reject_without_hidden_motion_freedom(tmp_path,fault):
    _,_,contacts,p,_,scene,_=prepare(tmp_path); a=p['actors']['A']; t=a['tracks'][0]
    if fault=='binding': p['contacts_sha256']='0'*64
    if fault=='schema': p['schema']='old-foot-contract'
    if fault=='actor': p['actors']['B']=p['actors'].pop('A')
    if fault=='track-duplicate': a['tracks']*=2
    if fault=='node-bool': t['node']=True
    if fault=='node-missing': t['node']=999
    if fault=='path': t['path']='scale'
    if fault=='static': t['node']=5
    if fault=='maximum-bool': t['maximum_change']=True
    if fault=='maximum-large': t['maximum_change']=.2201
    if fault=='window': a['window_s']=[0,3]
    if fault=='knots': a['knots_s']=[0,1,1,2]
    if fault=='protected': a['protected_s']=[[0,2]]
    if fault=='displacement': a['maximum_joint_displacement_m']=True
    if fault=='extra': a['edit_anything']=True
    if fault=='step':
        old=scene.actors['A']['sampler'].channels
        scene.actors['A']['sampler'].channels=[(*c[:4],'STEP') if c[:2]==(0,'translation') else c for c in old]
    with pytest.raises(ValueError): SceneEdits(p,scene,sha256(contacts))


def test_translation_export_preserves_clocks_boundary_keys_and_all_other_tracks(tmp_path):
    source,_,_,_,_,scene,edits=prepare(tmp_path); value=edits.initial.copy(); value.reshape(-1,3)[:,1]=.1
    output=tmp_path/'proposal.glb'; edits.export('A',value,output)
    report=edits.audit('A',output,0)
    assert report['passed'] and abs(report['tracks'][0]['maximum_change']-.002)<1e-7
    rig=RigAsset.load(output); reader=NativeSupportSampler(rig.document,rig.binary,0)
    old=scene.actors['A']['sampler']
    for a,b in zip(old.channels,reader.channels):
        assert a[:2]==b[:2] and a[4]==b[4]; np.testing.assert_array_equal(a[2],b[2])
        if a[:2]!=(0,'translation'): np.testing.assert_array_equal(a[3],b[3])
        else: np.testing.assert_array_equal(a[3][[0,-1]],b[3][[0,-1]])
    times=np.unique(np.r_[np.linspace(0,2,91),old.channels[0][2],.853725])
    decoded=np.array([reader.sample(float(t)) for t in times]); proxy=edits.worlds('A',value,times)
    np.testing.assert_allclose(proxy,decoded,atol=2e-12,rtol=0)
    assert sha256(source)==scene.inputs[str(source.resolve())]


def test_rotation_export_and_protected_interpolation_support(tmp_path):
    _,_,contacts,p,_,scene,_=prepare(tmp_path,rotation=True)
    p['actors']['A']['protected_s']=[[.853725,.853725]]
    edits=SceneEdits(p,scene,sha256(contacts)); x=edits.initial.copy(); x.reshape(-1,3)[:,0]=.1
    output=tmp_path/'rotation.glb'; edits.export('A',x,output); assert edits.audit('A',output,0)['passed']
    rig=RigAsset.load(output); sampler=NativeSupportSampler(rig.document,rig.binary,0)
    np.testing.assert_array_equal(sampler.sample(.853725),scene.actors['A']['sampler'].sample(.853725))
    times=np.unique(np.r_[np.linspace(0,2,91),sampler.channels[0][2]])
    np.testing.assert_allclose(edits.worlds('A',x,times),np.array([sampler.sample(float(t)) for t in times]),atol=2e-12,rtol=0)
    # Component boxes alone do not authorize a radial corner.
    x[:]=1.; assert max(np.linalg.norm(e['weights'] @ x[e['controls']],axis=1).max() for e in edits.actors['A']['tracks'])>1
    bad=tmp_path/'too-large.glb'; edits.export('A',x,bad); assert not edits.audit('A',bad,0)['passed']


def test_source_rates_and_contact_constraints_match_actual_decoded_exports(tmp_path):
    _,_,_,_,_,scene,edits=prepare(tmp_path); problem=SceneProblem(scene,edits)
    assert max(problem.model(problem.initial))>0
    x=edits.initial.copy(); x.reshape(-1,3)[:,1]=.1; path=tmp_path/'proposal.glb'; edits.export('A',x,path)
    decoded,_=problem.decoded(dict(A=path),x)
    np.testing.assert_allclose(problem.model(x),decoded,atol=5e-7,rtol=0)
    for cap in problem.caps['A'].caps: assert np.isfinite(cap).all()
    assert problem.caps['A'].tolerance==1e-5


@pytest.mark.parametrize('target',['actor','object'])
def test_partner_and_rotating_object_proxies_match_full_scene_audit(tmp_path,target):
    source,rig,reader,spec=setup(tmp_path,rotating=True)
    if target=='object': object_target(spec,reader,rig,gap=.001)
    else:
        spec['actors']['B']=copy.deepcopy(spec['actors']['A'])
        spec['contacts'][0]['target']=dict(space='actor',actor='B',vertices=[[6,0,0]],reduction='individual')
    path=tmp_path/'contacts.json'; save(path,spec)
    permissions=dict(schema='strep-native-scene-edit-v1',contacts_sha256=sha256(path),actors=dict(A=dict(
        window_s=[0,2],protected_s=[],knots_s=[0,.5,1,1.5,2],tracks=[dict(node=3,path='rotation',maximum_change=5)],
        maximum_joint_displacement_m=.02)))
    scene=SceneContacts(spec,tmp_path); edits=SceneEdits(permissions,scene,sha256(path)); problem=SceneProblem(scene,edits)
    x=edits.initial.copy(); x.reshape(-1,3)[:,0]=.01; out=tmp_path/'edited.glb'; edits.export('A',x,out)
    decoded,_=problem.decoded(dict(A=out),x)
    np.testing.assert_allclose(problem.model(x),decoded,atol=5e-7,rtol=0)
    other=copy.deepcopy(spec); other['actors']['A'].update(glb=out.name,sha256=sha256(out))
    audit,arrays=SceneContacts(other,tmp_path).evaluate()
    data=problem.rows[0]; worlds=problem.worlds(x)
    proxy=problem.skin_points('A',data['entry']['ids'],worlds,data['ids'],'individual')
    np.testing.assert_allclose(proxy,arrays['contact_0_effector_world_m'],atol=2e-12,rtol=0)


def test_explicit_second_animation_is_selected_even_when_clip_contents_duplicate(tmp_path):
    source,spec,contacts,p,path,scene,_=prepare(tmp_path)
    from gltf_tools import write_glb
    rig=RigAsset.load(source); doc=copy.deepcopy(rig.document); doc['animations'].append(copy.deepcopy(doc['animations'][0]))
    write_glb(source,doc,rig.binary); spec['actors']['A'].update(animation_index=1,sha256=sha256(source)); save(contacts,spec)
    p['contacts_sha256']=sha256(contacts); scene=SceneContacts(spec,tmp_path); edits=SceneEdits(p,scene,sha256(contacts))
    x=edits.initial.copy(); x.reshape(-1,3)[:,1]=.1; out=tmp_path/'second.glb'; edits.export('A',x,out)
    assert edits.audit('A',out,1)['passed']
    changed=RigAsset.load(out)
    before=NativeSupportSampler(doc,rig.binary,0); after=NativeSupportSampler(changed.document,changed.binary,0)
    for a,b in zip(before.channels,after.channels): np.testing.assert_array_equal(a[3],b[3])


def test_unpermitted_track_or_frozen_key_changes_reject(tmp_path):
    _,_,_,_,_,scene,edits=prepare(tmp_path)
    other=copy.deepcopy(edits); other.actors['A']['tracks'][0]['ids']=np.array([0])
    other.actors['A']['tracks'][0]['weights']=np.ones((1,3))/3
    x=other.initial.copy(); x.reshape(-1,3)[:,1]=.1
    path=tmp_path/'bad.glb'; other.export('A',x,path)
    with pytest.raises(ValueError,match='Frozen'): edits.audit('A',path,0)


def test_actual_proposal_job_always_retains_originals_pending_scene_engine_checks(tmp_path):
    source,_,contacts,_,permissions,_,_=prepare(tmp_path); digest=sha256(source); output=tmp_path/'fit'
    result=run(contacts,permissions,output,iterations=2,trust=.02)
    assert result['status']=='complete' and result['original_selected']
    assert sha256(output/result['selected_files']['A'])==digest==sha256(source)
    assert not result['engine_playback_verified'] and not result['collision_verified'] and not result['release_approved']
    assert read(output/'contact-audit/result.json')['schema']=='strep-native-scene-contact-audit-v1'
    assert result['source_rate_tolerance']==1e-5 and result['source_rate_bins']==4
    for p in result['probes']:
        for path,h in p['files_sha256'].items(): assert sha256(output/path)==h
    with pytest.raises(ValueError,match='Fresh'): run(contacts,permissions,output)


def test_mutated_input_leaves_original_snapshot_and_terminal_failure(tmp_path,monkeypatch):
    source,_,contacts,_,permissions,_,_=prepare(tmp_path); digest=sha256(source)
    import native_scene_fit
    def mutate(problem,evaluate,*args):
        source.write_bytes(source.read_bytes()+b'changed')
        return problem.initial.copy(),dict(final_merit=[1.,1.],history=[])
    monkeypatch.setattr(native_scene_fit,'optimize',mutate)
    output=tmp_path/'failed'
    with pytest.raises(ValueError): run(contacts,permissions,output)
    assert read(output/'pipeline.json')['status']=='failed' and not (output/'result.json').exists()
    assert sha256(output/'input/actor-0.glb')==digest


def test_mutated_archived_permission_rejects_even_if_original_request_is_unchanged(tmp_path,monkeypatch):
    source,_,contacts,_,permissions,_,_=prepare(tmp_path); digest=sha256(source)
    import native_scene_fit
    output=tmp_path/'changed-archive'
    def mutate(problem,evaluate,*args):
        (output/'permissions.json').write_text('{}')
        return problem.initial.copy(),dict(final_merit=[0.,0.],history=[])
    monkeypatch.setattr(native_scene_fit,'optimize',mutate)
    with pytest.raises(ValueError,match='snapshot changed'): run(contacts,permissions,output)
    assert read(output/'pipeline.json')['status']=='failed'
    assert sha256(output/'input/actor-0.glb')==digest


def test_actual_final_constraints_override_an_optimizer_metadata_claim(tmp_path,monkeypatch):
    _,_,contacts,_,permissions,_,_=prepare(tmp_path)
    import native_scene_fit
    def incorrect_claim(problem,evaluate,*args):
        return problem.initial.copy(),dict(final_merit=[0.,0.],history=[])
    monkeypatch.setattr(native_scene_fit,'optimize',incorrect_claim)
    result=run(contacts,permissions,tmp_path/'claimed-pass')
    assert not result['native_constraints_pass'] and result['original_selected']


def test_already_passing_source_still_has_no_geometry_or_engine_approval(tmp_path):
    source,spec,contacts,p,permissions,_,_=prepare(tmp_path)
    spec['contacts'][0]['target']['points_m'][0][1]-=.002; save(contacts,spec)
    p['contacts_sha256']=sha256(contacts); save(permissions,p)
    output=tmp_path/'passing-input'; result=run(contacts,permissions,output)
    assert result['native_constraints_pass'] and not result['optimization']['history']
    assert result['original_selected'] and sha256(output/result['selected_files']['A'])==sha256(source)
    request=read(output/'request.json')
    assert request['actor_snapshots']['A']['sha256']==sha256(source)
    assert (output/request['actor_snapshots']['A']['path']).is_file()


def test_joint_displacement_rows_cover_every_joint_and_uniform_time(tmp_path):
    _,_,contacts,p,_,scene,_=prepare(tmp_path)
    p['actors']['A']['maximum_joint_displacement_m']=.0005
    edits=SceneEdits(p,scene,sha256(contacts)); problem=SceneProblem(scene,edits)
    x=edits.initial.copy(); x.reshape(-1,3)[:,1]=.1
    current=problem.worlds(x)['A'][problem.rate_ids]; original=problem.source_world['A'][problem.rate_ids]
    joints=scene.actors['A']['rig'].joints
    selected=current[:,joints]; reference=original[:,joints]
    expected=(np.linalg.norm(selected[:,:,:3,3]-reference[:,:,:3,3],axis=2)-.0005)/.0005
    offset=sum(len(e['ids']) for e in edits.actors['A']['tracks'])
    actual=problem.constraints(x)[offset:offset+expected.size]
    np.testing.assert_array_equal(np.sort(actual),np.sort(expected.ravel()))
    assert (actual>0).sum()==(expected>0).sum()>0
