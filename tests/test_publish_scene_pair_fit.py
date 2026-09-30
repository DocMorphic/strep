import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from publish_scene_pair_fit import reviewed_variants
from strep import save, read, sha256


def fixture(folder, accepted):
    fit=folder/'fit'; fit.mkdir(); (fit/'source').mkdir(); (folder/'replay').mkdir(); (folder/'engine').mkdir()
    save(fit/'request.json', {'test_fixture':True})
    save(fit/'source/sample-000.json', {'sample':0})
    save(fit/'source-index.json', {'sample-000.json':sha256(fit/'source/sample-000.json')})
    cases=[]; actors={}; checks=[]; trial_actors=[]
    for version in ['input']+(['trial-0'] if accepted else []):
        for actor in ['First','Second']:
            path=fit/(version+'-'+actor+'.glb'); path.write_bytes(('fixture '+version+' '+actor).encode())
            digest=sha256(path); identifier=version+'-'+actor
            cases.append(dict(id=identifier,path=path.name,sha256=digest,frames=3,fps=30))
            checks.append(dict(id=identifier,source_sha256=digest,frames=3,bones=77,imported_skinned_surfaces=1,max_position_error_m=0,max_basis_element_error=0))
            if version=='input':actors[actor]=dict(sha256=digest)
            else:trial_actors.append(dict(actor=actor,sha256=digest))
    save(folder/'request.json',dict(actors=actors)); save(fit/'manifest.json',dict(cases=cases))
    if accepted:
        (fit/'trial-0').mkdir(); save(fit/'trial-0/geometry.json', {'test_fixture':True})
        save(fit/'trials.json',[dict(folder='trial-0',accepted_local_step=True,reasons=[],actors=trial_actors,
            geometry=dict(geometry_sha256=sha256(fit/'trial-0/geometry.json')))])
    save(fit/'result.json',dict(status='complete',request_sha256=sha256(fit/'request.json'),manifest_sha256=sha256(fit/'manifest.json'),
        source_index_sha256=sha256(fit/'source-index.json'), selected='trial-0' if accepted else None,
        trials_sha256=sha256(fit/'trials.json') if accepted else None))
    save(folder/'replay/request.json',dict(study_result_sha256=sha256(fit/'result.json'),study_request_sha256=sha256(fit/'request.json')))
    save(folder/'replay/verification.json',dict(request_sha256=sha256(folder/'replay/request.json'),
        trials=[dict(folder='trial-0',actors=[dict(actor=a,rates=dict(failures=0)) for a in actors])] if accepted else []))
    save(folder/'engine/verification.json',dict(checks=checks))


@pytest.mark.parametrize('accepted',[True,False])
def test_only_reviewed_candidate_or_preserved_source_is_published(tmp_path,accepted):
    fixture(tmp_path,accepted); variants,result=reviewed_variants(tmp_path)
    assert [v[0] for v in variants] == ['source']+(['candidate'] if accepted else [])
    assert set(variants[0][1]) == {'First','Second'}


@pytest.mark.parametrize('failure',['source_sample','candidate_geometry','engine_hash','missing_engine','motion_replay'])
def test_missing_or_changed_evidence_prevents_publication(tmp_path,failure):
    fixture(tmp_path,True)
    if failure=='source_sample':save(tmp_path/'fit/source/sample-000.json',{'changed':True})
    if failure=='candidate_geometry':save(tmp_path/'fit/trial-0/geometry.json',{'changed':True})
    if failure in ['engine_hash','missing_engine']:
        path=tmp_path/'engine/verification.json'; value=read(path)
        if failure=='engine_hash':value['checks'][0]['source_sha256']='bad'
        else:value['checks'].pop()
        save(path,value)
    if failure=='motion_replay':
        path=tmp_path/'replay/verification.json'; value=read(path); value['trials'][0]['actors'][0]['rates']['failures']=1;save(path,value)
    with pytest.raises(ValueError):reviewed_variants(tmp_path)
