import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_godot_payload import payload


def fixture():
    rig = SimpleNamespace(document={'nodes': [{'name': 'Hips'}, {'name': 'LeftHand'}]}, joints=[0, 1])
    times = np.array([0, 2.0917224884033203, 3.6666667461395264], np.float32)
    values = np.tile([0., 0., 0., 1.], (3, 1))
    sampler = SimpleNamespace(channels=[(1, 'rotation', times, values, 'LINEAR')], duration=float(times[-1]), name='Test')
    return rig, sampler


def test_original_float32_native_keys_export_without_bake_or_shared_array():
    rig, sampler = fixture(); data = payload(rig, sampler, 'digest')
    assert data['channels'][0]['times_s'] == sampler.channels[0][2].astype(float).tolist()
    assert data['duration_s'] == 3.6666667461395264 and not data['loop']
    assert data['source_sha256'] == 'digest' and data['channels'][0]['bone'] == 'LeftHand'
    data['channels'][0]['values'][0][0] = 2
    assert sampler.channels[0][3][0, 0] == 0


@pytest.mark.parametrize('fault', ['duplicate', 'path', 'cubic', 'external'])
def test_no_silent_mapping_or_interpolation_fallback(fault):
    rig, sampler = fixture()
    if fault == 'duplicate': rig.document['nodes'][0]['name'] = 'LeftHand'
    elif fault == 'path': rig.document['nodes'][0]['name'] = 'Hips:property'
    else:
        node, path, times, values, mode = sampler.channels[0]
        sampler.channels[0] = (99 if fault == 'external' else node, path, times, values, 'CUBICSPLINE' if fault == 'cubic' else mode)
    with pytest.raises(ValueError): payload(rig, sampler, 'digest')
