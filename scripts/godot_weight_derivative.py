"""Opt-in GLB weight derivative for the pinned Godot import experiment.

Keep the original asset and every unrelated payload byte. This changes weight
coefficients slightly; its receipt is not a fidelity or animation approval.
"""
import argparse
import copy
from pathlib import Path
import numpy as np
from gltf_tools import DTYPES, SIZES, write_glb
from rig_asset import RigAsset, array
from native_scene_imported_skin import godot_normalize
from native_engine_contacts import packed_weights
from strep import sha256, save


def balanced_pairs(joints, weights):
    joints, weights = np.asarray(joints), np.asarray(weights, float)
    if (weights.ndim != 2 or weights.shape[1] not in (4, 8) or not len(weights)
            or joints.shape != weights.shape or joints.dtype.kind not in 'iu'
            or not np.isfinite(weights).all() or np.any(weights < 0)
            or np.any(weights.sum(axis=1) <= 0)):
        raise ValueError('Complete finite four/eight influence pairs required')
    normalized = weights / weights.sum(axis=1, keepdims=True)
    scaled = normalized * 65535
    integers = np.floor(scaled).astype(np.int64)
    remaining = 65535 - integers.sum(axis=1)
    if np.any(remaining < 0) or np.any(remaining >= weights.shape[1]):
        raise ValueError('Invalid largest-remainder allocation')
    fractions = np.argsort(-(scaled - integers), axis=1, kind='stable')
    for slot in range(weights.shape[1]):
        rows = np.flatnonzero(remaining > slot)
        integers[rows, fractions[rows, slot]] += 1
    order = np.argsort(integers, axis=1, kind='stable')
    encoded = np.take_along_axis(integers, order, axis=1).astype(np.float32) / np.float32(65535)
    sorted_joints = np.take_along_axis(joints, order, axis=1)
    sorted_integers = np.take_along_axis(integers, order, axis=1)
    result_joints, result_weights = sorted_joints.copy(), encoded.copy()
    resolved = np.zeros(len(weights), bool)
    # A float32 sequential sum can exceed one even in ascending order. Select
    # the first cyclic pair order whose simulated import keeps every allocated
    # integer. No weight-only reorder, changed integer or relaxed mass bound.
    for shift in range(weights.shape[1]):
        rows = np.flatnonzero(~resolved)
        if not len(rows): break
        candidate = np.roll(encoded[rows], shift, axis=1)
        desired = np.roll(sorted_integers[rows], shift, axis=1)
        actual = np.rint(packed_weights(godot_normalize(candidate))*65535).astype(np.int64)
        good = rows[np.all(actual == desired, axis=1)]
        result_weights[good] = np.roll(encoded[good], shift, axis=1)
        result_joints[good] = np.roll(sorted_joints[good], shift, axis=1)
        resolved[good] = True
    if not resolved.all(): raise ValueError('No checked cyclic pair order preserves every allocated weight')
    return result_joints, result_weights


def layout(document, binary, number):
    accessor = document['accessors'][number]; view = document['bufferViews'][accessor['bufferView']]
    if accessor['type'] != 'VEC4' or accessor.get('normalized') or 'sparse' in accessor:
        raise ValueError('Plain four-component influence accessors required')
    dtype = np.dtype(DTYPES[accessor['componentType']])
    start = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
    stride = view.get('byteStride', 4 * dtype.itemsize)
    return np.ndarray((accessor['count'], 4), dtype=dtype, buffer=binary,
                      offset=start, strides=(stride, dtype.itemsize))


