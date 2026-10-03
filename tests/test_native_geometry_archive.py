"""Complete geometry transport preserves queries, failures and array lifetimes."""
import copy
import gc
from pathlib import Path
import sys
import weakref
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
import native_scene_geometry as geometry
from native_observation_archive import ObservationArchive, verify
from native_scene_contacts import SceneContacts
from strep import read, save, sha256
from test_native_scene_geometry import closed_fixture, policy


def scene_fixture(tmp_path, fault=None, mode='explicit'):
    _, path, spec = closed_fixture(tmp_path)
    spec['actors']['B'] = copy.deepcopy(spec['actors']['A'])
    spec['actors']['B']['placement']['translation_m'] = [5., 0., 0.]
    spec['objects'] = {
        'ball': dict(geometry=dict(schema='strep-object-geometry-v1', shape='sphere', radius_m=.1),
            keyframes=[dict(time_s=t, translation_m=[10.+t, 0., 0.], rotation_xyzw=[0,0,0,1]) for t in (0.,2.)]),
        'crate': dict(geometry=dict(schema='strep-object-geometry-v1', shape='box', size_m=[.2,.3,.4]),
            keyframes=[dict(time_s=0., translation_m=[-10.,0.,0.], rotation_xyzw=[0,0,0,1])])}
    planes = dict(floor=dict(normal_world=[0.,1.,0.], offset_m=-2.))
    if fault == 'partner': spec['actors']['B']['placement']['translation_m'] = [.2,0.,0.]
    if fault == 'plane': planes['wall'] = dict(normal_world=[1.,0.,0.], offset_m=.3)
    if fault == 'containment':
        actor = SceneContacts(spec, tmp_path).actors['A']
        center = actor['rig'].vertices(actor['sampler'].sample(1.)).mean(0)
        spec['objects']['ball']['keyframes'] = [dict(time_s=0., translation_m=center.tolist(), rotation_xyzw=[0,0,0,1])]
    save(path, spec)
    return path, SceneContacts(spec, tmp_path), policy(path, mode=mode, planes=planes)


@pytest.mark.parametrize('fault', [None, 'partner', 'plane', 'containment'])
def test_dense_and_streamed_reports_and_every_array_are_exact(tmp_path, fault):
    path, scene, p = scene_fixture(tmp_path, fault)
    before = {name:sha256(name) for name in [str(path), *scene.inputs]}
    dense, arrays = geometry.evaluate(scene, p, sha256(path))
    progress = []
    archive = tmp_path/'observations.npz'
    streamed, bindings = geometry.evaluate_to_archive(scene, p, sha256(path), archive, progress.append)
    assert streamed == dense
    assert dense['sampled_conditions_pass'] is (fault is None)
    assert len(progress) == len(dense['times_s'])
    assert bindings == dict(observations_sha256=sha256(archive),
        observation_receipt_sha256=sha256(Path(str(archive)+'.receipt.json')))
    with np.load(archive, allow_pickle=False) as saved:
        assert saved.files == list(arrays)
        for name, value in arrays.items():
            actual = saved[name]
            assert actual.dtype.str == value.dtype.str and actual.shape == value.shape
            assert actual.tobytes(order='C') == value.tobytes(order='C')
    assert verify(archive)['arrays'] == len(arrays)
    assert before == {name:sha256(name) for name in before}
    assert all(len(s['actor_objects']) == 4 and len(s['actor_pairs']) == 1
        and len(s['world_planes']) == (4 if fault=='plane' else 2) for s in streamed['samples'])


def test_observed_callbacks_preserve_complete_expanded_clock(tmp_path):
    path, scene, p = scene_fixture(tmp_path, mode='native-and-frame-populations')
    # A short explicit policy here still expands to every native/frame time.
    # Actual callback observations are preserved rather than replaced by sources.
    def vertices(name, time):
        actor = scene.actors[name]; position, rotation = actor['placement']
        return actor['rig'].vertices(actor['sampler'].sample(time)) @ rotation.T + position + [.013,0.,0.]
    def objects(name, times):
        positions, rotations = scene.object_poses(name, times)
        return positions + [.07,0.,0.], rotations
    callbacks = dict(actor_vertices=vertices, object_poses=objects)
    dense, arrays = geometry.evaluate(scene, p, sha256(path), **callbacks)
    archive = tmp_path/'expanded.npz'
    streamed, _ = geometry.evaluate_to_archive(scene, p, sha256(path), archive, **callbacks)
    assert streamed == dense and len(streamed['times_s']) > 3
    with np.load(archive, allow_pickle=False) as saved:
        assert saved.files == list(arrays)
        for name, value in arrays.items(): assert saved[name].tobytes() == value.tobytes()


