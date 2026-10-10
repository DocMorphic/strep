"""Complete scene replay fixtures; mocked engine output is not Godot evidence."""
import copy
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import action_worker_lock
import native_scene_engine as producer
from native_scene_contacts import SceneContacts
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from strep import read, save, sha256
import verify_native_scene_engine as verifier
from verify_native_scene_engine import run
from test_native_scene_engine import mock_actor, serialized
from test_native_scene_geometry import closed_fixture, policy


def bundle(tmp_path, monkeypatch, mode='import', population='objects', bad_floor=False):
    monkeypatch.setattr(action_worker_lock, 'ROOT', tmp_path / 'fixture-lock')
    source, path, spec = closed_fixture(tmp_path)
    rig = RigAsset.load(source)
    sampler = NativeSupportSampler(rig.document, rig.binary, 0)
    spec['contacts'][0]['target'] = dict(
        space='world', points_m=[rig.vertices(sampler.sample(1.))[0].tolist()])
    if population in ('objects', 'partners-and-objects'):
        for name, distance in [('item', 5.), ('other', 8.)]:
            spec['objects'][name] = dict(
                geometry=dict(schema='strep-object-geometry-v1', shape='sphere', radius_m=.1),
                keyframes=[dict(time_s=0., translation_m=[distance, 0., 0.], rotation_xyzw=[0., 0., 0., 1.])])
        spec['contacts'][0]['target'] = dict(
            space='object', object='item', points_m=[[.1, 0., 0.]])
    if population == 'partners-and-objects':
        spec['actors']['B'] = copy.deepcopy(spec['actors']['A'])
        spec['actors']['B']['placement']['translation_m'] = [12., 0., 0.]
        partner = copy.deepcopy(spec['contacts'][0])
        partner['id'] = 'partner'
        partner['target'] = dict(space='actor', actor='B', vertices=[[6, 0, 0]], reduction='individual')
        spec['contacts'].append(partner)
    save(path, spec)
    pp = tmp_path / 'policy.json'
    save(pp, policy(path, planes=dict(ground=dict(
        normal_world=[0., 1., 0.], offset_m=3. if bad_floor else -2.))))
    scene = SceneContacts(spec, tmp_path)
    executable = tmp_path / 'fixture-engine'
    executable.write_bytes(b'mocked engine only')

    def execute(command, **kwargs):
        request = read(command[-2])
        cases = []
        for case in request['cases']:
            rig = RigAsset.load(case['path'])
            sampler = NativeSupportSampler(rig.document, rig.binary, case['animation_index'])
            row = mock_actor(rig, sampler, request['sample_times_s'], path=case['path'],
                             animation_index=case['animation_index'], reverse=True)
            row['id'] = case['id']
            cases.append(row)
            if 'animation_output' in case:
                Path(case['animation_output']).write_bytes(b'mocked native Animation resource')
        objects = []
        for name in scene.objects:
            positions, rotations = scene.object_poses(name, request['sample_times_s'])
            frames = []
            for time, position, rotation in zip(request['sample_times_s'], positions, rotations):
                matrix = np.eye(4)
                matrix[:3, :3], matrix[:3, 3] = rotation, position
                frames.append(dict(requested_time_s=time, matrix=serialized(matrix),
                                   rotation_xyzw=Rotation.from_matrix(rotation).as_quat().tolist()))
            objects.append(dict(id=name, frames=frames))
        save(command[-1], dict(engine=dict(string='fixture only'), cases=cases, objects=objects))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(producer.subprocess, 'run', execute)
    output = tmp_path / 'producer'
    producer.run(path, output, geometry_policy=pp, engine=executable, playback_mode=mode)
    return path, pp, output


@pytest.mark.parametrize('mode', ['import', 'native-authoring'])
@pytest.mark.parametrize('population', ['actors', 'objects', 'partners-and-objects'])
def test_complete_populations_replay_in_both_modes_without_rewriting_sources(tmp_path, monkeypatch, mode, population):
    path, pp, output = bundle(tmp_path, monkeypatch, mode, population)
    before = {p: sha256(p) for p in tmp_path.rglob('*') if p.is_file()}
    result = run(path, pp, output, tmp_path / 'replay')
    recorded = read(output / 'result.json')
    assert result['all_replayed_observations_exact'] and result['playback_mode'] == mode
    assert result['recorded_sampled_conditions_pass'] == recorded['all_sampled_conditions_pass']
    assert result['recorded_sampled_conditions_pass'] is (population == 'actors')
    assert not result['geometry_reductions']['geometry_queries_rerun']
    assert not result['quality_approved'] and not result['release_approved'] and not result['training_admitted']
    assert set(result['verifier_implementation_sha256']) == set(verifier.VERIFIER_METHODS)
    assert all(sha256(p) == digest for p, digest in before.items())
    with pytest.raises(ValueError, match='Fresh'):
        run(path, pp, output, tmp_path / 'replay')


def test_original_failed_geometry_remains_a_verified_failure(tmp_path, monkeypatch):
    path, pp, output = bundle(tmp_path, monkeypatch, bad_floor=True)
    assert not read(output / 'result.json')['imported_geometry_samples_pass']
    result = run(path, pp, output, tmp_path / 'replay')
    assert result['all_replayed_observations_exact']
    assert not result['recorded_sampled_conditions_pass'] and not result['geometry_reductions']['passed']


