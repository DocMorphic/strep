import copy
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from bounded_path_trajectory import BoundedPathFitter
from finish_bounded_surface_path import validate_control_protocol
import refined_partner_basis as refined


@pytest.fixture
def problem(monkeypatch):
    import paired_hand_trajectory as temporal
    cls=temporal.TrajectoryActor
    def without_skin(a,m):
        wrapped=object.__new__(cls);wrapped.base=a;wrapped.matrix=m;wrapped.dim=m.shape[1]*a.dim;return wrapped
    monkeypatch.setattr(temporal,'TrajectoryActor',without_skin)
    monkeypatch.setattr(refined,'UniqueBoundedPathFitter',BoundedPathFitter)
    actor=lambda:SimpleNamespace(local=np.zeros((150,1,4,4)),dim=12,limits=np.radians([15.,25.,35.,30.]))
    fitter=BoundedPathFitter([actor(),actor()])
    return fitter,np.random.default_rng(92).normal(size=120)*.025


def test_nested_knots_preserve_entire_motion_event_and_norm_bounds(problem):
    f,x=problem;g,y,proof=refined.refine(f,x,[50,60,62.5,65,67.5,70,75,80,87.5,100])
    np.testing.assert_allclose(f.values(x),g.values(y),atol=2e-17)
    assert np.array_equal(f.values(x)[75],g.values(y)[75])
    assert g.step_pair(y)[0].min()>=0
    assert proof['refined_control_count']==240
    assert np.array_equal(g.values(y)[:46],np.zeros((46,24)))


@pytest.mark.parametrize('knots',[[50,65,75,100],[49,50,62.5,75,87.5,100],[50,62.5,75,75,87.5,100],[50,62.5,float('nan'),75,87.5,100]])
def test_refinement_cannot_remove_old_knots_change_extent_or_duplicate(problem,knots):
    with pytest.raises(ValueError):refined.refine(*problem,knots)


@pytest.mark.parametrize('extra',[[],[65,67.5,70,72.5,77.5,80,82.5,85]])
def test_export_protocol_validates_coarse_and_refined_clock(problem,extra):
    f,x=problem;knots=sorted(set(f.knots+extra));g,y,_=refined.refine(f,x,knots)
    recipe=dict(knots=knots,joint_edit_degrees=[15,25,35,30])
    data=dict(controls=y.tolist(),basis=g.matrix.tolist(),control_bounds=g.bounds.tolist(),control_radii=g.control_radii.tolist(),trajectory_values=g.values(y).tolist())
    validate_control_protocol(recipe,data,data)
    forged=copy.deepcopy(data);forged['basis'][65][0]+=.00001
    with pytest.raises(ValueError,match='declared knots'):validate_control_protocol(recipe,forged,forged)
    forged=copy.deepcopy(data);forged['trajectory_values'][65][0]+=.00001
    with pytest.raises(ValueError,match='differs from controls'):validate_control_protocol(recipe,forged,forged)


def test_added_timing_can_resolve_opposing_planes_without_changing_event_or_limits():
    from paired_hand_fit import envelope
    from paired_hand_trajectory import basis
    from frame_guarded_partner_step import solve
    peaks=[]
    for knots in ([50,75,100],[50,65,70,75,100]):
        b=basis(envelope(150,75,30),knots);m=np.kron(b,np.eye(3));dim=m.shape[1]
        jac=np.stack([m[65*3],-m[70*3]])
        candidate,report=solve(np.zeros(dim),[-.02,-.02],jac,[.02,.02],np.repeat(b[75]!=0,3),
            np.full(len(knots),.3),np.diff(m.reshape(150,3,dim),axis=0).reshape(-1,dim),.02)
        assert candidate is not None
        assert np.array_equal(m[75*3:76*3]@candidate,np.zeros(3))
        assert report['per_frame_cap_excess_m']<=1e-8
        assert report['edit_step_max_radians']<=np.radians(5)+1e-8
        peaks.append(report['predicted_peak_m'])
    assert peaks[0]==pytest.approx(.02,abs=1e-8)
    assert peaks[1]<.01


@pytest.mark.parametrize('knots',[[50,62.5,75,87.5,100],
                                 [50,62.5,65,67.5,70,72.5,75,77.5,80,82.5,85,87.5,100]])
def test_completed_warm_start_restores_exact_saved_controls(problem,knots):
    from refined_partner_start import restore
    f,x=problem;g,y,_=refined.refine(f,x,knots)
    # Saved optimized controls differ from the original nested initialization.
    y=y.copy();y[12:15]+=[.005,-.002,.001]
    original_recipe=dict(knots=f.knots,joint_edit_degrees=[15,25,35,30],source='fixed')
    declared={**original_recipe,'knots':knots}
    data=dict(controls=y.tolist(),basis=g.matrix.tolist(),control_bounds=g.bounds.tolist(),
              control_radii=g.control_radii.tolist(),trajectory_values=g.values(y).tolist())
    restored,controls=restore(f,x,original_recipe,data,data,declared)
    assert np.array_equal(controls,y)
    assert np.array_equal(restored.values(controls),g.values(y))
    assert not np.shares_memory(controls,y)
    for changed in [{**declared,'source':'different'}, {**declared,'joint_edit_degrees':[16,25,35,30]}]:
        with pytest.raises(ValueError,match='physical protocol'):
            restore(f,x,original_recipe,data,data,changed)
    forged=copy.deepcopy(data);forged['controls']=x.tolist()
    if len(x)!=len(y):
        with pytest.raises(ValueError,match='dimensions'):
            restore(f,x,original_recipe,forged,forged,declared)
