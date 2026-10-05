"""Actual tiny animated GLB inspection; no production characters or listener."""
import copy
import io
import json
import shutil
import subprocess
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from test_studio_material_region import setup as region_setup, save_preview
from test_rig_material_patch import unsigned
from gltf_tools import append_accessor, write_glb
from rig_asset import RigAsset
from strep import read, save, sha256
import studio_material_region as regions
import studio_material_region_pose as inspection
import action_studio_server as server
import action_worker_lock


def setup(tmp_path, monkeypatch, modify=None):
    payload, resolver, asset = region_setup(tmp_path, monkeypatch)
    if modify:
        rig = RigAsset.load(asset); doc = copy.deepcopy(rig.document); binary = bytearray(rig.binary)
        modify(doc, binary, payload); write_glb(asset, doc, binary)
        payload['actor']['sha256'] = sha256(asset)
        profile = json.loads(payload['profile_json']); profile['character_sha256'] = sha256(asset)
        payload['profile_json'] = json.dumps(profile)
        import hashlib
        payload['profile_sha256'] = hashlib.sha256(payload['profile_json'].encode()).hexdigest()
    for name in inspection.METHODS:
        shutil.copyfile(Path(inspection.__file__).parent/name, tmp_path/'scripts'/name)
    preview, _ = save_preview(payload, resolver)
    request = dict(schema=inspection.SCHEMA, id=preview['id'], preview_sha256=preview['result_sha256'], animation_index=0, time_s=.5)
    return preview, request, resolver, asset


@pytest.mark.parametrize('time', [0., .125, .5, 1.])
def test_actual_native_pose_matches_analytic_translation_and_keeps_every_vertex(tmp_path, monkeypatch, time):
    preview, request, resolver, asset = setup(tmp_path, monkeypatch); request['time_s'] = time
    before = sha256(asset); result = inspection.inspect_pose(request, resolver, 'sample'); p = result['pose']
    np.testing.assert_allclose(p['positions_m'], np.asarray(preview['patch']['reference_positions_m'])+[0, 0, time], atol=1e-15, rtol=0)
    assert p['triangle_vertex_indices'] == [[0, 1, 2]] and p['face_references'] == preview['patch']['face_references']
    assert p['vertices'] == preview['patch']['vertices'] and p['time_s'] == time and p['duration_s'] == 1
    np.testing.assert_allclose(p['triangle_unit_winding_normals'], [[0, 0, 1]], atol=1e-15)
    assert p['animation_sampled'] and not p['scene_placement_applied'] and not p['contact_conditions_measured']
    assert result['preview_sha256'] == preview['result_sha256'] and result['patch_sha256'] == preview['patch_sha256']
    folder = tmp_path/'reports/material-region-pose-previews/sample'
    assert sha256(folder/'pose.json') == result['pose_sha256'] and read(folder/'pose.json') == p
    assert {x.name for x in folder.iterdir()} == {'request.json', 'pose.json', 'result.json', 'pipeline.json'}
    assert sha256(asset) == before and sha256(regions.folder_for('preview')/'result.json') == preview['result_sha256']
    assert all(result[k] is False for k in ('animation_edited', 'engine_executed', 'human_reviewed', 'quality_approved', 'training_admitted', 'release_approved'))


@pytest.mark.parametrize('mode', ['STEP', 'LINEAR', 'CUBICSPLINE'])
def test_actual_interpolation_and_exact_keys_are_retained(tmp_path, monkeypatch, mode):
    def modify(doc, binary, payload):
        sampler = doc['animations'][0]['samplers'][0]; sampler['interpolation'] = mode
        if mode == 'CUBICSPLINE':
            # Zero Hermite tangents give smoothstep: at .25, z = .15625.
            sampler['output'] = append_accessor(doc, binary, [[0, 0, 0]]*4+[[0, 0, 1], [0, 0, 0]], 'VEC3')
    preview, request, resolver, _ = setup(tmp_path, monkeypatch, modify); request['time_s'] = .25
    result = inspection.inspect_pose(request, resolver, 'between')
    delta = np.asarray(result['pose']['positions_m'])-preview['patch']['reference_positions_m']
    np.testing.assert_allclose(delta, np.tile([0, 0, {'STEP': 0, 'LINEAR': .25, 'CUBICSPLINE': .15625}[mode]], (3, 1)), atol=1e-15)
    request['time_s'] = 1
    end = inspection.inspect_pose(request, resolver, 'key')
    np.testing.assert_allclose(np.asarray(end['pose']['positions_m'])-preview['patch']['reference_positions_m'], np.tile([0, 0, 1], (3, 1)), atol=1e-15)


