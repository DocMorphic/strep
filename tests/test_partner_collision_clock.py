from pathlib import Path
import math
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from partner_collision_clock import PartnerCollisionClock


def clock(variants=None,actors=None):
    return PartnerCollisionClock(3,['original','edited'] if variants is None else variants,
        {'A':8,'B':10} if actors is None else actors,representation='saved',tolerance_m=.005)


def records(actors=None):
    actors={'A':8,'B':10} if actors is None else actors
    return [dict(frame=f,mode=v,representation='saved',source=a,target=b,
        vertices_checked=actors[a],max_depth_m=0.,vertices_over_tolerance=0,
        deepest_vertex=None,passed_existing_depth_screen=True)
        for f in range(3) for v in ['original','edited'] for a in actors for b in actors if a!=b]


def test_last_frame_last_direction_last_variant_required():
    c=clock();r=records();c.add(r[:-1]);p=c.report()
    assert p['status']=='partial' and p['missing_conditions']==1 and not p['complete_depth_screen_pass']
    assert p['variants']['edited']['complete_frames']==[0,1]
    c.add(r[-1:]);p=c.report()
    assert p['status']=='complete' and p['expected_conditions']==p['observed_conditions']==12
    assert p['complete_original_integer_clock'] and p['complete_depth_screen_pass']
    assert not p['quality_approved'] and not p['source_bindings_verified'] and not p['continuous_collision_checked']


def test_complete_failing_clock_is_complete_evidence_not_success():
    c=clock();r=records();r[-1].update(max_depth_m=.006,vertices_over_tolerance=1,deepest_vertex=9,passed_existing_depth_screen=False)
    c.add(r);p=c.report()
    assert p['status']=='complete' and not p['complete_depth_screen_pass']
    assert p['variants']['edited']['frames_over_tolerance']==[2] and p['variants']['edited']['vertex_exceedances']==1
    assert p['variants']['edited']['peak_condition']==dict(frame=2,source='B',target='A')


def test_exact_screen_boundary_and_smallest_float_excess_have_distinct_decisions():
    c=clock();r=records();r[0].update(max_depth_m=.005,deepest_vertex=0)
    r[-1].update(max_depth_m=math.nextafter(.005,math.inf),vertices_over_tolerance=1,deepest_vertex=0,passed_existing_depth_screen=False)
    c.add(r);p=c.report()
    assert p['variants']['original']['frames_over_tolerance']==[] and p['variants']['edited']['frames_over_tolerance']==[2]
    assert p['added_physical_tolerance_m']==0


def test_both_batch_duplicate_forms_are_rejected_without_partial_update():
    c=clock();r=records()
    with pytest.raises(ValueError):c.add([r[0],r[0]])
    assert c.report()['observed_conditions']==0
    c.add([r[0]])
    with pytest.raises(ValueError):c.add([r[1],r[0]])
    assert c.report()['observed_conditions']==1


def test_third_actor_requires_every_ordered_pair():
    actors={'A':8,'B':10,'prop_animated_partner':6};c=clock(actors=actors);r=records(actors)
    assert len(r)==36
    c.add([row for row in r if row['source']!='prop_animated_partner'])
    assert c.report()['missing_conditions']==12 and not c.report()['complete_original_integer_clock']
    c.add([row for row in r if row['source']=='prop_animated_partner'])
    assert c.report()['complete_original_integer_clock']


def test_owned_protocol_observations_and_reports():
    variants=['original','edited'];actors={'A':8,'B':10};c=clock(variants,actors);r=records()
    c.add(r);variants.clear();actors.clear();r[0]['max_depth_m']=12
    p=c.report();p['variants']['original']['complete_frames'].clear();p['variants']['original']['peak_condition']['frame']=999
    assert c.report()['complete_depth_screen_pass'] and c.report()['variants']['original']['complete_frames']==[0,1,2]


