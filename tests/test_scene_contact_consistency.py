"""Exact metadata necessities; no motion, skeleton, mesh or model loaded."""
import copy
from decimal import Decimal, localcontext
from fractions import Fraction
import math
import random
import shutil
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import scene_contact_consistency as consistency
import scene_generation as generation
from strep import ROOT,save,read,sha256
from test_scene_generation_guides import compiled


def scene(target_distance=3,source_distance=2,tolerance=.25):
    base=dict(actor='A',effector=dict(joint='RightHand',offset_m=[0,0,0]),
        target=dict(space='world',point_m=[0,0,0]),start_frame=10,end_frame=90,tolerance_m=tolerance)
    first=copy.deepcopy(base);first['id']='grip-1'
    second=copy.deepcopy(base);second.update(id='grip-2',start_frame=50,end_frame=100)
    second['effector']['offset_m']=[source_distance,0,0];second['target']['point_m']=[target_distance,0,0]
    return dict(frame_count=120,actors={'A':{}},objects={'box':{}},contacts=[first,second])


def test_world_targets_conflict_for_the_entire_overlap_without_sampling():
    value=scene();original=copy.deepcopy(value);report=consistency.diagnose(value)
    assert value==original and report['conflicting_pairs']==[[0,1]]
    pair=report['overlapping_pairs'][0]
    assert pair['overlap_frames']==[50,90] and pair['contact_ids']==['grip-1','grip-2']
    assert pair['source_separation_squared_m2']==dict(numerator='4',denominator='1')
    assert pair['target_separation_squared_m2']==dict(numerator='9',denominator='1')
    assert pair['tolerance_sum_m']==dict(numerator='1',denominator='2')
    assert not report['feasibility_approved'] and not report['source_pose_geometry_checked']


@pytest.mark.parametrize('space',['world','object','partner'])
def test_same_rigid_target_frame_invariance(space):
    value=scene()
    if space=='object':
        for c in value['contacts']:c['target']=dict(space='object',object='box',point_m=c['target']['point_m'])
    if space=='partner':
        value['actors']['B']={}
        for c in value['contacts']:c['target']=dict(space='actor',actor='B',joint='LeftHand',offset_m=c['target']['point_m'])
    # Rigid 90-degree rotation preserves the distance condition.
    value['contacts'][1]['target']['offset_m' if space=='partner' else 'point_m']=[0,3,0]
    report=consistency.diagnose(value)
    assert report['has_proven_pair_conflict'] and report['overlapping_pairs'][0]['target_rigid_frame'][0] in ['world','object','actor']


def test_annotations_do_not_hide_declared_rigid_point_conflicts():
    value=scene()
    for c in value['contacts']:
        c['effector'].update(label='Wrist proxy',status='Needs review',palm_normal_local=[0,1,0])
        c['target']['label']='Authored target'
    assert consistency.diagnose(value)['has_proven_pair_conflict']


@pytest.mark.parametrize('target,tolerance,conflict',[(3,.5,False),(3,math.nextafter(.5,0),True),(3,math.nextafter(.5,1),False),(2,0,False),(1,0,True)])
def test_exact_boundary_and_one_ulp_changes(target,tolerance,conflict):
    report=consistency.diagnose(scene(target_distance=target,tolerance=tolerance))
    assert report['has_proven_pair_conflict']==conflict
    assert report['feasibility_approved'] is False


def test_rational_inequality_agrees_with_independent_high_precision_square_roots():
    rng=random.Random(817)
    with localcontext() as context:
        context.prec=90
        for _ in range(1000):
            a=Fraction(rng.randrange(1,100000),17);b=Fraction(rng.randrange(1,100000),31);t=Fraction(rng.randrange(0,1000),43)
            decimal=lambda value:Decimal(value.numerator)/Decimal(value.denominator)
            gap=abs(decimal(a).sqrt()-decimal(b).sqrt())-decimal(t)
            assert abs(gap)>Decimal('1e-70')
            assert consistency.distances_conflict(a,b,t)==(gap>0)


@pytest.mark.parametrize('reason',['source_surface','source_region','missing_offset','target_surface','different_objects','different_partner_joints','missing_tolerance'])
def test_unsupported_pairs_remain_explicitly_unassessed(reason):
    value=scene()
    if reason=='source_surface':value['contacts'][0]['effector']['surface_vertex']=42
    if reason=='source_region':value['contacts'][0]['region_contact']={}
    if reason=='missing_offset':value['contacts'][0]['effector'].pop('offset_m')
    if reason=='target_surface':value['contacts'][0]['target']['surface_vertex']=42
    if reason=='different_objects':
        for i,c in enumerate(value['contacts']):c['target']=dict(space='object',object=str(i),point_m=c['target']['point_m'])
    if reason=='different_partner_joints':
        for i,c in enumerate(value['contacts']):c['target']=dict(space='actor',actor='B',joint=str(i),offset_m=c['target']['point_m'])
    if reason=='missing_tolerance':value['contacts'][0].pop('tolerance_m')
    report=consistency.diagnose(value)
    assert report['overlapping_pairs'][0]['status']=='unassessed'
    assert not report['has_proven_pair_conflict'] and not report['feasibility_approved']


