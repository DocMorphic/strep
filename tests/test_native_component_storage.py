"""Typed actual Float32 key edits, strict bounds, frozen support and continuation."""
from pathlib import Path
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_contacts import SceneContacts
from native_scene_boundary_edit import BoundarySceneEdits,SCHEMA as BOUNDARY
from native_rotation_storage_repair import authoring_digest,StorageAdjustedEdits
from native_component_storage_repair import SCHEMA,ComponentAdjustedEdits
from native_component_storage_continuation import ComponentContinuationEdits,state_for
from native_storage_continuation import StorageContinuationEdits
from native_scene_fit import SceneProblem
from strep import read,save,sha256
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from gltf_tools import append_accessor,write_glb
from test_native_fit_storage import fixture as rotation_fixture


def fixture(tmp_path,*,boundaries=False):
    base,_,_,contacts,permissions_path,boundary_path,_=rotation_fixture(tmp_path)
    # A constant root has zero source-rate caps, isolating the effect of one
    # stored-key neighbor instead of borrowing acceleration from another bin.
    source=Path(next(iter(base.scene.inputs)));rig=RigAsset.load(source)
    doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary);animation=doc['animations'][0]
    channel=next(c for c in animation['channels'] if c['target']==dict(node=0,path='translation'))
    sampler=animation['samplers'][channel['sampler']];count=doc['accessors'][sampler['input']]['count']
    sampler['output']=append_accessor(doc,binary,np.tile([0.,1.2,0.],(count,1)),'VEC3')
    write_glb(source,doc,binary);rig=RigAsset.load(source);reader=NativeSupportSampler(rig.document,rig.binary,0)
    spec=read(contacts);spec['actors']['A']['sha256']=sha256(source)
    spec['contacts'][0]['target']['points_m']=rig.vertices(reader.sample(0))[[0]].tolist();save(contacts,spec)
    permissions=read(permissions_path);permissions['actors']['A']['tracks'].insert(0,dict(node=0,path='translation',maximum_change=.02))
    permissions['contacts_sha256']=sha256(contacts)
    save(permissions_path,permissions)
    request=dict(schema=BOUNDARY,permissions=permissions,boundary_keys=dict(A=dict(start='edit' if boundaries else 'preserve',end='edit' if boundaries else 'preserve')),
        acknowledge_changed_boundary_compatibility=boundaries);save(boundary_path,request)
    base=BoundarySceneEdits(request,SceneContacts(read(contacts),tmp_path),sha256(contacts),rotation_storage_policy='unit')
    policy=dict(schema=SCHEMA,authoring_sha256=authoring_digest(base),allowed_paths=['rotation','translation'],
        maximum_component_steps=1,maximum_corrections=64,acknowledge_storage_adjustment=True)
    row=dict(actor='A',node=0,path='translation',key_index=5,component=1,step=1)
    return base,policy,row,contacts,permissions_path,boundary_path


@pytest.mark.parametrize('path',['translation','rotation'])
@pytest.mark.parametrize('step',[-1,1])
def test_actual_typed_neighbor_preserves_other_values_and_unrounded_curve(tmp_path,path,step):
    base,policy,row,*_=fixture(tmp_path);value=base.initial.copy()
    if path=='rotation':row.update(node=3,path='rotation',component=3)
    row['step']=step;edits=ComponentAdjustedEdits(base,policy,[row]);before=base.values('A',value)
    actual=edits.values('A',value);key=row['node'],row['path'];expected=before[key].copy()
    expected[row['key_index'],row['component']]=np.nextafter(np.float32(expected[row['key_index'],row['component']]),np.float32(np.inf if step>0 else -np.inf))
    for item in actual:np.testing.assert_array_equal(actual[item],expected if item==key else before[item])
    for item,data in base.values('A',value,quantized=False).items():np.testing.assert_array_equal(edits.values('A',value,quantized=False)[item],data)
    output=tmp_path/'changed.glb';edits.export('A',value,output)
    assert edits.audit('A',output,0,value=value)['passed']
    assert not edits.audit('A',output,0,value=value)['native_conditions_assessed']
    with pytest.raises(ValueError,match='Fresh'):edits.export('A',value,output)


@pytest.mark.parametrize('fault',['actor','node-bool','node-missing','path-scale','path-unallowed','component-bool','translation-w','key-bool','key-negative','key-end','step-bool','step-zero','step-two','duplicate','extra'])
def test_bad_or_unpermitted_corrections_reject_before_export(tmp_path,fault):
    base,policy,row,*_=fixture(tmp_path);rows=[row]
    if fault=='actor':row['actor']='B'
    elif fault=='node-bool':row['node']=False
    elif fault=='node-missing':row['node']=5
    elif fault=='path-scale':row['path']='scale'
    elif fault=='path-unallowed':policy['allowed_paths']=['rotation']
    elif fault=='component-bool':row['component']=True
    elif fault=='translation-w':row['component']=3
    elif fault=='key-bool':row['key_index']=True
    elif fault=='key-negative':row['key_index']=-1
    elif fault=='key-end':row['key_index']=0
    elif fault=='step-bool':row['step']=True
    elif fault=='step-zero':row['step']=0
    elif fault=='step-two':row['step']=2
    elif fault=='duplicate':rows.append(copy.deepcopy(row))
    else:row['approved']=True
    with pytest.raises(ValueError):ComponentAdjustedEdits(base,policy,rows)


