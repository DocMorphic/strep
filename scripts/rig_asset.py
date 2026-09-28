"""Validated, self-contained GLB rig input for the first general transfer path.

This deliberately has a smaller supported surface than all of glTF. Rejecting an
unsupported asset is preferable to silently dropping skinning or morph channels.
Historical fixture readers remain unchanged for reproducibility.
"""
import json
import struct
from pathlib import Path
import numpy as np
from gltf_tools import local_matrix, global_matrices, DTYPES, SIZES


def read_asset(path):
    raw = Path(path).read_bytes()
    if len(raw) < 20 or struct.unpack_from('<III', raw) != (0x46546C67, 2, len(raw)):
        raise ValueError('Invalid GLB 2 header')
    chunks, offset = [], 12
    while offset < len(raw):
        if offset + 8 > len(raw):
            raise ValueError('Truncated GLB chunk header')
        size, kind = struct.unpack_from('<II', raw, offset)
        if size % 4 or offset + 8 + size > len(raw):
            raise ValueError('Invalid GLB chunk bounds/alignment')
        chunks.append((kind, raw[offset + 8:offset + 8 + size]))
        offset += 8 + size
    if [kind for kind, _ in chunks] != [0x4E4F534A, 0x004E4942]:
        raise ValueError('Expected exactly JSON and BIN chunks')
    document = json.loads(chunks[0][1])
    binary = chunks[1][1]
    if document.get('asset', {}).get('version') != '2.0':
        raise ValueError('Only glTF 2.0 supported')
    buffers = document.get('buffers', [])
    if len(buffers) != 1 or 'uri' in buffers[0]:
        raise ValueError('A single embedded buffer is required')
    length = buffers[0].get('byteLength', -1)
    if not isinstance(length, int) or length < 0 or not 0 <= len(binary) - length <= 3:
        raise ValueError('Invalid embedded buffer length')
    if any('uri' in image for image in document.get('images', [])):
        raise ValueError('External/data-URI images unsupported; embed images in GLB')
    if document.get('extensionsRequired'):
        raise ValueError('Required glTF extensions are not supported by rig import v1')
    # Optional compression/instancing/quantization can also alter geometry.
    unsupported = {'KHR_draco_mesh_compression', 'EXT_meshopt_compression',
                   'EXT_mesh_gpu_instancing', 'KHR_mesh_quantization'}
    if unsupported.intersection(document.get('extensionsUsed', [])):
        raise ValueError('Compressed, quantized or instanced geometry unsupported')
    return document, binary[:length]


def index(items, value, label):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < len(items):
        raise ValueError(f'Invalid {label} index: {value}')
    return items[value]


def array(document, binary, number):
    item = index(document.get('accessors', []), number, 'accessor')
    if 'sparse' in item or 'bufferView' not in item:
        raise ValueError('Sparse/implicit-zero accessors unsupported')
    view = index(document.get('bufferViews', []), item['bufferView'], 'bufferView')
    if view.get('buffer') != 0:
        raise ValueError('External buffer unsupported')
    try:
        dtype, width = np.dtype(DTYPES[item['componentType']]), SIZES[item['type']]
    except KeyError as error:
        raise ValueError('Unsupported accessor encoding') from error
    count, start, size = item.get('count'), view.get('byteOffset', 0), view.get('byteLength')
    offset, stride = item.get('byteOffset', 0), view.get('byteStride', width * dtype.itemsize)
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (count, start, size, offset, stride)):
        raise ValueError('Accessor offsets/counts must be integers')
    if min(start, size, offset) < 0 or count < 1 or stride < width * dtype.itemsize:
        raise ValueError('Invalid accessor range or stride')
    if start + size > len(binary) or offset + (count - 1) * stride + width * dtype.itemsize > size:
        raise ValueError('Accessor exceeds bufferView bounds')
    if (start + offset) % dtype.itemsize or stride % dtype.itemsize:
        raise ValueError('Misaligned accessor')
    values = np.ndarray((count, width), dtype=dtype, buffer=binary,
                        offset=start + offset, strides=(stride, dtype.itemsize)).copy()
    if item.get('normalized'):
        if dtype.kind not in 'iu' or dtype.itemsize > 2:
            raise ValueError('Invalid normalized accessor component type')
        values = values.astype(float) / np.iinfo(dtype).max
        if dtype.kind == 'i':
            values = np.maximum(values, -1)
    if not np.isfinite(values).all():
        raise ValueError('Non-finite accessor')
    if item['type'] == 'MAT4':
        return values.reshape(count, 4, 4).transpose(0, 2, 1)
    return values[:, 0] if width == 1 else values


