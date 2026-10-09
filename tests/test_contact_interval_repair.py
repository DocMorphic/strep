"""Exact saved origins, whole-interval retention and immutable study lifecycle."""
import sys
from pathlib import Path
from contextlib import nullcontext,contextmanager
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import repair_contact_interval as module


def source():
    return dict(posed_joints=np.zeros((6,77,3),dtype=np.float32),root_positions=np.zeros((6,3),dtype=np.float32),
        local_rot_mats=np.tile(np.eye(3,dtype=np.float32),(6,77,1,1)),global_rot_mats=np.tile(np.eye(3,dtype=np.float32),(6,77,1,1)),
        foot_contacts=np.ones((6,6),dtype=bool))


class Window:
    frames=[2,3];seed=np.array([.113,.117]);scale=np.array([.3,.7])
    def __init__(self):self.constructed=0
    def controls(self,x):
        x=np.asarray(x,dtype=float)
        if x.shape!=(2,) or not np.isfinite(x).all():raise ValueError('Complete finite controls required')
        return x
    def independent(self,x):
        self.constructed+=1
        motion={k:v[self.frames].copy() for k,v in source().items()}
        # Reconstruction differs from the original saved geometry even at seed.
        motion['posed_joints'][:,0,0]=np.asarray(x)-self.seed+.01
        return {},motion
    def saved_representation(self,x,*,motion):return motion['posed_joints'][:,0,0].astype(float)-.02


def test_normalized_seed_roundtrip_keeps_exact_original_saved_geometry():
    w=Window();original=source();origin=module.ExactSavedOrigin(w,original)
    assert not np.array_equal(origin.normalized_seed*w.scale,w.seed)
    controls=origin.controls(origin.normalized_seed.copy())
    np.testing.assert_array_equal(controls,w.seed)
    saved=origin.motion(controls)
    assert set(saved)==set(module.POSE_TRACKS) and w.constructed==0
    for key in saved:np.testing.assert_array_equal(saved[key],original[key][w.frames])
    np.testing.assert_array_equal(origin.rows(controls),[-.02,-.02])
    saved['posed_joints'][:]=10;original['posed_joints'][:]=20
    assert not origin.motion(controls)['posed_joints'].any()


def test_new_proposal_is_constructed_without_rebasing_original_saved_origin():
    w=Window();origin=module.ExactSavedOrigin(w,source());candidate=origin.controls(origin.normalized_seed+.01)
    motion=origin.motion(candidate)
    assert w.constructed==1 and set(motion)==set(module.POSE_TRACKS)
    np.testing.assert_allclose(motion['posed_joints'][:,0,0],[.013,.017],rtol=1e-6)
    np.testing.assert_array_equal(origin.rows(origin.seed),[-.02,-.02])


def test_fit_without_improvement_retains_exact_source_at_final_observation():
    w=Window();origin=module.ExactSavedOrigin(w,source());observations=[]
    def observer(label,candidate,slacks,retained):
        observations.append((label,origin.motion(origin.controls(candidate))))
    value,report=module.fit(lambda x:-np.ones(2),lambda x:(-np.ones(2),np.zeros((2,2))),
        origin.normalized_seed,np.zeros(2),np.ones(2),iterations=1,trust=.1,seconds=5,
        observer=observer,representation_measure=lambda x:origin.rows(origin.controls(x)))
    np.testing.assert_array_equal(value,origin.normalized_seed)
    np.testing.assert_array_equal(report['initial_represented_slacks'],origin.initial_rows)
    np.testing.assert_array_equal(report['final_represented_slacks'],origin.initial_rows)
    assert observations[-1][0]=='final' and not observations[-1][1]['posed_joints'].any()


def test_saved_audit_uses_actual_internal_positions_and_fixed_current_neighbors():
    w=Window();original=source();original['posed_joints'][2,:,0]=.01;original['posed_joints'][3,:,0]=.02
    captured=[]
    def audit(motion,*,neighbors):
        captured.append((motion['posed_joints'].copy(),{f:np.array(v) for f,v in neighbors.items()}))
        return dict(pose_checks_passed=False)
    w.problems=[SimpleNamespace(frame=f,t=lambda x:x,neighbors={f-1:np.full((77,3),-.5),f+1:np.full((77,3),.5)},audit_motion=audit) for f in w.frames]
    origin=module.ExactSavedOrigin(w,original);report=origin.audit(origin.seed)
    np.testing.assert_array_equal(captured[0][1][3],original['posed_joints'][3])
    np.testing.assert_array_equal(captured[1][1][2],original['posed_joints'][2])
    assert np.all(captured[0][1][1]==-.5) and np.all(captured[1][1][4]==.5)
    assert not report['window_checks_passed'] and w.constructed==0