def test_geometry_releases_previous_frames_without_changing_query_population(tmp_path, monkeypatch):
    path, scene, p = scene_fixture(tmp_path)
    refs = []
    class TrackedArchive(ObservationArchive):
        def __setitem__(self, name, value):
            super().__setitem__(name, value)
            if name.startswith('frame_'): refs.append((int(name.split('_')[1]), weakref.ref(value)))
    monkeypatch.setattr(geometry, 'ObservationArchive', TrackedArchive)
    def progress(row):
        gc.collect()
        assert all(ref() is None for frame, ref in refs if frame < row['completed_samples']-1)
    report, _ = geometry.evaluate_to_archive(scene, p, sha256(path), tmp_path/'released.npz', progress)
    assert len(refs) == 3*4*len(report['times_s'])
    gc.collect(); assert all(ref() is None for _, ref in refs)


def test_whole_array_budget_failure_retains_prior_complete_arrays(tmp_path):
    path, scene, p = scene_fixture(tmp_path)
    archive = tmp_path/'budget.npz'
    with pytest.raises(ValueError, match='per-array budget'):
        geometry.evaluate_to_archive(scene, p, sha256(path), archive, maximum_array_bytes=256)
    assert not archive.exists()
    failed = read(Path(str(archive)+'.partial.receipt.json'))
    assert failed['status'] == 'failed' and len(failed['completed_arrays']) == 3
    assert not failed['quality_approved'] and not failed['release_approved']
    with np.load(Path(str(archive)+'.partial'), allow_pickle=False) as saved:
        assert saved.files == ['times_s', 'frame_0_A_ball_depth_lower_m', 'frame_0_A_ball_depth_upper_m']
        assert saved[saved.files[1]].shape == (12,)


def test_query_execution_failure_retains_partial_and_failed_pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(action_worker_lock, 'ROOT', tmp_path/'fixture-lock')
    path, scene, p = scene_fixture(tmp_path); pp = tmp_path/'policy.json'; save(pp, p)
    original = geometry.query; calls = []
    def fail_after_one_frame(*args, **kwargs):
        calls.append(1)
        if len(calls) == 5: raise ValueError('fixture query execution failure')
        return original(*args, **kwargs)
    monkeypatch.setattr(geometry, 'query', fail_after_one_frame)
    out = tmp_path/'failed'
    with pytest.raises(ValueError, match='query execution failure'): geometry.run(path, pp, out)
    assert read(out/'pipeline.json')['status'] == 'failed' and not (out/'result.json').exists()
    failed = read(out/'observations.npz.partial.receipt.json')
    assert len(failed['completed_arrays']) == 13 and not (out/'observations.npz').exists()
    assert sha256(out/'observations.npz.partial') == failed['archive_sha256']
    assert sha256(path) == p['contacts_sha256']


@pytest.mark.parametrize('filename', ['geometry.json', 'geometry-observations.npz', 'geometry-observations.npz.receipt.json'])
def test_actor_geometry_transport_is_bound_before_combination(tmp_path, monkeypatch, filename):
    from test_native_object_scene_engine import producers
    from native_object_scene_engine import load
    args = producers(tmp_path, monkeypatch)
    actors = args[2]; target = actors/filename
    target.write_bytes(target.read_bytes()+b'\n')
    with pytest.raises(ValueError, match='Actor geometry'): load(*args)


def test_combined_replay_checks_transport_scope_even_with_updated_bindings(tmp_path, monkeypatch):
    from test_verify_native_object_scene_engine import bundle
    from verify_native_object_scene_engine import run
    args = bundle(tmp_path, monkeypatch); combined = args[-1]
    receipt_path = combined/'geometry-observations.npz.receipt.json'
    receipt = read(receipt_path); receipt['geometry_verified'] = True; save(receipt_path, receipt)
    report = read(combined/'geometry.json'); report['observation_receipt_sha256'] = sha256(receipt_path)
    save(combined/'geometry.json', report)
    result = read(combined/'result.json')
    result['files_sha256'].update({name:sha256(combined/name) for name in ('geometry.json',receipt_path.name)})
    save(combined/'result.json', result)
    with pytest.raises(ValueError, match='transport only'): run(*args, tmp_path/'verification')
    assert read(tmp_path/'verification/pipeline.json')['status'] == 'failed'


@pytest.mark.parametrize('producer', ['actors', 'objects'])
def test_changed_executed_binary_clock_helpers_cannot_be_composed(tmp_path, monkeypatch, producer):
    from test_native_object_scene_engine import producers
    from native_object_scene_engine import load
    args = producers(tmp_path, monkeypatch)
    folder = args[2] if producer=='actors' else args[3]
    target = folder/'project/native_engine_clock.gd'
    target.write_bytes(target.read_bytes()+b'\n')
    with pytest.raises(ValueError, match='Executed .* script changed'): load(*args)
