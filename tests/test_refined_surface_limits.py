import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from study_refined_surface_limits import surface_variant,VARIANTS


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
