"""Explicit body-frame bridge fixtures; no inferred anatomy or human quality."""
import copy
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from rig_body_tracks import sample
from articulated_motion_dynamics import diagnose
from test_native_support import fixture
from rig_asset import RigAsset
from gltf_tools import append_accessor, write_glb
from strep import sha256


def binding(name='declared-body', node=0, com=None, axes=None):
    return dict(id=name, node=node, com_from_node_local_m=[0, 0, 0] if com is None else com,
                body_rotation_from_node_xyzw=[0, 0, 0, 1] if axes is None else axes,
                provenance='Explicit numerical fixture; not anthropometry.')


def placement():
    return dict(translation_m=[0, 0, 0], rotation_xyzw=[0, 0, 0, 1])


def test_declared_com_and_body_axes_follow_world_placement_without_changing_rig(tmp_path):
    source, rig, _, _ = fixture(tmp_path); digest = sha256(source); document = copy.deepcopy(rig.document)
    axis = Rotation.from_euler('x', 40, degrees=True)
    world = Rotation.from_euler('y', 90, degrees=True)
    offset = [.1, 0, 0]; transform = dict(translation_m=[3, 2, -4], rotation_xyzw=world.as_quat().tolist())
    r = sample(rig, 0, [binding(com=offset, axes=axis.as_quat().tolist())], 11, transform, rigid_tolerance=1e-8)
    times = np.linspace(0, 2, 11); y = 1.2 + .06 * np.maximum(0, abs(times-1)-.3)
    expected = np.column_stack([np.full(11, .1), y, np.zeros(11)]) @ world.as_matrix().T + [3, 2, -4]
    np.testing.assert_allclose(np.array(r['world_com_positions_m'])[:, 0], expected, atol=1e-7, rtol=0)
    q = np.array(r['body_rotations_xyzw'])[:, 0]
    np.testing.assert_allclose(Rotation.from_quat(q).as_matrix(), np.tile((world*axis).as_matrix(), (11, 1, 1)), atol=1e-12)
    assert r['fps'] == 5 and r['uniform_times_s'][0] == 0 and r['uniform_times_s'][-1] == 2
    assert rig.document == document and sha256(source) == digest
    assert not r['body_properties_inferred'] and r['physical_approval'] is None and not r['release_approved']


def test_original_rig_body_tracks_feed_complete_tree_demand_with_explicit_anchors(tmp_path):
    _, rig, _, _ = fixture(tmp_path)
    r = sample(rig, 0, [binding('root', 0), binding('child', 1)], 11, placement(), rigid_tolerance=1e-8)
    def body(name, parent, anchor):
        return dict(id=name, parent=parent, mass_kg=1., inertia_body_about_com_kg_m2=(np.eye(3)*.1).tolist(),
                    joint_from_own_com_local_m=[0, 0, 0], joint_from_parent_com_local_m=anchor,
                    provenance='Explicit one-kilogram fixture; no human profile.')
    profile = [body('root', None, None), body('child', 'root', [-.2, 0, 0])]
    d = diagnose(profile, r['world_com_positions_m'], r['body_rotations_xyzw'], np.zeros((11, 2, 3)), np.zeros((11, 2, 3)),
                 fps=r['fps'], gravity_world_m_s2=[0, -10, 0],
                 phases=[dict(id='known', start_frame=0, end_frame_exclusive=11, support_assumption='supported')],
                 anchor_tolerance_m=1e-7, force_tolerance_N=1e-6, torque_tolerance_Nm=1e-6)
    p = np.array(r['world_com_positions_m'])
    expected = 2 * (np.diff(p[:, 0], n=2, axis=0)*25 - [0, -10, 0])
    np.testing.assert_allclose(d['residual_floating_root_force_world_N'], expected, atol=1e-10)
    assert d['assessed_samples'] == 9 and d['floating_root_wrench_consistent_samples'] == 0
    assert d['unestimated_endpoint_frames'] == [0, 10] and not d['training_admitted']


def test_binding_order_and_output_snapshots_do_not_change_body_identity(tmp_path):
    _, rig, _, _ = fixture(tmp_path); rows = [binding('child', 1), binding('root', 0)]
    transform = placement(); r = sample(rig, 0, rows, 11, transform, rigid_tolerance=1e-8)
    rows[0]['com_from_node_local_m'][0] = 42; transform['translation_m'][0] = 99
    assert r['body_ids'] == ['child', 'root'] and r['bindings'][0]['com_from_node_local_m'] == [0, 0, 0]
    assert r['placement']['translation_m'] == [0, 0, 0]
    np.testing.assert_allclose(np.array(r['world_com_positions_m'])[:, 0, 0], -.2)


def test_animated_scale_cannot_be_projected_to_a_rigid_body(tmp_path):
    path, rig, _, _ = fixture(tmp_path); doc = copy.deepcopy(rig.document); data = bytearray(rig.binary)
    animation = doc['animations'][0]; values = np.ones((11, 3)); values[5] = [.5, 1, 1]
    animation['channels'].append(dict(sampler=len(animation['samplers']), target=dict(node=0, path='scale')))
    animation['samplers'].append(dict(input=animation['samplers'][0]['input'], output=append_accessor(doc, data, values, 'VEC3'), interpolation='LINEAR'))
    write_glb(path, doc, data); rig = RigAsset.load(path)
    with pytest.raises(ValueError, match='scale|rigid'):
        sample(rig, 0, [binding()], 11, placement(), rigid_tolerance=1e-8)


@pytest.mark.parametrize('bad', ['node_bool', 'nonjoint', 'duplicate_node', 'duplicate_id', 'offset', 'axes', 'provenance', 'extra', 'frames', 'clock_rate', 'animation', 'placement', 'tolerance', 'nonfinite'])
def test_missing_or_inconsistent_body_track_contract_is_rejected(tmp_path, bad):
    _, rig, _, _ = fixture(tmp_path); rows = [binding()]; count = 11; index = 0; transform = placement(); tolerance = 1e-8
    if bad == 'node_bool': rows[0]['node'] = True
    if bad == 'nonjoint': rows[0]['node'] = 6
    if bad == 'duplicate_node': rows.append(binding('another', 0))
    if bad == 'duplicate_id': rows.append(binding('declared-body', 1))
    if bad == 'offset': rows[0]['com_from_node_local_m'] = [1001, 0, 0]
    if bad == 'axes': rows[0]['body_rotation_from_node_xyzw'] = [0, 0, 0, 2]
    if bad == 'provenance': rows[0]['provenance'] = ''
    if bad == 'extra': rows[0]['inferred_mass'] = 1
    if bad == 'frames': count = True
    if bad == 'clock_rate': count = 500
    if bad == 'animation': index = True
    if bad == 'placement': transform['rotation_xyzw'] = [0, 0, 0, 2]
    if bad == 'tolerance': tolerance = .1
    if bad == 'nonfinite': rows[0]['com_from_node_local_m'] = [np.nan, 0, 0]
    with pytest.raises(ValueError):
        sample(rig, index, rows, count, transform, rigid_tolerance=tolerance)
