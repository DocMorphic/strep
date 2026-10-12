"""Real saved-key repair, original references and public fitting integration."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_fit_storage as storage
from native_scene_fit import SceneProblem,run
from native_scene_resume import ResumeState
from native_scene_boundary_edit import BoundarySceneEdits,SCHEMA as BOUNDARY
from native_scene_contacts import SceneContacts
from native_rotation_storage_repair import StorageAdjustedEdits,authoring_digest,SCHEMA as REPAIR
from native_storage_continuation import state_for,StorageContinuationEdits
from native_rotation_speed_fit import SpeedLimitedSceneProblem
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from gltf_tools import append_accessor,write_glb
from strep import save,read,sha256
from test_native_scene_fit import prepare


def fixture(tmp_path):
    source,spec,contacts,permissions,permissions_path,_,_=prepare(tmp_path)
    rig=RigAsset.load(source);doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
    animation=doc['animations'][0];channel=next(c for c in animation['channels'] if c['target']['node']==3)
    old=animation['samplers'][channel['sampler']]
    q=np.tile(Rotation.from_euler('z',30,degrees=True).as_quat(),(11,1))
    channel['sampler']=len(animation['samplers'])
    animation['samplers'].append(dict(old,output=append_accessor(doc,binary,q,'VEC4')))
    write_glb(source,doc,binary);rig=RigAsset.load(source);reader=NativeSupportSampler(rig.document,rig.binary,0)
    spec['actors']['A']['sha256']=sha256(source)
    spec['contacts'][0].update(mode='touch',interval_s=[0.,0.],limits=dict(position_m=1e-5),
        target=dict(space='world',points_m=rig.vertices(reader.sample(0))[[0]].tolist()))
    save(contacts,spec);permissions['contacts_sha256']=sha256(contacts)
    permissions['actors']['A']['tracks']=[dict(node=3,path='rotation',maximum_change=5.)]
    save(permissions_path,permissions)
    boundary=dict(schema=BOUNDARY,permissions=permissions,boundary_keys=dict(A=dict(start='preserve',end='preserve')),
        acknowledge_changed_boundary_compatibility=False)
    boundary_path=tmp_path/'boundary.json';save(boundary_path,boundary)
    base=BoundarySceneEdits(boundary,SceneContacts(spec,tmp_path),sha256(contacts),rotation_storage_policy='source-scale')
    policy=dict(schema=REPAIR,authoring_sha256=authoring_digest(base),maximum_component_steps=1,
        maximum_corrections=64,acknowledge_storage_adjustment=True)
    policy_path=tmp_path/'repair-policy.json';save(policy_path,policy)
    correction=dict(actor='A',node=3,key_index=int(base.actors['A']['tracks'][0]['ids'][0]),component=3,step=1)
    return base,policy,correction,contacts,permissions_path,boundary_path,policy_path


def corrected(base,policy,correction,tmp_path):
    path=tmp_path/'corrected.glb';StorageAdjustedEdits(base,policy,[correction]).export('A',base.initial,path)
    state=state_for(base,policy,base.initial,[correction],{'A':path});state_path=tmp_path/'continuation.json';save(state_path,state)
    return StorageContinuationEdits(base,policy,state,tmp_path),state_path


@pytest.mark.parametrize('speed',[False,True])
def test_actual_storage_only_defect_is_repaired_and_all_original_rows_pass(tmp_path,speed):
    base,policy,correction,*_=fixture(tmp_path);editor,_=corrected(base,policy,correction,tmp_path)
    problem=SpeedLimitedSceneProblem(base.scene,editor,rotation_speed_limits={('A',3):0.}) if speed else SceneProblem(base.scene,editor)
    original=SceneProblem(base.scene,base);before=[v.copy() for v in problem.caps['A'].caps]
    folder=tmp_path/'proposal';folder.mkdir();helper=storage.FitStorage(problem,policy,stages=2,probes=8)
    residual,worlds,actual,report=helper.evaluate(problem.initial,folder)
    assert report['status']=='native-repaired' and report['native_failed_before']>0
    assert report['unrounded_failed']==report['native_failed_after']==0 and np.all(residual<=0)
    assert actual.corrections==[] and report['native_conditions_pass']
    assert report['unrounded_observations_sha256']==sha256(folder/'unrounded-observations.npz')
    with np.load(folder/'unrounded-observations.npz',allow_pickle=False) as intended:
        np.testing.assert_array_equal(intended['residual'],problem.constraints(problem.initial,problem.worlds(problem.initial,quantized=False)))
    assert not report['geometry_assessed'] and not report['quality_approved'] and not report['release_approved']
    for old,new in zip(before,problem.caps['A'].caps):np.testing.assert_array_equal(old,new)
    np.testing.assert_array_equal(original.source_world['A'],problem.source_world['A'])
    archive=read(folder/'storage-search/search-result.json');assert archive['tested_neighbors']>=1
    assert archive['native_conditions_pass'] and editor.corrections==[correction]
    assert sha256(folder/'A.glb')==sha256(folder/'storage-search'/archive['final_label']/'actor-0.glb')
    for record in archive['records']:
        probe=read(folder/'storage-search'/record['label']/'probe.json')
        assert probe['native_conditions']==len(residual)
        if speed:assert probe['rotation_speed_audit']['tracks'][0]['neighbor_comparisons']==10
    if speed:assert problem.last_speed_output_audit['passed']


def test_passing_native_export_never_runs_search(tmp_path,monkeypatch):
    base,policy,*_=fixture(tmp_path);problem=SceneProblem(base.scene,base);folder=tmp_path/'proposal';folder.mkdir()
    monkeypatch.setattr(storage,'search',lambda *a,**k:pytest.fail('Unnecessary search'))
    native,_,_,report=storage.FitStorage(problem,policy).evaluate(problem.initial,folder)
    assert np.all(native<=0) and report['status']=='already-native-feasible'


def test_intended_contact_failure_is_not_precision_repaired(tmp_path,monkeypatch):
    base,policy,_,contacts,_,_,_=fixture(tmp_path);spec=read(contacts)
    spec['contacts'][0]['target']['points_m'][0][0]+=.001;save(contacts,spec)
    request=copy.deepcopy(base.request);request['permissions']['contacts_sha256']=sha256(contacts)
    base=BoundarySceneEdits(request,SceneContacts(spec,tmp_path),sha256(contacts),rotation_storage_policy='source-scale')
    policy['authoring_sha256']=authoring_digest(base);problem=SceneProblem(base.scene,base)
    monkeypatch.setattr(storage,'search',lambda *a,**k:pytest.fail('Intended failure must remain visible'))
    folder=tmp_path/'proposal';folder.mkdir();native,_,_,report=storage.FitStorage(problem,policy).evaluate(problem.initial,folder)
    assert np.any(native>0) and report['status']=='intended-motion-failed' and report['unrounded_failed']>0


def test_failed_search_keeps_original_proposal_and_every_failed_export(tmp_path,monkeypatch):
    base,policy,correction,*_=fixture(tmp_path);editor,_=corrected(base,policy,correction,tmp_path)
    problem=SceneProblem(base.scene,editor);folder=tmp_path/'proposal';folder.mkdir()
    def fail_search(problem,value,policy,seed,decode,**kwargs):
        native,worlds=decode(seed,'start');changed=[dict(seed[0],step=-1)]
        other,_=decode(changed,'failed');assert np.any(other>0)
        return changed,dict(native_conditions_pass=False,final_label='failed')
    monkeypatch.setattr(storage,'search',fail_search)
    native,_,actual,report=storage.FitStorage(problem,policy).evaluate(problem.initial,folder)
    assert np.any(native>0) and actual.corrections==[correction] and report['status']=='native-repair-failed'
    assert report['selected_native_label']=='start' and (folder/'storage-search/failed/observations.npz').exists()
    assert sha256(folder/'A.glb')==sha256(folder/'storage-search/start/actor-0.glb')


@pytest.mark.parametrize('filename',['probe.json','observations.npz','actor-0.glb'])
def test_changed_failed_search_evidence_cannot_be_ignored(tmp_path,monkeypatch,filename):
    base,policy,correction,*_=fixture(tmp_path);editor,_=corrected(base,policy,correction,tmp_path)
    problem=SceneProblem(base.scene,editor);folder=tmp_path/'proposal';folder.mkdir()
    def corrupt(problem,value,policy,seed,decode,**kwargs):
        decode(seed,'start');changed=[dict(seed[0],step=-1)];decode(changed,'failed')
        (folder/'storage-search/failed'/filename).write_bytes(b'changed failed evidence')
        return changed,dict(native_conditions_pass=False,final_label='failed')
    monkeypatch.setattr(storage,'search',corrupt)
    with pytest.raises(ValueError,match='Recorded native search probe changed'):
        storage.FitStorage(problem,policy).evaluate(problem.initial,folder)
    assert not (folder/'A.glb').exists()


@pytest.mark.parametrize('mutation',['policy','seed','authoring','times','uniform','lower','upper','worlds','caps','source'])
def test_mutated_reference_cannot_export(tmp_path,mutation):
    base,policy,*_=fixture(tmp_path);problem=SceneProblem(base.scene,base);helper=storage.FitStorage(problem,policy)
    if mutation=='policy':helper.policy['maximum_corrections']=63
    elif mutation=='seed':helper.seed.append({})
    elif mutation=='authoring':base.request['permissions']['actors']['A']['maximum_joint_displacement_m']=.021
    elif mutation in ('times','uniform','lower','upper'):getattr(problem,mutation)[0]+=.001
    elif mutation=='worlds':problem.source_world['A'][0,0,0,3]+=.001
    elif mutation=='caps':problem.caps['A'].caps[0][0,0]+=.001
    else:Path(next(iter(base.scene.inputs))).write_bytes(b'changed')
    folder=tmp_path/'proposal';folder.mkdir()
    with pytest.raises(ValueError):helper.evaluate(problem.initial,folder)


@pytest.mark.parametrize('stages,probes',[(True,8),(0,8),(9,8),(2,True),(2,0),(2,65)])
def test_finite_search_budget_is_explicit(tmp_path,stages,probes):
    base,policy,*_=fixture(tmp_path)
    with pytest.raises(ValueError):storage.FitStorage(SceneProblem(base.scene,base),policy,stages=stages,probes=probes)


def job_fixture(tmp_path):
    base,policy,correction,contacts,permissions,boundary,repair=fixture(tmp_path)
    # Endpoint contact and high floor clearance keep this complete synthetic
    # job small; geometry pass is a fixture fact, never human-motion evidence.
    geometry=tmp_path/'geometry.json';save(geometry,dict(schema='strep-native-scene-geometry-v1',
        contacts_sha256=sha256(contacts),clock=dict(mode='native-and-frame-populations',times_s=[0.,2.]),
        limits=dict(penetration_m=.005,depth_resolution_m=1e-5,surface_tolerance_m=1e-8),
        planes=dict(floor=dict(normal_world=[0.,1.,0.],offset_m=-1.))))
    return base,policy,correction,contacts,permissions,boundary,repair,geometry


@pytest.mark.parametrize('speed',[False,True])
def test_public_surface_fit_repairs_start_and_writes_original_bound_next_state(tmp_path,speed):
    base,policy,correction,contacts,permissions,boundary,repair,geometry=job_fixture(tmp_path)
    _,continuation=corrected(base,policy,correction,tmp_path);kwargs={}
    if speed:
        speed_path=tmp_path/'speed.json';save(speed_path,dict(schema='strep-native-rotation-speed-policy-v1',
            contacts_sha256=sha256(contacts),tracks=[dict(actor='A',node=3,maximum_degrees_per_second=0.)]))
        kwargs['rotation_speed_policy']=speed_path
    out=tmp_path/'job';result=run(contacts,permissions,out,proposal_model='surface-vector',iterations=1,
        geometry_policy=geometry,boundary_edit=boundary,storage_repair_policy=repair,storage_continuation=continuation,
        rotation_storage_policy='source-scale',storage_repair_stages=2,storage_repair_probes=8,**kwargs)
    assert result['native_constraints_pass'] and result['sampled_geometry_conditions_pass']
    assert result['original_selected'] and not result['release_approved']
    assert result['probes'][0]['storage_repair_status']=='native-repaired'
    next_state=read(out/'final-storage-continuation.json');assert next_state['corrections']==[]
    # Each proposal starts from the explicitly bound corrections, never a new
    # source epoch. The final serialized state must reproduce its actual export.
    continued=StorageContinuationEdits(base,policy,next_state,out)
    new=tmp_path/'reexport.glb';continued.export('A',continued.initial,new)
    assert sha256(new)==sha256(out/'proposal/actor-0.glb')
    assert sha256(out/'storage-continuation.json')==sha256(continuation)
    assert sha256(out/'continuation-input/actor-0.glb')==read(continuation)['actors']['A']['sha256']
    if speed:assert result['rotation_speed_conditions_pass']
    with pytest.raises(ValueError,match='corrected-key continuation'):
        ResumeState(out,sha256(contacts),sha256(permissions),base)


def test_serialized_speed_audit_rejects_another_authoring_instance(tmp_path):
    first=tmp_path/'first';second=tmp_path/'second';first.mkdir();second.mkdir()
    base,policy,correction,*_=fixture(first);other,other_policy,other_row,*_=fixture(second)
    editor,_=corrected(base,policy,correction,first)
    unrelated=StorageAdjustedEdits(other,other_policy,[other_row])
    problem=SpeedLimitedSceneProblem(base.scene,editor,rotation_speed_limits={('A',3):1.})
    with pytest.raises(ValueError,match='original authoring instance'):
        problem.decoded({'A':first/'corrected.glb'},problem.initial,output_edits=unrelated)


@pytest.mark.parametrize('fault',['missing-boundary','missing-policy','legacy-resume','wrong-model','orphan-budget','permissions'])
def test_public_fit_rejects_unbound_or_dropped_storage_inputs(tmp_path,fault):
    base,policy,correction,contacts,permissions,boundary,repair,geometry=job_fixture(tmp_path)
    _,state=corrected(base,policy,correction,tmp_path)
    kwargs=dict(proposal_model='surface-vector',geometry_policy=geometry,boundary_edit=boundary,
        storage_repair_policy=repair,storage_continuation=state,rotation_storage_policy='source-scale')
    if fault=='missing-boundary':kwargs['boundary_edit']=None
    elif fault=='missing-policy':kwargs['storage_repair_policy']=None
    elif fault=='legacy-resume':kwargs['resume_from']=tmp_path/'previous'
    elif fault=='wrong-model':kwargs['proposal_model']='scalar'
    elif fault=='orphan-budget':kwargs.update(storage_repair_policy=None,storage_continuation=None,storage_repair_stages=2)
    else:
        request=read(boundary);request['permissions']['actors']['A']['maximum_joint_displacement_m']=.021;save(boundary,request)
    out=tmp_path/'job'
    with pytest.raises(ValueError):run(contacts,permissions,out,**kwargs)
    assert not out.exists()