def test_batch_arrival_order_does_not_change_tied_peak_or_receipt():
    a=clock();b=clock();r=records();a.add(r[:5]);a.add(r[5:]);b.add(list(reversed(r)))
    assert a.report()==b.report()


@pytest.mark.parametrize('fault',['frame','bool_frame','variant','self_pair','unknown_actor','representation',
    'vertices','bool_vertices','count','nan','negative_depth','overlarge_depth','missing_peak','bad_peak',
    'spurious_peak','false_decision','inconsistent_count','missing_field'])
def test_invalid_batch_does_not_partly_advance(fault):
    c=clock();r=records()[:2];row=r[-1]
    if fault=='frame':row['frame']=3
    elif fault=='bool_frame':row['frame']=True
    elif fault=='variant':row['mode']='unlisted'
    elif fault=='self_pair':row['target']=row['source']
    elif fault=='unknown_actor':row['source']='C'
    elif fault=='representation':row['representation']='raw'
    elif fault=='vertices':row['vertices_checked']=9
    elif fault=='bool_vertices':row['vertices_checked']=True
    elif fault=='count':row['vertices_over_tolerance']=-1
    elif fault=='nan':row['max_depth_m']=math.nan
    elif fault=='negative_depth':row['max_depth_m']=-1
    elif fault=='overlarge_depth':row['max_depth_m']=1e7
    elif fault=='missing_peak':row['max_depth_m']=.001
    elif fault=='bad_peak':row.update(max_depth_m=.001,deepest_vertex=10)
    elif fault=='spurious_peak':row['deepest_vertex']=0
    elif fault=='false_decision':row['passed_existing_depth_screen']=False
    elif fault=='inconsistent_count':row['vertices_over_tolerance']=1
    else:row.pop('max_depth_m')
    with pytest.raises(ValueError):c.add(r)
    assert c.report()['observed_conditions']==0


@pytest.mark.parametrize('fault',['frames','bool_frames','duplicate_variant','actor_count','vertex_count',
    'representation','zero_screen','nan_screen','condition_budget'])
def test_invalid_protocol_rejected_before_coverage_allocation(fault):
    options=dict(frame_count=3,variants=['one','two'],actor_vertices={'A':8,'B':10},representation='saved',tolerance_m=.005)
    if fault=='frames':options['frame_count']=10001
    elif fault=='bool_frames':options['frame_count']=True
    elif fault=='duplicate_variant':options['variants']=['one','one']
    elif fault=='actor_count':options['actor_vertices']={'A':8}
    elif fault=='vertex_count':options['actor_vertices']={'A':0,'B':10}
    elif fault=='representation':options['representation']='preview'
    elif fault=='zero_screen':options['tolerance_m']=0
    elif fault=='nan_screen':options['tolerance_m']=math.nan
    else:options.update(frame_count=300,variants=list('abcdefgh'),actor_vertices={k:8 for k in 'ABCDEFGH'})
    with pytest.raises(ValueError):PartnerCollisionClock(**options)


def test_empty_journal_is_partial_and_diagnostic_missing_list_is_explicitly_bounded():
    c=PartnerCollisionClock(30,['only'],{'A':8,'B':10},representation='raw',tolerance_m=.005)
    p=c.report()
    assert p['missing_conditions']==60 and len(p['first_missing_conditions'])==16
    assert not p['all_observed_depth_screens_pass'] and not p['complete_original_integer_clock']
    assert p['variants']['only']['maximum_depth_m'] is None
    with pytest.raises(ValueError):c.add([])


def test_single_pose_and_long_authored_clocks_do_not_infer_action_categories():
    c=PartnerCollisionClock(1,['original'],{'A':8,'B':10},representation='saved',tolerance_m=.005)
    c.add([r for r in records() if r['frame']==0 and r['mode']=='original'])
    assert c.report()['complete_original_integer_clock']
    long=PartnerCollisionClock(1000,['any action sequence'],{'A':50000,'B':80000},representation='raw',tolerance_m=.005)
    assert long.report()['expected_conditions']==2000 and long.report()['missing_conditions']==2000
