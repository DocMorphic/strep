"""Preserve source quaternion scale without changing intended orientations or caps."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_fit import prepare
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from native_scene_fit import run
from native_support_feasibility import merit
from gltf_tools import append_accessor,write_glb
from rig_asset import RigAsset
from strep import save,read,sha256


def scaled(tmp_path,*,factor=1+1e-7):
    source,spec,c,p,permissions,old,unused=prepare(tmp_path,rotation=True)
    rig=RigAsset.load(source);doc=copy.deepcopy(rig.document);data=bytearray(rig.binary)
    animation=doc['animations'][0]
    for channel in animation['channels']:
        if channel['target']==dict(node=3,path='rotation'):
            sampler=animation['samplers'][channel['sampler']]
            old_values=next(v for n,path,t,v,m in old.actors['A']['sampler'].channels if n==3 and path=='rotation')
            q=(Rotation.from_rotvec([.37,.21,.29]).as_quat()*factor).astype(np.float32)
            sampler['output']=append_accessor(doc,data,np.tile(q,(len(old_values),1)),'VEC4')
    write_glb(source,doc,data);spec['actors']['A']['sha256']=sha256(source);save(c,spec)
    p['contacts_sha256']=sha256(c);save(permissions,p);scene=SceneContacts(spec,tmp_path)
    unit=SceneEdits(p,scene,sha256(c));preserved=SceneEdits(p,scene,sha256(c),rotation_storage_policy='source-scale')
    return source,c,permissions,unit,preserved


def test_infinitesimal_edit_does_not_renormalize_source_float32_components(tmp_path):
    source,c,p,unit,preserved=scaled(tmp_path);x=unit.initial.copy();x[::3]=1e-15
    old=unit.values('A',unit.initial)[3,'rotation'].astype(np.float32)
    legacy=unit.values('A',x)[3,'rotation'].astype(np.float32)
    new=preserved.values('A',x)[3,'rotation'].astype(np.float32)
    np.testing.assert_array_equal(new,old);assert not np.array_equal(legacy,old)
    unchanged=tmp_path/'unchanged.glb';edited=tmp_path/'small.glb'
    preserved.export('A',unit.initial,unchanged);preserved.export('A',x,edited)
    assert sha256(unchanged)==sha256(edited) and preserved.audit('A',edited,0)['passed']


def test_source_scale_quaternion_product_preserves_right_multiplication_and_length(tmp_path):
    source,c,p,unit,preserved=scaled(tmp_path);x=unit.initial.copy();x.reshape(-1,3)[:]=[.1,-.07,.03]
    entry=preserved.actors['A']['tracks'][0];delta=entry['weights']@x[entry['controls']]*entry['unit']
    original=entry['source'][entry['ids']].astype(float)
    actual=preserved.values('A',x,quantized=False)[3,'rotation'][entry['ids']]
    expected=Rotation.from_quat(original)*Rotation.from_rotvec(delta)
    np.testing.assert_allclose(Rotation.from_quat(actual).as_matrix(),expected.as_matrix(),atol=5e-16,rtol=0)
    np.testing.assert_allclose(np.linalg.norm(actual,axis=1),np.linalg.norm(original,axis=1),atol=5e-16,rtol=0)
    output=tmp_path/'source-scale.glb';preserved.export('A',x,output)
    assert preserved.audit('A',output,0)['passed']


def test_resume_infers_source_scale_policy_and_rejects_incompatible_legacy_replay(tmp_path,monkeypatch):
    import native_scene_fit as fit
    source,c,p,unit,preserved=scaled(tmp_path);tiny=unit.initial.copy();tiny[::3]=1e-15
    def keep(problem,evaluate,*args):
        evaluate(problem.initial,'start')
        return tiny.copy(),dict(history=[],final_merit=list(merit(problem.model(tiny))))
    monkeypatch.setattr(fit,'optimize',keep)
    prior=tmp_path/'prior';run(c,p,prior,rotation_storage_policy='source-scale')
    resumed=tmp_path/'resumed';result=run(c,p,resumed,resume_from=prior)
    assert result['rotation_storage_policy']==read(resumed/'request.json')['rotation_storage_policy']=='source-scale'
    assert sha256(resumed/'probes/start/A.glb')==sha256(prior/'probes/final/A.glb')
    with np.load(prior/'source-rate-caps.npz') as a,np.load(resumed/'source-rate-caps.npz') as b:
        for k in a.files:np.testing.assert_array_equal(a[k],b[k])
    bad=tmp_path/'legacy'
    with pytest.raises(ValueError,match='exact resume exports'):run(c,p,bad,resume_from=prior,rotation_storage_policy='unit')
    assert read(bad/'pipeline.json')['status']=='failed'


@pytest.mark.parametrize('policy',['normalise-anything',True,4])
def test_invalid_policy_does_not_create_outputs(tmp_path,policy):
    source,c,p,unit,preserved=scaled(tmp_path);out=tmp_path/'bad'
    with pytest.raises(ValueError):run(c,p,out,rotation_storage_policy=policy)
    assert not out.exists()


def test_source_scale_rejects_larger_source_normalization_errors(tmp_path):
    with pytest.raises(ValueError,match='near-unit original Float32'):scaled(tmp_path,factor=1+2e-6)


def test_source_scale_rejects_non_float32_source_values(tmp_path):
    source,c,p,unit,preserved=scaled(tmp_path);scene=unit.scene
    for n,path,t,v,m in scene.actors['A']['sampler'].channels:
        if n==3 and path=='rotation':v[:,0]+=1e-12
    with pytest.raises(ValueError,match='near-unit original Float32'):
        SceneEdits(read(p),scene,sha256(c),rotation_storage_policy='source-scale')
