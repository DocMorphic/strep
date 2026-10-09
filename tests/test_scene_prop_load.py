"""Native-load provenance/clock/support guards; fixture forces are analytic."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_prop_load import measure
from verify_scene_prop_load import verify


def capture():
    rows=[]
    for tick in range(9):
        pose=np.eye(4);pose[0,3]=tick/60
        rows.append(dict(tick=tick,session=0,source_time_s=tick/60,transport='live',failure='',modes={'P':'held' if tick<7 else 'released'},
            members={'P':['left','right'] if tick<3 else ['right'] if tick<7 else []},
            props={'P':dict(pose=pose.tolist(),velocity=[0,0,0],spin=[0,0,0],gravity=[0,-9.81,0],inverse_mass=.5,inverse_inertia=[1,1,1],step_s=1/60)}))
    return dict(faults=[],quality_approved=False,release_approved=False,physics_fps=60,last_tick=8,records=rows,
        bodies={'P':dict(mass_kg=2,inertia_diagonal=[1,1,1],center_of_mass_policy='custom_zero_body_origin',center_of_mass_mode=1,center_of_mass_local_m=[0,0,0])})


def test_analytic_load_preserves_all_support_boundaries_and_no_capacity_claim():
    source=capture();before=copy.deepcopy(source);actual=measure(source,'P');d=actual['diagnostic']
    np.testing.assert_allclose(d['required_non_gravity_force_world_N'],np.tile([0,19.62,0],(7,1)),atol=1e-12)
    np.testing.assert_allclose(d['required_torque_about_com_world_Nm'],0)
    assert d['excluded_boundary_frames']==[2,3,6,7]
    assert [p['interior_samples'] for p in d['phases']]==[1,2,0]
    assert d['phases'][-1]['support_assumption']=='unknown' and not d['phases'][-1]['free_flight_residual_applicable']
    assert actual['held_interior_samples']==3 and actual['held_com_velocity_disagreement_max_m_s']==pytest.approx(1)
    assert actual['held_spin_disagreement_max_rad_s']==0 and d['physical_approval'] is None
    assert not actual['quality_approved'] and not actual['release_approved'] and source==before


def test_native_gravity_changes_are_retained_and_used_per_sample():
    run=capture();run['records'][4]['props']['P']['gravity']=[2,-4,6];actual=measure(run,'P')
    np.testing.assert_allclose(actual['diagnostic']['required_non_gravity_force_world_N'][3],[-4,8,-12],atol=1e-12)
    assert actual['diagnostic']['gravity_m_s2'][4]==[2,-4,6]


def test_editing_report_metadata_does_not_mutate_native_capture():
    run=capture();report=measure(run,'P');report['body_settings']['inertia_diagonal'][0]=99
    assert run['bodies']['P']['inertia_diagonal']==[1,1,1]


def test_member_order_is_not_a_new_support_phase():
    run=capture();run['records'][1]['members']['P'].reverse()
    assert len(measure(run,'P')['diagnostic']['phases'])==3


def test_independent_replay_checks_complete_analytic_capture():
    run=capture();result=verify(run,measure(run,'P'),'P')
    assert result['central_samples']==7 and result['ownership_phases']==3 and result['held_interiors']==3
    assert not result['quality_approved'] and not result['release_approved']


def test_rotating_anisotropic_body_matches_analytic_gyroscopic_load():
    run=capture();inertia=np.diag([1.,2.,2.5]);omega=np.array([.3,.5,.7])
    run['bodies']['P']['inertia_diagonal']=np.diag(inertia).tolist()
    rotations=Rotation.from_rotvec(np.arange(9)[:,None]/60*omega).as_matrix()
    for i,row in enumerate(run['records']):
        pose=np.asarray(row['props']['P']['pose']);pose[:3,:3]=rotations[i]
        row['props']['P']['pose']=pose.tolist();row['props']['P']['inverse_inertia']=(1/np.diag(inertia)).tolist()
    report=measure(run,'P');expected=rotations[1:-1]@np.cross(omega,inertia@omega)
    np.testing.assert_allclose(report['diagnostic']['required_torque_about_com_world_Nm'],expected,atol=1e-11)
    assert verify(run,report,'P')['central_samples']==7
    assert report['held_spin_disagreement_max_rad_s']==pytest.approx(np.linalg.norm(omega))


def test_independent_replay_rejects_a_nonmaximal_peak_inside_its_phase():
    run=capture()
    for row in run['records']:row['props']['P']['gravity'][0]=row['tick']
    report=measure(run,'P');stats=report['diagnostic']['phases'][1]['required_non_gravity_force_N']
    assert stats['peak_frame']==5
    stats['peak_frame']=4
    with pytest.raises(ValueError):verify(run,report,'P')


@pytest.mark.parametrize('fault',['force','torque','gravity','missing-sample','boundary','free-flight','peak','body','velocity','approved'])
def test_independent_replay_rejects_changed_load_evidence(fault):
    run=capture();report=measure(run,'P');d=report['diagnostic']
    if fault=='force':d['required_non_gravity_force_world_N'][1][0]+=.1
    elif fault=='torque':d['required_torque_about_com_world_Nm'][2][0]=1
    elif fault=='gravity':d['gravity_m_s2'][3][0]=1
    elif fault=='missing-sample':d['sample_frames'].pop()
    elif fault=='boundary':d['same_phase_stencil'][1]=True
    elif fault=='free-flight':d['phases'][-1]['free_flight_residual_applicable']=True
    elif fault=='peak':d['phases'][0]['required_non_gravity_force_N']['peak_frame']=5
    elif fault=='body':report['body_settings']=copy.deepcopy(report['body_settings']);report['body_settings']['mass_kg']=3
    elif fault=='velocity':report['sampled_com_velocity_minus_body_velocity_world_m_s'][0][0]=0
    else:report['release_approved']=True
    with pytest.raises(ValueError):verify(run,report,'P')


@pytest.mark.parametrize('fault',['truncated','tick','clock','reset','transport','fault','approved','com-auto','com-offset','com-missing','mass','inverse-mass','inertia','step','pose-scale','pose-nan','gravity-nan','velocity-nan','spin-nan','owner-empty','owner-duplicate','unknown-mode'])
def test_incomplete_or_invalid_native_assumptions_never_produce_a_load_report(fault):
    run=capture();row=run['records'][4];state=row['props']['P'];body=run['bodies']['P']
    if fault=='truncated':run['records'].pop()
    elif fault=='tick':row['tick']=3
    elif fault=='clock':row['source_time_s']+=.001
    elif fault=='reset':row['session']=1
    elif fault=='transport':row['transport']='preview'
    elif fault=='fault':row['failure']='failed'
    elif fault=='approved':run['quality_approved']=True
    elif fault=='com-auto':body['center_of_mass_mode']=0
    elif fault=='com-offset':body['center_of_mass_local_m']=[.1,0,0]
    elif fault=='com-missing':del body['center_of_mass_policy']
    elif fault=='mass':body['mass_kg']=True
    elif fault=='inverse-mass':state['inverse_mass']=.4
    elif fault=='inertia':state['inverse_inertia']=[1,2,1]
    elif fault=='step':state['step_s']=.02
    elif fault=='pose-scale':state['pose'][0][0]=2
    elif fault=='pose-nan':state['pose'][0][3]=float('nan')
    elif fault=='gravity-nan':state['gravity'][0]=float('nan')
    elif fault=='velocity-nan':state['velocity'][0]=float('nan')
    elif fault=='spin-nan':state['spin'][0]=float('nan')
    elif fault=='owner-empty':row['members']['P']=[]
    elif fault=='owner-duplicate':row['members']['P']=['right','right']
    else:row['modes']['P']='free-flight'
    with pytest.raises((ValueError,KeyError)):measure(run,'P')
