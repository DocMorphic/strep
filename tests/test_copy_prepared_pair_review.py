import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import copy_prepared_pair_review as module
from strep import read,save,sha256


def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path)
    jobs=tmp_path/'reports/paired-edit-jobs';source=jobs/'source';source.mkdir(parents=True)
    (source/'input').mkdir();(source/'implementation').mkdir()
    for name in ['input/scene.json','input/a.glb','input/b.glb','implementation/model.py']:
        (source/name).write_bytes(name.encode())
    external=tmp_path/'native';external.write_bytes(b'original')
    save(source/'request.json',dict(scene_snapshot=dict(path='input/scene.json',sha256=sha256(source/'input/scene.json')),
        actors={n:dict(path='input/'+n+'.glb',sha256=sha256(source/'input'/f'{n}.glb')) for n in ['a','b']},
        implementation={'model.py':sha256(source/'implementation/model.py')},inputs={str(external):sha256(external)}))
    save(source/'state.json',dict(status='prepared'))
    save(source/'job.json',dict(label='old review'));(source/'fit').mkdir();save(source/'fit/result.json',dict(selected='candidate'))
    return source,jobs/'copy',external


def test_review_copy_preserves_bytes_without_inheriting_results(tmp_path,monkeypatch):
    source,output,_=fixture(tmp_path,monkeypatch)
    module.copy_request(source,output)
    record=read(output/'review-origin.json')
    for name,digest in record['copied'].items():assert sha256(output/name)==sha256(source/name)==digest
    assert not (output/'job.json').exists() and not (output/'fit').exists()
    assert read(source/'fit/result.json')['selected']=='candidate'
    assert not record['quality_approved']
    with pytest.raises(ValueError,match='fresh'):module.copy_request(source,output)


@pytest.mark.parametrize('fault',['actor','scene','method','input','state','escape','destination'])
def test_changed_or_escaping_prepared_evidence_does_not_create_review(tmp_path,monkeypatch,fault):
    source,output,external=fixture(tmp_path,monkeypatch)
    if fault=='actor':(source/'input/a.glb').write_bytes(b'changed')
    if fault=='scene':(source/'input/scene.json').write_bytes(b'changed')
    if fault=='method':(source/'implementation/model.py').write_bytes(b'changed')
    if fault=='input':external.write_bytes(b'changed')
    if fault=='state':save(source/'state.json',dict(status='processing'))
    if fault=='escape':
        record=read(source/'request.json');record['actors']['a']['path']='../../outside.glb';save(source/'request.json',record)
    if fault=='destination':output=tmp_path/'outside'
    with pytest.raises(ValueError):module.copy_request(source,output)
    assert not output.exists()
