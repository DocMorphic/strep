import numpy as np
import pytest
from threadpoolctl import threadpool_limits
from test_rig_coupled_pose import setup
from rig_pose_tolerances import PoseTolerances


def test_independent_target_distance_and_rotation_derivatives():
    f,c=setup();t=PoseTolerances(c);rng=np.random.default_rng(1042)
    controls=rng.normal(size=np.prod(c.shape))*.0007
    residual,jac=t.pair(controls)
    for index,goal in enumerate(f.goals):
        world=f.pose(goal['frame'],c.parameters(controls)[goal['frame']])[0][goal['node']]
        distance=np.linalg.norm(world[:3,3]-goal['position_m'])
        from scipy.spatial.transform import Rotation
        angle=Rotation.from_matrix(np.linalg.solve(goal['rotation_matrix'],world[:3,:3])).magnitude()
        assert residual[2*index]==pytest.approx(1-(distance/.005)**2,abs=1e-9)
        # Source GLB matrices have tiny floating-point orthogonality error.
        assert residual[2*index+1]==pytest.approx(1-(1-np.cos(angle))/(1-np.cos(np.radians(5))),abs=2e-5)
    for _ in range(8):
        direction=rng.normal(size=len(controls));direction/=np.linalg.norm(direction);step=1e-7
        np.testing.assert_allclose(jac@direction,(t.pair(controls+step*direction)[0]-t.pair(controls-step*direction)[0])/(2*step),atol=2e-5,rtol=2e-5)


def test_feasibility_stage_meets_both_targets_and_preserves_motion_limits(tmp_path):
    f,c=setup();t=PoseTolerances(c);before=f.world.copy()
    with threadpool_limits(limits=1):values,trace,result=t.solve(tmp_path,max_iterations=40)
    assert result['targets_reached'],result
    assert result['result']=='target_tolerances_met'
    assert not result['quality_approved'] and not result['infeasibility_proven']
    assert np.array_equal(f.world[[0,-1]],before[[0,-1]])
    for frame,x in enumerate(values):assert f.constraints(frame,x)[0].min()>=-1e-7
    assert np.all(np.abs(values)<=f.envelope[:,None]*f.bounds+1e-9)
    assert all(m['position_error_m']<=.005 and m['orientation_error_degrees']<=5 for m in result['target_metrics'])


def test_unmet_target_is_retained_as_failure_without_infeasibility_claim(tmp_path):
    f,c=setup();f.goals[0]['position_m']+=np.array([3,0,0]);t=PoseTolerances(c)
    with threadpool_limits(limits=1):values,_,result=t.solve(tmp_path,max_iterations=15)
    assert not result['targets_reached'] and result['result']=='target_tolerances_not_met'
    assert not result['infeasibility_proven'] and not result['quality_approved']
    for frame,x in enumerate(values):assert f.constraints(frame,x)[0].min()>=-1e-7
    assert np.all(np.abs(values)<=f.envelope[:,None]*f.bounds+1e-9)


@pytest.mark.parametrize('settings',[dict(position_m=True),dict(position_m=0),dict(position_m=float('nan')),dict(orientation_degrees=0),dict(orientation_degrees=180)])
def test_invalid_tolerances_rejected(settings):
    _,c=setup()
    with pytest.raises(ValueError):PoseTolerances(c,**settings)
