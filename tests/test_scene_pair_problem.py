import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_pair_problem import MotionRows, ScenePairProblem, load_actors
from timed_rotation_edit import TimedRotationEdit
from paired_approach_basis import BoundSkin
from test_timed_rotation_edit import fixture
from strep import read,save,sha256,ROOT


def actors():
    result = []
    for index, names in enumerate([['Arm'], ['Arm', 'Twin']]):
        doc, binary = fixture()
        model = TimedRotationEdit(doc, binary, names, np.arange(181)/120, [.1, 1.3], [[.7, .7]])
        rig = SimpleNamespace(joints=[0, 1, 2, 3], inverse=np.tile(np.eye(4), (4, 1, 1)), primitives=[dict(
            positions=np.array([[.1, .2, 0], [0, .2, .1], [.2, .1, .1]]),
            joints=np.array([[2], [2], [3]]), weights=np.ones((3, 1)))])
        rotation = np.diag([-1., 1., -1.]) if index else np.eye(3); shift = np.array([index*.05, 0., 0.])
        result.append(dict(name=str(index), model=model, rig=rig, skin=BoundSkin(rig), rotation=rotation, translation=shift,
                           rates=MotionRows(model, rig.joints, rotation, shift)))
    return result


def samples(pair):
    return [dict(sample=i, time_s=float(t), directions=[dict(source=s, target=1-s, maximum_depth_m=.02, records=[
        dict(vertex=0, target_vertices=[0, 1, 2], barycentric=[.2, .3, .5], normal=[1., 0., 0.])]) for s in [0, 1]])
        for i, t in enumerate(pair[0]['model'].times)]


def test_scene_coupling_handles_unequal_control_counts_and_both_directions():
    pair = actors(); problem = ScenePairProblem(pair, samples(pair)); zero = np.zeros(problem.size)
    linear = problem.linearize(zero); direction = np.random.default_rng(14).normal(size=problem.size)*1e-6
    moved = problem.surface_rows([a['model'].world(p) for a, p in zip(pair, problem.split(direction))])
    np.testing.assert_allclose(moved['gaps'], linear['gaps']+linear['gap_jacobian']@direction, atol=1e-10, rtol=0)
    np.testing.assert_allclose(moved['surface_vectors'], linear['surface_vectors']+np.einsum('nid,d->ni', linear['surface_jacobians'], direction), atol=1e-10, rtol=0)
    assert problem.sizes == [9, 18]
    count = len(pair[0]['model'].times)
    assert all(np.linalg.norm(linear['gap_jacobian'][block, columns]) > 0 for block in [slice(0, count), slice(count, None)] for columns in [slice(0, 9), slice(9, None)])
    assert np.all(np.linalg.norm(linear['vectors'], axis=1) <= linear['radii']+1e-10)


def test_motion_rows_cover_every_changed_stencil_and_leave_unaffected_joints_out():
    actor = actors()[0]; model = actor['model']; policy = actor['rates']
    controls = np.arange(model.size)*.001
    before = policy.positions(model.source_world); after = policy.positions(model.world(controls))
    for order, rows, cols, caps in policy.specs:
        changed = np.linalg.norm(np.diff(after-before, n=order, axis=0), axis=2) > 1e-12
        covered = np.zeros(changed.shape, bool); covered[rows, cols] = True
        assert np.all(~changed | covered)
        assert set(cols) == {2}  # Arm rotation moves its child, not the Arm's own origin.
        baseline = np.linalg.norm(np.diff(before, n=order, axis=0)/policy.dt**order, axis=2)
        assert np.all(baseline[rows, cols] <= caps+1e-12)


def test_motion_jacobians_use_seconds_and_authored_placements():
    actor = actors()[1]; model = actor['model']; policy = actor['rates']
    zero = np.zeros(model.size); world, jac = model.world_pair(zero); base, derivative = policy.values(world, jac)
    direction = np.random.default_rng(19).normal(size=model.size)*1e-7
    actual, _ = policy.values(model.world(direction))
    np.testing.assert_allclose(actual, base+np.einsum('nid,d->ni', derivative, direction), atol=1e-8, rtol=0)
    assert policy.dt == pytest.approx(1/120)


def test_incomplete_or_wrong_time_witnesses_are_rejected():
    pair = actors(); rows = samples(pair)
    with pytest.raises(ValueError, match='Complete ordered'):
        ScenePairProblem(pair, rows[:-1])
    rows[3]['time_s'] += .001
    with pytest.raises(ValueError, match='time mismatch'):
        ScenePairProblem(pair, rows)


def test_saved_request_uses_snapshots_or_rejects_version_mismatch():
    folder = Path(__file__).resolve().parents[1]/'reports/paired-edit-jobs/curve-controls-trimmed-v1'
    if not folder.exists(): pytest.skip('Local immutable request required')
    request=read(folder/'request.json')
    for name,digest in request['implementation'].items():
        assert sha256(folder/'implementation'/name)==digest
        if sha256(ROOT/'scripts'/name)!=digest:
            with pytest.raises(ValueError,match='Prepared edit implementation changed: '+name):load_actors(folder)
            return
    record, pair = load_actors(folder)
    assert [a['name'] for a in pair] == ['A', 'B']
    assert all(a['source'].is_relative_to(folder) for a in pair)
    assert len(pair[0]['rates'].radii) > 0
    assert pair[0]['model'].protected[0, 0] == pytest.approx(2.0917225950783)


@pytest.mark.parametrize('changed',['archive','current'])
def test_changed_implementation_is_rejected_before_loading_actor_payloads(tmp_path,monkeypatch,changed):
    import scene_pair_problem as module
    root=tmp_path/'project';(root/'scripts').mkdir(parents=True)
    folder=tmp_path/'request';(folder/'implementation').mkdir(parents=True)
    archived=folder/'implementation/adapter.py';current=root/'scripts/adapter.py'
    archived.write_text('saved implementation',encoding='utf-8');current.write_bytes(archived.read_bytes())
    save(folder/'request.json',dict(implementation={'adapter.py':sha256(archived)}))
    save(folder/'state.json',dict(status='prepared'))
    (archived if changed=='archive' else current).write_text('different implementation',encoding='utf-8')
    monkeypatch.setattr(module,'ROOT',root)
    with pytest.raises(ValueError,match='Prepared edit implementation changed: adapter.py'):load_actors(folder)
