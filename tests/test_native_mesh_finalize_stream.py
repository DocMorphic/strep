"""One verified frame pass, exact outputs, and no publication after late failure."""
import json
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_mesh_geometry_journal as journal
from native_mesh_prop_scene import MeshPropScene
from strep import read,save,sha256
from test_native_mesh_geometry_journal import fixture,advance,equal_arrays


@pytest.mark.parametrize('materialize',[False,True])
@pytest.mark.parametrize('overlap',[False,True])
def test_full_output_matches_direct_queries_with_one_frame_validation(tmp_path,monkeypatch,materialize,overlap):
    path,policy_path,_,policy,_=fixture(tmp_path,monkeypatch,overlap)
    expected,arrays=MeshPropScene(path).geometry(policy)
    folder=tmp_path/'journal';head=advance(folder,journal.prepare(path,policy_path,folder),3)
    original={p:sha256(p) for p in folder.rglob('*') if p.is_file()}
    real=journal.verify_archive;reads=[]
    def measured(path,*args,**kwargs):
        if path.parent.parent==folder/'frames':reads.append(path)
        return real(path,*args,**kwargs)
    monkeypatch.setattr(journal,'verify_archive',measured)
    monkeypatch.setattr(MeshPropScene,'geometry',lambda *args,**kwargs:pytest.fail('Finalization must not re-query motion'))
    output=tmp_path/'final'
    result=journal.finalize(folder,head['checkpoint'],head['sha256'],output,materialize_observations=materialize)
    assert len(reads)==len(set(reads))==3
    assert read(output/'geometry.json')==expected
    if materialize:equal_arrays(output/'observations.npz',arrays)
    else:
        actual=dict(journal.iter_observations(output/'observations-index.json',result['observation_index_sha256']))
        assert actual.keys()==arrays.keys()
        for name,value in arrays.items():
            assert actual[name].dtype==value.dtype and actual[name].shape==value.shape
            assert actual[name].tobytes()==value.tobytes()
    assert all(sha256(path)==digest for path,digest in original.items())
    assert not result['quality_approved'] and not result['release_approved']


@pytest.mark.parametrize('fault',['last-array','last-reduction','source-during-stream'])
@pytest.mark.parametrize('materialize',[False,True])
def test_late_failure_leaves_only_unpublished_partial_output(tmp_path,monkeypatch,fault,materialize):
    path,policy_path,_,_,_=fixture(tmp_path,monkeypatch)
    folder=tmp_path/'journal';head=advance(folder,journal.prepare(path,policy_path,folder),3)
    row=read(folder/head['checkpoint'])
    if fault=='last-array':
        (folder/row['frame']['directory']/'observations.npz').write_bytes(b'broken')
    elif fault=='last-reduction':
        row['checked_prefix_pass']=not row['checked_prefix_pass'];save(folder/head['checkpoint'],row)
        head['sha256']=sha256(folder/head['checkpoint'])
    else:
        real=journal.frame
        def changed(folder,entry,request):
            result=real(folder,entry,request)
            if entry['index']==2:(tmp_path/'prop.glb').write_bytes(b'changed after the last verified frame')
            return result
        monkeypatch.setattr(journal,'frame',changed)
    output=tmp_path/'partial'
    with pytest.raises(ValueError):
        journal.finalize(folder,head['checkpoint'],head['sha256'],output,materialize_observations=materialize)
    assert not (output/'result.json').exists() and not (output/'observations-index.json').exists()
    assert (output/'geometry.json').exists()
    assert not read(folder/'progress.json')['sampled_conditions_pass']
