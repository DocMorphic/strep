"""Stored-anchor alignment and byte-identical export with frozen offsets."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_rotation_storage_repair import fixture
from native_rotation_storage_repair import StorageAdjustedEdits
from native_stored_curve_proxy import StoredCurveProxy
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_scene_fit import SceneProblem
from native_scene_norms import rows,linearize
from strep import sha256


def prepare(tmp_path):
    base,policy,row=fixture(tmp_path);editor=StorageAdjustedEdits(base,policy,[row])
    x=base.initial.copy();x[0]=.013;path=tmp_path/'anchor.glb';editor.export('A',x,path)
    return editor,x,path,StoredCurveProxy(editor,x,{'A':path})


def test_anchor_keys_and_complete_worlds_match_actual_export(tmp_path):
    editor,x,path,proxy=prepare(tmp_path)
    rig=RigAsset.load(path);reader=NativeSupportSampler(rig.document,rig.binary,0)
    actual={(node,track):values for node,track,clock,values,mode in reader.channels}
    for key,values in proxy.values('A',x,quantized=False).items():np.testing.assert_array_equal(values,actual[key])
    times=np.unique(np.r_[np.linspace(0,2,241),reader.channels[0][2]])
    np.testing.assert_allclose(proxy.worlds('A',x,times,quantized=False),np.array([reader.sample(float(t)) for t in times]),atol=2e-12,rtol=0)
    assert not proxy.anchor.flags.writeable and all(not a.flags.writeable for a in proxy.offsets['A'].values())


def test_float32_endpoint_neighborhood_uses_scalar_native_clamping(tmp_path):
    editor,x,path,proxy=prepare(tmp_path);rig=RigAsset.load(path);reader=NativeSupportSampler(rig.document,rig.binary,0)
    last=np.float32(reader.duration);ulp=float(np.spacing(last));times=np.array([float(last)-ulp/4,float(last),float(last)+ulp/4])
    np.testing.assert_allclose(proxy.worlds('A',x,times,quantized=False),np.array([reader.sample(float(t)) for t in times]),atol=2e-12,rtol=0)


def test_frozen_offsets_remain_smooth_and_original_quantization_is_unchanged(tmp_path):
    editor,x,path,proxy=prepare(tmp_path);before={k:v.copy() for k,v in proxy.offsets['A'].items()}
    for step in (-.001,.001):
        other=x.copy();other[0]+=step
        continuous=editor.values('A',other,quantized=False)
        for key,values in proxy.values('A',other,quantized=False).items():np.testing.assert_array_equal(values,continuous[key]+before[key])
        for key,values in proxy.values('A',other).items():np.testing.assert_array_equal(values,editor.values('A',other)[key])
    for key in before:np.testing.assert_array_equal(proxy.offsets['A'][key],before[key])


def test_every_native_derivative_matches_direct_scalar_trs_sampling(tmp_path):
    editor,x,path,proxy=prepare(tmp_path);problem=SceneProblem(editor.scene,editor)
    centered=copy.copy(problem);centered.edits=proxy
    original={k:v.copy() for k,v in editor.values('A',x,quantized=False).items()}
    rig=RigAsset.load(path);reader=NativeSupportSampler(rig.document,rig.binary,0)
    stored={(node,track):values.astype(float).copy() for node,track,clock,values,mode in reader.channels}
    offsets={k:stored[k]-v for k,v in original.items()};channels=reader.channels
    def vectors(value):
        keys=editor.values('A',value,quantized=False)
        reader.channels=[(node,track,clock,keys[node,track]+offsets[node,track] if (node,track) in keys else payload,mode)
            for node,track,clock,payload,mode in channels]
        worlds={'A':np.array([reader.sample(float(t)) for t in problem.times])}
        return rows(problem,value,worlds)
    _,jacobian,report=linearize(centered,x,step=.001,difference_source='continuous',difference_scheme='central')
    assert report['central_difference_columns']==problem.size
    for i in range(problem.size):
        plus,minus=x.copy(),x.copy();plus[i]+=.001;minus[i]-=.001
        a,b=vectors(plus),vectors(minus)
        np.testing.assert_array_equal(a.caps,b.caps);np.testing.assert_array_equal(a.scales,b.scales)
        expected=((a.vectors-b.vectors)/.002).ravel()
        np.testing.assert_allclose(jacobian[:,i].toarray().ravel(),expected,atol=2e-9,rtol=1e-8)


def test_export_and_original_library_are_identical_to_existing_editor(tmp_path):
    editor,x,path,proxy=prepare(tmp_path);other=x.copy();other[0]+=.001
    a,b=tmp_path/'base.glb',tmp_path/'proxy.glb';editor.export('A',other,a);proxy.export('A',other,b)
    assert sha256(a)==sha256(b) and proxy.audit('A',b,0,value=other)['passed']
    c,d=tmp_path/'base-library.glb',tmp_path/'proxy-library.glb'
    editor.append_candidate('A',other,c,'Unapproved');proxy.append_candidate('A',other,d,'Unapproved')
    assert sha256(c)==sha256(d)


def test_changed_anchor_bytes_reject(tmp_path):
    editor,x,path,proxy=prepare(tmp_path);path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='bytes changed'):proxy.values('A',x,quantized=False)


def test_wrong_storage_payload_cannot_seed_proxy(tmp_path):
    base,policy,row=fixture(tmp_path);editor=StorageAdjustedEdits(base,policy,[row]);x=base.initial.copy();x[0]=.013
    path=tmp_path/'plain.glb';base.export('A',x,path)
    with pytest.raises(ValueError):StoredCurveProxy(editor,x,{'A':path})


@pytest.mark.parametrize('fault',['corrections','request','box','weights'])
def test_changed_editor_contract_requires_fresh_proxy(tmp_path,fault):
    editor,x,path,proxy=prepare(tmp_path)
    if fault=='corrections':editor.corrections[0]['step']=-editor.corrections[0]['step']
    elif fault=='request':editor.base.request['acknowledge_changed_boundary_compatibility']=True
    elif fault=='box':editor.base.upper[0]=.5
    elif fault=='weights':editor.base.actors['A']['tracks'][0]['weights'][0,0]+=.1
    with pytest.raises(ValueError,match='contract changed'):proxy.values('A',x,quantized=False)


@pytest.mark.parametrize('fault',['missing-actor','extra-actor','unbound-editor','outside','nonfinite','bool-mode'])
def test_invalid_proxy_contract_rejects(tmp_path,fault):
    editor,x,path,proxy=prepare(tmp_path)
    if fault=='bool-mode':
        with pytest.raises(ValueError):proxy.values('A',x,quantized=1)
        return
    files={'A':path};base=editor
    if fault=='missing-actor':files={}
    elif fault=='extra-actor':files['B']=path
    elif fault=='unbound-editor':base=editor.base
    elif fault=='outside':x[0]=2.
    elif fault=='nonfinite':x[0]=np.nan
    with pytest.raises(ValueError):StoredCurveProxy(base,x,files)
