import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation, Slerp
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from contact_locked_native import locked_pair, NativeRotationEdit
from test_timed_rotation_edit import fixture
from gltf_tools import read_glb
from paired_temporal_neighbor import rotation_channels


@pytest.mark.parametrize('fraction', [.13, .5, .83])
def test_locked_pair_retains_noncommuting_contact(fraction):
    center, first, last = Rotation.from_rotvec([[.2, -.3, .1], [.4, -.1, -.2], [-.1, -.2, .3]]).as_matrix()
    endpoints, record = locked_pair(center, first, last, fraction)
    actual = Slerp([0, 1], Rotation.from_matrix(endpoints))([fraction]).as_matrix()[0]
    np.testing.assert_allclose(actual, center, rtol=0, atol=1e-12)
    assert record['success']


def test_native_export_clones_shared_sampler_and_keeps_clocks(tmp_path):
    doc, binary = fixture(); edit = NativeRotationEdit(doc, binary, ['Arm'], [0., .4, 1.5], [.1, 1.3], [], (doc, binary))
    e = edit.model.entries[0]; q = e['source'].copy(); q[e['ids']] = (Rotation.from_quat(q[e['ids']])*Rotation.from_rotvec([.01, -.02, .03])).as_quat()
    path = tmp_path/'native.glb'; edit.export({1: q}, path)
    changed, payload = read_glb(path); old = rotation_channels(doc, binary); new = rotation_channels(changed, payload)
    np.testing.assert_array_equal(new[1][1], old[1][1]); np.testing.assert_array_equal(new[3][2], old[3][2])
    assert not np.array_equal(new[1][2], old[1][2])


def test_export_rejects_frozen_keys_and_original_budget(tmp_path):
    doc, binary = fixture(); edit = NativeRotationEdit(doc, binary, ['Arm'], [0., .4, 1.5], [.1, 1.3], [], (doc, binary))
    e = edit.model.entries[0]; q = e['source'].copy(); q[0] = Rotation.from_rotvec([.1, 0, 0]).as_quat()
    with pytest.raises(ValueError, match='Frozen'): edit.export({1: q}, tmp_path/'bad.glb')
    q = e['source'].copy(); q[e['ids']] = Rotation.from_rotvec([2., 0, 0]).as_quat()
    with pytest.raises(ValueError, match='budget'): edit.export({1: q}, tmp_path/'bad.glb')


def test_invalid_contact_fraction_rejected():
    for t in (0, 1, float('nan')):
        with pytest.raises(ValueError): locked_pair(np.eye(3), np.eye(3), np.eye(3), t)
