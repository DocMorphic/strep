"""Portable source-bound authoring connects to actual native engine APIs."""
import copy
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
import material_scene_package as packages
from native_contact_revision import validate
from native_scene_contacts import SceneContacts
from native_scene_authoring_job import validated as validate_recipe
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from strep import read,save,sha256
from test_material_patch_revision import setup
from test_native_scene_engine import mock_actor


def fixture(tmp_path,*,relative=True):
    draft,spec,baseline,materials,_=setup(tmp_path)
    draft['geometry']=dict(clock=dict(mode='explicit',times_s=[0.,.5,1.]),
        limits=dict(penetration_m=.005,depth_resolution_m=1e-6,surface_tolerance_m=1e-8),planes={})
    if relative:
        for entry in draft['scene']['actors'].values():entry['glb']='animated/character.glb'
    save(baseline,draft);spec['baseline_sha256']=sha256(baseline)
    selection=tmp_path/'material-selection.json';save(selection,spec)
    out=tmp_path/'package';return baseline,selection,materials,out


def build(tmp_path):
    baseline,selection,materials,out=fixture(tmp_path)
    result=packages.prepare(baseline,selection,out)
    return baseline,selection,materials,out,result


def test_complete_portable_package_preserves_original_intent_and_only_transports_paths(tmp_path):
    baseline,selection,materials,out,result=build(tmp_path)
    assert result['actors']==2 and result['material_bundles']==1 and result['revised_contacts']==1
    assert (out/'input/source-draft.json').read_bytes()==baseline.read_bytes()
    assert (out/'input/source-selection.json').read_bytes()==selection.read_bytes()
    assert packages.files(out/'input/materials/bundle-0')==packages.files(materials)
    revised,lineage=validate(read(out/'draft.json'));original=read(baseline)
    assert revised['geometry']==original['geometry'] and revised['object_edit'] is None
    assert lineage['baseline']==read(out/'baseline.json')
    for alias,entry in original['scene']['actors'].items():
        actual=revised['scene']['actors'][alias]
        assert {k:v for k,v in actual.items() if k!='glb'}=={k:v for k,v in entry.items() if k!='glb'}
        assert sha256(out/actual['glb'])==entry['sha256']
    row=revised['scene']['contacts'][0]
    for key in ('interval_s','limits','mode','actor','id'):assert row[key]==original['scene']['contacts'][0][key]
    assert row['vertices']==row['target']['vertices']==[[6,0,i] for i in [2,0,1]]
    scene=SceneContacts(read(out/'contacts.json'),out)
    assert scene.actor_points('A',scene.rows[0]['ids'],[.5]).shape==(1,3,3)
    assert read(out/'geometry-policy.json')['contacts_sha256']==sha256(out/'contacts.json')
    assert not any(result[k] for k in ('animation_edited','motion_contacts_measured','engine_executed',
        'quality_approved','training_admitted','release_approved'))


def test_moved_package_replays_without_original_files_or_paths(tmp_path,monkeypatch):
    _,_,_,out,result=build(tmp_path);moved=tmp_path.parent/(tmp_path.name+' portable');shutil.move(str(out),moved)
    shutil.move(str(tmp_path),tmp_path.parent/(tmp_path.name+' original unavailable'))
    before=packages.files(moved)
    # Python 3.10 Path.open has its own cached accessor: explicitly guard every route.
    import builtins,io
    old_builtin,old_io,old_path=builtins.open,io.open,Path.open
    def guard(path):
        if isinstance(path,(str,bytes,Path)):
            value=Path(path).resolve()
            assert not value.is_relative_to(tmp_path),'Original path read attempted'
    def builtin(path,*a,**kw):guard(path);return old_builtin(path,*a,**kw)
    def iopen(path,*a,**kw):guard(path);return old_io(path,*a,**kw)
    def popen(path,*a,**kw):guard(path);return old_path(path,*a,**kw)
    monkeypatch.setattr(builtins,'open',builtin);monkeypatch.setattr(io,'open',iopen);monkeypatch.setattr(Path,'open',popen)
    assert packages.verify(moved,expected_result_sha256=sha256(moved/'result.json'))==result
    assert packages.files(moved)==before


