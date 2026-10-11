"""Locate recorded stored/unrounded rate failures without loading a motion model.

Reads one-actor storage-comparison receipts, not arbitrary NPZ motion files.
No pose decoding, geometry computation, correction or approval is performed.
"""
import argparse
import array
import ast
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import zipfile


GROUPS = ('track_bound', 'joint_displacement', 'position_speed',
          'position_acceleration', 'angular_speed', 'angular_acceleration')


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate receipt field: ' + key)
        result[key] = value
    return result


def nonfinite(value):
    raise ValueError('Nonfinite receipt value: ' + value)


def read(path):
    return json.loads(Path(path).read_bytes(), object_pairs_hook=unique, parse_constant=nonfinite)


def vector(archive, name):
    """Read only a finite, one-dimensional little-endian Float64 NPY vector."""
    member = name + '.npy'
    if archive.namelist().count(member) != 1:
        raise ValueError('One complete ' + member + ' required')
    info = archive.getinfo(member)
    if info.file_size > 8_020_000:
        raise ValueError('Recorded vector exceeds the inspection budget')
    raw = archive.read(member)
    if raw[:6] != b'\x93NUMPY' or len(raw) < 12:
        raise ValueError('NPY vector header required')
    if raw[6:8] == b'\x01\x00':
        start = 10; length = struct.unpack_from('<H', raw, 8)[0]
    elif raw[6:8] in (b'\x02\x00', b'\x03\x00'):
        start = 12; length = struct.unpack_from('<I', raw, 8)[0]
    else:
        raise ValueError('Supported NPY header version required')
    if not 1 <= length <= 16384 or start + length > len(raw):
        raise ValueError('Complete bounded NPY header required')
    header = ast.literal_eval(raw[start:start+length].decode('latin1'))
    shape = header.get('shape') if isinstance(header, dict) else None
    if (not isinstance(shape, tuple) or len(shape) != 1 or type(shape[0]) is not int
            or not 1 <= shape[0] <= 1_000_000 or header.get('descr') != '<f8'
            or header.get('fortran_order') is not False or len(raw)-start-length != shape[0]*8):
        raise ValueError('Complete one-dimensional little-endian Float64 vector required')
    values = array.array('d'); values.frombytes(raw[start+length:])
    if sys.byteorder != 'little': values.byteswap()
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Finite recorded vector required')
    return values


def rig_joints(path):
    """Read joint order/parents from the bound source's GLB JSON only."""
    path = Path(path)
    with path.open('rb') as stream:
        header = stream.read(20)
        if len(header) != 20: raise ValueError('Complete GLB header required')
        magic, version, total, length, kind = struct.unpack('<4sIIII', header)
        if (magic != b'glTF' or version != 2 or total != path.stat().st_size
                or kind != 0x4E4F534A or not 1 <= length <= 4_194_304 or 20+length > total):
            raise ValueError('Bound GLB with a complete JSON chunk required')
        document = json.loads(stream.read(length), object_pairs_hook=unique, parse_constant=nonfinite)
    nodes, skins = document.get('nodes'), document.get('skins')
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= 10000 or not isinstance(skins, list) or len(skins) != 1:
        raise ValueError('One source skin with complete node identities required')
    joints = skins[0].get('joints') if isinstance(skins[0], dict) else None
    if (not isinstance(joints, list) or not joints
            or any(type(i) is not int or not 0 <= i < len(nodes) for i in joints)
            or len(set(joints)) != len(joints)):
        raise ValueError('Distinct existing source skin joints required')
    parents = [-1]*len(nodes)
    for i, node in enumerate(nodes):
        if not isinstance(node, dict) or ('name' in node and not isinstance(node['name'], str)):
            raise ValueError('Valid source node identity required')
        children = node.get('children', [])
        if not isinstance(children, list): raise ValueError('Explicit child indices required')
        for child in children:
            if type(child) is not int or not 0 <= child < len(nodes) or parents[child] != -1:
                raise ValueError('Distinct existing child with one parent required')
            parents[child] = i
    for node in range(len(nodes)):
        seen = set(); current = node
        while current >= 0:
            if current in seen: raise ValueError('Acyclic source hierarchy required')
            seen.add(current); current = parents[current]
    return nodes, joints, parents


