import numpy as np
import pytest
from threadpoolctl import threadpool_limits
from test_rig_coupled_pose import setup
from rig_coupled_pose import CoupledPoseFitter,window_basis
from rig_pose_tolerances import PoseTolerances
from rig_target_refinement import TargetPreservingRefiner


def reached(tmp_path):
    f,c=setup()
    with threadpool_limits(limits=1):_,_,summary=PoseTolerances(c).solve(tmp_path,max_iterations=40)
    assert summary['targets_reached']
    c=CoupledPoseFitter(f,window_basis(f.envelope,2))
    return f,TargetPreservingRefiner(c)


def test_unreached_input_is_rejected():
    _,c=setup()
    with pytest.raises(ValueError,match='already meeting'):TargetPreservingRefiner(c)


def test_full_surface_and_support_derivatives(tmp_path):
    f,refiner=reached(tmp_path);rng=np.random.default_rng(803)
    x=rng.normal(size=np.prod(refiner.coupled.shape))*.0003
    with threadpool_limits(limits=1):
        residual,jac=refiner.surface_pair(x)
        for _ in range(8):
            direction=rng.normal(size=len(x));direction/=np.linalg.norm(direction);step=1e-7
            np.testing.assert_allclose(jac@direction,(refiner.surface_pair(x+step*direction)[0]-refiner.surface_pair(x-step*direction)[0])/(2*step),atol=3e-4,rtol=3e-5)
        # Independent full skin heights must match the floor rows.
        parameters=refiner.coupled.parameters(x)
        for row,frame in enumerate(refiner.coupled.active):
            points=f.rig.vertices(f.pose(frame,parameters[frame])[0])
            assert residual[row]==pytest.approx((points[:,1].min()+refiner.floor_caps[frame])/.01,abs=1e-8)


def test_quality_improves_without_losing_targets_or_regressing_guards(tmp_path):
    f,refiner=reached(tmp_path);before=f.world.copy()
    with threadpool_limits(limits=1):values,records,result=refiner.solve(tmp_path,max_iterations=25)
    assert result['cost_after']<result['cost_before'],result
    assert all(row['within_tolerances'] for row in result['target_metrics'])
    assert np.array_equal(f.world[[0,-1]],before[[0,-1]])
    for frame,x in enumerate(values):assert f.constraints(frame,x)[0].min()>=-1e-7
    assert np.all(np.maximum(0,-f.positions[:,:,1].min(axis=1))<=refiner.floor_caps+1e-9)
    for support,caps in zip(f.supports,refiner.support_caps):
        track=f.positions[support['start_frame']:support['end_frame_exclusive']][:,support['vertices']].mean(axis=1)
        assert np.all(np.linalg.norm(track-support['target_position_m'],axis=1)<=caps['position']+1e-8)
        assert np.all(np.linalg.norm(np.diff(track,axis=0),axis=1)<=caps['edge']+1e-8)
    assert not result['quality_approved']