@pytest.mark.parametrize('with_edit',[False,True])
def test_explicit_object_holds_and_optional_edit_keep_original_settings(tmp_path,with_edit):
    baseline,selection,_,out=fixture(tmp_path);draft=read(baseline);spec=read(selection)
    draft['scene']['objects']={'item':dict(geometry=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.25),
        keyframes=[dict(time_s=t,translation_m=[0,0,0],rotation_xyzw=[0,0,0,1]) for t in [0.,1.]])}
    reference=copy.deepcopy(spec['edits'][0]['source']);reference['reduction']='centroid'
    draft['scene']['contacts']=[];spec['edits']=[]
    for name,actor,vertex,x in [('left','A',0,-.25),('right','B',1,.25)]:
        draft['scene']['contacts'].append(dict(id=name,actor=actor,vertices=[[6,0,vertex]],reduction='individual',
            target=dict(space='object',object='item',points_m=[[x,0,0]]),mode='hold',interval_s=[.25,.75],
            limits=dict(position_m=.005,relative_speed_m_s=.005)))
        spec['edits'].append(dict(id=name,source=copy.deepcopy(reference),partner=None))
    if with_edit:
        draft['object_edit']=dict(schema='strep-native-object-hold-fit-v1',object='item',contact_ids=['left','right'],
            edit_window_s=[.1,.9],maximum_translation_m=.01,maximum_rotation_degrees=2.,maximum_keys=3601)
    save(baseline,draft);spec['baseline_sha256']=sha256(baseline);save(selection,spec)
    result=packages.prepare(baseline,selection,out);assert packages.verify(out)==result
    revised=read(out/'draft.json');assert revised['scene']['objects']==draft['scene']['objects']
    assert revised['object_edit']==draft['object_edit'] and revised['geometry']==draft['geometry']
    for original,actual in zip(draft['scene']['contacts'],revised['scene']['contacts']):
        for key in ('target','interval_s','limits','mode'):assert actual[key]==original[key]
        assert actual['reduction']=='centroid' and actual['vertices']==[[6,0,i] for i in [2,0,1]]
    assert (out/'object-edit.json').exists()==with_edit
    if with_edit:assert read(out/'object-edit.json')==dict(contacts_sha256=sha256(out/'contacts.json'),**draft['object_edit'])


def test_current_method_change_during_replay_rejects_without_touching_source(tmp_path,monkeypatch):
    _,_,_,out,_=build(tmp_path);original_derive,original_hash=packages.derive,packages.sha256;finished=[]
    def derived(*a,**kw):
        value=original_derive(*a,**kw);finished.append(True);return value
    def changed_hash(path):
        if finished and Path(path).resolve()==packages.ROOT/'scripts/material_scene_package.py':return '0'*64
        return original_hash(path)
    monkeypatch.setattr(packages,'derive',derived);monkeypatch.setattr(packages,'sha256',changed_hash)
    with pytest.raises(ValueError,match='method changed during replay'):packages.verify(out)


@pytest.mark.parametrize('fault',['baseline','empty','hash','vertex','geometry','actor','budget'])
def test_invalid_sources_reject_without_a_partial_package(tmp_path,fault):
    baseline,selection,_,out=fixture(tmp_path);draft=read(baseline);spec=read(selection)
    if fault=='baseline':spec['baseline_sha256']='0'*64
    elif fault=='empty':spec['edits']=[]
    elif fault=='hash':spec['edits'][0]['source']['result_sha256']=None
    elif fault=='vertex':spec['edits'][0]['source']['vertex_indices']=[True]
    elif fault=='geometry':draft['geometry']['limits']['penetration_m']=-1
    elif fault=='actor':draft['scene']['actors']['A']['sha256']='0'*64
    save(baseline,draft)
    if fault not in ('baseline',):spec['baseline_sha256']=sha256(baseline)
    save(selection,spec)
    with pytest.raises(ValueError):packages.prepare(baseline,selection,out,maximum_payload_bytes=1 if fault=='budget' else packages.DEFAULT_PAYLOAD_BYTES)
    assert not out.exists()


def rebind(out):
    request,result=read(out/'request.json'),read(out/'result.json')
    request['payload_sha256']={n:sha256(out/n) for n in request['payload_sha256']}
    save(out/'request.json',request);result['request_sha256']=sha256(out/'request.json');save(out/'result.json',result)


@pytest.mark.parametrize('fault',['geometry','timing','actor-path','selection','proof','normal-type','contact-order','extra',
    'missing-parent','method','actor-request-path','material-request-path','approve','budget'])
