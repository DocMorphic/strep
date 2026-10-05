"""Complete synthetic neutral import records; no live engine or motion trials."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import reserved_partner_engine as audit
import action_worker_lock as locks
from native_engine_contacts import packed_weights
from native_scene_imported_skin import source_engine_weights
from rig_asset import RigAsset
from test_reserved_partner_fixtures import build
from strep import read, save, sha256


def record_matrix(value):
    return value[:3, :].T.tolist()


def observations(request, *, reverse_bones=False):
    rows = []
    for item in request['pairs']:
        actors = {}
        for name, entry in item['actors'].items():
            rig = RigAsset.load(entry['path']); placement = audit.transform(entry['placement'])
            source_names = [rig.document['nodes'][n]['name'] for n in rig.joints]
            names = source_names[::-1] if reverse_bones else source_names
            order = [source_names.index(n) for n in names]; node = f'/pair/{name}/mesh'
            weights = packed_weights(source_engine_weights(rig)); meshes = []; offset = 0
            for primitive in rig.primitives:
                count = len(primitive['positions'])
                meshes.append(dict(node=node, surface=primitive['primitive'], positions=primitive['positions'].astype(float).tolist(),
                    bones=primitive['joints'].ravel().astype(int).tolist(), weights=weights[offset:offset+count].ravel().tolist(),
                    binds=[dict(bone=names.index(source_names[i]), pose=record_matrix(v)) for i, v in enumerate(rig.inverse)],
                    indices=[], primitive_type=3))
                offset += count
            actors[name] = dict(rig_id=entry['rig_id'], bone_names=names,
                bone_parents=audit.nearest_joint_parents(rig, names),
                bones_world=[record_matrix(m) for m in placement@rig.reference[rig.joints][order]],
                placement_world=record_matrix(placement), skeleton_world=record_matrix(placement),
                mesh_world=[dict(node=node, matrix=record_matrix(placement))], meshes=meshes, nonreset_animations=[])
        rows.append(dict(id=item['id'], actors=actors))
    return dict(engine=dict(major=4, minor=7, patch=2, status='synthetic-test'), compression_disabled=True,
                gpu_skin_baked=False, animation_played=False, pairs=rows)


def prepared(tmp_path):
    _, bundle, _ = build(tmp_path)
    request, bindings = audit.inputs(bundle)
    return bundle, request, observations(request), bindings


@pytest.mark.parametrize('reverse_bones', [False, True])
def test_all_six_actors_all_vertices_bones_roles_and_triangles_are_checked(tmp_path, reverse_bones):
    bundle, request, _, bindings = prepared(tmp_path)
    checked, arrays = audit.reduce(request, observations(request, reverse_bones=reverse_bones))
    assert checked['actors'] == 6 and checked['complete_vertex_observations'] == 18
    assert checked['complete_bones'] == checked['complete_role_origins'] == 114
    assert len(arrays) == 36 and checked['static_import_pass']
    assert all(row['actors'][name]['imported_skin']['source_faces'] == 1 for row in checked['pairs'] for name in ('A', 'B'))
    assert not checked['quality_approved'] and not checked['release_approved']
    assert checked['motion_trials_executed'] == 0 and not checked['imported_skin_weights_renormalized']
    assert all(sha256(path) == digest for path, digest in bindings.items())


def test_vertex_order_and_global_winding_change_do_not_drop_triangles(tmp_path):
    _, request, raw, _ = prepared(tmp_path)
    mesh = raw['pairs'][0]['actors']['A']['meshes'][0]
    order = [2, 1, 0]
    mesh['positions'] = [mesh['positions'][i] for i in order]
    mesh['bones'] = np.array(mesh['bones']).reshape(3, 4)[order].ravel().tolist()
    mesh['weights'] = np.array(mesh['weights']).reshape(3, 4)[order].ravel().tolist()
    checked, _ = audit.reduce(request, raw)
    assert checked['pairs'][0]['actors']['A']['imported_skin']['winding'] == 'globally-reversed'


@pytest.mark.parametrize('fault', ['bone-pose', 'basis', 'parents', 'parent-type', 'mesh-space', 'skeleton-space',
    'placement', 'role-order', 'rig-id', 'missing-actor', 'missing-pair', 'duplicate-pair',
    'pair-order', 'missing-bone', 'missing-surface', 'triangle', 'weight', 'bind', 'indices', 'animation'])
def test_incomplete_or_changed_imported_populations_reject(tmp_path, fault):
    _, request, raw, _ = prepared(tmp_path)
    actor = raw['pairs'][0]['actors']['A']; mesh = actor['meshes'][0]
    if fault == 'bone-pose': actor['bones_world'][-1][3][0] += .001
    if fault == 'basis': actor['bones_world'][-1][0][0] += .001
    if fault == 'parents': actor['bone_parents'][-1] = -1
    if fault == 'parent-type': actor['bone_parents'][-1] = float(actor['bone_parents'][-1])
    if fault == 'mesh-space': actor['mesh_world'][0]['matrix'][3][0] += .001
    if fault == 'skeleton-space': actor['skeleton_world'][3][0] += .001
    if fault == 'placement': actor['placement_world'][3][0] += .001
    if fault == 'role-order': request['pairs'][0]['actors']['A']['role_order'].reverse()
    if fault == 'rig-id': actor['rig_id'] = 'other-rig'
    if fault == 'missing-actor': raw['pairs'][0]['actors'].pop('B')
    if fault == 'missing-pair': raw['pairs'].pop()
    if fault == 'duplicate-pair': raw['pairs'][1] = copy.deepcopy(raw['pairs'][0])
    if fault == 'pair-order': raw['pairs'].reverse()
    if fault == 'missing-bone': actor['bone_names'].pop()
    if fault == 'missing-surface': actor['meshes'].clear()
    if fault == 'triangle': mesh['indices'] = [0, 1, 1]
    if fault == 'weight': mesh['weights'][0] = .9
    if fault == 'bind': mesh['binds'][0]['pose'][3][0] += .001
    if fault == 'indices': mesh['indices'] = [0, 1, 99]
    if fault == 'animation': actor['nonreset_animations'] = ['untested-clip']
    with pytest.raises(ValueError): audit.reduce(request, raw)


def test_equal_neutral_pose_cannot_hide_a_different_skin_function(tmp_path):
    _, request, raw, _ = prepared(tmp_path)
    actor = raw['pairs'][0]['actors']['A']; mesh = actor['meshes'][0]
    # Both bone*inverse pairs give identity at rest. Assigning all vertices to
    # the child changes every future animated skin function despite equal rest.
    mesh['bones'] = [1 if i%4 == 0 else n for i, n in enumerate(mesh['bones'])]
    with pytest.raises(ValueError, match='skin-function'): audit.reduce(request, raw)


@pytest.mark.parametrize('field', ['compression_disabled', 'gpu_skin_baked', 'animation_played', 'version', 'limits'])
def test_unreviewed_import_encoding_or_scope_cannot_pass(tmp_path, field):
    _, request, raw, _ = prepared(tmp_path)
    if field == 'version': raw['engine']['patch'] += 1
    elif field == 'limits': request['limits']['skin_position_m'] *= 10
    else: raw[field] = not raw[field]
    with pytest.raises(ValueError): audit.reduce(request, raw)


def fake_engine(tmp_path, monkeypatch):
    bundle, _, _, _ = prepared(tmp_path)
    engine = tmp_path/'engine.exe'; engine.write_bytes(b'Synthetic only; never executed.')
    monkeypatch.setattr(locks, 'ROOT', tmp_path/'lock-root')
    def execute(command, **kwargs):
        assert '--headless' in command and command[-3] == '--'
        save(command[-1], observations(read(command[-2])))
        kwargs['stdout'].write('Synthetic import record; no live Godot.\n')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(audit.subprocess, 'run', execute)
    output = tmp_path/'engine-output'; result = audit.run(bundle, output, engine)
    return output, result


def test_complete_bound_saved_import_reduction_is_reproduced(tmp_path, monkeypatch):
    output, result = fake_engine(tmp_path, monkeypatch)
    checked = audit.verify(output)
    assert checked['static_import_pass'] and result['status'] == 'complete'
    assert not checked['gpu_render_checked'] and not checked['interaction_contacts_checked']


@pytest.mark.parametrize('fault', ['arrays', 'summary', 'raw', 'inventory'])
def test_rebound_saved_evidence_cannot_invent_complete_import(tmp_path, monkeypatch, fault):
    output, result = fake_engine(tmp_path, monkeypatch)
    if fault == 'arrays':
        path = output/'observations.npz'
        with np.load(path, allow_pickle=False) as saved: arrays = {k: saved[k] for k in saved.files}
        arrays['pair_0_A_imported_vertices_world_m'][0, 0] += .001
        np.savez_compressed(path, **arrays)
    elif fault == 'summary':
        path = output/'verification.json'; value = read(path); value['complete_bones'] -= 1; save(path, value)
    elif fault == 'raw':
        path = output/'engine-output.json'; value = read(path); value['pairs'][0]['actors']['A']['bone_parents'][-1] = -1; save(path, value)
    else:
        result['files_sha256'].pop('observations.npz'); path = None
    if path is not None: result['files_sha256'][path.name] = sha256(path)
    save(output/'result.json', result)
    with pytest.raises(ValueError): audit.verify(output)


def test_busy_or_existing_output_rejects_before_real_import(tmp_path, monkeypatch):
    monkeypatch.setattr(locks, 'ROOT', tmp_path/'lock-root'); output = tmp_path/'out'
    with locks.worker_lock(), pytest.raises(RuntimeError, match='Another'):
        audit.run(tmp_path/'absent', output, tmp_path/'absent.exe')
    assert not output.exists()
    output.mkdir(); (output/'sentinel').write_text('keep')
    with pytest.raises(ValueError, match='Fresh'):
        audit.run(tmp_path/'absent', output, tmp_path/'absent.exe')
    assert (output/'sentinel').read_text() == 'keep'