def diagnose(receipt_path, observations_path, source_path, bindings_path, actor, *, detail_offset=0, maximum_details=256):
    if (type(detail_offset) is not int or detail_offset < 0 or type(maximum_details) is not int
            or not 1 <= maximum_details <= 10000):
        raise ValueError('Nonnegative detail offset and 1-10000 detail rows required')
    paths = [Path(p).resolve() for p in (receipt_path, observations_path, source_path, bindings_path)]
    receipt_path, observations_path, source_path, bindings_path = paths
    checksums = {str(p): digest(p) for p in paths}
    implementation = str(Path(__file__).resolve());checksums[implementation] = digest(implementation)
    receipt, source, binding = read(receipt_path), read(source_path), read(bindings_path)
    if (binding.get('status') != 'complete' or not isinstance(binding.get('cases'), list)
            or binding['cases'].count(receipt) != 1 or receipt.get('observations_sha256') != checksums[str(observations_path)]):
        raise ValueError('Receipt and observations must belong to the complete retained comparison')
    declared = binding.get('source_bindings_sha256')
    if not isinstance(declared, dict) or checksums[str(source_path)] not in declared.values():
        raise ValueError('Source contact request is not bound by the retained comparison')
    actors = source.get('actors')
    if not isinstance(actors, dict) or set(actors) != {actor}:
        raise ValueError('This receipt layout requires exactly one named actor')
    asset = actors[actor]; path = Path(asset['glb'])
    if not path.is_absolute(): path = source_path.parent/path
    path = path.resolve(); checksum = digest(path)
    if checksum != asset.get('sha256') or checksum not in declared.values():
        raise ValueError('Source rig identity differs from the retained comparison')
    checksums[str(path)] = checksum
    nodes, joints, parents = rig_joints(path)
    with zipfile.ZipFile(observations_path) as archive:
        stored, unrounded, caps, scales, times = [vector(archive, name) for name in
            ('stored_residual', 'unrounded_residual', 'native_caps', 'native_scales', 'uniform_times_s')]
    if (len(times) < 3 or times[0] < 0 or any(b <= a for a, b in zip(times, times[1:]))
            or not len(stored) == len(unrounded) == len(caps) == len(scales) == receipt.get('conditions')
            or any(v <= 0 for v in scales)):
        raise ValueError('Complete residual, scale and ordered rate-clock populations required')
    groups = receipt.get('groups'); count = len(joints)
    if not isinstance(groups, list) or [g.get('metric') for g in groups] != list(GROUPS):
        raise ValueError('Complete ordered native condition groups required')
    expected = [None, len(times)*count, (len(times)-1)*count, (len(times)-2)*count,
                (len(times)-1)*count, (len(times)-2)*count]
    output = []; offset = 0; failures = []; failure_count = 0
    for index, (group, size) in enumerate(zip(groups, expected)):
        length = group.get('conditions')
        if type(length) is not int or length < 1 or offset+length > len(stored) or size is not None and length != size:
            raise ValueError('Native group dimensions differ from the source skin/rate clock')
        actual = [sum(v > 0 for v in values[offset:offset+length]) for values in (stored, unrounded)]
        declared_counts = [group.get('stored_failed'), group.get('unrounded_failed')]
        if any(type(v) is not int or v < 0 for v in declared_counts) or actual != declared_counts:
            raise ValueError('Recorded failure counts differ from complete stored residuals')
        output.append(dict(metric=group['metric'],conditions=length,stored_failed=actual[0],unrounded_failed=actual[1]))
        if index >= 2:
            width = 2 if index in (2,4) else 3
            for row in range(offset, offset+length):
                if stored[row] <= 0 and unrounded[row] <= 0: continue
                failure_count += 1
                if not detail_offset <= failure_count-1 < detail_offset+maximum_details: continue
                frame, slot = divmod(row-offset, count); node = joints[slot]
                ancestors = []; current = node if index >= 4 else parents[node]
                while current >= 0:
                    ancestors.append(dict(node=current,name=nodes[current].get('name')));current = parents[current]
                failures.append(dict(metric=group['metric'],row=row,actor=actor,node=node,
                    name=nodes[node].get('name'),joint_slot=slot,rate_frame=frame,
                    units=('m/s','m/s^2','rad/s','rad/s^2')[index-2],
                    sample_times_s=list(times[frame:frame+width]),
                    stored_failed=stored[row]>0,unrounded_failed=unrounded[row]>0,
                    stored_normalized_residual=stored[row],unrounded_normalized_residual=unrounded[row],
                    recorded_norm_cap=caps[row],recorded_scale=scales[row],
                    stored_absolute_excess_from_receipt=max(0.,stored[row])*scales[row],
                    influencing_rotation_nodes=ancestors))
        offset += length
    if detail_offset > failure_count: raise ValueError('Detail offset exceeds the complete rate-failure population')
    if (offset != len(stored) or receipt.get('stored_pass') is not all(v <= 0 for v in stored)
            or receipt.get('unrounded_pass') is not all(v <= 0 for v in unrounded)
            or receipt.get('stored_failed') != sum(v > 0 for v in stored)
            or receipt.get('unrounded_failed') != sum(v > 0 for v in unrounded)):
        raise ValueError('Complete recorded native decisions differ from their residual population')
    if any(digest(p) != checksum for p, checksum in checksums.items()):
        raise ValueError('Inspection inputs changed')
    return dict(schema='strep-native-rate-receipt-diagnostic-v1',mode=receipt.get('mode'),label=receipt.get('label'),
        implementation_sha256=checksums[implementation],
        inputs_sha256=checksums,actor=actor,source_skin_joints=count,rate_samples=len(times),
        recorded_native_conditions=len(stored),groups=output,rate_failures=failures,
        rate_failure_count=failure_count,detail_offset=detail_offset,maximum_details=maximum_details,
        details_returned=len(failures),all_rate_failure_details_included=detail_offset==0 and len(failures)==failure_count,
        stored_pass=receipt['stored_pass'],unrounded_pass=receipt['unrounded_pass'],
        original_selected=True,quality_approved=False,training_admitted=False,release_approved=False,
        scope='Complete recorded residual/count and source-joint identity inspection only. Rotation ancestry lists structural influence, not editable permission or guaranteed repair. Bounds/displacement counts stay visible without per-row joint interpretation. No pose re-decoding, geometry/engine computation, model execution or quality approval.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('receipt', 'observations', 'source', 'bindings', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--actor', required=True)
    parser.add_argument('--detail-offset',type=int,default=0)
    parser.add_argument('--maximum-details',type=int,default=256);args = parser.parse_args()
    if args.output.exists(): raise ValueError('Fresh inspection output required')
    result = diagnose(args.receipt,args.observations,args.source,args.bindings,args.actor,
        detail_offset=args.detail_offset,maximum_details=args.maximum_details)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:
        stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(recorded_conditions=result['recorded_native_conditions'],rate_failures=result['rate_failure_count'],
        details_returned=result['details_returned'],all_details_included=result['all_rate_failure_details_included'],
        stored_pass=result['stored_pass'],unrounded_pass=result['unrounded_pass'],quality_approved=False)))


if __name__ == '__main__': main()