def test_rebound_or_extra_payload_cannot_change_original_authoring_contract(tmp_path,fault):
    _,_,_,out,_=build(tmp_path)
    if fault in ('geometry','timing','actor-path'):
        p=out/'baseline.json';value=read(p)
        if fault=='geometry':value['geometry']['limits']['penetration_m']=.02
        elif fault=='timing':value['scene']['contacts'][0]['interval_s']=[.25,.25]
        else:value['scene']['actors']['A']['glb']='input/actors/actor-1.glb'
        save(p,value)
    elif fault=='selection':
        p=out/'selection.json';value=read(p);value['edits'][0]['source']['vertex_indices']=[0,2,1];save(p,value)
    elif fault in ('proof','normal-type'):
        p=out/'material-proof.json';value=read(p)
        if fault=='proof':value['explicit_vertex_correspondence']=False
        else:value['quality_approved']=0
        save(p,value)
    elif fault=='contact-order':
        p=out/'contacts.json';value=read(p);value['contacts'][0]['vertices'].reverse();save(p,value)
    elif fault=='extra':(out/'extra.txt').write_text('Unrelated payload')
    elif fault=='missing-parent':(out/'input/materials/bundle-0/parent/identity.json').unlink()
    elif fault=='method':(out/'implementation/material_scene_package.py').write_bytes(b'changed')
    elif fault in ('actor-request-path','material-request-path','budget'):
        request=read(out/'request.json')
        if fault=='actor-request-path':request['actors'][0]['snapshot']='../outside.glb'
        elif fault=='material-request-path':request['materials'][0]['snapshot']='../outside'
        else:request['maximum_payload_bytes']=1
        save(out/'request.json',request)
    else:
        result=read(out/'result.json');result['quality_approved']=True;save(out/'result.json',result)
    if fault!='missing-parent':rebind(out)
    with pytest.raises(ValueError):packages.verify(out)


def test_explicit_result_pin_fresh_output_and_failed_copy_preservation(tmp_path,monkeypatch):
    baseline,selection,_,out,_=build(tmp_path)
    with pytest.raises(ValueError,match='caller'):packages.verify(out,expected_result_sha256='0'*64)
    with pytest.raises(ValueError,match='Fresh'):packages.prepare(baseline,selection,out)
    original=packages.shutil.copyfile
    # Files are JSON-saved, so mutate an original during the first copied actor.
    def copying(source,target,**kwargs):
        result=original(source,target,**kwargs)
        if Path(target).name=='actor-0.glb':baseline.write_bytes(baseline.read_bytes()+b'\n')
        return result
    monkeypatch.setattr(packages.shutil,'copyfile',copying);failed=tmp_path/'failed'
    with pytest.raises(ValueError,match='Original authoring'):packages.prepare(baseline,selection,failed)
    assert read(failed/'pipeline.json')['status']=='failed' and not (failed/'result.json').exists()


def test_execution_refuses_existing_production_worker_before_snapshot(tmp_path,monkeypatch):
    _,_,_,out,_=build(tmp_path);execution=tmp_path/'execution'
    monkeypatch.setattr(packages,'worker_busy',lambda:True)
    with pytest.raises(ValueError,match='production worker'):packages.run(out,execution,tmp_path/'not-an-engine')
    assert not execution.exists()


def test_complete_native_authoring_api_executes_with_material_lineage_and_keeps_failures(tmp_path,monkeypatch):
    _,_,_,out,_=build(tmp_path)
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'fixture-lock')
    engine=tmp_path/'explicit-mocked-engine';engine.write_bytes(b'no actual engine execution in this fixture')
    def execute(command,**kwargs):
        request=read(command[-2]);cases=[]
        for case in request['cases']:
            rig=RigAsset.load(case['path']);sampler=NativeSupportSampler(rig.document,rig.binary,case['animation_index'])
            row=mock_actor(rig,sampler,request['sample_times_s'],path=case['path']);row['id']=case['id'];cases.append(row)
            # This fixture has two mesh nodes; the shared single-node mock needs
            # distinct imported references and an identity placement for each.
            for mesh,primitive in zip(row['meshes'],rig.primitives):mesh['node']=f"mesh-{primitive['node']}"
            for frame in row['frames']:
                frame['mesh_world']=[dict(node=name,matrix=copy.deepcopy(frame['skeleton_world']))
                    for name in dict.fromkeys(mesh['node'] for mesh in row['meshes'])]
            Path(case['animation_output']).write_bytes(b'explicit mocked resource')
        save(command[-1],dict(engine=dict(string='fixture only'),cases=cases,objects=[]))
        return SimpleNamespace(returncode=0)
    import subprocess
    monkeypatch.setattr(subprocess,'run',execute)
    before=packages.files(out);execution=tmp_path/'execution';result=packages.run(out,execution,engine)
    assert result['status']=='complete' and result['material_lineage_preserved'] and not result['sampled_conditions_pass']
    assert packages.files(out)==packages.files(execution/'authoring')==before
    job=read(execution/'engine-job/result.json')
    assert [s['id'] for s in job['stages']]==['source-contacts','actors-engine','replay']
    _,_,scene,_=validate_recipe(execution/'recipe.json');assert list(scene.actors)==['A','B']
    assert result['engine_result_sha256']==sha256(execution/'engine-job/result.json')
    assert not result['quality_approved'] and not result['release_approved'] and result['original_selected']
