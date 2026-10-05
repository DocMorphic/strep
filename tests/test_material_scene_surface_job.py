"""Facing failures block acceptance even when native point/geometry checks pass."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
import material_scene_surface_job as jobs
from material_scene_package import prepare
from material_patch_bundle import create,source_binding,SELECTION_SCHEMA
from material_patch_revision import SCHEMA as REVISION_SCHEMA
from rig_asset import RigAsset
from gltf_tools import write_glb,append_accessor
from native_support_clock import NativeSupportSampler
from strep import read,save,sha256
from test_rig_material_patch import fixture,unsigned
from test_material_patch_bundle import target_from,move
from test_native_scene_engine import mock_actor
from test_native_object_hold_fit import fixture as object_fixture


@pytest.fixture(scope='module')
def authored(tmp_path_factory):
    folder=tmp_path_factory.mktemp('explicit-surface-job');character,profile=fixture(folder/'source')
    rig=RigAsset.load(character);binary=bytearray(rig.binary)
    # Use a synthetic nondegenerate surface so the facing gate is isolated
    # from the deliberately degenerate material-selection test fixture.
    rig.document['meshes'][0]['primitives'][0]['indices']=unsigned(rig.document,binary,[0,1,2,0,2,3],'SCALAR')
    # A rigid one-bone fixture isolates the facing decision from quantized
    # multi-influence deficits, which are covered by the imported-skin suite.
    for primitive in (rig.primitives[0],rig.primitives[2]):
        count=len(primitive['positions']);attributes=rig.document['meshes'][rig.document['nodes'][primitive['node']]['mesh']]['primitives'][primitive['primitive']]['attributes']
        attributes['JOINTS_0']=unsigned(rig.document,binary,[[3,0,0,0]]*count,'VEC4')
        attributes['JOINTS_1']=unsigned(rig.document,binary,[[0,0,0,0]]*count,'VEC4')
        attributes['WEIGHTS_0']=append_accessor(rig.document,binary,[[1,0,0,0]]*count,'VEC4')
        attributes['WEIGHTS_1']=append_accessor(rig.document,binary,[[0,0,0,0]]*count,'VEC4')
    write_glb(character,rig.document,binary);p=read(profile);p['character_sha256']=sha256(character);save(profile,p)
    selection=folder/'patch-selection.json';save(selection,dict(schema=SELECTION_SCHEMA,source=source_binding(character,profile),
        patches=[dict(id='surface',role='LeftHand',face_references=[[6,0,0]],selector=dict(include_children=True,
            minimum_weight=1.,minimum_twice_area_m2=1e-12,maximum_faces=512,maximum_vertices=256))]))
    bundle=folder/'patch';create(character,profile,selection,bundle)
    target,target_profile=target_from(character,profile,folder/'animated');animated=folder/'animated-patch';move(bundle,target,target_profile,animated)
    rig=RigAsset.load(target);sampler=NativeSupportSampler(rig.document,rig.binary,0);point=rig.vertices(sampler.sample(.5))[0].tolist()
    baseline=folder/'draft.json';save(baseline,dict(schema='strep-studio-native-scene-v1',object_edit=None,
        geometry=dict(clock=dict(mode='explicit',times_s=[0.,.5,1.]),limits=dict(penetration_m=.005,
            depth_resolution_m=1e-6,surface_tolerance_m=1e-8),planes=dict(reference_plane=dict(normal_world=[0.,1.,0.],offset_m=-10.))),
        scene=dict(schema='strep-native-scene-contacts-v1',duration_s=1.,actors=dict(A=dict(glb=str(target),sha256=sha256(target),
            animation_index=0,placement=dict(translation_m=[0,0,0],rotation_xyzw=[0,0,0,1]))),objects={},contacts=[
            dict(id='touch',actor='A',vertices=[[6,0,1]],reduction='individual',target=dict(space='world',points_m=[point]),
                mode='touch',interval_s=[.5,.5],limits=dict(position_m=.005))])))
    specification=folder/'revision.json';save(specification,dict(schema=REVISION_SCHEMA,baseline_sha256=sha256(baseline),
        edits=[dict(id='touch',source=dict(bundle=str(animated),result_sha256=sha256(animated/'result.json'),
            patch_id='surface',vertex_indices=[0],reduction='individual'),partner=None)]))
    package=folder/'package';prepare(baseline,specification,package)
    engine=folder/'mocked-engine';engine.write_bytes(b'explicit mocked fixture engine; no actual engine runs')
    return package,engine


def policy(package,opposed=True):
    return dict(schema='strep-native-surface-contact-v1',contacts_sha256=sha256(package/'contacts.json'),
        maximum_actor_pose_queries=2000,limits=dict(maximum_opposition_error_degrees=15.,backface_allowance_m=.0005,
            minimum_normal_area_m2=1e-14,minimum_normal_coherence=.1),
        contacts=dict(touch=dict(target_normal=dict(space='world',normals=[[0.,0.,-1. if opposed else 1.]]))))


def planned(tmp_path,authored,opposed=True):
    package,engine=authored;p=tmp_path/'surface-policy.json';save(p,policy(package,opposed));recipe=tmp_path/'recipe.json'
    jobs.plan(package,p,engine,recipe);return package,p,recipe


@pytest.mark.parametrize('fault',['policy','package','engine','extra','method'])
def test_pinned_plan_rejects_changed_inputs_before_execution(tmp_path,authored,fault):
    package,p,recipe=planned(tmp_path,authored);value=read(recipe)
    if fault=='policy':save(p,{**read(p),'maximum_actor_pose_queries':1999})
    elif fault in ('package','engine'):value[fault]['sha256']='0'*64
    elif fault=='extra':value['quality_approved']=True
    else:value['implementation_sha256']['material_scene_surface_job.py']='0'*64
    save(recipe,value)
    with pytest.raises(ValueError):jobs.validated(recipe)
    assert not (tmp_path/'execution').exists()


def test_busy_worker_refuses_before_output_and_plan_cannot_mutate_package(tmp_path,authored,monkeypatch):
    package,p,recipe=planned(tmp_path,authored)
    with pytest.raises(ValueError,match='outside'):jobs.plan(package,p,authored[1],package/'recipe.json')
    monkeypatch.setattr(jobs,'worker_busy',lambda:True)
    with pytest.raises(ValueError,match='worker'):jobs.run(recipe,tmp_path/'execution')
    assert not (tmp_path/'execution').exists()


@pytest.mark.parametrize('fault',['timing','limit','actor','geometry','other-object'])
def test_active_object_edit_changes_only_declared_keyframes(tmp_path,fault):
    source,path,spec,scene,edit=object_fixture(tmp_path);active=copy.deepcopy(spec)
    active['objects']['item']['keyframes'][1]['translation_m'][0]+=.001
    candidate=tmp_path/'candidate.json';save(candidate,active)
    jobs.active_scene(spec,tmp_path,candidate,edit)
    if fault=='timing':active['contacts'][0]['interval_s'][0]+=.01
    elif fault=='limit':active['contacts'][0]['limits']['position_m']=.02
    elif fault=='actor':active['actors']['A']['placement']['translation_m'][0]+=.01
    elif fault=='geometry':active['objects']['item']['geometry']['radius_m']+=.01
    else:active['objects']['extra']=copy.deepcopy(active['objects']['item'])
    save(candidate,active)
    with pytest.raises(ValueError):jobs.active_scene(spec,tmp_path,candidate,edit)
    with pytest.raises(ValueError):jobs.active_scene(spec,tmp_path,candidate,None)


def mocked_engine(monkeypatch):
    import subprocess
    def execute(command,**kwargs):
        request=read(command[-2]);cases=[]
        for case in request['cases']:
            rig=RigAsset.load(case['path']);sampler=NativeSupportSampler(rig.document,rig.binary,case['animation_index'])
            row=mock_actor(rig,sampler,request['sample_times_s'],path=case['path']);row['id']=case['id']
            for mesh,primitive in zip(row['meshes'],rig.primitives):mesh['node']=f"mesh-{primitive['node']}"
            for frame in row['frames']:
                frame['mesh_world']=[dict(node=name,matrix=copy.deepcopy(frame['skeleton_world']))
                    for name in dict.fromkeys(mesh['node'] for mesh in row['meshes'])]
            cases.append(row);Path(case['animation_output']).write_bytes(b'explicit mocked resource')
        save(command[-1],dict(engine=dict(string='fixture only'),cases=cases,objects=[]));return SimpleNamespace(returncode=0)
    monkeypatch.setattr(subprocess,'run',execute)


@pytest.mark.parametrize('opposed',[True,False])
def test_full_native_api_job_requires_facing_even_when_points_and_geometry_pass(tmp_path,authored,monkeypatch,opposed):
    package,p,recipe=planned(tmp_path,authored,opposed);before=jobs.files(package)
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'fixture-lock');mocked_engine(monkeypatch)
    output=tmp_path/'execution';result=jobs.run(recipe,output)
    assert result['status']=='complete' and result['point_and_geometry_conditions_pass']
    assert result['native_and_imported_surface_conditions_pass']==result['sampled_conditions_pass']==opposed
    assert result['surface_counts']['source-native']['failed_orientation_or_side_points']==int(not opposed)
    assert result['surface_counts']['native-authoring']['failed_orientation_or_side_points']==int(not opposed)
    expected=read(p);expected['contacts_sha256']=sha256(Path(read(output/'authoring-execution/engine-job/result.json')['artifacts']['active_contacts']))
    assert read(output/'effective-surface-policy.json')==expected and jobs.files(package)==before
    assert read(output/'surface-replay.json')['complete_normals_points_and_decisions_recomputed']
    assert not any(result[k] for k in ('studio_selection_changed','quality_approved','training_admitted','release_approved',
        'gpu_render_checked','physics_verified','real_time_playback_verified','human_reviewed'))


def test_mid_surface_replay_receipt_mutation_preserves_failed_partial_job(tmp_path,authored,monkeypatch):
    _,_,recipe=planned(tmp_path,authored)
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'fixture-lock');mocked_engine(monkeypatch)
    original=jobs.surface_verify;output=tmp_path/'execution'
    def changed(folder):
        result=original(folder);p=output/'authoring-execution/engine-job/result.json';value=read(p)
        value['quality_approved']=True;save(p,value);return result
    monkeypatch.setattr(jobs,'surface_verify',changed)
    with pytest.raises(ValueError,match='receipts changed'):jobs.run(recipe,output)
    assert read(output/'pipeline.json')['status']=='failed' and not (output/'result.json').exists()
    assert (output/'surface-audit/result.json').exists() and (output/'surface-replay.json').exists()