def parents_of(document):
    nodes = document.get('nodes', [])
    if not nodes:
        raise ValueError('Rig has no nodes')
    parents = [-1] * len(nodes)
    for parent, node in enumerate(nodes):
        for child in node.get('children', []):
            index(nodes, child, 'child')
            if parents[child] != -1:
                raise ValueError('A node has multiple parents or duplicate children')
            parents[child] = parent
    for node in range(len(nodes)):
        seen = set()
        while node != -1:
            if node in seen:
                raise ValueError('Cycle in rig hierarchy')
            seen.add(node)
            node = parents[node]
    return parents


class RigAsset:
    def __init__(self, document, binary):
        self.document, self.binary = document, binary
        self.parents = parents_of(document)
        nodes = document['nodes']
        # v1 transfer solves rigid rotations; never silently strip reflection,
        # nonuniform scale or shear with Rotation.from_matrix.
        for node in nodes:
            if 'matrix' in node and any(k in node for k in ('translation', 'rotation', 'scale')):
                raise ValueError('Node combines matrix and TRS')
            if 'rotation' in node and abs(np.linalg.norm(node['rotation']) - 1) > 1e-5:
                raise ValueError('Node quaternion must be normalized')
            matrix = local_matrix(node)
            if not np.isfinite(matrix).all() or not np.allclose(matrix[3], [0, 0, 0, 1], atol=1e-7):
                raise ValueError('Invalid affine node matrix')
            if not np.allclose(matrix[:3, :3].T @ matrix[:3, :3], np.eye(3), atol=1e-5) or abs(np.linalg.det(matrix[:3, :3]) - 1) > 1e-5:
                raise ValueError('Rig import v1 requires unit scale and proper rigid node transforms')
        self.reference = global_matrices(document)
        skins = document.get('skins', [])
        if len(skins) != 1:
            raise ValueError('Rig import v1 requires exactly one skin')
        self.skin = skins[0]
        self.joints = self.skin.get('joints', [])
        for joint in self.joints:
            index(nodes, joint, 'skin joint')
        if not self.joints or len(set(self.joints)) != len(self.joints):
            raise ValueError('Empty or duplicate skin joints')
        self.inverse = (array(document, binary, self.skin['inverseBindMatrices'])
                        if 'inverseBindMatrices' in self.skin else np.repeat(np.eye(4)[None], len(self.joints), axis=0))
        if 'inverseBindMatrices' in self.skin:
            acc = document['accessors'][self.skin['inverseBindMatrices']]
            if acc['type'] != 'MAT4' or acc['componentType'] != 5126 or acc.get('normalized'):
                raise ValueError('Inverse binds require float MAT4')
        if self.inverse.shape != (len(self.joints), 4, 4) or not np.allclose(self.inverse[:, 3], [0, 0, 0, 1], atol=1e-5):
            raise ValueError('Invalid inverse bind matrices')
        if np.any(np.abs(np.linalg.det(self.inverse)) < 1e-10):
            raise ValueError('Singular inverse bind matrix')
        scenes = document.get('scenes', [])
        scene = index(scenes, document.get('scene', 0), 'scene')
        self.active = set()
        def visit(node):
            index(nodes, node, 'scene node')
            self.active.add(node)
            for child in nodes[node].get('children', []):
                visit(child)
        for root in scene.get('nodes', []):
            index(nodes, root, 'scene root')
            if self.parents[root] != -1:
                raise ValueError('Scene roots must be hierarchy roots')
            visit(root)
        if not set(self.joints).issubset(self.active):
            raise ValueError('All skin joints must belong to the selected scene')
        self.primitives = []
        for node_number in sorted(self.active):
            node = nodes[node_number]
            if 'mesh' not in node:
                continue
            if 'skin' in node and node['skin'] != 0:
                raise ValueError('Unexpected skin index')
            mesh = index(document.get('meshes', []), node['mesh'], 'mesh')
            for primitive_number, primitive in enumerate(mesh['primitives']):
                if primitive.get('targets') or mesh.get('weights') or node.get('weights'):
                    raise ValueError('Morph targets unsupported in rig transfer v1')
                if primitive.get('mode', 4) != 4:
                    raise ValueError('Only triangle primitives supported')
                attributes = primitive['attributes']
                positions = array(document, binary, attributes['POSITION'])
                if positions.ndim != 2 or positions.shape[1] != 3 or document['accessors'][attributes['POSITION']]['componentType'] != 5126:
                    raise ValueError('POSITION must be float VEC3')
                joints, weights = None, None
                if 'skin' in node:
                    if any(name.startswith(('JOINTS_', 'WEIGHTS_')) and name not in ('JOINTS_0', 'WEIGHTS_0', 'JOINTS_1', 'WEIGHTS_1') for name in attributes):
                        raise ValueError('At most eight skin influences supported')
                    joints, weights = [], []
                    for channel in (0, 1):
                        j, w = f'JOINTS_{channel}', f'WEIGHTS_{channel}'
                        if channel == 1 and j not in attributes and w not in attributes:
                            continue
                        if j not in attributes or w not in attributes:
                            raise ValueError('Skin joints and weights must be paired')
                        ja, wa = (document['accessors'][attributes[key]] for key in (j, w))
                        if ja['type'] != 'VEC4' or ja['componentType'] not in (5121, 5123) or ja.get('normalized'):
                            raise ValueError('JOINTS must be unsigned integer VEC4')
                        if wa['type'] != 'VEC4' or not (wa['componentType'] == 5126 and not wa.get('normalized') or wa['componentType'] in (5121, 5123) and wa.get('normalized')):
                            raise ValueError('WEIGHTS must be float or normalized unsigned VEC4')
                        joints.append(array(document, binary, attributes[j]))
                        weights.append(array(document, binary, attributes[w]))
                    joints, weights = np.concatenate(joints, axis=1), np.concatenate(weights, axis=1)
                    if joints.shape[0] != len(positions) or weights.shape != joints.shape or joints.max() >= len(self.joints):
                        raise ValueError('Skin influence shape or joint index mismatch')
                    if np.any(weights < 0) or np.max(np.abs(weights.sum(axis=1) - 1)) > 1e-3:
                        raise ValueError('Skin weights must be nonnegative and sum to one')
                    weights = weights / weights.sum(axis=1, keepdims=True)
                self.primitives.append(dict(node=node_number, primitive=primitive_number,
                                            positions=positions, joints=joints, weights=weights))
        if not any(p['joints'] is not None for p in self.primitives):
            raise ValueError('Selected scene contains no skinned mesh')

    @classmethod
    def load(cls, path):
        return cls(*read_asset(path))

    def vertices(self, matrices):
        transforms = matrices[self.joints] @ self.inverse
        result = []
        for primitive in self.primitives:
            points = np.c_[primitive['positions'], np.ones(len(primitive['positions']))]
            if primitive['joints'] is None:
                posed = (matrices[primitive['node']] @ points.T).T[:, :3]
            else:
                # glTF 2.0: skinned mesh-node transform is ignored. Bind-shape
                # transforms may already be baked into inverse binds/vertices.
                posed = np.einsum('nvij,nj->nvi', transforms[primitive['joints']], points)
                posed = np.sum(posed[:, :, :3] * primitive['weights'][:, :, None], axis=1)
            result.append(posed)
        return np.concatenate(result)

    def inventory(self):
        return dict(nodes=[dict(index=i, name=n.get('name'), parent=self.parents[i],
                               skin_joint=i in self.joints, reference_position_m=self.reference[i, :3, 3].tolist())
                           for i, n in enumerate(self.document['nodes'])],
                    primitives=[dict(node=p['node'], primitive=p['primitive'], vertices=len(p['positions']),
                                     influences=0 if p['joints'] is None else p['joints'].shape[1]) for p in self.primitives],
                    original_animations=[a.get('name', f'animation-{i}') for i, a in enumerate(self.document.get('animations', []))],
                    reference_pose='Default node transforms; inverse binds are preserved, not assumed to be the reference pose',
                    reference_mesh_min_y_m=float(self.vertices(self.reference)[:, 1].min()))