def test_collapsed_actual_blended_skin_remains_in_receipt_with_unavailable_normals(tmp_path, monkeypatch):
    def modify(doc, binary, payload):
        attrs = doc['meshes'][0]['primitives'][0]['attributes']
        attrs['JOINTS_0'] = unsigned(doc, binary, [[3, 0, 0, 0]]*4, 'VEC4')
        attrs['WEIGHTS_0'] = append_accessor(doc, binary, [[.5, .5, 0, 0]]*4, 'VEC4')
        attrs['WEIGHTS_1'] = append_accessor(doc, binary, [[0, 0, 0, 0]]*4, 'VEC4')
        animation = doc['animations'][0]
        animation['samplers'].append(dict(input=animation['samplers'][0]['input'], output=append_accessor(doc, binary, [[0, 0, 0, 1], [0, 0, 1, 0]], 'VEC4'), interpolation='LINEAR'))
        animation['channels'].append(dict(sampler=1, target=dict(node=4, path='rotation')))
        payload['role'] = 'Root'
    preview, request, resolver, _ = setup(tmp_path, monkeypatch, modify); request['time_s'] = 1
    p = inspection.inspect_pose(request, resolver, 'collapsed')['pose']
    assert len(p['positions_m']) == 3 and len(p['face_references']) == 1
    assert p['triangle_unit_winding_normals'] == [None] and p['patch_winding']['degenerate_local_faces'] == [0]
    assert not p['patch_winding']['normal_available'] and p['patch_winding']['area_weighted_winding_normal'] is None
    assert p['triangle_twice_areas_m2'][0] <= preview['patch']['selector']['minimum_twice_area_m2']


def test_actual_rigid_rotation_changes_surface_direction_from_default_pose(tmp_path, monkeypatch):
    def modify(doc, binary, payload):
        animation = doc['animations'][0]
        animation['samplers'].append(dict(input=animation['samplers'][0]['input'], output=append_accessor(doc, binary,
            [[0, 0, 0, 1], [2**-.5, 0, 0, 2**-.5]], 'VEC4'), interpolation='LINEAR'))
        animation['channels'].append(dict(sampler=1, target=dict(node=1, path='rotation')))
    preview, request, resolver, _ = setup(tmp_path, monkeypatch, modify); request['time_s'] = 1
    p = inspection.inspect_pose(request, resolver, 'rotation')['pose']
    np.testing.assert_allclose(p['triangle_unit_winding_normals'], [[0, -1, 0]], atol=1e-15)
    matrix = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
    np.testing.assert_allclose(p['positions_m'], np.asarray(preview['patch']['reference_positions_m'])@matrix.T+[0, 0, 1], atol=1e-15)
    assert preview['orientation']['triangle_unit_winding_normals'] == [[0, 0, 1]]


def test_long_clip_uses_its_actual_time_without_a_thirty_second_approximation(tmp_path, monkeypatch):
    def modify(doc, binary, payload):
        doc['animations'][0]['samplers'][0]['input'] = append_accessor(doc, binary, [0, 60], 'SCALAR')
    preview, request, resolver, _ = setup(tmp_path, monkeypatch, modify); request['time_s'] = 45
    p = inspection.inspect_pose(request, resolver, 'long')['pose']
    assert p['duration_s'] == 60 and p['time_s'] == 45
    np.testing.assert_allclose(np.asarray(p['positions_m'])-preview['patch']['reference_positions_m'], np.tile([0, 0, .75], (3, 1)), atol=1e-15)


