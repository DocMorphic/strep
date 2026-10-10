import sys,copy
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from protected_inequality_step import fit,margin_start_attempts
from pose_proposal_archive import ProposalArchive,load_record
from geometry_conic_start import replay


def motion_fixture():
    def measure(x):return np.array([x[0]-.5,1-x[0]])
    def pair(x):return measure(x),np.array([[1.],[-1.]])
    def vectors(x):return dict(offsets=np.array([[x[0],0.,0.]]),jacobian=np.array([[[1.],[0.],[0.]]]),
        limits=np.array([1.]),scales=np.array([1.]),rows=np.array([1]),distance=np.array([True]))
    return dict(measure=measure,linearize=pair,seed=[0.],lower=[0.],upper=[1.],iterations=2,trust=.1,
        seconds=10.,solve_iterations=2,proposal='nonlinear',proposal_start='geometry-descent',
        proposal_priority='worst-first',proposal_geometry_solver='conic',proposal_margin_fallback=True,
        proposal_tangent_guard=True,vectorize=vectors)


def test_actual_conic_starts_are_retained_only_after_nonlinear_and_saved_replay(tmp_path):
    args=motion_fixture();args['representation_measure']=args['measure']
    args['record_store']=ProposalArchive(tmp_path)
    value,report=fit(**args)
    assert value[0] == pytest.approx(.2,abs=1e-6)
    assert report['proposal_geometry_solver']=='conic' and report['nontradeoff_rows_preserved']
    assert len(report['history'])==2 and all(r['accepted'] for r in report['history'])
    assert all(t['retention_guard_passed'] and t['tangent_guard_passed'] and t['representation_guard_passed'] for t in report['trials'] if t['accepted'])
    assert report['represented_source_rows_preserved'] and not report['quality_approved'] and not report['release_approved']
    for reference in report['proposal_starts']:
        start,bindings=load_record(tmp_path,reference,array_values=True)
        linear,_=load_record(tmp_path,report['proposal_linearizations'][reference['iteration']-1],array_values=True)
        assert bindings and start['retained'] is False and len(margin_start_attempts(start))==1
        checked=replay(start,linear['slacks'],linear['jacobian'])
        assert checked==dict(verified_points=2,scalar_rows=2,norm_vectors=1,retained=False)


def test_saved_representation_blocks_all_conic_pose_proposals():
    args=motion_fixture();args['representation_measure']=lambda x:np.r_[args['measure'](x),-x[0]]
    value,report=fit(**args)
    np.testing.assert_array_equal(value,[0.])
    assert report['proposal_starts'][0]['success'] and not any(t['accepted'] for t in report['trials'])
    assert any(t['retention_guard_passed'] and not t['representation_guard_passed'] for t in report['trials'])
    assert report['represented_source_rows_preserved'] and report['stop'] in ['no_guarded_improvement','time_or_measurement_budget']


def test_measurement_expiry_during_conic_replay_cannot_promote_proposal():
    args=motion_fixture();args['maximum_calls']=2
    args['representation_measure']=lambda x:np.r_[args['measure'](x),-x[0]]
    value,report=fit(**args)
    np.testing.assert_array_equal(value,[0.])
    assert report['proposal_starts'][0]['success'] and report['stop']=='time_or_measurement_budget'
    assert len(report['trials'])==1 and report['trials'][0]['accepted'] is False and not report['quality_approved']


@pytest.mark.parametrize('options',[dict(proposal_geometry_solver='other'),dict(proposal_geometry_solver=None),
    dict(proposal_start='zero',vectorize=None),dict(proposal_start='linear-feasible',vectorize=None)])
def test_invalid_conic_selection_does_not_measure(options):
    args=motion_fixture();args.update(options);args['measure']=lambda x:pytest.fail('Invalid option measured')
    with pytest.raises(ValueError):fit(**args)


@pytest.mark.parametrize('field,value',[('retained',True),('quality_approved',True),('release_approved',True),
    ('scalar_rows',1),('norm_cones',2),('control_count',2),('epigraph_tie_tolerance',.1),
    ('initial_worst',99.),('primary_status','PrimalInfeasible'),('selected_phase','other')])
def test_tampered_conic_provenance_or_population_fails_independent_replay(field,value):
    args=motion_fixture();_,report=fit(**args);start=copy.deepcopy(report['proposal_starts'][0]);start[field]=value
    linear=report['proposal_linearizations'][0]
    with pytest.raises((ValueError,AssertionError)):replay(start,linear['slacks'],linear['jacobian'])


@pytest.mark.parametrize('target',['delta','primary_delta'])
def test_tampered_point_cannot_be_replayed(target):
    args=motion_fixture();_,report=fit(**args);start=copy.deepcopy(report['proposal_starts'][0]);start[target]=[.8]
    linear=report['proposal_linearizations'][0]
    with pytest.raises((ValueError,AssertionError)):replay(start,linear['slacks'],linear['jacobian'])


def test_complete_norm_or_scalar_loss_fails_even_with_unchanged_solver_status():
    args=motion_fixture();_,report=fit(**args);start=copy.deepcopy(report['proposal_starts'][0]);linear=report['proposal_linearizations'][0]
    start['vectors']['jacobian']=[[[100.],[0.],[0.]]]
    with pytest.raises(ValueError,match='affine'):replay(start,linear['slacks'],linear['jacobian'])
    start=copy.deepcopy(report['proposal_starts'][0]);start['caps'][0]=.9
    with pytest.raises(ValueError,match='affine'):replay(start,linear['slacks'],linear['jacobian'])


@pytest.mark.parametrize('field,value', [('phase',2),('phase',True),('solver_status','MaxTime'),
    ('solver_iterations',-1),('solver_iterations',True),('point_shape',[1]),
    ('finite_complete_point',False),('finite_complete_point',1),('point',[.8,.1]),('point',None)])
def test_tampered_solver_observation_cannot_supply_checked_motion(field,value):
    args=motion_fixture();_,report=fit(**args)
    start=copy.deepcopy(report['proposal_starts'][0]);linear=report['proposal_linearizations'][0]
    start['solver_points'][0][field]=value
    with pytest.raises((ValueError,AssertionError,TypeError)):
        replay(start,linear['slacks'],linear['jacobian'])


def test_every_invoked_phase_must_be_observed_and_legacy_reports_still_replay():
    args=motion_fixture();_,report=fit(**args)
    start=copy.deepcopy(report['proposal_starts'][0]);linear=report['proposal_linearizations'][0]
    legacy=copy.deepcopy(start);legacy.pop('solver_point_schema');legacy.pop('solver_points')
    assert replay(legacy,linear['slacks'],linear['jacobian'])['verified_points']==2
    start['solver_points'].pop()
    with pytest.raises(ValueError,match='phase'):replay(start,linear['slacks'],linear['jacobian'])


def test_observation_cannot_rewrite_primary_epigraph():
    args=motion_fixture();_,report=fit(**args)
    start=copy.deepcopy(report['proposal_starts'][0]);linear=report['proposal_linearizations'][0]
    start['solver_points'][0]['point'][-1]+=.01
    with pytest.raises(ValueError,match='epigraph'):replay(start,linear['slacks'],linear['jacobian'])
