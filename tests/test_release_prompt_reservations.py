import copy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from check_release_prompt_reservations import screen


def fixture():
    return ({'cases':[{'id':'a','family':'gesture','prompt':'Wave, then bow.','seeds':[101,102]}]},
            {'prompts':[{'normalized':'walk forward'}],'seeds':[{'seed':99}],'parse_errors':[]},
            {'action_families':[{'id':'gesture'}],'evaluation_design':{'minimum_prompts_per_family':1,'seeds_per_prompt':2}})


def test_exact_clearance_is_not_release_approval():
    result=screen(*fixture())
    assert result['exact_overlap_screen_passed']
    assert not result['release_trials_ready'] and not result['quality_approved']


def test_old_prompt_case_and_punctuation_cannot_hide_overlap():
    reservation,inventory,matrix=fixture()
    reservation['cases'][0]['prompt']='WALK forward!'
    result=screen(reservation,inventory,matrix)
    assert result['exact_normalized_prompt_overlap']==['a']
    assert not result['exact_overlap_screen_passed']


def test_seed_reuse_and_missing_family_are_detected():
    reservation,inventory,matrix=fixture()
    reservation['cases'][0]['seeds']=[99,102]
    matrix['action_families'].append({'id':'parkour'})
    result=screen(reservation,inventory,matrix)
    assert result['seed_overlap']==[{'case':'a','seeds':[99]}]
    assert 'Insufficient prompts: parkour' in result['structural_errors']
    assert not result['exact_overlap_screen_passed']


def test_duplicate_case_does_not_inflate_coverage():
    reservation,inventory,matrix=fixture()
    reservation['cases'].append(copy.deepcopy(reservation['cases'][0]))
    result=screen(reservation,inventory,matrix)
    assert 'Duplicate case identifiers' in result['structural_errors']
    assert not result['exact_overlap_screen_passed']