@pytest.mark.parametrize('fault', ['negative', 'past-end', 'nan', 'boolean-time', 'boolean-index', 'index', 'schema', 'extra', 'binding', 'source', 'method', 'name'])
def test_invalid_or_changed_inputs_never_produce_complete_receipts(tmp_path, monkeypatch, fault):
    preview, request, resolver, asset = setup(tmp_path, monkeypatch); name = 'bad'
    if fault == 'negative': request['time_s'] = -1
    elif fault == 'past-end': request['time_s'] = 1.0000001
    elif fault == 'nan': request['time_s'] = float('nan')
    elif fault == 'boolean-time': request['time_s'] = True
    elif fault == 'boolean-index': request['animation_index'] = True
    elif fault == 'index': request['animation_index'] = 9
    elif fault == 'schema': request['schema'] = 'other'
    elif fault == 'extra': request['placement'] = [1, 2, 3]
    elif fault == 'binding': request['preview_sha256'] = '0'*64
    elif fault == 'source': asset.write_bytes(asset.read_bytes()+b'x')
    elif fault == 'method': (tmp_path/'scripts/rig_clip_import.py').write_bytes(b'changed')
    else: name = '../escape'
    with pytest.raises((ValueError, IndexError)): inspection.inspect_pose(request, resolver, name)
    folder = tmp_path/'reports/material-region-pose-previews/bad'
    assert not (folder/'result.json').exists()
    if folder.exists(): assert read(folder/'pipeline.json')['status'] == 'failed'


@pytest.mark.parametrize('fault', ['source', 'method', 'request'])
def test_change_during_sampling_cannot_yield_complete_result(tmp_path, monkeypatch, fault):
    _, request, resolver, asset = setup(tmp_path, monkeypatch); original = inspection.posed_region
    def changed(*args):
        p = original(*args)
        if fault == 'source': asset.write_bytes(asset.read_bytes()+b'x')
        elif fault == 'method': (tmp_path/'scripts/studio_material_region_pose.py').write_bytes(b'changed')
        else: save(tmp_path/'reports/material-region-pose-previews/race/request.json', {})
        return p
    monkeypatch.setattr(inspection, 'posed_region', changed)
    with pytest.raises(ValueError): inspection.inspect_pose(request, resolver, 'race')
    folder = tmp_path/'reports/material-region-pose-previews/race'
    assert not (folder/'result.json').exists() and read(folder/'pipeline.json')['status'] == 'failed'


def test_fresh_results_and_actual_python_javascript_receipt_parity(tmp_path, monkeypatch):
    preview, request, resolver, _ = setup(tmp_path, monkeypatch)
    result = inspection.inspect_pose(request, resolver, 'sample')
    with pytest.raises(ValueError, match='Fresh'): inspection.inspect_pose(request, resolver, 'sample')
    path = tmp_path/'parity.json'; save(path, dict(preview=preview, request=request, result=result))
    module = (Path(inspection.__file__).parent/'material-region-pose.mjs').as_uri()
    code = "import {readFileSync} from 'node:fs';import {checkedAuthorPose} from "+json.dumps(module)+";const v=JSON.parse(readFileSync(process.argv[1],'utf8'));checkedAuthorPose(v.result,v.request,v.preview);"
    run = subprocess.run(['node', '--input-type=module', '-e', code, str(path)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout+run.stderr
    assert server.allowed_file('/material-region-pose.mjs') == server.ROOT/'scripts/material-region-pose.mjs'


@pytest.mark.parametrize('fault,status', [('host', 403), ('origin', 403), ('type', 415), ('size', 400), ('busy', 409), ('valid', 201)])
def test_pose_handler_loopback_and_worker_gates_without_listener(tmp_path, monkeypatch, fault, status):
    _, request, resolver, _ = setup(tmp_path, monkeypatch); monkeypatch.setattr(server, 'allowed_file', resolver)
    h = server.Handler.__new__(server.Handler); h.path = '/api/native-scene-material-region-pose'; data = json.dumps(request).encode()
    h.headers = {'Host': '127.0.0.1:8768', 'Origin': 'http://127.0.0.1:8768', 'Content-Type': 'application/json', 'Content-Length': str(len(data))}
    h.rfile = io.BytesIO(data); h.server = SimpleNamespace(allowed_hosts={'127.0.0.1:8768'}, job_lock=threading.Lock())
    replies = []; h.respond = lambda s, v: replies.append((s, v)); calls = []
    @contextmanager
    def lock():
        calls.append('lock')
        if fault == 'busy': raise RuntimeError('busy')
        yield
    monkeypatch.setattr(action_worker_lock, 'worker_lock', lock)
    if fault == 'host': h.headers['Host'] = 'remote'
    elif fault == 'origin': h.headers['Origin'] = 'http://remote'
    elif fault == 'type': h.headers['Content-Type'] = 'text/plain'
    elif fault == 'size': h.headers['Content-Length'] = '1048577'
    h.do_POST(); assert replies[0][0] == status
    assert calls == (['lock'] if fault in ('busy', 'valid') else [])
    if fault == 'valid': assert replies[0][1]['pose']['time_s'] == .5
