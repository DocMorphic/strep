import copy,json,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import audit_object_contact_forces as subject
from strep import sha256


def fixture():
    track=dict(fps=30,space='world',size_m=[.4,.4,.4],positions_m=[[0,0,0]]*17,rotations_xyzw=[[0,0,0,1]]*17)
    spec=dict(schema=subject.SCHEMA,masses_kg=[1.,20.],gravity_m_s2=[0,-9.81,0],
        phases=[dict(id='before',start_frame=0,end_frame_exclusive=4,support_assumption='unknown'),
            dict(id='held',start_frame=4,end_frame_exclusive=13,support_assumption='supported'),
            dict(id='after',start_frame=13,end_frame_exclusive=17,support_assumption='unknown')],
        contacts=[dict(id=name,point_from_com_local_m=[sign*.2,.1,0],normal_into_body_local=[-sign,0,0],friction_coefficient=.5,max_force_N=100.,start_frame=4,end_frame_exclusive=13) for name,sign in [('left',1),('right',-1)]],
        assumption_notes={k:'Hypothetical explicit test assumption, not measured.' for k in ['com','mass','inertia','friction','capacity','contacts']},
        force_tolerance_N=1e-6,torque_tolerance_Nm=1e-6,seconds_per_sample=.25)
    return track,spec


def test_complete_phase_population_is_retained_without_boundary_or_unknown_approval():
    track,spec=fixture();report=subject.assess(track,spec,1.)
    assert [r['frame'] for r in report['assessed_samples']]==list(range(5,12))
    assert [r['frame'] for r in report['unassessed_samples']]==[1,2,3,4,12,13,14,15]
    assert report['unestimated_endpoint_frames']==[0,16]
    assert len(report['demand']['sample_frames'])==15
    assert all(r['assessment']['conditional_force_balance_passed'] for r in report['assessed_samples'])
    assert report['quality_approved'] is False and report['release_approved'] is False


def test_mass_changes_force_feasibility_without_modifying_motion_or_contact_intent():
    track,spec=fixture();original=copy.deepcopy((track,spec))
    low=subject.assess(track,spec,1.);high=subject.assess(track,spec,20.)
    assert (track,spec)==original
    assert all(r['assessment']['status']=='infeasible_axis_bound' for r in high['assessed_samples'])
    np.testing.assert_allclose(np.array(high['demand']['required_non_gravity_force_world_N']),20*np.array(low['demand']['required_non_gravity_force_world_N']),rtol=0,atol=1e-12)


def test_contact_levers_and_normals_follow_original_object_orientation():
    from scipy.spatial.transform import Rotation
    track,spec=fixture();rotation=Rotation.from_euler('z',.3)
    track['rotations_xyzw']=[rotation.as_quat().tolist()]*17
    report=subject.assess(track,spec,1.)
    for original,actual in zip(spec['contacts'],report['assessed_samples'][0]['assessment']['contacts']):
        np.testing.assert_allclose(actual['lever_from_com_world_m'],rotation.apply(original['point_from_com_local_m']),atol=1e-12)
        np.testing.assert_allclose(actual['normal_into_body_world'],rotation.apply(original['normal_into_body_local']),atol=1e-12)


def test_missing_declared_support_cannot_be_silently_skipped():
    track,spec=fixture();spec['contacts']=[]
    report=subject.assess(track,spec,1.)
    assert len(report['assessed_samples'])==7
    assert all(r['assessment']['status']=='infeasible_axis_bound' for r in report['assessed_samples'])


def test_free_flight_contact_overlap_is_rejected_even_only_at_an_unestimated_endpoint():
    track,spec=fixture();spec['phases']=[dict(id='flight',start_frame=0,end_frame_exclusive=17,support_assumption='free_flight')]
    spec['contacts'][0].update(start_frame=0,end_frame_exclusive=1);spec['contacts']=spec['contacts'][:1]
    with pytest.raises(ValueError,match='free flight'):subject.validate(track,spec)


@pytest.mark.parametrize('field,value',[('masses_kg',[1.,1.]),('masses_kg',[True]),('seconds_per_sample',0),
    ('gravity_m_s2',[np.nan,0,0]),('force_tolerance_N',True),('contacts',[{}]),('assumption_notes',{})])
def test_malformed_or_missing_assumptions_fail_before_allocating_output(field,value):
    track,spec=fixture();spec[field]=value
    with pytest.raises((ValueError,KeyError)):subject.validate(track,spec)


def setup_files(tmp_path,monkeypatch):
    monkeypatch.setattr(subject,'ROOT',tmp_path)
    track,spec=fixture();a=tmp_path/'track.json';b=tmp_path/'spec.json'
    a.write_text(json.dumps(track));b.write_text(json.dumps(spec));return a,b


def test_fresh_study_freezes_inputs_methods_all_samples_and_refuses_overwrite(tmp_path,monkeypatch):
    a,b=setup_files(tmp_path,monkeypatch);before={a:sha256(a),b:sha256(b)};output=tmp_path/'reports/force'
    report=subject.run(a,b,output)
    assert report['status']=='complete' and [r['conditional_feasible'] for r in report['cases']]==[7,0]
    assert json.loads((output/'pipeline.json').read_text())['status']=='complete'
    assert sha256(output/'inputs/object-track.json')==before[a]
    assert sha256(output/'inputs/force-spec.json')==before[b]
    assert {p:sha256(p) for p in before}==before
    for row in report['cases']:assert sha256(output/row['file'])==row['sha256']
    with pytest.raises(FileExistsError):subject.run(a,b,output)


def test_source_mutation_is_a_failed_study_not_a_completed_certificate(tmp_path,monkeypatch):
    a,b=setup_files(tmp_path,monkeypatch);original=subject.assess
    def changed(*args):
        result=original(*args);b.write_text(b.read_text()+' ');return result
    monkeypatch.setattr(subject,'assess',changed);output=tmp_path/'reports/force'
    with pytest.raises(ValueError,match='inputs changed'):subject.run(a,b,output)
    assert not (output/'result.json').exists()
    assert json.loads((output/'pipeline.json').read_text())['status']=='failed'


def test_close_distinct_masses_keep_distinct_output_files(tmp_path,monkeypatch):
    a,b=setup_files(tmp_path,monkeypatch);spec=json.loads(b.read_text());spec['masses_kg']=[1.,1.00000001];b.write_text(json.dumps(spec))
    output=tmp_path/'reports/force';report=subject.run(a,b,output)
    assert len({r['file'] for r in report['cases']})==2
    for row in report['cases']:assert sha256(output/row['file'])==row['sha256']