@pytest.mark.parametrize('fault',['schema','authoring','paths-type','paths-empty','paths-repeat','paths-scale','steps-bool','steps-two','limit-bool','limit-large','ack','extra'])
def test_explicit_component_policy_is_required(tmp_path,fault):
    base,policy,_,*_=fixture(tmp_path)
    if fault=='schema':policy['schema']='strep-native-rotation-storage-repair-v1'
    elif fault=='authoring':policy['authoring_sha256']='0'*64
    elif fault=='paths-type':policy['allowed_paths']={}
    elif fault=='paths-empty':policy['allowed_paths']=[]
    elif fault=='paths-repeat':policy['allowed_paths']=['translation','translation']
    elif fault=='paths-scale':policy['allowed_paths']=['scale']
    elif fault=='steps-bool':policy['maximum_component_steps']=True
    elif fault=='steps-two':policy['maximum_component_steps']=2
    elif fault=='limit-bool':policy['maximum_corrections']=True
    elif fault=='limit-large':policy['maximum_corrections']=65
    elif fault=='ack':policy['acknowledge_storage_adjustment']=False
    else:policy['approved']=True
    with pytest.raises(ValueError):ComponentAdjustedEdits(base,policy,[])


def test_root_neighbor_causes_rate_failure_without_rebasing_source_caps(tmp_path):
    base,policy,row,*_=fixture(tmp_path);problem=SceneProblem(base.scene,base)
    original=problem.worlds(base.initial,quantized=False);edits=ComponentAdjustedEdits(base,policy,[row])
    output=tmp_path/'bad.glb';edits.export('A',base.initial,output)
    native,_=problem.decoded({'A':output},base.initial)
    assert np.all(problem.constraints(base.initial,original)<=0) and np.any(native>0)
    for key,value in base.values('A',base.initial,quantized=False).items():np.testing.assert_array_equal(edits.values('A',base.initial,quantized=False)[key],value)


@pytest.mark.parametrize('fault',['policy','corrections','authoring'])
def test_loaded_component_contract_cannot_be_mutated(tmp_path,fault):
    base,policy,row,*_=fixture(tmp_path);edits=ComponentAdjustedEdits(base,policy,[row])
    if fault=='policy':edits.policy['allowed_paths']=['rotation']
    elif fault=='corrections':edits.corrections[0]['key_index']=0
    else:base.request['acknowledge_changed_boundary_compatibility']=True
    with pytest.raises(ValueError,match='contract changed'):edits.values('A',base.initial)


def test_explicit_boundary_and_protected_support_remain_required(tmp_path):
    base,policy,row,*_=fixture(tmp_path,boundaries=True);row['key_index']=0
    output=tmp_path/'boundary.glb';edits=ComponentAdjustedEdits(base,policy,[row]);edits.export('A',base.initial,output)
    assert edits.audit('A',output,0,value=base.initial)['passed']
    request=copy.deepcopy(base.request);request['permissions']['actors']['A']['protected_s']=[[0.,.1]]
    with pytest.raises(ValueError):BoundarySceneEdits(request,base.scene,base.request['permissions']['contacts_sha256'])


def test_continuation_keeps_exact_source_and_typed_payload(tmp_path):
    base,policy,row,*_=fixture(tmp_path);path=tmp_path/'candidate.glb'
    ComponentAdjustedEdits(base,policy,[row]).export('A',base.initial,path)
    state=state_for(base,policy,base.initial,[row],{'A':path});edits=ComponentContinuationEdits(base,policy,state,tmp_path)
    second=tmp_path/'reexport.glb';edits.export('A',edits.initial,second);assert sha256(second)==sha256(path)
    assert edits.check_continuation()['original_scene_reference_retained']
    original=SceneProblem(base.scene,base);actual=SceneProblem(base.scene,edits)
    np.testing.assert_array_equal(original.source_world['A'],actual.source_world['A'])
    for a,b in zip(original.caps['A'].caps,actual.caps['A'].caps):np.testing.assert_array_equal(a,b)
    with pytest.raises(ValueError):StorageContinuationEdits(base,policy,state,tmp_path)
    with pytest.raises(ValueError):StorageAdjustedEdits(base,policy,[row])
    edits.corrections.clear()
    with pytest.raises(ValueError):edits.check_continuation()


def test_strict_bound_payload_identity_and_controls_cannot_be_bypassed(tmp_path):
    base,policy,row,*_=fixture(tmp_path);edits=ComponentAdjustedEdits(base,policy,[row]);plain=tmp_path/'plain.glb'
    base.export('A',base.initial,plain)
    with pytest.raises(ValueError,match='payload differs'):edits.audit('A',plain,0,value=base.initial)
    value=base.initial.copy();value[0]=2.
    with pytest.raises(ValueError,match='control boxes'):edits.values('A',value)
    # A neighbor beyond a source-relative translation cap is still rejected.
    base.actors['A']['tracks'][0]['maximum']=1e-12
    with pytest.raises(ValueError,match='strict track bound'):edits.values('A',base.initial)
