import sys
from pathlib import Path
import itertools
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from waypoint_lattice import shortest_path,LinearGuide


def test_dynamic_program_matches_exhaustive_paths_with_rate_and_invalid_node_constraints():
    times=np.array([0.,1.,1.5,2.5]);states=np.array([[0.],[.5],[1.]])
    costs=np.array([[0,0,0],[2,.8,0],[2,np.inf,.1],[0,0,0.]])
    limits=np.array([1.]);weight=.2
    options=[]
    for a,b in itertools.product(range(3),repeat=2):
        ids=[0,a,b,0];points=states[ids];speed=np.diff(points,axis=0)/np.diff(times)[:,None]
        if np.any(np.abs(speed)>limits):continue
        value=sum(costs[i,j] for i,j in enumerate(ids))+weight*np.sum(np.diff(times)[:,None]*(speed/limits)**2)
        if np.isfinite(value):options.append((value,ids))
    path,result=shortest_path(times,states,costs,limits,weight)
    assert result['total_cost']==pytest.approx(min(options)[0])
    assert result['state_indices']==min(options)[1]
    np.testing.assert_array_equal(path[[0,-1]],0)


def test_disconnected_path_is_reported_instead_of_violating_rate_cap():
    points,result=shortest_path([0,1,2],[[0],[2]],[[0,0],[np.inf,0],[0,0]],[1])
    assert points is None and result['status']=='no_feasible_path'


def test_piecewise_linear_guide_keeps_endpoints_domain_and_rate_bounds():
    guide=LinearGuide([1,2,3],[[0,0,0],[.06,30,-30],[0,0,0]],[.06,30,30])
    np.testing.assert_allclose(guide(1.5),[.03,15,-15])
    np.testing.assert_array_equal(guide(0),0);np.testing.assert_array_equal(guide(4),0)
    with pytest.raises(ValueError):LinearGuide([1,2,3],[[0,0,0],[.06,30,-30],[0,0,0]],[.05,30,30])
    with pytest.raises(ValueError):guide(np.nan)


@pytest.mark.parametrize('fault',['clock','nan','negative_cost','zero_limit','duplicate','no_boundary'])
def test_invalid_graph_inputs(fault):
    times=[0,1,2];states=[[0.],[1.]];costs=np.zeros((3,2));limits=[1.]
    if fault=='clock':times=[0,0,2]
    if fault=='nan':costs[1,1]=np.nan
    if fault=='negative_cost':costs[1,1]=-1
    if fault=='zero_limit':limits=[0]
    if fault=='duplicate':states=[[0.],[0.]]
    if fault=='no_boundary':states=[[1.],[2.]]
    with pytest.raises(ValueError):shortest_path(times,states,costs,limits)
