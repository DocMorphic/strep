"""One-neighbor envelope, preserved authoring support and real asset decoding."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_fit import prepare
from native_scene_boundary_edit import BoundarySceneEdits,SCHEMA as BOUNDARY_SCHEMA
from native_rotation_storage_repair import StorageAdjustedEdits,authoring_digest,SCHEMA
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from strep import sha256


def fixture(tmp_path):
    _,_,contacts,p,_,scene,_=prepare(tmp_path,rotation=True)
    request=dict(schema=BOUNDARY_SCHEMA,permissions=p,boundary_keys={'A':dict(start='preserve',end='preserve')},acknowledge_changed_boundary_compatibility=False)
    base=BoundarySceneEdits(request,scene,sha256(contacts),rotation_storage_policy='source-scale')
    policy=dict(schema=SCHEMA,authoring_sha256=authoring_digest(base),maximum_component_steps=1,maximum_corrections=64,acknowledge_storage_adjustment=True)
    entry=base.actors['A']['tracks'][0]
    row=dict(actor='A',node=3,key_index=int(entry['ids'][0]),component=3,step=1)
    return base,policy,row


def test_empty_adjustment_preserves_export_bytes(tmp_path):
    base,p,_=fixture(tmp_path);adjusted=StorageAdjustedEdits(base,p,[]);x=base.initial.copy();x[0]=.01
    a,b=tmp_path/'default.glb',tmp_path/'adjusted.glb';base.export('A',x,a);adjusted.export('A',x,b)
    assert sha256(a)==sha256(b)


@pytest.mark.parametrize('step',[-1,1])
def test_single_float32_neighbor_preserves_every_other_component_and_decodes(tmp_path,step):
    base,p,row=fixture(tmp_path);row['step']=step;adjusted=StorageAdjustedEdits(base,p,[row]);x=base.initial.copy();x[0]=.01
    nearest=base.values('A',x)[3,'rotation'];actual=adjusted.values('A',x)[3,'rotation']
    expected=nearest.copy();i=row['key_index'];expected[i,3]=np.nextafter(np.float32(nearest[i,3]),np.float32(np.inf if step>0 else -np.inf))
    np.testing.assert_array_equal(actual,expected)
    np.testing.assert_array_equal(adjusted.values('A',x,quantized=False)[3,'rotation'],base.values('A',x,quantized=False)[3,'rotation'])
    path=tmp_path/'neighbor.glb';adjusted.export('A',x,path);report=adjusted.audit('A',path,0,value=x)
    assert report['passed'] and not report['native_conditions_assessed'] and not report['release_approved']
    rig=RigAsset.load(path);reader=NativeSupportSampler(rig.document,rig.binary,0)
    times=np.unique(np.r_[np.linspace(0,2,91),reader.channels[0][2]])
    np.testing.assert_allclose(adjusted.worlds('A',x,times),np.array([reader.sample(float(t)) for t in times]),atol=2e-12,rtol=0)
    with pytest.raises(ValueError,match='Fresh'):adjusted.export('A',x,path)


def test_plain_or_differently_adjusted_payload_cannot_inherit_repair_audit(tmp_path):
    base,p,row=fixture(tmp_path);x=base.initial.copy();x[0]=.01
    adjusted=StorageAdjustedEdits(base,p,[row]);path=tmp_path/'plain.glb';base.export('A',x,path)
    with pytest.raises(ValueError,match='payload differs'):adjusted.audit('A',path,0,value=x)
    repaired=tmp_path/'repaired.glb';adjusted.export('A',x,repaired)
    other=StorageAdjustedEdits(base,p,[dict(row,step=-1)])
    with pytest.raises(ValueError,match='payload differs'):other.audit('A',repaired,0,value=x)


def test_appended_variant_retains_storage_corrections_and_complete_original_library(tmp_path):
    base,p,row=fixture(tmp_path);adjusted=StorageAdjustedEdits(base,p,[row]);x=base.initial.copy();x[0]=.01
    path=tmp_path/'appended.glb';index=adjusted.append_candidate('A',x,path,'Unapproved repaired variant')
    rig=RigAsset.load(path);original=base.scene.actors['A']['rig']
    assert rig.document['animations'][:-1]==original.document['animations']
    assert rig.binary[:len(original.binary)]==original.binary
    reader=NativeSupportSampler(rig.document,rig.binary,index)
    raw=next(c[3] for c in reader.channels if c[:2]==(3,'rotation'))
    np.testing.assert_array_equal(raw,adjusted.values('A',x)[3,'rotation'])
    with pytest.raises(ValueError,match='Fresh'):adjusted.append_candidate('A',x,path,'Duplicate')


@pytest.mark.parametrize('fault',['schema','binding','step-bool','step-two','budget-bool','budget-large','acknowledgement','extra'])
def test_explicit_policy_cannot_change_its_envelope_or_source(tmp_path,fault):
    base,p,row=fixture(tmp_path)
    if fault=='schema':p['schema']='old'
    if fault=='binding':p['authoring_sha256']='0'*64
    if fault=='step-bool':p['maximum_component_steps']=True
    if fault=='step-two':p['maximum_component_steps']=2
    if fault=='budget-bool':p['maximum_corrections']=True
    if fault=='budget-large':p['maximum_corrections']=65
    if fault=='acknowledgement':p['acknowledge_storage_adjustment']=False
    if fault=='extra':p['extra']=True
    with pytest.raises(ValueError):StorageAdjustedEdits(base,p,[row])


@pytest.mark.parametrize('fault',['actor','node-bool','unpermitted-node','key-bool','protected-key','component-bool','component-large','step-bool','step-two','duplicate','budget'])
def test_no_unpermitted_key_or_duplicate_can_expand_the_storage_changes(tmp_path,fault):
    base,p,row=fixture(tmp_path);rows=[row]
    if fault=='actor':row['actor']='B'
    if fault=='node-bool':row['node']=True
    if fault=='unpermitted-node':row['node']=0
    if fault=='key-bool':row['key_index']=True
    if fault=='protected-key':row['key_index']=0
    if fault=='component-bool':row['component']=True
    if fault=='component-large':row['component']=4
    if fault=='step-bool':row['step']=True
    if fault=='step-two':row['step']=2
    if fault=='duplicate':rows=[row,copy.deepcopy(row)]
    if fault=='budget':p['maximum_corrections']=1;other=copy.deepcopy(row);other['component']=2;rows.append(other)
    with pytest.raises(ValueError):StorageAdjustedEdits(base,p,rows)


def test_original_boxes_and_strict_track_bounds_still_apply(tmp_path):
    base,p,row=fixture(tmp_path);adjusted=StorageAdjustedEdits(base,p,[row])
    with pytest.raises(ValueError,match='boxes'):adjusted.values('A',np.full(base.size,1.01))
    with pytest.raises(ValueError,match='track bound'):adjusted.values('A',np.ones(base.size))
