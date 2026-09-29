from pathlib import Path
import sys
from fractions import Fraction
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from contact_pose_sphere_bound import sphere_bound,sqrt_enclosure
from contact_pose_reachability import point_bound


@pytest.mark.parametrize('value',[Fraction(0),Fraction(4),Fraction(2),Fraction(1,3),Fraction(10**100),Fraction(1,10**100)])
def test_sqrt_bounds_are_outward_by_exact_squared_comparison(value):
    low,high=sqrt_enclosure(value)
    assert low*low<=value<=high*high and high-low<=Fraction(1,2**96)


def test_diagonal_conflict_missed_by_individual_axes():
    args=([[0,0,0]],[1],[[0,0,0]],[.2,.2,0])
    assert not point_bound(*args)['any_verified_conflict']
    result=sphere_bound(*args)
    assert result['conflict_verified'] and result['joint_displacement_lower_bound_m']>.27
    certificate=result['certificate']
    assert Fraction(certificate['squared_margin_exact'])==Fraction(certificate['distance_squared_exact'])-Fraction(certificate['allowed_distance_upper_exact'])**2>0


def test_euclidean_lever_allowance_tighter_than_l1_but_preserves_rotation():
    args=([[0,0,0]],[1],[[.1,.1,.1]],[.45,0,0])
    assert not point_bound(*args)['any_verified_conflict']
    assert sphere_bound(*args)['conflict_verified']
    assert not sphere_bound([[0,0,0]],[1],[[.1,.1,.1]],[np.sqrt(.03),0,0],joint_budget=0)['conflict_verified']


def test_constructed_rigid_candidates_inside_joint_budget_do_not_conflict():
    from scipy.spatial.transform import Rotation
    rng=np.random.default_rng(55)
    for _ in range(60):
        w=rng.random(8);w/=w.sum();w*=1.000002
        p=rng.normal(size=(8,3));q=rng.normal(size=(8,3))*.1
        d=rng.normal(size=(8,3));d*=.22/np.linalg.norm(d,axis=1)[:,None]
        r=Rotation.random(8,random_state=rng).as_matrix()
        target=(w[:,None]*(p+d+np.einsum('vij,vj->vi',r,q))).sum(0)
        assert not sphere_bound(p,w,q,target)['conflict_verified']


def test_reserve_and_weight_mass_are_used():
    assert not sphere_bound([[0,0,0]],[1],[[0,0,0]],[.2250005,0,0])['conflict_verified']
    assert not sphere_bound([[0,0,0]],[2],[[0,0,0]],[.44,0,0])['conflict_verified']
    assert sphere_bound([[0,0,0]],[1],[[0,0,0]],[.23,0,0])['conflict_verified']


def test_invalid_parameters_rejected():
    with pytest.raises(ValueError):sqrt_enclosure(Fraction(-1))
    with pytest.raises(ValueError):sqrt_enclosure(Fraction(1),True)
    for weights in [[-1],[0],[float('nan')]]:
        with pytest.raises(ValueError):sphere_bound([[0,0,0]],weights,[[0,0,0]],[0,0,0])
    with pytest.raises(ValueError):sphere_bound([[0,0,0]],[1],[[0,0,0]],[0,0,0],rotation_norm_bound=.9)
