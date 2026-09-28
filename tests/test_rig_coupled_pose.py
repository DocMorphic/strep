import numpy as np
import pytest
from threadpoolctl import threadpool_limits
from test_rig_pose_trajectory import make
from rig_pose_trajectory import PoseTrajectoryFitter
from rig_coupled_pose import CoupledPoseFitter,window_basis
from verify_trajectory_fit import energy


def setup():
    rig,w,local,spec,targets,s,goal=make()
    envelope=np.array([0,.7,1,.7,0])
    fitter=PoseTrajectoryFitter(rig,spec,local,targets,envelope,[s],[goal])
    return fitter,CoupledPoseFitter(fitter,window_basis(envelope,2))


def test_coupled_derivatives_against_independent_whole_trajectory_and_constraints():
    f,c=setup();reference_world=f.world.copy();reference_local=f.locals.copy()
    original_points=f.positions.copy();rng=np.random.default_rng(130)
    x=rng.normal(size=np.prod(c.shape))*.0003
    with threadpool_limits(limits=1):
        value,gradient=c.objective_pair(x);residual,jac=c.inequality_pair(x)
        def independent(v):
            c.synchronize(v)
            result=energy(f.world,f.positions,f.locals,reference_world,original_points,reference_local,
                f.spec,dict(targets_m={k:v.tolist() for k,v in f.targets.items()}),f.supports,f.settings)['total']
            for g in f.goals:
                transform=f.world[g['frame'],g['node']]
                result+=np.sum(((transform[:3,3]-g['position_m'])*g['position_weight'])**2)
                result+=np.sum(((transform[:3,:3]-g['rotation_matrix'])*g['rotation_weight'])**2)
            return result
        assert value==pytest.approx(independent(x),abs=1e-7)
        for _ in range(8):
            direction=rng.normal(size=len(x));direction/=np.linalg.norm(direction);step=1e-7
            numeric=(independent(x+step*direction)-independent(x-step*direction))/(2*step)
            assert gradient@direction==pytest.approx(numeric,rel=3e-5,abs=2e-5)
            np.testing.assert_allclose(jac@direction,
                (c.inequality_pair(x+step*direction)[0]-c.inequality_pair(x-step*direction)[0])/(2*step),rtol=3e-5,atol=2e-4)


def test_coordinated_solve_keeps_context_and_decreases_true_energy(tmp_path):
    f,c=setup();before=f.world.copy();goal=f.goals[0]
    initial_error=np.linalg.norm(before[goal['frame'],goal['node'],:3,3]-goal['position_m'])
    with threadpool_limits(limits=1):values,records,result=c.solve(tmp_path,max_iterations=15)
    assert result['cost_after']<result['cost_before']
    assert np.array_equal(f.world[[0,-1]],before[[0,-1]])
    assert np.all(np.abs(values)<=f.envelope[:,None]*f.bounds+1e-9)
    for frame,x in enumerate(values):assert f.constraints(frame,x)[0].min()>=-1e-7
    assert np.linalg.norm(f.world[goal['frame'],goal['node'],:3,3]-goal['position_m'])<initial_error
    # The correction must actually coordinate neighboring editable frames.
    assert np.linalg.norm(values[1])>0 and np.linalg.norm(values[3])>0


def test_controls_cannot_modify_fixed_context():
    f,_=setup();bad=window_basis(f.envelope);bad[0,0]=.1
    with pytest.raises(ValueError,match='fixed frames'):CoupledPoseFitter(f,bad)


@pytest.mark.parametrize('envelope',[[0,0,0],[0,1,0],[0,.5,float('nan'),1,0],[0,.5,1.1,.5,0]])
def test_invalid_or_too_short_window_rejected(envelope):
    with pytest.raises(ValueError):window_basis(envelope)
