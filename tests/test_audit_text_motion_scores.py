import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import audit_text_motion_scores as auditor
from text_motion_retrieval import evaluate


def setup(tmp_path,monkeypatch):
    monkeypatch.setattr(auditor,'ROOT',tmp_path)
    study=tmp_path/'study';study.mkdir()
    def save(path,data):path.write_text(json.dumps(data),encoding='utf-8')
    v=lambda n:[float(i==n) for i in range(256)]
    vectors=dict(text_ids=['jump','wave'],text_vectors=[v(0),v(1)],motion_ids=['a','b'],
                 motion_vectors=[v(0),v(0)],expected_text_ids=['jump','wave'])
    source=tmp_path/'source';source.write_text('immutable')
    plan=dict(schema='strep-tmr-development-study-v1',split='development',
              texts=[dict(id='jump'),dict(id='wave')],
              motions=[dict(id='a',text_id='jump'),dict(id='b',text_id='wave')],
              bindings={'source':auditor.digest(source)})
    protocol=tmp_path/'protocol.json';save(protocol,plan)
    save(study/'embeddings.json',vectors)
    result=evaluate(**vectors)
    result.update(protocol_sha256=auditor.digest(protocol),
                  embeddings_sha256=auditor.digest(study/'embeddings.json'))
    save(study/'result.json',result)
    def update():save(study/'pipeline.json',dict(status='complete',result_sha256=auditor.digest(study/'result.json')))
    update()
    return protocol,study,tmp_path/'audit.json',save,update


def test_complete_scalar_audit(tmp_path,monkeypatch):
    protocol,study,out,_,_=setup(tmp_path,monkeypatch)
    receipt=auditor.audit(protocol,study,out)
    assert receipt['score_population']==4 and receipt['conservative_top1_count']==1
    assert receipt['max_dot_replay_error']==0 and not receipt['quality_approved']
    assert json.loads(out.read_text())==receipt
    with pytest.raises(FileExistsError):auditor.audit(protocol,study,out)


@pytest.mark.parametrize('damage',['score','rank','count','approval','population','source','vectors'])
def test_rejects_changed_evidence(tmp_path,monkeypatch,damage):
    protocol,study,out,save,update=setup(tmp_path,monkeypatch)
    result=json.loads((study/'result.json').read_text())
    if damage=='score':result['scores'][0][0]=.7
    elif damage=='rank':result['rows'][0]['rank_worst']=2
    elif damage=='count':result['conservative_top1_count']=2
    elif damage=='approval':result['release_approved']=True
    elif damage=='population':result['motion_ids'].reverse()
    elif damage=='source':(tmp_path/'source').write_text('changed')
    elif damage=='vectors':
        vectors=json.loads((study/'embeddings.json').read_text());vectors['motion_vectors'][0][0]=2
        save(study/'embeddings.json',vectors)
        result['embeddings_sha256']=auditor.digest(study/'embeddings.json')
    save(study/'result.json',result);update()
    with pytest.raises(ValueError):auditor.audit(protocol,study,out)
    assert not out.exists()


def test_preserved_original_method_bytes_survive_source_upgrade(tmp_path,monkeypatch):
    protocol,study,out,save,update=setup(tmp_path,monkeypatch)
    original=tmp_path/'scripts/producer.py';original.parent.mkdir();original.write_text('original method')
    plan=json.loads(protocol.read_text());plan['bindings']['scripts/producer.py']=auditor.digest(original)
    save(protocol,plan)
    result=json.loads((study/'result.json').read_text());result['protocol_sha256']=auditor.digest(protocol)
    save(study/'result.json',result);update()
    snapshot=study/'implementation/scripts/producer.py';snapshot.parent.mkdir(parents=True)
    snapshot.write_bytes(original.read_bytes());original.write_text('later implementation')
    receipt=auditor.audit(protocol,study,out)
    assert receipt['original_method_snapshots_used']==1
    out.unlink();snapshot.write_text('corrupted original method')
    with pytest.raises(ValueError):auditor.audit(protocol,study,out)
