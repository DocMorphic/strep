"""Corrected starts reproduce keys while caps and source worlds stay original."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_storage_continuation import StorageContinuationEdits,state_for
from native_rotation_storage_repair import StorageAdjustedEdits
from native_scene_fit import SceneProblem
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from strep import sha256
from test_native_rotation_storage_repair import fixture


def prepare(tmp_path):
    base,policy,row=fixture(tmp_path);value=base.initial.copy();value[0]=.01
    path=tmp_path/'corrected.glb';StorageAdjustedEdits(base,policy,[row]).export('A',value,path)
    state=state_for(base,policy,value,[row],{'A':path})
    return base,policy,state,path


def test_initial_keys_worlds_and_original_caps_are_not_rebased(tmp_path):
    base,policy,state,path=prepare(tmp_path);before=SceneProblem(base.scene,base)
    continued=StorageContinuationEdits(base,policy,state,tmp_path);after=SceneProblem(base.scene,continued)
    assert continued.scene is base.scene and continued.base is base
    np.testing.assert_array_equal(after.initial,state['controls']);np.testing.assert_array_equal(base.initial,np.zeros(base.size))
    np.testing.assert_array_equal(before.source_world['A'],after.source_world['A'])
    for a,b in zip(before.caps['A'].caps,after.caps['A'].caps):np.testing.assert_array_equal(a,b)
    rig=RigAsset.load(path);sampler=NativeSupportSampler(rig.document,rig.binary,0)
    np.testing.assert_allclose(after.worlds(after.initial)['A'],np.array([sampler.sample(float(t)) for t in after.times]),atol=2e-12,rtol=0)
    out=tmp_path/'reexport.glb';continued.export('A',after.initial,out);assert sha256(out)==sha256(path)
    old=base.values('A',after.initial,quantized=False);new=continued.values('A',after.initial,quantized=False)
    for k in old:np.testing.assert_array_equal(old[k],new[k])
    report=continued.check_continuation();assert report['original_scene_reference_retained'] and not report['native_conditions_assessed'] and not report['release_approved']


@pytest.mark.parametrize('fault',['schema','authoring','policy-binding','source','controls-bool','controls-box','controls-nan','actor','index-bool','index','hash','extra','correction'])
def test_bad_or_partial_state_cannot_start(tmp_path,fault):
    base,policy,state,path=prepare(tmp_path)
    if fault=='schema':state['schema']='other'
    elif fault=='authoring':state['authoring_sha256']='0'*64
    elif fault=='policy-binding':state['storage_policy_sha256']='0'*64
    elif fault=='source':state['source_assets_sha256']={}
    elif fault=='controls-bool':state['controls'][0]=True
    elif fault=='controls-box':state['controls'][0]=2
    elif fault=='controls-nan':state['controls'][0]=float('nan')
    elif fault=='actor':state['actors']={}
    elif fault=='index-bool':state['actors']['A']['animation_index']=True
    elif fault=='index':state['actors']['A']['animation_index']=1
    elif fault=='hash':state['actors']['A']['sha256']='0'*64
    elif fault=='extra':state['approved']=True
    else:state['corrections']=[]
    with pytest.raises(ValueError):StorageContinuationEdits(base,policy,state,tmp_path)


@pytest.mark.parametrize('fault',['file','initial','policy','corrections','state','authoring'])
def test_loaded_state_change_is_detected(tmp_path,fault):
    base,policy,state,path=prepare(tmp_path);continued=StorageContinuationEdits(base,policy,state,tmp_path)
    if fault=='file':path.write_bytes(path.read_bytes()+b'changed')
    elif fault=='initial':continued.initial[0]=.02
    elif fault=='policy':continued.policy['maximum_corrections']=63
    elif fault=='corrections':continued.corrections.clear()
    elif fault=='state':continued.state['controls'][0]=.03
    else:base.request['permissions']['actors']['A']['maximum_joint_displacement_m']=.01
    with pytest.raises(ValueError):continued.check_continuation()


def test_proposal_changes_stay_inside_original_envelope(tmp_path):
    base,policy,state,path=prepare(tmp_path);continued=StorageContinuationEdits(base,policy,state,tmp_path)
    value=continued.initial.copy();value[0]+=.001
    out=tmp_path/'proposal.glb';continued.export('A',value,out)
    assert continued.audit('A',out,0,value=value)['passed']
    with pytest.raises(ValueError):continued.values('A',np.full(base.size,1.01))
    assert not continued.check_continuation()['quality_approved']


@pytest.mark.parametrize('fault',['candidate','source'])
def test_binding_detects_file_changes_during_payload_audit(tmp_path,monkeypatch,fault):
    base,policy,state,path=prepare(tmp_path);original=StorageAdjustedEdits.audit
    def changed(self,*args,**kwargs):
        report=original(self,*args,**kwargs)
        target=path if fault=='candidate' else Path(next(iter(base.scene.inputs)))
        target.write_bytes(target.read_bytes()+b'changed');return report
    monkeypatch.setattr(StorageAdjustedEdits,'audit',changed)
    with pytest.raises(ValueError):state_for(base,policy,state['controls'],state['corrections'],{'A':path})
