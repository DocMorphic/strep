import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import pytest
from test_paired_hand_fit import setup
from paired_hand_fit import PairFitter
from paired_hand_clearance import SkinPoints,SurfaceObjective,refine


def test_selected_surface_jacobians_and_both_actor_collision_derivatives():
    actors,_=setup();fitter=PairFitter(*actors,event=75)
    x=np.random.default_rng(181).normal(size=24)*.02
    ids=np.array([14712,1427,1428])
    for actor,v in zip(actors,[x[:12],x[12:]]):
        points,jac=SkinPoints(actor).evaluate(75,v,ids)
        expected=actor.rig.vertices(actor.pose(75,v))[ids]@actor.rotation.T+actor.translation
        np.testing.assert_allclose(points,expected,atol=1e-10)
        assert np.isfinite(jac).all()
    records=[dict(source=a,target=b,points=[(14712,[1427,1428,14712],[.2,.3,.5],[0.,1.,0.]),
        (1427,[14712,1427,1428],[.1,.6,.3],[1.,0.,0.])]) for a,b in [(0,1),(1,0)]]
    objective=SurfaceObjective(fitter,records,margin=2.)
    residual,jac=objective.pair(x)
    assert len(residual)==len(x)+9+4
    assert np.linalg.norm(jac[-4:,:12])>0 and np.linalg.norm(jac[-4:,12:])>0
    for col in range(len(x)):
        delta=np.eye(len(x))[col]*1e-7
        numeric=(objective.pair(x+delta)[0]-objective.pair(x-delta)[0])/2e-7
        np.testing.assert_allclose(jac[:,col],numeric,atol=3e-5,rtol=2e-4)


def test_reject_initial_pose_outside_existing_edit_budget():
    actors,_=setup();fitter=PairFitter(*actors,event=75)
    with pytest.raises(ValueError,match='Invalid initial'):
        refine(fitter,fitter.bounds*2,np.zeros((0,3),dtype=int))
