import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from text_motion_retrieval import evaluate


def basis(index):
    return [float(i == index) for i in range(256)]


def fixture():
    return dict(text_ids=['jump','wave'], text_vectors=[basis(0),basis(1)],
                motion_ids=['a','b','c'], motion_vectors=[basis(0),basis(1),basis(1)],
                expected_text_ids=['jump','wave','jump'])


def test_competing_actions_and_multiple_seeds():
    data=fixture(); original=copy.deepcopy(data); result=evaluate(**data)
    assert result['scores']==[[1,.5],[.5,1],[.5,1]]
    assert [r['rank_worst'] for r in result['rows']]==[1,1,2]
    assert result['rows'][2]['margin_to_best_alternative']==-.5
    assert result['conservative_top1_count']==2
    assert result['conservative_top3_count']==3
    assert data==original
    assert not result['release_approved'] and not result['training_admitted']


def test_tied_descriptions_do_not_silently_pass():
    data=fixture(); data['text_vectors']=[basis(0),basis(0)]
    result=evaluate(**data)
    assert result['rows'][0]['rank_best']==1
    assert result['rows'][0]['rank_worst']==2
    assert result['rows'][0]['top_text_ids']==['jump','wave']
    assert result['conservative_top1_count']==0


def test_opposite_embeddings():
    data=fixture(); data['motion_vectors'][0]=[-v for v in basis(0)]
    assert evaluate(**data)['scores'][0]==[0,.5]


def test_full_breadth_candidate_and_seed_population():
    ids=['action-'+str(i) for i in range(78)]
    data=dict(text_ids=ids,text_vectors=[basis(i) for i in range(78)],
              motion_ids=['clip-'+str(i) for i in range(390)],
              motion_vectors=[basis(i%78) for i in range(390)],
              expected_text_ids=[ids[i%78] for i in range(390)])
    result=evaluate(**data)
    assert result['population']==390 and result['candidate_descriptions']==78
    assert result['conservative_top1_count']==390
    assert len(result['scores'])==390 and all(len(row)==78 for row in result['scores'])


@pytest.mark.parametrize('change', ['nan','norm','dimension','missing','duplicate','unrepresented','boolean'])
def test_invalid_population(change):
    data=fixture()
    if change=='nan': data['motion_vectors'][0][0]=float('nan')
    elif change=='norm': data['motion_vectors'][0][0]=2
    elif change=='dimension': data['motion_vectors'][0].pop()
    elif change=='missing': data['motion_vectors'].pop()
    elif change=='duplicate': data['motion_ids'][1]='a'
    elif change=='unrepresented': data['expected_text_ids']=['jump']*3
    elif change=='boolean': data['text_vectors'][0][0]=True
    with pytest.raises(ValueError): evaluate(**data)