@pytest.mark.parametrize('after,accepted,preserved',[
    ([-.5,0,.5],True,True),([-1,0,.5],False,True),([-.5,-1e-12,.5],False,False),
    ([-1.000000000001,.5,.5],False,False),([0,0,.5],True,True)])
def test_whole_interval_rejects_boundary_loss_and_failed_row_regression(after,accepted,preserved):
    labels=['object:frame-2','all-reference-speed:2:J0:frame-1','floor:frame-3']
    decision,rows=module.compare_interval(labels,[-1,0,.5],labels,after)
    assert decision['update_retained']==accepted and decision['source_rows_preserved']==preserved
    assert not decision['quality_approved'] and not decision['release_approved']
    assert bool(rows['source_passing_lost'] or rows['protected_source_regressed'])==(not preserved)


def test_interval_row_population_cannot_change_between_original_and_proposed():
    with pytest.raises(ValueError):module.compare_interval(['floor:frame-1'],[-1],['floor:frame-2'],[0])


@pytest.mark.parametrize('options',[
    dict(frames=[]),dict(frames=[1]),dict(frames=[1,3]),dict(width=6),dict(width=True),
    dict(iterations=True),dict(iterations=0),dict(iterations=101),dict(solve_iterations=0),dict(solve_iterations=301),
    dict(trust=float('nan')),dict(trust=.31),dict(trust=True),dict(seconds=0),dict(seconds=1801),dict(seconds=True),
    dict(resume=False),dict(resume='')])
def test_invalid_repair_never_acquires_worker(tmp_path,monkeypatch,options):
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'worker_lock',lambda:pytest.fail('Invalid repair acquired worker'))
    args=dict(frames=[1,2]);args.update(options)
    with pytest.raises(ValueError):module.run(tmp_path/'source',tmp_path/'out',**args)
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('output',['source','source/new','outside'])
def test_original_source_and_output_stay_separate(tmp_path,monkeypatch,output):
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'worker_lock',lambda:pytest.fail('Overlapping repair acquired worker'))
    path=tmp_path.parent/'outside' if output=='outside' else tmp_path/output
    with pytest.raises(ValueError):module.run(tmp_path/'source',path,[1,2])


def test_lock_covers_native_and_full_interval_lifecycle(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path);active=[]
    @contextmanager
    def lock():
        active.append(True)
        try:yield
        finally:active.pop()
    def run(study,output,frames,*budgets):
        assert active and budgets==(3,8,.03,300,10,None,[])
        return 'whole-interval-checked'
    monkeypatch.setattr(module,'worker_lock',lock);monkeypatch.setattr(module,'threadpool_limits',lambda **k:nullcontext())
    monkeypatch.setattr(module,'_run',run)
    assert module.run(tmp_path/'source',tmp_path/'out',[1,2])=='whole-interval-checked'
    assert not active


def test_failed_study_preserved_and_existing_output_rejected_before_lock(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'worker_lock',nullcontext)
    monkeypatch.setattr(module,'threadpool_limits',lambda **k:nullcontext())
    def fail(study,output,*args):output.mkdir();raise ValueError('Global saved rows failed')
    monkeypatch.setattr(module,'_run',fail);output=tmp_path/'out'
    with pytest.raises(ValueError):module.run(tmp_path/'source',output,[1,2])
    before=(output/'pipeline.json').read_bytes()
    assert module.read(output/'pipeline.json')['status']=='failed'
    monkeypatch.setattr(module,'worker_lock',lambda:pytest.fail('Existing output acquired worker'))
    with pytest.raises(FileExistsError):module.run(tmp_path/'source',output,[1,2])
    assert (output/'pipeline.json').read_bytes()==before


@pytest.mark.parametrize('output,resume',[('parent/new','parent'),('parent','parent/new')])
def test_interval_predecessor_cannot_overlap_output(tmp_path,monkeypatch,output,resume):
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'worker_lock',lambda:pytest.fail('Overlapping resume acquired worker'))
    with pytest.raises(ValueError):module.run(tmp_path/'source',tmp_path/output,[1,2],resume=tmp_path/resume)


def test_bound_interval_is_forwarded_inside_worker_lock(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'worker_lock',nullcontext)
    monkeypatch.setattr(module,'threadpool_limits',lambda **k:nullcontext())
    def run(*args):
        assert args[-2]==tmp_path/'parent' and args[-1]==[]
        return 'bound-interval'
    monkeypatch.setattr(module,'_run',run)
    assert module.run(tmp_path/'source',tmp_path/'out',[1,2],resume=tmp_path/'parent')=='bound-interval'
