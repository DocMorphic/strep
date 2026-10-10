"""Protocol/provenance fixtures only; no model, tensor or motion-quality evidence."""
import hashlib
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_text_motion_study as subject


def fixtures(tmp_path,monkeypatch):
    monkeypatch.setattr(subject,'ROOT',tmp_path)
    def save(path,data):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data),encoding='utf-8')
    model=tmp_path/'models/critic';model.mkdir(parents=True)
    weights=model/'placeholder';weights.write_bytes(b'not loaded by protocol preparation')
    save(model/'hub-metadata.json',dict(sha='pinned-revision'))
    save(tmp_path/'benchmarks/text-motion-evaluator-v1.json',dict(directory='models/critic',
        revision='pinned-revision',required_files_sha256={'placeholder':subject.sha256(weights)}))
    catalog=tmp_path/'catalog.json';save(catalog,dict(cases=[dict(id='unknown-new-action',family='new-family')]))
    for name in ['prepare_text_motion_study.py','score_text_motion.py','text_motion_retrieval.py',
                 'strep.py','action_worker_lock.py']:
        path=tmp_path/'scripts'/name;path.parent.mkdir(exist_ok=True);path.write_text('fixture method')
    batches=[];records=[]
    for i,seed in enumerate([11,22]):
        batch=tmp_path/f'batch-{i}';batches.append(batch)
        requests=[]
        for actor in ['a','b']:
            item=dict(id='unknown-new-action-'+actor,segments=[dict(prompt='Action '+actor+'.',duration_s=1)],seeds=[seed])
            requests.append(item)
        request=dict(schema_version=1,requests=requests)
        rd=hashlib.sha256(json.dumps(request,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        save(batch/'request.json',request);entries={}
        for item in requests:
            filename=item['id']+'.safetensors';path=batch/'conditioning'/filename
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(item['id'].encode())
            entries[item['segments'][0]['prompt']]=dict(file=filename,sha256=subject.sha256(path))
            folder=batch/'raw'/item['id']/f'seed-{seed}'/'attempt-001';folder.mkdir(parents=True)
            motion=folder/'motion.npz';motion.write_bytes(b'protocol fixture, no tensor inference')
            record=folder/'record.json';records.append(record)
            save(record,dict(status='generated',seed=seed,request=item,request_sha256=rd,
                checkpoint_revision='6c9233af1180b8151e3c4703477104af5dce9dd5',
                checkpoint_sha256='ef0a0ca45a6089ab4532dde609785771ae3f38755b4ae6cf314b0213e07cd4a3',
                npz_sha256=subject.sha256(motion),timeline=[dict(start_frame=0,end_frame_exclusive=30)]))
        save(batch/'conditioning/manifest.json',dict(status='complete',request_sha256=rd,entries=entries))
    return catalog,batches,tmp_path/'protocol.json',records,save


def test_all_declared_batches_seeds_and_arbitrary_family(tmp_path,monkeypatch):
    catalog,batches,out,_,_=fixtures(tmp_path,monkeypatch)
    result=subject.prepare(catalog,batches,out)
    assert result['candidate_descriptions']==2 and result['motion_population']==4
    plan=json.loads(out.read_text())
    assert [m['seed'] for m in plan['motions']]==[11,11,22,22]
    assert {m['family'] for m in plan['motions']}=={'new-family'}
    assert plan['policy']['held_out'] is False and not result['release_approved']
    assert all(subject.sha256(tmp_path/name)==checksum for name,checksum in plan['bindings'].items())
    with pytest.raises(ValueError):subject.prepare(catalog,batches,out)


@pytest.mark.parametrize('damage',['failed','motion','clock','conditioning','duplicate_batch','outside'])
def test_preserve_failure_denominator_and_reject_changed_inputs(tmp_path,monkeypatch,damage):
    catalog,batches,out,records,save=fixtures(tmp_path,monkeypatch)
    record=json.loads(records[-1].read_text())
    if damage=='failed':record['status']='failed';save(records[-1],record)
    elif damage=='motion':records[-1].with_name('motion.npz').write_bytes(b'changed')
    elif damage=='clock':record['timeline'][0]['end_frame_exclusive']=29;save(records[-1],record)
    elif damage=='conditioning':
        cache=batches[-1]/'conditioning/manifest.json';meta=json.loads(cache.read_text());meta['request_sha256']='changed';save(cache,meta)
    elif damage=='duplicate_batch':batches.append(batches[-1])
    elif damage=='outside':out=tmp_path.parent/'outside-protocol.json'
    with pytest.raises(ValueError):subject.prepare(catalog,batches,out)
    assert not out.exists()
