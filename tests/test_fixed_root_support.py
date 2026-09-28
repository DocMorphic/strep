from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from fixed_root_support import constant_root_initial,relax_fixed_root
from rig_periodic_contact import neighbor_constraints


class Toy:
    def __init__(self,target):
        self.target=target;self.local=np.zeros(len(target));self.bounds=np.full(target.shape[1],.2)
        self.spec=dict(limits=dict(root_step_m=.015,joint_step_degrees=5),max_nfev=30)
    def objective_pair(self,frame,x,neighbors):return x-self.target[frame],np.eye(len(x))


def test_root_elimination_reaches_known_free_optimum():
    target=np.full((5,9),.03);fitter=Toy(target)
    initial=np.zeros((5,9));initial[:,:3]=[.01,.04,-.01]
    result,records,summary=relax_fixed_root(fitter,initial,sweeps=2)
    assert np.array_equal(result[:,:3],initial[:,:3])
    np.testing.assert_allclose(result[:,3:],target[:,3:],atol=1e-7)
    assert all(r['cost_after']<=r['cost_before'] for r in records)
    assert summary['root_parameter_variation_m']==0


def test_conflicting_targets_stay_inside_adjacent_and_absolute_limits():
    target=np.zeros((5,9));target[::2,3:]=2.;target[1::2,3:]=-2.
    fitter=Toy(target);initial=np.zeros_like(target);initial[:,:3]=[0,.06,0]
    result,_,_=relax_fixed_root(fitter,initial,sweeps=2)
    assert np.array_equal(result[:,:3],initial[:,:3])
    assert np.all(np.abs(result)<=fitter.bounds+1e-8)
    for i in range(4):assert neighbor_constraints(result[i],[result[i+1]],.015,np.radians(5))[0].min()>=-1e-7


def test_median_is_constant_without_changing_leg_edits():
    initial=np.arange(45).reshape(5,9)*.001
    result=constant_root_initial(initial,np.ones(9))
    np.testing.assert_array_equal(result[:,:3],np.broadcast_to(initial[2,:3],(5,3)))
    np.testing.assert_array_equal(result[:,3:],initial[:,3:])
    assert not np.shares_memory(initial,result)


def test_reject_changed_root_and_invalid_parameters():
    initial=np.zeros((5,9));fitter=Toy(initial)
    initial[2,0]=.001
    with pytest.raises(ValueError):relax_fixed_root(fitter,initial)
    initial[0,0]=np.nan
    with pytest.raises(ValueError):constant_root_initial(initial,fitter.bounds)
    with pytest.raises(ValueError):relax_fixed_root(fitter,np.zeros((5,9)),sweeps=0)
