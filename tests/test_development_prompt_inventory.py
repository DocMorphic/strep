import sys
import json
import pytest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from inventory_development_prompts import extract,normalize,reserved_catalog_exclusion


def test_case_punctuation_and_unicode_width_do_not_hide_overlap():
    assert normalize('Ａ person RUNS, then stops!')==normalize('A person runs then stops.')


def test_nested_actor_segments_and_integer_seeds_retain_origins():
    data={'actors':[{'segments':[{'prompt':'Wave, then bow.'}],'seeds':[17,23]}],
          'seed':True,'metadata':{'seed':41},'unused':'Not a motion prompt'}
    prompts,seeds=extract(data)
    assert [(p['text'],p['pointer']) for p in prompts]==[('Wave, then bow.','/actors/0/segments/0/prompt')]
    assert {s['seed'] for s in seeds}=={17,23,41}
    assert next(s for s in seeds if s['seed']==23)['pointer']=='/actors/0/seeds/1'


def test_edit_and_source_prompts_both_count_as_development_exposure():
    prompts,_=extract({'source_prompt':'Run forward.','edit_prompt':'Turn left while running.'})
    assert {p['field'] for p in prompts}=={'source_prompt','edit_prompt'}


def test_document_pointer_escapes_are_unambiguous():
    prompts,_=extract({'a/b~c':{'prompt':'Wave'}})
    assert prompts[0]['pointer']=='/a~1b~0c/prompt'


def test_only_unexecuted_catalog_can_be_exempted(tmp_path):
    folder=tmp_path/'benchmarks';folder.mkdir();path=folder/'reserved.json'
    data={'status':'reserved_prompts_not_release_ready','cases':[{'generated':False}]}
    path.write_text(json.dumps(data))
    assert list(reserved_catalog_exclusion(path,tmp_path))==['benchmarks/reserved.json']
    data['cases'][0]['generated']=True;path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='unexecuted'):reserved_catalog_exclusion(path,tmp_path)


def test_execution_records_cannot_be_exempted_by_location(tmp_path):
    folder=tmp_path/'reports';folder.mkdir();path=folder/'request.json'
    path.write_text('{}')
    with pytest.raises(ValueError,match='Only an explicit'):reserved_catalog_exclusion(path,tmp_path)
