"""Changed-key support, clamping and fail-closed snapshot inheritance."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from gltf_tools import append_accessor
from native_rotation_support import rotation_support
from rig_clip_import import AnimationSampler


def fixture(clock=None):
    clock = np.asarray(np.arange(6) if clock is None else clock, dtype=np.float32)
    doc = dict(asset={'version':'2.0'}, nodes=[{'name':'arm'}, {'name':'hand'}, {'name':'root'}],
               buffers=[{'byteLength':0}], accessors=[], bufferViews=[], animations=[{'channels':[], 'samplers':[]}])
    binary = bytearray(); animation = doc['animations'][0]
    for node in [0, 1]:
        t = append_accessor(doc, binary, clock, 'SCALAR')
        q = Rotation.from_euler('z', np.arange(len(clock))*3, degrees=True).as_quat().astype(np.float32)
        output = append_accessor(doc, binary, q, 'VEC4')
        animation['channels'].append({'target':{'node':node, 'path':'rotation'}, 'sampler':len(animation['samplers'])})
        animation['samplers'].append({'input':t, 'output':output, 'interpolation':'LINEAR'})
    t = append_accessor(doc, binary, np.array([0, 7], dtype=np.float32), 'SCALAR')
    output = append_accessor(doc, binary, np.zeros((2, 3), dtype=np.float32), 'VEC3')
    animation['channels'].append({'target':{'node':2, 'path':'translation'}, 'sampler':len(animation['samplers'])})
    animation['samplers'].append({'input':t, 'output':output, 'interpolation':'LINEAR'})
    doc['buffers'][0]['byteLength'] = len(binary)
    return doc, bytes(binary)


def edited(doc, binary, edits):
    new = copy.deepcopy(doc); payload = bytearray(binary)
    sampler = AnimationSampler(doc, binary, 0)
    for node, keys in edits.items():
        values = next(v.copy() for n, path, t, v, mode in sampler.channels if n == node and path == 'rotation')
        values[keys] = Rotation.from_euler('xyz', [19, -11, 7], degrees=True).as_quat()
        channel = new['animations'][0]['channels'][node]
        descriptor = copy.deepcopy(new['animations'][0]['samplers'][channel['sampler']])
        descriptor['output'] = append_accessor(new, payload, values.astype(np.float32), 'VEC4')
        channel['sampler'] = len(new['animations'][0]['samplers'])
        new['animations'][0]['samplers'].append(descriptor)
    new['buffers'][0]['byteLength'] = len(payload)
    return new, bytes(payload)


@pytest.mark.parametrize('keys,expected', [([2], [[1.,3.]]), ([1,4], [[0.,2.],[3.,5.]]),
                                        ([0], [[0.,1.]]), ([5], [[4.,7.]]),
                                        ([2,3], [[1.,4.]])])
def test_clamped_and_merged_support_matches_native_decoder_outside(keys, expected):
    doc, binary = fixture(); new, payload = edited(doc, binary, {0:keys})
    proof = rotation_support(doc, binary, new, payload, [0])
    assert proof['support_intervals_s'] == expected
    assert not proof['quality_approved'] and not proof['release_approved']
    before = AnimationSampler(doc, binary, 0); after = AnimationSampler(new, payload, 0)
    left = next(c for c in before.channels if c[:2] == (0, 'rotation'))
    right = next(c for c in after.channels if c[:2] == (0, 'rotation'))
    for time in np.linspace(0, 7, 701):
        if any(a <= time <= b for a, b in expected):
            continue
        np.testing.assert_array_equal(before.value(left[1], *left[2:], float(time)),
                                      after.value(right[1], *right[2:], float(time)))


def test_multiple_nodes_union_and_exact_identity():
    doc, binary = fixture(); new, payload = edited(doc, binary, {0:[1], 1:[3]})
    assert rotation_support(doc, binary, new, payload, [0,1])['support_intervals_s'] == [[0.,4.]]
    assert rotation_support(doc, binary, doc, binary, [0,1])['support_intervals_s'] == []


def test_single_key_change_invalidates_whole_clamped_duration():
    doc, binary = fixture([2]); new, payload = edited(doc, binary, {0:[0]})
    assert rotation_support(doc, binary, new, payload, [0])['support_intervals_s'] == [[0.,7.]]


@pytest.mark.parametrize('fault', ['binary','node','clock','mode','nonselected','sampler-prefix',
                                  'external-buffer','metadata','nan','nonunit','shape','weights-path'])
def test_changed_inputs_or_unsupported_native_semantics_fail_closed(fault):
    doc, binary = fixture(); new, payload = edited(doc, binary, {0:[2]})
    animation = new['animations'][0]; selected = animation['samplers'][animation['channels'][0]['sampler']]
    if fault == 'binary': payload = bytes([binary[0]^1])+payload[1:]
    elif fault == 'node': new['nodes'][0]['translation'] = [1,0,0]
    elif fault == 'mode': selected['interpolation'] = 'STEP'
    elif fault == 'nonselected': animation['channels'][1]['sampler'] = animation['channels'][0]['sampler']
    elif fault == 'sampler-prefix': animation['samplers'][0]['interpolation'] = 'STEP'
    elif fault == 'external-buffer': new['buffers'][0]['uri'] = 'external.bin'
    elif fault == 'metadata': animation['extras'] = {'different':True}
    elif fault == 'weights-path':
        doc['animations'][0]['channels'][2]['target']['path'] = 'weights'
        animation['channels'][2]['target']['path'] = 'weights'
    else:
        scratch = bytearray(payload)
        if fault == 'clock':
            selected['input'] = append_accessor(new, scratch, np.arange(6, dtype=np.float32)+.01, 'SCALAR')
        else:
            q = np.tile([0.,0.,0.,1.], (6,1)).astype(np.float32)
            if fault == 'nan': q[2,0] = np.nan
            elif fault == 'nonunit': q[2,3] = 2.
            elif fault == 'shape': q = q[:5]
            selected['output'] = append_accessor(new, scratch, q, 'VEC4')
        payload = bytes(scratch); new['buffers'][0]['byteLength'] = len(payload)
    with pytest.raises(ValueError): rotation_support(doc, binary, new, payload, [0])


@pytest.mark.parametrize('nodes', [[True],[0,0],[-1],[3],[2]])
def test_invalid_or_missing_selected_nodes_fail(nodes):
    doc, binary = fixture()
    with pytest.raises(ValueError): rotation_support(doc, binary, doc, binary, nodes)
