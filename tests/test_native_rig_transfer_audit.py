"""Candidate binding/failure handling only; engine calls below are doubles."""
import copy
from pathlib import Path
import shutil
import sys

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_rig_transfer import pair,fixture
from gltf_tools import write_glb
from rig_asset import RigAsset
from strep import save,read,sha256
import native_rig_transfer as bridge
import audit_native_rig_transfer as audit


@pytest.fixture(scope='module')
def candidate(tmp_path_factory):
    root=tmp_path_factory.mktemp('native-transfer');args=pair(root)
    out=root/'candidate';bridge.export(*args,0,out)
    return out


def test_complete_bound_candidate_has_correct_appended_selection(candidate):
    value=audit.bound_candidate(candidate)
    assert value[-2]==1 and value[1]['target_skin_joints']==17 and value[1]['source_skin_joints']==19
    assert value[-1]==value[1]['target_mapping']['Hips']


@pytest.mark.parametrize('fault',['candidate','source','profile','method','report-method','status','selection','mapping',
    'snapshot-population','stored-clock','stored-transform','material-rehashed','old-clip-rehashed','recipe-rehashed'])
def test_corrupt_rehashed_or_incomplete_candidates_reject(candidate,tmp_path,fault):
    out=tmp_path/'candidate';shutil.copytree(candidate,out);report=read(out/'report.json')
    if fault in ('candidate','source','profile','method'):
        p=out/{'candidate':'character.glb','source':'source.glb','profile':'source-profile.json','method':'implementation/retarget_rig.py'}[fault]
        p.write_bytes(p.read_bytes()+b'corrupted')
    elif fault=='report-method':report['implementation_sha256'].pop('retarget_rig.py')
    elif fault=='status':report['status']='failed'
    elif fault=='selection':report['output_animation_index']=0
    elif fault=='mapping':report['target_mapping']['LeftHand']=report['target_mapping']['RightHand']
    elif fault=='snapshot-population':report['input_snapshots_sha256'].pop('source-profile.json')
    elif fault in ('stored-clock','stored-transform'):
        with np.load(out/'target-transforms.npz',allow_pickle=False) as a:values={k:a[k].copy() for k in a.files}
        if fault=='stored-clock':values['times_s'][1]+=.001
        else:values['global_matrices'][1,0,0,3]+=.1
        np.savez_compressed(out/'target-transforms.npz',**values);report['transforms_sha256']=sha256(out/'target-transforms.npz')
    else:
        rig=RigAsset.load(out/'character.glb');doc=copy.deepcopy(rig.document)
        if fault=='material-rehashed':doc['materials'][0]['pbrMetallicRoughness']['roughnessFactor']=.2
        if fault=='old-clip-rehashed':doc['animations'][0]['extras']['original']=False
        if fault=='recipe-rehashed':doc['animations'][1]['extras']['strep_native_transfer']['source_animation_index']=1
        write_glb(out/'character.glb',doc,rig.binary);report['glb_sha256']=sha256(out/'character.glb')
    save(out/'report.json',report)
    with pytest.raises(ValueError):audit.bound_candidate(out)


def test_target_optional_role_missing_in_source_rejects_valid_profiles(tmp_path):
    a,ap=fixture(tmp_path,'source',optional=False)
    b,bp=fixture(tmp_path,'target',optional=True,animated=False)
    with pytest.raises(ValueError,match='Every requested target role'):bridge.prepare(RigAsset.load(a),read(ap),RigAsset.load(b),read(bp),0)


def test_engine_failure_keeps_snapshot_and_original_selection(candidate,tmp_path,monkeypatch):
    before=sha256(candidate/'report.json')
    engine=tmp_path/'engine-double.exe';engine.write_bytes(b'Never executed engine double')
    monkeypatch.setattr(audit,'ENGINE',engine);monkeypatch.setattr(audit,'ENGINE_SHA256',sha256(engine))
    def fail(*args,**kwargs):raise ValueError('Injected owned engine stage failure')
    monkeypatch.setattr(audit,'engine_run',fail)
    out=tmp_path/'failed'
    with pytest.raises(ValueError,match='Injected'):audit.run(candidate,out)
    assert read(out/'pipeline.json')['status']=='failed' and read(out/'pipeline.json')['original_selected']
    assert not (out/'result.json').exists() and sha256(candidate/'report.json')==before
    assert sha256(out/'character.glb')==sha256(candidate/'character.glb')
    before_pipeline=sha256(out/'pipeline.json')
    with pytest.raises(ValueError,match='Fresh'):audit.run(candidate,out)
    assert sha256(out/'pipeline.json')==before_pipeline


def test_mapped_matrix_conversion_preserves_original_target_metadata(tmp_path):
    a,ap,b,bp=pair(tmp_path);rig=RigAsset.load(b);doc=copy.deepcopy(rig.document)
    from gltf_tools import local_matrix
    n=next(n for n in doc['nodes'] if n['name']=='target_LeftHand')
    matrix=local_matrix(n); n.pop('translation');n.pop('rotation');n['matrix']=matrix.T.reshape(-1).tolist();n['extras']={'user-authored':'keep'}
    write_glb(b,doc,rig.binary);p=read(bp);p['character_sha256']=sha256(b);save(bp,p)
    out=tmp_path/'candidate';report=bridge.export(a,ap,b,bp,0,out)
    derived=RigAsset.load(out/'character.glb')
    assert report['original_target_payload_preserved']
    assert derived.document['nodes'][report['target_mapping']['LeftHand']]['extras']=={'user-authored':'keep'}


def test_swing_alignment_proper_rotation_and_shortest_angle_without_torch():
    from retarget_rig import swing
    from scipy.spatial.transform import Rotation
    rng=np.random.default_rng(731);pairs=list(zip(rng.normal(size=(32,3)),rng.normal(size=(32,3))))
    pairs += [(np.array([1.,0,0]),np.array([-1.,0,0])),(np.array([0.,1,0]),np.array([0.,1,0]))]
    for a,b in pairs:
        result=swing(a,b)
        np.testing.assert_allclose(result@(a/np.linalg.norm(a)),b/np.linalg.norm(b),atol=1e-12,rtol=0)
        np.testing.assert_allclose(result.T@result,np.eye(3),atol=1e-12,rtol=0)
        assert np.linalg.det(result)==pytest.approx(1.)
        assert Rotation.from_matrix(result).magnitude()==pytest.approx(np.arccos(np.clip(a@b/(np.linalg.norm(a)*np.linalg.norm(b)),-1,1)),abs=1e-7)
