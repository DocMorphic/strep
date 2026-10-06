"""Failure semantics/population validation, not collision-algorithm evidence."""
import copy
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from native_geometry_failure_profile import summarize, SCOPE_SCHEMA


@pytest.fixture
def inputs():
    pair=dict(actors=['A','B'],passed=False,surface=dict(records=[dict(kind='proper_crossing')]),
              vertex_containment=[dict(source='A',target='B',available=True,max_depth_m=.006,deepest_vertex=1)])
    report=dict(schema='strep-native-scene-geometry-result-v1',status='complete',times_s=[0.,.5,1.],topology={'A':{},'B':{}},
                limits={'penetration_m':.005},sampled_conditions_pass=False,
                samples=[dict(time_s=t,passed=False,conditions_available=True,degenerate_faces={'A':[],'B':[]},
                              actor_pairs=[copy.deepcopy(pair)],actor_objects=[],world_planes=[]) for t in [0.,.5,1.]])
    scope=dict(schema=SCOPE_SCHEMA,geometry_sha256='a'*64,object_motion_editable=False,planes_editable=False,
               actors={n:dict(window_s=[.2,.8],protected_s=[]) for n in ['A','B']})
    return report,scope


def test_distinguishes_source_window_blockers_and_potential_editability_without_approval(inputs):
    report,scope=inputs;before=copy.deepcopy(inputs);result=summarize(report,scope,'a'*64)
    assert result['samples']==3 and result['failed_samples']==3
    assert result['counts']['immutable_failed_conditions']==2 and result['counts']['potentially_editable_failed_conditions']==1
    assert result['surface_record_counts']=={'proper_crossing':3}
    assert result['vertex_depth_peaks']['A->B']['depth_m']==.006
    assert result['source_window_blockers_present'] and not result['editable_failures_proven_feasible']
    assert result['original_geometry_decision'] is False and result['original_acceptance_unchanged']
    assert inputs==before and not result['quality_approved'] and not result['release_approved']


def test_protection_and_context_actors_remain_immutable(inputs):
    report,scope=inputs;scope['actors']['A']['protected_s']=[[.4,.6]];scope['actors']['B']=None
    result=summarize(report,scope,'a'*64)
    assert result['counts']['immutable_failed_conditions']==3


def test_near_contact_stays_unresolved_and_is_not_relabelled_penetration(inputs):
    report,scope=inputs
    for sample in report['samples']:
        pair=sample['actor_pairs'][0];pair['surface']['records'][0]['kind']='boundary_or_near_contact'
        pair['vertex_containment'][0]['max_depth_m']=0
    result=summarize(report,scope,'a'*64)
    assert result['reason_counts']=={'unresolved-boundary-or-near-contact':3}
    assert 'transverse-surface-crossings' not in result['reason_counts']


@pytest.mark.parametrize('fault',['binding','actor-population','editable-object','editable-plane','scope-bool','duplicate-time',
                                'sample-alignment','missing-sample','boolean-alias','report-decision','sample-decision','unknown-kind'])
def test_invalid_or_inconsistent_evidence_cannot_be_profiled(inputs,fault):
    report,scope=inputs
    if fault=='binding':scope['geometry_sha256']='b'*64
    elif fault=='actor-population':scope['actors'].pop('B')
    elif fault=='editable-object':scope['object_motion_editable']=True
    elif fault=='editable-plane':scope['planes_editable']=True
    elif fault=='scope-bool':scope['actors']['A']['window_s'][0]=True
    elif fault=='duplicate-time':report['times_s'][1]=0
    elif fault=='sample-alignment':report['samples'][1]['time_s']=.6
    elif fault=='missing-sample':report['samples'].pop()
    elif fault=='boolean-alias':report['samples'][0]['passed']=0
    elif fault=='report-decision':report['sampled_conditions_pass']=True
    elif fault=='sample-decision':report['samples'][0]['passed']=True
    else:report['samples'][0]['actor_pairs'][0]['surface']['records'][0]['kind']='certified-clear'
    with pytest.raises(ValueError):summarize(report,scope,'a'*64)