def test_disjoint_events_and_different_joints_are_not_conflated():
    value=scene();value['contacts'][0]['end_frame']=49
    report=consistency.diagnose(value);assert report['disjoint_pair_count']==1 and report['overlapping_pairs']==[]
    value['contacts'][1]['effector']['joint']='LeftHand'
    assert consistency.diagnose(value)['same_joint_pair_population']==0


def test_pair_budget_rejects_complete_population_instead_of_thinning():
    value=scene();value['contacts']=[dict(value['contacts'][0],id=str(i)) for i in range(100)]
    original=copy.deepcopy(value)
    with pytest.raises(ValueError,match='no pairs were thinned'):consistency.diagnose(value)
    assert value==original


@pytest.mark.parametrize('defect',['bool','nan','negative_tolerance','bad_offset','bad_interval'])
def test_malformed_numeric_contract_rejected(defect):
    value=scene()
    if defect=='bool':value['contacts'][0]['effector']['offset_m'][0]=True
    if defect=='nan':value['contacts'][0]['target']['point_m'][0]=float('nan')
    if defect=='negative_tolerance':value['contacts'][0]['tolerance_m']=-1
    if defect=='bad_offset':value['contacts'][0]['effector']['offset_m']=[0,0]
    if defect=='bad_interval':value['contacts'][0]['start_frame']=False
    with pytest.raises(ValueError):consistency.diagnose(value)


def test_prepare_retains_conflicting_intent_before_pose_or_model_loading(tmp_path,monkeypatch):
    source=tmp_path/'scene.json';plan=tmp_path/'plan.json';output=tmp_path/'prepared'
    save(source,scene());save(plan,dict(A=dict(segments=[dict(prompt='Lift an object.',duration_s=4)],seeds=[17])))
    def unexpected(*args,**kwargs):raise AssertionError('Conflicting metadata reached poses or model')
    monkeypatch.setattr(generation,'requests',unexpected);monkeypatch.setattr(generation.np,'load',unexpected)
    with pytest.raises(ValueError,match='retained audit'):generation.prepare(source,plan,output,diagnostic_targets=True)
    assert read(output/'pipeline.json')['failed_stage']=='scene_contact_consistency'
    assert read(output/'authored-scene.json')==read(source) and read(output/'actor-plan.json')==read(plan)
    original=(output/'contact-consistency.json').read_bytes()
    with pytest.raises(FileExistsError):generation.prepare(source,plan,output)
    assert (output/'contact-consistency.json').read_bytes()==original


@pytest.fixture
def prepared(tmp_path):
    value=scene(target_distance=2);folder=tmp_path/'prepared';folder.mkdir();snapshot=folder/'source-snapshot';snapshot.mkdir()
    save(folder/'contact-consistency.json',consistency.diagnose(value));shutil.copyfile(ROOT/'scripts/scene_contact_consistency.py',snapshot/'scene_contact_consistency.py')
    freeze=dict(contact_consistency_sha256=sha256(folder/'contact-consistency.json'),contact_consistency_method_sha256=sha256(snapshot/'scene_contact_consistency.py'))
    return folder,value,freeze


def test_prepared_audit_and_legacy_scope(prepared,tmp_path):
    folder,value,freeze=prepared
    assert consistency.validate_prepared(folder,freeze,value)==consistency.diagnose(value)
    assert consistency.validate_prepared(tmp_path,{},value) is None


@pytest.mark.parametrize('defect',['binding','missing','snapshot','rebound_status','changed_targets'])
def test_pre_generation_binding_cannot_be_dropped_or_rebound(prepared,defect):
    folder,value,freeze=prepared
    if defect=='binding':freeze.pop('contact_consistency_sha256')
    if defect=='missing':(folder/'contact-consistency.json').unlink()
    if defect=='snapshot':(folder/'source-snapshot/scene_contact_consistency.py').write_text('changed',encoding='utf-8')
    if defect=='rebound_status':
        report=read(folder/'contact-consistency.json');report['feasibility_approved']=True;save(folder/'contact-consistency.json',report)
        freeze['contact_consistency_sha256']=sha256(folder/'contact-consistency.json')
    if defect=='changed_targets':value['contacts'][1]['target']['point_m']=[3,0,0]
    with pytest.raises(ValueError):consistency.validate_prepared(folder,freeze,value)


def test_generation_preflight_calls_consistency_check_before_pose_queries(compiled):
    from scene_generation_guides import validate_prepared_guidance
    folder,value,plan,batch,freeze=compiled
    save(folder/'contact-consistency.json',consistency.diagnose(value))
    shutil.copyfile(ROOT/'scripts/scene_contact_consistency.py',folder/'source-snapshot/scene_contact_consistency.py')
    freeze.update(contact_consistency_sha256=sha256(folder/'contact-consistency.json'),
                  contact_consistency_method_sha256=sha256(folder/'source-snapshot/scene_contact_consistency.py'))
    assert validate_prepared_guidance(folder,freeze,batch)['full_scene_evaluation_unchanged']
    freeze.pop('contact_consistency_sha256')
    with pytest.raises(ValueError,match='consistency binding'):validate_prepared_guidance(folder,freeze,batch)


def test_consistency_artifact_cannot_masquerade_as_legacy_guidance(prepared):
    from scene_generation_guides import validate_prepared_guidance
    folder,value,freeze=prepared
    with pytest.raises(ValueError,match='guide-plan binding'):validate_prepared_guidance(folder,freeze,dict(requests=[]))
