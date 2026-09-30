import sys
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from regional_pose_bounded import coordinates
from regional_pose_witness import RegionalPoseProblem
from grasp_pose_witness_bounded import physical_parameters


@pytest.fixture(scope='module')
def problem():
    return RegionalPoseProblem(ROOT/'reports/scene-region-jobs/cylinder-contact-v1/fit',96)


def test_normalized_bounded_seed_preserves_original_pose(problem):
    initial,scale=coordinates(problem)
    physical=physical_parameters(problem.t(initial*scale),problem.limits).numpy()
    np.testing.assert_allclose(physical,problem.seed,atol=1e-12,rtol=1e-12)
    actual,_=problem.independent(physical);expected,_=problem.independent(problem.seed)
    assert actual['bounds_passed'] and not actual['pose_witness_passed']
    assert abs(actual['contacts'][0]['anchor_error_m']-expected['contacts'][0]['anchor_error_m'])<1e-9


@pytest.mark.parametrize('height',[0.,.4,1.])
def test_extreme_normalized_trials_obey_serialized_source_relative_limits(problem,height):
    initial,scale=coordinates(problem)
    z=np.full(len(initial),1e4);z[::2]*=-1;z[-1]=height
    physical=physical_parameters(problem.t(z*scale),problem.limits).numpy()
    assert np.all(np.linalg.norm(physical[:-1].reshape(-1,3),axis=1)<=problem.limits)
    audit,_=problem.independent(physical)
    assert audit['bounds_passed']
    assert audit['root_lift_m']==pytest.approx(height*problem.config['max_root_lift_m'])
    assert not audit['pose_witness_passed']
