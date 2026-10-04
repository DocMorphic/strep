"""Structural native support, complete contact order and conditional failures."""
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_contact_support import fixed_actor_times,contact_support,diagnose
from native_contact_norms import ContactNorms
from test_native_contact_norms import prepared


def edits():
    return SimpleNamespace(actors={'A':dict(tracks=[dict(clock=np.array([0.,.5,1.,1.5,2.]),
        ids=np.array([1,2,3]),weights=np.array([[0.],[1.],[0.]]))])})


def test_exact_keys_neighbor_support_and_endpoint_clamping():
    value=edits();times=np.array([-.1,0.,.5,.75,1.,1.25,1.5,1.75,2.,2.1])
    np.testing.assert_array_equal(fixed_actor_times(value,'A',times),[True,True,True,False,False,False,True,True,True,True])
    np.testing.assert_array_equal(fixed_actor_times(value,'uneditable-actor',times),np.ones(len(times),bool))


def test_every_declared_track_is_considered_conservatively():
    value=edits();second=dict(clock=np.array([0.,1.,2.]),ids=np.array([1]),weights=np.array([[1.]]))
    value.actors['A']['tracks'].append(second)
    np.testing.assert_array_equal(fixed_actor_times(value,'A',[0.,.5,1.,1.5,2.]),[True,False,False,False,True])


@pytest.mark.parametrize('fault',['empty-times','nan-times','clock-order','clock-nan','index','duplicate-index','weights-shape','weights-nan'])
def test_missing_or_malformed_complete_support_rejects(fault):
    value=edits();entry=value.actors['A']['tracks'][0];times=np.array([0.,1.,2.])
    if fault=='empty-times':times=times[:0]
    if fault=='nan-times':times[0]=np.nan
    if fault=='clock-order':entry['clock'][1]=entry['clock'][0]
    if fault=='clock-nan':entry['clock'][1]=np.nan
    if fault=='index':entry['ids'][0]=-1
    if fault=='duplicate-index':entry['ids'][1]=entry['ids'][0]
    if fault=='weights-shape':entry['weights']=entry['weights'][:1]
    if fault=='weights-nan':entry['weights'][0,0]=np.nan
    with pytest.raises(ValueError):fixed_actor_times(value,'A',times)


@pytest.mark.parametrize('partner',[False,True])
@pytest.mark.parametrize('hold',[False,True])
def test_actual_fixture_row_order_and_native_support_match_all_source_rows(tmp_path,partner,hold):
    problem,p,digest=prepared(tmp_path,partner=partner,hold=hold)
    source=ContactNorms(problem,p,digest);rows,gaps,identity=source.sample(problem.source_world)
    mask,report=diagnose(problem,np.r_[rows.residual(),-gaps/.005])
    assert report['point_identity']==identity['identity']
    assert mask.shape==(3*len(rows.caps),) and report['complete_surface_rows']==len(mask)
    assert not report['measurement_authenticated'] and not report['quality_approved'] and not report['release_approved']
    # Every fixed source clock remains identical under a nonzero native edit.
    candidate=problem.initial.copy();candidate[:]=[.02,-.01,.03]
    worlds=problem.worlds(candidate)
    for data,observation in zip(problem.rows,report['contacts']):
        frozen=np.asarray(observation['fixed_pose_times'],bool);indices=data['ids'][frozen]
        for name in problem.scene.actors:
            np.testing.assert_allclose(worlds[name][indices],problem.source_world[name][indices],atol=1e-12,rtol=0)


def mock_problem(*,partner=False,centroid=False):
    entry=dict(ids=np.array([0,1]),authored=dict(id='group',actor='A',reduction='centroid' if centroid else 'vertices',
        target=dict(space='actor',actor='B') if partner else dict(space='world')))
    return SimpleNamespace(edits=edits(),scene=SimpleNamespace(actors={'A':{},'B':{}},check_inputs=lambda:None),
        rows=[dict(entry=entry,times=np.array([0.,1.,2.]))])


@pytest.mark.parametrize('centroid',[False,True])
def test_all_point_and_facing_rows_keep_their_original_order(centroid):
    problem=mock_problem(centroid=centroid);mask,report=contact_support(problem)
    points=np.array([True,False,True]) if centroid else np.array([True,True,False,False,True,True])
    np.testing.assert_array_equal(mask,np.r_[points,np.repeat(points,2)])
    residual=np.full(len(mask),-1.);residual[np.flatnonzero(mask)[0]]=1.;residual[np.flatnonzero(~mask)[0]]=2.
    _,diagnostic=diagnose(problem,residual)
    assert diagnostic['failed_fixed_surface_row_count']==1 and diagnostic['maximum_fixed_source_violation']==1.
    assert diagnostic['fixed_source_failures_present']


def test_partner_must_also_be_fixed_before_a_contact_is_classified_fixed():
    problem=mock_problem(partner=True);problem.edits.actors['B']=dict(tracks=[dict(clock=np.array([0.,1.,2.]),ids=np.array([0]),weights=np.array([[1.]]))])
    mask,report=contact_support(problem)
    assert report['contacts'][0]['fixed_pose_times']==[False,False,True]


@pytest.mark.parametrize('fault',['short','nan','matrix'])
def test_partial_or_reordered_shape_populations_are_not_reduced(fault):
    problem=mock_problem();mask,_=contact_support(problem);residual=np.zeros(len(mask))
    if fault=='short':residual=residual[:-1]
    if fault=='nan':residual[0]=np.nan
    if fault=='matrix':residual=residual[None]
    with pytest.raises(ValueError):diagnose(problem,residual)