def derivative(source, output, *, source_sha256):
    source, output = Path(source).resolve(), Path(output).resolve()
    receipt = Path(str(output) + '.weights.json')
    if source == output or output.exists() or receipt.exists():
        raise ValueError('Fresh derivative asset and receipt paths required')
    if sha256(source) != source_sha256: raise ValueError('Exact original asset digest required')
    rig = RigAsset.load(source); document = copy.deepcopy(rig.document)
    binary = bytearray(rig.binary); assignments = {}; affected = set(); rows = []
    for entry in rig.primitives:
        if entry['joints'] is None: continue
        primitive = document['meshes'][document['nodes'][entry['node']]['mesh']]['primitives'][entry['primitive']]
        attributes = primitive['attributes']; channels = [0] + ([1] if 'WEIGHTS_1' in attributes else [])
        if any(document['accessors'][attributes[f'WEIGHTS_{i}']]['componentType'] != 5126 for i in channels):
            raise ValueError('Derivative v1 requires original float32 weights; no encoding substitution')
        raw = np.concatenate([array(document, rig.binary, attributes[f'WEIGHTS_{i}']) for i in channels], axis=1)
        joints, weights = balanced_pairs(entry['joints'], raw)
        for i in channels:
            for kind, values in [('JOINTS', joints), ('WEIGHTS', weights)]:
                number = attributes[f'{kind}_{i}']; value = values[:, 4*i:4*i+4]
                if any(k in document['accessors'][number] for k in ('min', 'max')):
                    raise ValueError('Influence bounds unsupported; do not retain stale extrema')
                if number in assignments and not np.array_equal(assignments[number], value):
                    raise ValueError('Shared influence accessor requires incompatible derivatives')
                assignments[number] = value; affected.add(number)
        imported = packed_weights(godot_normalize(weights))
        rows.append(dict(node=entry['node'], primitive=entry['primitive'], vertices=len(raw),
            influences=raw.shape[1], maximum_predicted_mass_deficit=float((1-imported.sum(axis=1)).max()),
            mean_predicted_mass_deficit=float((1-imported.sum(axis=1)).mean())))
    # Prove writable influence bytes never alias a different accessor, image or
    # unrelated payload. Shared influence accessors must request identical data.
    mask = np.zeros(len(binary), bool)
    for number in assignments:
        view = layout(document, binary, number)
        accessor = document['accessors'][number]; descriptor = document['bufferViews'][accessor['bufferView']]
        start = descriptor.get('byteOffset', 0) + accessor.get('byteOffset', 0)
        for component in range(4 * view.dtype.itemsize):
            ids = start + component + np.arange(len(view)) * view.strides[0]
            if mask[ids].any(): raise ValueError('Aliased influence accessor payload unsupported')
            mask[ids] = True
    for number, item in enumerate(document['accessors']):
        if number in affected: continue
        descriptor = document['bufferViews'][item['bufferView']]
        start = descriptor.get('byteOffset', 0) + item.get('byteOffset', 0)
        width = SIZES[item['type']] * np.dtype(DTYPES[item['componentType']]).itemsize
        stride = descriptor.get('byteStride', width)
        if any(mask[start+c+np.arange(item['count'])*stride].any() for c in range(width)):
            raise ValueError('Influence bytes alias an unrelated accessor')
    for image in document.get('images', []):
        descriptor = document['bufferViews'][image['bufferView']]
        start = descriptor.get('byteOffset', 0)
        if mask[start:start+descriptor['byteLength']].any(): raise ValueError('Influence bytes alias an image')
    for number, value in assignments.items():
        layout(document, binary, number)[:] = value
    before, after = np.frombuffer(rig.binary, np.uint8), np.frombuffer(binary, np.uint8)
    if not np.array_equal(before[~mask], after[~mask]): raise ValueError('Unrelated payload changed')
    output.parent.mkdir(parents=True, exist_ok=True); write_glb(output, document, binary)
    loaded = RigAsset.load(output)
    if loaded.document != document or loaded.binary != bytes(binary):
        raise ValueError('Derivative serialization changed document or payload')
    for number, value in assignments.items():
        if not np.array_equal(array(document, loaded.binary, number), value):
            raise ValueError('Derivative influence payload changed')
    if sha256(source) != source_sha256: raise ValueError('Original asset changed')
    result = dict(schema='strep-godot-weight-derivative-v1', source=str(source), source_sha256=source_sha256,
        output=str(output), output_sha256=sha256(output), method_sha256=sha256(__file__),
        method='Largest-remainder unsigned16 allocation, float32 encoding, first checked cyclic order of stable ascending joint/weight pairs',
        original_asset_preserved=True, unrelated_document_and_payload_preserved=True,
        original_weight_coefficients_exact=False, primitive_rows=rows,
        engine_playback_verified=False, original_skin_fidelity_verified=False,
        quality_approved=False, release_approved=False)
    save(receipt, result); return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source'); parser.add_argument('output'); parser.add_argument('--source-sha256', required=True)
    args = parser.parse_args(); result = derivative(args.source, args.output, source_sha256=args.source_sha256)
    print(dict(output_sha256=result['output_sha256'], release_approved=False))
