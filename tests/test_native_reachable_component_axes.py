"""Alternative-axis proposals preserve complete clocks, pairs and clear samples."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_component_trajectory_model import build as original_build, observe
from native_component_trajectory_step import _trajectory
from native_reachable_component_axes import build


def fixture(times=(0., 1.)):
    p = np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],
                  [-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]], float)*.1
    f = np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],
                  [3,7,6],[3,6,2],[0,4,7],[0,7,3],[1,2,6],[1,6,5]])
    points = {'A':np.repeat(p[None],len(times),axis=0),
              'B':np.array([p+[.4 if i==0 else .18,0,0] for i in range(len(times))])}
    j = {n:np.zeros((*v.shape,1)) for n,v in points.items()};j['A'][...,2,0]=1.
    return dict(vertices=points,point_jacobians=j,local_faces={'A':f,'B':f},
                source_vertex_ids={'A':list(range(8)), 'B':list(range(20,28))},
                times_s=list(times),required_times_s=list(times))


def test_reachable_alternative_separates_overlap_that_closest_axis_cannot_move():
    data=fixture();old=original_build(**data)
    result=build(**data,lower_delta=[0.],upper_delta=[.3]);new=result.trajectory
    assert result.report['changed_sample_indices']==[1]
    assert abs(old.groups[1]['axis_world'][0])==1 and abs(new.groups[1]['axis_world'][2])==1
    assert np.all(old.jacobian.toarray()[64:]==0) and np.all(new.jacobian.toarray()[64:]==1)
    moved={n:v+data['point_jacobians'][n][...,0]*.21 for n,v in data['vertices'].items()}
    assert observe(old,moved)[64:].min()<0 and observe(new,moved)[64:].min()>0
    np.testing.assert_array_equal(observe(new,data['vertices']),new.gaps_m)
    _trajectory(new,1)
    assert not any(result.report[k] for k in ('native_constraints_checked','nonlinear_reachability_proven','collision_certified','quality_approved','release_approved'))


def test_original_clear_axis_margin_columns_and_quadrature_stay_exact():
    data=fixture((0.,.2,1.));old=original_build(**data)
    result=build(**data,lower_delta=[0.],upper_delta=[.3]);new=result.trajectory
    assert new.groups[0]==old.groups[0] and result.screens[0]['original_clear_axis_preserved']
    for key in ('gaps_m','clearances_m'):np.testing.assert_array_equal(getattr(new,key)[:64],getattr(old,key)[:64])
    np.testing.assert_array_equal(new.jacobian.toarray()[:64],old.jacobian.toarray()[:64])
    np.testing.assert_array_equal(new.weights_s,old.weights_s)
    assert new.report['positive_sample_indices']==[0] and len(new.gaps_m)==192


def test_all_signed_normals_edges_and_pair_columns_are_present():
    data=fixture();result=build(**data,lower_delta=[-.01],upper_delta=[.3])
    for frame,screen in enumerate(result.screens):
        axes=screen['axes_world'];p=data['vertices'];j=data['point_jacobians']
        assert screen['complete_raw_axis_count']==348
        assert screen['tested_signed_axes']==2*(348-len(screen['skipped_raw_axis_indices']))==len(axes)
        np.testing.assert_array_equal(axes[::2],-axes[1::2])
        expected=[]
        for axis in axes:
            row_max=[]
            for a in range(8):
                for b in range(8):
                    coefficient=float(axis@(j['A'][frame,a,:,0]-j['B'][frame,b,:,0]))
                    gap=float(axis@(p['A'][frame,a]-p['B'][frame,b]))
                    row_max.append(gap+max(coefficient*-.01,coefficient*.3))
            expected.append(min(row_max))
        np.testing.assert_allclose(screen['estimated_box_potential_m'],expected,atol=2e-16,rtol=0)


def test_late_collision_and_last_control_are_not_truncated():
    data=fixture(tuple(np.linspace(0,1,70)))
    data['point_jacobians']={n:np.concatenate([np.zeros((*v.shape,2)),data['point_jacobians'][n]],axis=-1) for n,v in data['vertices'].items()}
    result=build(**data,lower_delta=[0,0,0],upper_delta=[0,0,.3]);new=result.trajectory
    assert len(new.gaps_m)==4480 and new.jacobian.shape==(4480,3) and len(result.screens)==70
    assert 69 in result.report['changed_sample_indices'] and np.all(new.jacobian.toarray()[-64:,2]==1)


def test_zero_box_keeps_closest_axes_and_stable_order():
    data=fixture();old=original_build(**data);result=build(**data,lower_delta=[0],upper_delta=[0])
    assert result.report['changed_sample_indices']==[]
    np.testing.assert_array_equal(result.trajectory.gaps_m,old.gaps_m)
    np.testing.assert_array_equal(result.trajectory.jacobian.toarray(),old.jacobian.toarray())


def test_independent_row_potential_does_not_claim_one_feasible_joint_delta():
    data=fixture((0.,));data['vertices']['B'][0]=data['vertices']['A'][0]+[.18,0,0]
    # Opposite vertex coefficients can each attain a favorable scalar maximum,
    # but this diagnostic never returns a jointly feasible motion or pass flag.
    data['point_jacobians']['A'][0,:,2,0]=[-1,1,1,-1,-1,1,1,-1]
    result=build(**data,lower_delta=[-.3],upper_delta=[.3])
    assert result.report['independent_row_maxima_not_proven_jointly_attainable']
    assert result.trajectory.gaps_m.min()<0 and not result.report['nonlinear_reachability_proven']
    assert not result.report['quality_approved'] and not result.report['collision_certified']


def test_nonfinite_late_screen_does_not_return_a_partial_proposal():
    data=fixture();data['point_jacobians']['A'][-1,:,2,0]=1e308
    # Projection is initially finite; maximizing at this finite endpoint overflows.
    with np.errstate(over='ignore',invalid='ignore'):
        with pytest.raises(ValueError,match='Finite complete'):
            build(**data,lower_delta=[0.],upper_delta=[1e308])


def test_inputs_and_returned_metadata_do_not_alias():
    data=fixture();before=copy.deepcopy(data);lo=np.array([0.]);hi=np.array([.3])
    result=build(**data,lower_delta=lo,upper_delta=hi)
    result.report['lower_delta'][0]=-99;result.trajectory.groups[0]['left_vertex_ids'].clear()
    for name in data['vertices']:
        np.testing.assert_array_equal(data['vertices'][name],before['vertices'][name])
        np.testing.assert_array_equal(data['point_jacobians'][name],before['point_jacobians'][name])
    assert data['source_vertex_ids']==before['source_vertex_ids'] and lo.tolist()==[0.] and hi.tolist()==[.3]


@pytest.mark.parametrize('fault', ['nan','infinite','positive-lower','negative-upper','reversed','wrong-size','boolean','axes-small','axes-boolean','elements-small','elements-boolean','elements-large','late-open','short-clock','late-nan-column'])
def test_incomplete_or_oversized_populations_reject_whole(fault):
    data=fixture();kw=dict(lower_delta=[0.],upper_delta=[.3])
    if fault=='nan':kw['upper_delta']=[np.nan]
    if fault=='infinite':kw['upper_delta']=[np.inf]
    if fault=='positive-lower':kw['lower_delta']=[.1]
    if fault=='negative-upper':kw['upper_delta']=[-.1]
    if fault=='reversed':kw.update(lower_delta=[.2],upper_delta=[.1])
    if fault=='wrong-size':kw.update(lower_delta=[0.,0.],upper_delta=[.3,.3])
    if fault=='boolean':kw.update(lower_delta=[False],upper_delta=[True])
    if fault=='axes-small':kw['maximum_candidate_axes']=695
    if fault=='axes-boolean':kw['maximum_candidate_axes']=True
    if fault=='elements-small':kw['maximum_screen_elements']=64*696-1
    if fault=='elements-boolean':kw['maximum_screen_elements']=True
    if fault=='elements-large':kw['maximum_screen_elements']=8000001
    if fault=='late-open':data['local_faces']['B']=data['local_faces']['B'][:-1]
    if fault=='short-clock':data['times_s']=[0.]
    if fault=='late-nan-column':data['point_jacobians']['A'][-1,0,0,0]=np.nan
    with pytest.raises(ValueError):build(**data,**kw)
