"""Immutable real-GLB sampling/explicit dynamics workflow fixtures."""
import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import rig_articulated_dynamics as workflow
from test_native_support import fixture
from test_rig_body_tracks import binding, placement
from strep import save, read, sha256


def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, 'ROOT', tmp_path)
    source, _, _, _ = fixture(tmp_path)
    def body(name, parent, anchor):
        return dict(id=name, parent=parent, mass_kg=1., inertia_body_about_com_kg_m2=(np.eye(3)*.1).tolist(),
                    joint_from_own_com_local_m=[0, 0, 0], joint_from_parent_com_local_m=anchor,
                    provenance='Explicit synthetic body properties; not human data.')
    request = dict(schema=workflow.SCHEMA, glb=dict(path=source.name, sha256=sha256(source)), animation_index=0,
                   bindings=[binding('root', 0), binding('child', 1)], sample_count=11, placement=placement(),
                   profile=[body('root', None, None), body('child', 'root', [-.2, 0, 0])], rigid_tolerance=1e-8,
                   external_forces_world_N=np.zeros((11, 2, 3)).tolist(), external_torques_about_com_world_Nm=np.zeros((11, 2, 3)).tolist(),
                   gravity_world_m_s2=[0, -10, 0],
                   phases=[dict(id='known', start_frame=0, end_frame_exclusive=11, support_assumption='supported')],
                   anchor_tolerance_m=1e-7, force_tolerance_N=1e-6, torque_tolerance_Nm=1e-6,
                   assumption_notes=dict(body_model='Declared synthetic masses/COMs/inertias, not anatomy.',
                                         external_wrenches='Explicit zero reactions; no ground support inferred.',
                                         support='Known phase for diagnosis; zero wrench is an explicit unsupported assumption.',
                                         capacity='Not measured or assessed.'))
    path = tmp_path/'request.json'; save(path, request)
    return source, path, request, tmp_path/'reports/body-demand'


def test_complete_original_motion_and_explicit_demands_are_frozen_without_approval(tmp_path, monkeypatch):
    source, path, request, output = setup(tmp_path, monkeypatch); original = source.read_bytes(); digest = sha256(path)
    r = workflow.run(path, output); protocol = read(output/'protocol.json'); tracks = read(output/'body-tracks.json'); d = read(output/'demands.json')
    assert r['status'] == read(output/'pipeline.json')['status'] == 'complete'
    assert source.read_bytes() == original == (output/'inputs/character.glb').read_bytes() and sha256(path) == digest
    assert r['samples'] == 11 and r['assessed_samples'] == 9 and r['floating_root_wrench_consistent_samples'] == 0
    assert tracks['body_ids'] == d['body_ids'] == ['root', 'child'] and d['unestimated_endpoint_frames'] == [0, 10]
    assert r['physical_approval'] is None and all(r[k] is False for k in ['quality_approved', 'release_approved', 'training_admitted'])
    for name, h in r['files_sha256'].items(): assert sha256(output/name) == h
    for name, h in protocol['methods_sha256'].items(): assert sha256(output/'implementation'/name) == h
    with pytest.raises(FileExistsError): workflow.run(path, output)


@pytest.mark.parametrize('bad', ['original_hash', 'missing_wrenches', 'anchor_disconnect', 'body_order', 'provenance'])
def test_incomplete_model_never_receives_a_success_receipt(tmp_path, monkeypatch, bad):
    source, path, request, output = setup(tmp_path, monkeypatch)
    if bad == 'original_hash': request['glb']['sha256'] = '0'*64
    if bad == 'missing_wrenches': request['external_forces_world_N'] = []
    if bad == 'anchor_disconnect': request['profile'][1]['joint_from_parent_com_local_m'] = [-.19, 0, 0]
    if bad == 'body_order': request['profile'].reverse()
    if bad == 'provenance': request['assumption_notes']['capacity'] = ''
    save(path, request)
    with pytest.raises(ValueError): workflow.run(path, output)
    assert not (output/'result.json').exists()
    if bad in ['missing_wrenches', 'anchor_disconnect', 'body_order']:
        assert read(output/'pipeline.json')['status'] == 'failed' and (output/'inputs/character.glb').exists()


def test_source_mutation_after_measurement_preserves_failed_raw_evidence(tmp_path, monkeypatch):
    source, path, request, output = setup(tmp_path, monkeypatch); original = source.read_bytes(); real = workflow.diagnose
    def mutate(*args, **kwargs):
        result = real(*args, **kwargs); source.write_bytes(original+b'changed'); return result
    monkeypatch.setattr(workflow, 'diagnose', mutate)
    with pytest.raises(ValueError, match='input changed during measurement'): workflow.run(path, output)
    assert read(output/'pipeline.json')['status'] == 'failed' and not (output/'result.json').exists()
    assert (output/'inputs/character.glb').read_bytes() == original
    assert (output/'demands.json').exists() and (output/'body-tracks.json').exists()


def test_constant_original_rig_with_explicit_support_wrench_retains_internal_joint_load(tmp_path, monkeypatch):
    from gltf_tools import append_accessor, write_glb
    from rig_asset import RigAsset
    source, path, request, output = setup(tmp_path, monkeypatch); rig = RigAsset.load(source)
    doc = copy.deepcopy(rig.document); binary = bytearray(rig.binary)
    # Analytical two-body gravity fixture: static clip with an explicit root reaction.
    doc['animations'][0]['samplers'][1]['output'] = append_accessor(doc, binary, np.tile([0, 1.2, 0], (11, 1)), 'VEC3')
    write_glb(source, doc, binary); request['glb']['sha256'] = sha256(source)
    f = np.zeros((11, 2, 3)); t = f.copy(); f[:, 0, 1] = 20; t[:, 0, 2] = -2
    request['external_forces_world_N'] = f.tolist(); request['external_torques_about_com_world_Nm'] = t.tolist()
    request['assumption_notes']['external_wrenches'] = 'Explicit analytical 20 N support and -2 Nm root COM reaction; no inferred ground allocation.'
    save(path, request); r = workflow.run(path, output); d = read(output/'demands.json')
    assert r['floating_root_wrench_consistent_samples'] == 9 and r['physical_approval'] is None
    np.testing.assert_allclose(np.array(d['required_parent_on_body_force_world_N'])[:, 1], np.tile([0, 10, 0], (9, 1)), atol=1e-9)
    assert not r['training_admitted'] and not r['release_approved']
