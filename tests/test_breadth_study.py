import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_breadth_v2 import protocol,batches
from breadth_study import summarize


def test_every_case_actor_seed_occurs_once_across_bounded_batches():
    spec=protocol();seen=[]
    for _,batch in batches(spec):
        assert len(batch['requests'])<=20
        for request in batch['requests']:
            assert len(request['seeds'])<=4
            seen.extend((request['id'],seed) for seed in request['seeds'])
    expected={(case['id']+'-'+actor['id'].lower(),seed) for case in spec['cases'] for actor in case['actors'] for seed in case['seeds']}
    assert len(spec['cases'])==72 and len(seen)==390
    assert len(set(seen))==len(seen) and set(seen)==expected
    assert len({case['family'] for case in spec['cases']})==12


def test_missing_outputs_stay_in_denominators_and_never_receive_ratings():
    spec=protocol();report=summarize(spec,{})
    assert report['planned_actor_clips']==390 and report['exported']==0
    assert all(r['semantic_rating'] is None and r['joint_floor_screen'] is None and not r['quality_approved'] for r in report['rows'])
    assert sum(f['planned_actor_clips'] for f in report['families'])==390


def test_water_floor_numbers_do_not_become_contact_acceptance():
    spec=protocol();case=next(c for c in spec['cases'] if c['context']=='water')
    key=(case['id']+'-a',case['seeds'][0])
    result=summarize(spec,{key:{'metrics':{'max_joint_ground_penetration_m':0.,'foot_horizontal_speed_predicted_contact_m_s':{'p95':0.}},'flags':[]}})
    row=next(r for r in result['rows'] if r['exported'])
    assert row['joint_floor_depth_m']==0
    assert row['joint_floor_screen'] is None and row['predicted_foot_speed_screen'] is None
    assert row['scene_validation']=='missing_required_context_validation' and not row['quality_approved']


def test_actual_skin_penetration_is_separate_from_joint_proxies():
    spec=protocol();case=spec['cases'][0];key=(case['id']+'-a',case['seeds'][0])
    result=summarize(spec,{key:{'metrics':{'max_joint_ground_penetration_m':0.},'flags':[]}},
                     {key:{'mesh_max_depth_m':.025}})
    row=next(r for r in result['rows'] if r['exported'])
    assert row['joint_floor_screen'] is True and row['mesh_floor_screen'] is False
    assert row['semantic_rating'] is None and not row['quality_approved']
