"""Small GLB reader/writer and CPU skin evaluation for this measured fixture.

Implements glTF 2.0 TRS and column-major matrices. Unsupported layouts fail
explicitly; this is not a general glTF import library.
"""
import copy
import json
import struct
from pathlib import Path
import numpy as np


def authored_animation(label):
    """Avoid engine name-hint loop inference; retain the user's label explicitly."""
    return dict(name='Strep · '+label+' · motion',extras=dict(strep_label=label),channels=[],samplers=[])
from scipy.spatial.transform import Rotation

DTYPES = {5120: 'i1', 5121: 'u1', 5122: '<i2', 5123: '<u2', 5125: '<u4', 5126: '<f4'}
SIZES = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def read_glb(path):
    raw = Path(path).read_bytes()
    magic, version, length = struct.unpack_from('<III', raw)
    if magic != 0x46546c67 or version != 2 or length != len(raw):
        raise ValueError('Invalid GLB header')
    pos, document, binary = 12, None, None
    while pos < len(raw):
        size, kind = struct.unpack_from('<II', raw, pos)
        chunk = raw[pos + 8:pos + 8 + size]
        if kind == 0x4E4F534A:
            document = json.loads(chunk)
        elif kind == 0x004E4942:
            binary = chunk
        pos += size + 8
    if document is None or binary is None:
        raise ValueError('Missing GLB chunks')
    return document, binary


def accessor(document, binary, index):
    item = document['accessors'][index]
    if 'sparse' in item or item.get('normalized'):
        raise ValueError('Unsupported sparse/normalized accessor')
    view = document['bufferViews'][item['bufferView']]
    if view['buffer'] != 0:
        raise ValueError('External buffers unsupported')
    dtype = np.dtype(DTYPES[item['componentType']])
    count, width = item['count'], SIZES[item['type']]
    offset = view.get('byteOffset', 0) + item.get('byteOffset', 0)
    stride = view.get('byteStride', width * dtype.itemsize)
    array = np.ndarray((count, width), dtype=dtype, buffer=binary, offset=offset, strides=(stride, dtype.itemsize)).copy()
    if item['type'] == 'MAT4':
        return array.reshape(count, 4, 4).transpose(0, 2, 1)
    return array[:, 0] if width == 1 else array


def local_matrix(node):
    if 'matrix' in node:
        return np.array(node['matrix']).reshape(4, 4).T
    result = np.eye(4)
    result[:3, :3] = Rotation.from_quat(node.get('rotation', [0, 0, 0, 1])).as_matrix() @ np.diag(node.get('scale', [1, 1, 1]))
    result[:3, 3] = node.get('translation', [0, 0, 0])
    return result


def hierarchy(document):
    parents = [-1] * len(document['nodes'])
    for i, node in enumerate(document['nodes']):
        for child in node.get('children', []):
            if parents[child] != -1:
                raise ValueError('Multiple parents')
            parents[child] = i
    return parents


def global_matrices(document, overrides=None):
    parents = hierarchy(document)
    local = [local_matrix(node) for node in document['nodes']]
    for index, matrix in (overrides or {}).items():
        local[index] = matrix
    result = {}
    def visit(i):
        if i not in result:
            result[i] = local[i] if parents[i] < 0 else visit(parents[i]) @ local[i]
        return result[i]
    return np.array([visit(i) for i in range(len(local))])


def skin_vertices(document, binary, matrices, mesh_node=2):
    node = document['nodes'][mesh_node]
    primitive = document['meshes'][node['mesh']]['primitives'][0]
    attr = primitive['attributes']
    vertices = accessor(document, binary, attr['POSITION'])
    joints = accessor(document, binary, attr['JOINTS_0']).astype(int)
    weights = accessor(document, binary, attr['WEIGHTS_0'])
    skin = document['skins'][node['skin']]
    inverse = accessor(document, binary, skin['inverseBindMatrices'])
    transforms = matrices[skin['joints']] @ inverse
    points = np.c_[vertices, np.ones(len(vertices))]
    posed = np.einsum('nvij,nj->nvi', transforms[joints], points)
    return np.sum(posed[:, :, :3] * weights[:, :, None], axis=1)


def append_accessor(document, binary, array, kind):
    array = np.asarray(array, dtype='<f4')
    while len(binary) % 4:
        binary.append(0)
    start = len(binary)
    binary.extend(array.tobytes())
    view = len(document['bufferViews'])
    document['bufferViews'].append({'buffer': 0, 'byteOffset': start, 'byteLength': array.nbytes})
    item = {'bufferView': view, 'componentType': 5126, 'count': len(array), 'type': kind}
    if kind == 'SCALAR':
        item.update(min=[float(array.min())], max=[float(array.max())])
    index = len(document['accessors'])
    document['accessors'].append(item)
    return index


def write_glb(path, document, binary):
    document = copy.deepcopy(document)
    document['buffers'] = [{'byteLength': len(binary)}]
    encoded = json.dumps(document, separators=(',', ':'), allow_nan=False).encode()
    encoded += b' ' * (-len(encoded) % 4)
    binary = bytes(binary) + b'\0' * (-len(binary) % 4)
    raw = struct.pack('<III', 0x46546c67, 2, 28 + len(encoded) + len(binary))
    raw += struct.pack('<II', len(encoded), 0x4E4F534A) + encoded
    raw += struct.pack('<II', len(binary), 0x004E4942) + binary
    Path(path).write_bytes(raw)


def sample_animation(document, binary, animation_index, frame):
    nodes = copy.deepcopy(document['nodes'])
    animation = document['animations'][animation_index]
    for channel in animation['channels']:
        sampler = animation['samplers'][channel['sampler']]
        node, path = channel['target']['node'], channel['target']['path']
        values = accessor(document, binary, sampler['output'])
        nodes[node][path] = values[frame].tolist()
        if 'matrix' in nodes[node]:
            raise ValueError('Animated TRS on matrix node')
    return global_matrices({**document, 'nodes': nodes})
