import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from study_refined_surface_limits import surface_variant,VARIANTS


@pytest.mark.parametrize('name,kept,local',[
    ('original',[0,1,2,3,4,5],True),('without_positional',[0,3,4,5],True),
    ('without_angular',[0,1,2,5],True),('without_motion',[0,5],True),('edit_and_global_peak_only',[0],False)])
def test_motion_profile_omits_only_declared_conditions(name,kept,local):
    from study_refined_surface_limits import motion_variant
    population=dict(kinds=np.array(['edit','speed','acceleration','angular_speed','angular_acceleration','surface_distance']),
        vectors=np.arange(18).reshape(6,3),jacobians=np.arange(108).reshape(6,3,6),radii=np.arange(6)+1.,tolerances=np.arange(6)*1e-8)
    linear=dict(gaps=np.array([-.02,.001]),depth_caps=np.array([.02,.005]))
    caps,selected=motion_variant(linear,population,name)
    for key in selected:np.testing.assert_array_equal(selected[key],population[key][kept])
    np.testing.assert_array_equal(caps,[.02,.005] if local else [.02,.02])
    assert selected['radii'][0]==population['radii'][0]


@pytest.mark.parametrize('fault',[None,'norm','surface','trust','unused','nan'])
def test_cached_baseline_is_rechecked_without_another_solve(fault):
    from study_refined_surface_limits import verify_reference
    linear=dict(gaps=np.array([-.01]),gap_jacobian=np.array([[0.,0.,1.]]),depth_caps=np.array([.02]))
    population=dict(vectors=np.array([[.1,0,0]]),jacobians=np.eye(3)[None],radii=np.array([.12]),tolerances=np.array([1e-8]))
    step=np.array([0.,0.,0.])
    if fault=='norm':step[0]=.03
    if fault=='surface':step[2]=-.011
    if fault=='trust':step[0]=-.051
    if fault=='unused':step=np.r_[step,0]
    if fault=='nan':step[0]=np.nan
    if fault is None:np.testing.assert_array_equal(verify_reference(step,linear,population,.05),step)
    else:
        with pytest.raises(ValueError):verify_reference(step,linear,population,.05)


@pytest.mark.parametrize('name',VARIANTS)
def test_surface_ablation_retains_every_motion_row_budget_and_tolerance(name):
    kinds=np.array(['edit','speed','acceleration','angular_speed','angular_acceleration','surface_distance'])
    population=dict(kinds=kinds,vectors=np.arange(18).reshape(6,3),jacobians=np.arange(108).reshape(6,3,6),radii=np.arange(6)+1.,tolerances=np.arange(6)*1e-8)
    linear=dict(gaps=np.array([-.02,.001]),depth_caps=np.array([.02,.005]))
    caps,selected=surface_variant(linear,population,name)
    count=6 if name in ['original','distances_only'] else 5
    for key in selected:np.testing.assert_array_equal(selected[key],population[key][:count])
    np.testing.assert_array_equal(caps,[.02,.005] if name in ['original','planes_only'] else [.02,.02])
    np.testing.assert_array_equal(linear['depth_caps'],[.02,.005])
    np.testing.assert_array_equal(population['radii'],np.arange(6)+1.)


def test_unknown_ablation_cannot_silently_drop_conditions():
    with pytest.raises(ValueError):surface_variant({}, {}, 'drop_everything')


def test_fixed_witness_distance_can_reject_a_clear_tangential_escape():
    from coupled_surface_norms import separation_rows
    # A point initially 2 cm inside the top face of the box [-1,1]^2 x [-1,0].
    # It moves sideways and above that same face; exact box distance is 5 mm outside.
    triangle=np.array([[[-1.,-1.,0],[1.,-1.,0],[0.,1.,0]]]);bary=np.array([[.25,.25,.5]])
    start=np.array([[0.,0.,-.02]]);escaped=np.array([[.03,0.,.005]])
    vector,_=separation_rows(start,triangle,bary,np.zeros((1,3,3)),np.zeros((1,3,3,3)),0)
    moved,_=separation_rows(escaped,triangle,bary,np.zeros((1,3,3)),np.zeros((1,3,3,3)),0)
    radius=np.linalg.norm(vector[0]);assert radius==pytest.approx(.02)
    assert np.linalg.norm(moved[0])>radius
    q=np.abs(escaped[0]-[0,0,-.5])-[1,1,.5]
    signed_box_distance=np.linalg.norm(np.maximum(q,0))+min(float(q.max()),0)
    assert signed_box_distance==pytest.approx(.005)
    assert max(0.,-signed_box_distance)==0
