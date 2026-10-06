"""Control-aware direction ranking keeps all vertices, pairs and controls."""
from pathlib import Path
import sys, itertools
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_triangle_control_axis import choose, candidate_axes
from native_partner_surface_rows import separation_axis


def fixture():
    a=np.array([[0.,0,0],[1.,0,0],[0.,1,0]])
    b=np.array([[.2,.2,-.1],[.8,.2,.1],[.2,.8,.1]])
    return [a,b,np.zeros((3,3,2)),np.zeros((3,3,2)),np.array([-.1,-.1]),np.array([.1,.1])]


def independent_scores(args):
    a,b,jl,jr,lo,hi=args;axes=candidate_axes(a,b);actual=[];optimistic=[]
    for n in axes:
        rows=[];bounds=[]
        for i,j in itertools.product(range(3),repeat=2):
            gap=float(a[i]@n-b[j]@n);derivative=n@(jl[i]-jr[j])
            rows.append(gap)
            bounds.append(gap+sum(max(x*l,x*u) for x,l,u in zip(derivative,lo,hi)))
        actual.append(min(rows));optimistic.append(min(bounds))
    return axes,np.array(actual),np.array(optimistic)


def test_zero_derivatives_keep_existing_pose_axis_exactly():
    args=fixture();normal,report=choose(*args);baseline,gap=separation_axis(*args[:2])
    np.testing.assert_array_equal(normal,baseline)
    assert not report['changed_direction'] and report['baseline_gap_m']==gap
    assert report['all_nine_pairs_scored_per_direction'] and not report['quality_approved']


def test_control_direction_can_replace_smallest_current_overlap():
    args=fixture();args[2][:,0,0]=10.
    normal,report=choose(*args);axes,current,optimistic=independent_scores(args)
    assert report['changed_direction'] and report['selected_optimistic_gap_m']>report['baseline_optimistic_gap_m']
    selected=report['selected_index'];np.testing.assert_array_equal(normal,axes[selected])
    assert optimistic[selected]==pytest.approx(optimistic.max(),abs=1e-14)
    assert report['selected_gap_m']==pytest.approx(current[selected],abs=1e-14)


def test_all_nine_pairs_and_last_control_determine_score():
    args=fixture();args[2]=np.zeros((3,3,96));args[3]=np.zeros((3,3,96))
    args[2][2,0,95]=10.;args[3][2,1,95]=-4.
    args[4]=-np.ones(96)*.1;args[5]=np.ones(96)*.1
    normal,report=choose(*args);axes,current,optimistic=independent_scores(args)
    assert report['selected_optimistic_gap_m']==pytest.approx(optimistic.max(),abs=1e-14)
    assert report['selected_optimistic_gap_m']==pytest.approx(optimistic[report['selected_index']],abs=1e-14)


def test_both_orientations_of_every_nonzero_family_axis_are_retained():
    axes=candidate_axes(*fixture()[:2]);assert len(axes)%2==0 and 4<=len(axes)<=34
    np.testing.assert_array_equal(axes[1::2],-axes[::2])
    np.testing.assert_allclose(np.linalg.norm(axes,axis=1),1.,atol=1e-15,rtol=0)


def test_optimistic_rows_do_not_prove_simultaneous_feasibility():
    args=fixture();args[2][0,2,0]=10.;args[2][1,2,0]=-10.
    _,report=choose(*args)
    assert report['native_constraints_ignored'] and not report['simultaneous_affine_feasibility_proven']
    assert not report['release_approved'] and not report['nonlinear_geometry_infeasibility_proven']


def test_swapping_actors_preserves_best_score():
    args=fixture();args[2][:,0,0]=10.
    _,a=choose(*args);_,b=choose(args[1],args[0],args[3],args[2],args[4],args[5])
    assert a['selected_optimistic_gap_m']==pytest.approx(b['selected_optimistic_gap_m'],abs=1e-14)


def test_inputs_remain_immutable():
    args=fixture();saved=[a.copy() for a in args];choose(*args)
    for a,b in zip(args,saved):np.testing.assert_array_equal(a,b)


def test_explicit_original_baseline_is_retained_even_when_roundoff_changes_family():
    args=fixture();baseline=np.array([0.,0.,1.])
    normal,report=choose(*args,baseline_normal=baseline)
    assert report['explicit_baseline_retained']
    assert report['selected_optimistic_gap_m']>=report['baseline_optimistic_gap_m']
    assert report['candidate_directions']<=36


@pytest.mark.parametrize('normal',[[0,0,0],[1,1,0],[float('nan'),0,0],[1,0],[1j,0,0]])
def test_invalid_explicit_baseline_cannot_silently_change_population(normal):
    with pytest.raises(ValueError):choose(*fixture(),baseline_normal=normal)


@pytest.mark.parametrize('kind',['triangle_shape','nan','degenerate','complex','derivative_shape','derivative_nan',
                               'box_shape','box_inverted','box_without_zero','too_many_controls','overflow'])
def test_invalid_or_incomplete_inputs_return_no_partial_selection(kind):
    args=fixture()
    if kind=='triangle_shape':args[0]=args[0][:2]
    elif kind=='nan':args[1][0,0]=np.nan
    elif kind=='degenerate':args[0][2]=args[0][1]
    elif kind=='complex':args[2]=args[2].astype(complex)
    elif kind=='derivative_shape':args[3]=args[3][:2]
    elif kind=='derivative_nan':args[3][2,2,1]=np.inf
    elif kind=='box_shape':args[5]=np.array([.1])
    elif kind=='box_inverted':args[5][0]=-.2
    elif kind=='box_without_zero':args[4][0]=.01
    elif kind=='too_many_controls':args[2]=args[3]=np.zeros((3,3,97));args[4]=np.zeros(97);args[5]=np.ones(97)
    else:args[2][:]=1e308;args[5][:]=1e308
    with pytest.raises(ValueError):choose(*args)