@pytest.mark.parametrize('fault', ['pending', 'source', 'clock', 'missing-object', 'object-clock',
    'skin-summary', 'object-summary', 'contact-summary', 'decision', 'extra-array',
    'skin-array', 'missing-resource', 'import-claims-authoring', 'method-population',
    'missing-asset-binding', 'case-outside-snapshot', 'native-payload', 'missing-script'])
def test_changed_or_resealed_incomplete_evidence_is_rejected(tmp_path, monkeypatch, fault):
    mode = 'native-authoring' if fault in ('missing-resource', 'native-payload') else 'import'
    path, pp, output = bundle(tmp_path, monkeypatch, mode)
    result = read(output / 'result.json')
    receipt = read(output / 'raw-engine-receipt.json')
    if fault == 'pending':
        save(output / 'pipeline.json', dict(status='processing'))
    elif fault == 'source':
        path.write_bytes(path.read_bytes() + b'\n')
    elif fault in ('clock', 'missing-object', 'object-clock'):
        raw = read(output / 'engine-output.json')
        if fault == 'clock': raw['cases'][0]['frames'].pop()
        elif fault == 'missing-object': raw['objects'].pop()
        else: raw['objects'][0]['frames'][0]['requested_time_s'] += .01
        save(output / 'engine-output.json', raw)
        result['engine_output_sha256'] = receipt['engine_output_sha256'] = sha256(output / 'engine-output.json')
    elif fault == 'skin-summary':
        result['skin_errors']['A']['maximum_engine_native_vertex_error_m'] += .01
    elif fault == 'object-summary':
        result['objects']['item']['maximum_position_error_m'] += .01
    elif fault == 'contact-summary':
        result['imported_contacts']['loaded_skin_weights_normalized'] = True
    elif fault == 'decision':
        result['all_sampled_conditions_pass'] = not result['all_sampled_conditions_pass']
    elif fault in ('extra-array', 'skin-array'):
        archive = output / 'native-observations.npz'
        with np.load(archive, allow_pickle=False) as stored:
            arrays = {name: stored[name] for name in stored.files}
        if fault == 'extra-array': arrays['unrequested'] = np.zeros(1)
        else: arrays['A_skin_errors_m'][0] += .01
        np.savez_compressed(archive, **arrays)
        result['native_observations_sha256'] = sha256(archive)
    elif fault == 'missing-resource':
        result['animation_resources_sha256'] = receipt['animation_resources_sha256'] = {}
    elif fault == 'import-claims-authoring':
        request = read(output / 'request.json')
        request['cases'][0]['native_payload'] = {}
        save(output / 'request.json', request)
        receipt['request_sha256'] = sha256(output / 'request.json')
    elif fault == 'method-population':
        result['implementation_sha256'].pop('native_scene_engine.py')
        request = read(output / 'request.json')
        request['implementation_sha256'] = result['implementation_sha256']
        save(output / 'request.json', request)
        receipt['request_sha256'] = sha256(output / 'request.json')
    elif fault == 'missing-asset-binding':
        source_path = str((path.parent / read(path)['actors']['A']['glb']).resolve())
        result['inputs_sha256'].pop(source_path)
        result['source_snapshots'].pop(source_path)
        request = read(output / 'request.json')
        request['inputs_sha256'] = result['inputs_sha256']
        save(output / 'request.json', request)
        receipt['request_sha256'] = sha256(output / 'request.json')
    elif fault == 'case-outside-snapshot':
        request = read(output / 'request.json')
        duplicate = tmp_path / 'same-asset.glb'
        duplicate.write_bytes(Path(request['cases'][0]['path']).read_bytes())
        request['cases'][0]['path'] = str(duplicate)
        raw = read(output / 'engine-output.json')
        raw['cases'][0]['path'] = str(duplicate)
        save(output / 'request.json', request)
        save(output / 'engine-output.json', raw)
        receipt['request_sha256'] = sha256(output / 'request.json')
        receipt['engine_output_sha256'] = result['engine_output_sha256'] = sha256(output / 'engine-output.json')
    elif fault == 'native-payload':
        request = read(output / 'request.json')
        request['cases'][0]['native_payload']['channels'].pop()
        save(output / 'request.json', request)
        receipt['request_sha256'] = sha256(output / 'request.json')
    elif fault == 'missing-script':
        receipt['executed_scripts_sha256'].pop('native_godot_tracks.gd')
    save(output / 'raw-engine-receipt.json', receipt)
    result['raw_engine_receipt_sha256'] = sha256(output / 'raw-engine-receipt.json')
    save(output / 'result.json', result)
    with pytest.raises((ValueError, KeyError)):
        run(path, pp, output, tmp_path / 'replay')


def test_verifier_dependency_change_is_rejected_without_editing_live_source(tmp_path, monkeypatch):
    path, pp, output = bundle(tmp_path, monkeypatch)
    dependency = verifier.ROOT / 'scripts/native_object_scene_engine.py'
    original = verifier.sha256
    observations = 0

    def changed_digest(target):
        nonlocal observations
        if Path(target).resolve() == dependency.resolve():
            observations += 1
            if observations > 1:
                return '0' * 64
        return original(target)

    monkeypatch.setattr(verifier, 'sha256', changed_digest)
    with pytest.raises(ValueError, match='Verifier dependency changed'):
        run(path, pp, output, tmp_path / 'replay')
    assert read(tmp_path / 'replay/pipeline.json')['status'] == 'failed'
