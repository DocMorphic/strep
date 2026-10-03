"""Frozen batch routing/failure provenance; engine fixture is not motion evidence."""
from pathlib import Path
import sys,copy
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_engine_contact_population as batch
from strep import read,save,sha256
from engine_contact_sampling import contract,contract_sha256


@pytest.fixture
def population(tmp_path,monkeypatch):
    a=tmp_path/'a.glb';b=tmp_path/'b.glb';d=tmp_path/'draft.json';p=tmp_path/'policy.json'
    a.write_bytes(b'source');b.write_bytes(b'candidate');save(d,{});save(p,{})
    ref=lambda f:dict(path=f.name,sha256=sha256(f))
    case=dict(id='first',source=ref(a),candidate=ref(b),base=ref(a),draft=ref(d),policy=ref(p),
        metadata=dict(action='dance',rig='toy',candidate_role='rejected_raw_proposal',original_selection='retained_input'))
    manifest=tmp_path/'population.json';save(manifest,dict(schema='strep-native-engine-contact-population-v1',scope='Toy routing fixture',cases=[case]))
    calls=[]
    def audit(source,candidate,draft,policy,out,*,base,frame_sampling):
        calls.append((source,candidate,draft,policy,base,frame_sampling));out.mkdir()
        report=dict(status='complete',frame_sampling_contract=contract(),frame_sampling_contract_sha256=contract_sha256(),
            original_contact_population_replaced=False,quality_approved=False,release_approved=False,
            cases=[dict(id='source',samples=2),dict(id='candidate',samples=2,contact_samples_pass=False,
                game_frame_contact_samples_pass=True,all_contact_populations_pass=False)])
        save(out/'result.json',report);return report
    monkeypatch.setattr(batch,'audit_engine',audit)
    return manifest,calls,a,b


def test_every_case_uses_original_inputs_and_fixed_contract_without_promotion(population,tmp_path):
    path,calls,a,b=population;out=tmp_path/'out';report=batch.run(path,out)
    assert calls==[(str(a),str(b),str(tmp_path/'draft.json'),str(tmp_path/'policy.json'),str(a),True)]
    assert report['all_cases_completed'] and not report['all_candidates_contact_pass']
    assert report['engine_observations']==4 and not report['selections_changed'] and not report['release_approved']
    row=report['cases'][0]
    assert row['original_contact_pass'] is False and row['frame_contact_pass'] is True and not row['combined_contact_pass']
    assert row['metadata']['candidate_role']=='rejected_raw_proposal'
    assert sha256(out/'manifest.json')==sha256(path)
    for p,h in report['methods_sha256'].items():assert sha256(out/'implementation'/Path(p).name)==h


@pytest.mark.parametrize('fault',['schema','scope','empty','duplicate','bad_id','missing_hash','bad_hash','changed_file','missing_file','unknown_label','boolean_label','extra_key'])
def test_incomplete_or_changed_population_rejected_before_work(population,tmp_path,fault):
    path,calls,a,b=population;r=read(path)
    if fault=='schema':r['schema']='other'
    if fault=='scope':r['scope']=''
    if fault=='empty':r['cases']=[]
    if fault=='duplicate':r['cases'].append(copy.deepcopy(r['cases'][0]))
    if fault=='bad_id':r['cases'][0]['id']='../escape'
    if fault=='missing_hash':del r['cases'][0]['source']['sha256']
    if fault=='bad_hash':r['cases'][0]['source']['sha256']='0'*64
    if fault=='changed_file':a.write_bytes(b'changed')
    if fault=='missing_file':a.unlink()
    if fault=='unknown_label':r['cases'][0]['metadata']['quality_approved']='yes'
    if fault=='boolean_label':r['cases'][0]['metadata']['rig']=True
    if fault=='extra_key':r['cases'][0]['tolerance']=1.
    save(path,r)
    with pytest.raises(ValueError):batch.run(path,tmp_path/'out')
    assert not calls and not (tmp_path/'out').exists()


def test_missing_engine_case_retained_as_unavailable_and_other_cases_continue(population,tmp_path,monkeypatch):
    path,calls,a,b=population;r=read(path);second=copy.deepcopy(r['cases'][0]);second['id']='second';r['cases'].append(second);save(path,r)
    original=batch.audit_engine
    def fail_first(*args,**kwargs):
        if args[4].name=='first':raise ValueError('Unsupported imported skin')
        return original(*args,**kwargs)
    monkeypatch.setattr(batch,'audit_engine',fail_first)
    out=tmp_path/'out';report=batch.run(path,out)
    assert read(out/'pipeline.json')['status']=='complete'
    assert not report['all_cases_completed'] and not report['all_candidates_contact_pass']
    assert [r['status'] for r in report['cases']]==['failed','complete']
    assert report['cases'][0]['original_contact_pass'] is None and report['engine_observations']==4
    assert read(out/'first-failure.json')['error']=='Unsupported imported skin'


@pytest.mark.parametrize('target',['source','manifest'])
def test_changed_input_during_case_stops_batch_and_preserves_terminal_failure(population,tmp_path,monkeypatch,target):
    path,calls,a,b=population;original=batch.audit_engine
    def changed(*args,**kwargs):
        r=original(*args,**kwargs);(a if target=='source' else path).write_bytes(b'changed');return r
    monkeypatch.setattr(batch,'audit_engine',changed);out=tmp_path/'out'
    with pytest.raises(ValueError,match='changed'):batch.run(path,out)
    assert read(out/'pipeline.json')['status']=='failed' and not (out/'result.json').exists()
    assert (out/'first/result.json').exists()


def test_existing_output_never_overwritten(population,tmp_path):
    path,calls,a,b=population;out=tmp_path/'out';out.mkdir();(out/'preserved').write_bytes(b'old')
    with pytest.raises(FileExistsError):batch.run(path,out)
    assert (out/'preserved').read_bytes()==b'old' and not calls
