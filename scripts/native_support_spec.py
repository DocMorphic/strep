"""Source-bound native foot-support drafts; roles map explicitly to skin joints."""
import re
import numpy as np
from paired_temporal_neighbor import rotation_channels
from elbow_swivel import descendants


def number(value, name, low, high):
    if type(value) not in (int, float) or not np.isfinite(value) or not low <= value <= high:
        raise ValueError('Invalid '+name)
    return float(value)


def validate(spec, rig, reader, digest):
    fields = {'schema', 'glb_sha256', 'animation_index', 'duration_s', 'root_node', 'mapping', 'supports'}
    if not isinstance(spec, dict) or set(spec) != fields or spec['schema'] != 'strep-native-support-v1':
        raise ValueError('Explicit native support schema required')
    if spec['glb_sha256'] != digest or spec['animation_index'] != 0 or type(spec['animation_index']) is not int or type(spec['duration_s']) not in (int, float) or spec['duration_s'] != reader.duration:
        raise ValueError('Support draft belongs to another native animation')
    root = spec['root_node']
    if type(root) is not int or root not in rig.joints:
        raise ValueError('Mapped root must be a skin joint')
    mapping = spec['mapping']; allowed = {s+n for s in ('Left', 'Right') for n in ('Leg', 'Shin', 'Foot')}
    if not isinstance(mapping, dict) or not mapping or set(mapping)-allowed:
        raise ValueError('Explicit leg role mapping required')
    resolved = {}
    for role, target in mapping.items():
        if isinstance(target, str):
            choices = [n for n in rig.joints if rig.document['nodes'][n].get('name') == target]
            if len(choices) != 1: raise ValueError('Mapped name missing or ambiguous')
            target = choices[0]
        if type(target) is not int or target not in rig.joints or target == root:
            raise ValueError('Mapped support joint must be a non-root skin joint')
        if not descendants(rig.parents, root)[target]: raise ValueError('Support chain must descend from the mapped root')
        resolved[role] = target
    if len(set(resolved.values())) != len(resolved): raise ValueError('Distinct mapped roles required')
    supports = spec['supports']
    if not isinstance(supports, list) or not 1 <= len(supports) <= 64:
        raise ValueError('Choose 1–64 explicit support intervals')
    channels = rotation_channels(rig.document, rig.binary); rows = []; ids = set(); windows = {}
    for entry in supports:
        required = {'id', 'foot', 'stance_s', 'edit_keys', 'plane', 'clearance_m', 'maximum_gap_m', 'maximum_displacement_m', 'maximum_angle_degrees'}
        if not isinstance(entry, dict) or set(entry) != required or not isinstance(entry['id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', entry['id']) or entry['id'] in ids:
            raise ValueError('Distinct named support intervals required')
        ids.add(entry['id']); foot = entry['foot']
        if foot not in ('LeftFoot', 'RightFoot'): raise ValueError('Mapped left or right foot required')
        side = foot[:-4]; roles = [side+n for n in ('Leg', 'Shin', 'Foot')]
        if any(r not in resolved for r in roles): raise ValueError('Complete mapped support chain required')
        chain = [resolved[r] for r in roles]
        if rig.parents[chain[1]] != chain[0] or rig.parents[chain[2]] != chain[1]:
            raise ValueError('Direct thigh/knee/foot chain required; helper-bone chains unsupported')
        if any(n not in channels for n in chain): raise ValueError('Native leg rotation tracks required')
        times = channels[chain[0]][1]
        for n in chain:
            if not np.array_equal(channels[n][1], times): raise ValueError('Common native chain clock required')
        keys = entry['edit_keys']
        if not isinstance(keys, list) or len(keys) != 2 or any(type(k) is not int for k in keys) or not 0 <= keys[0] < keys[1] < len(times) or keys[1]-keys[0] < 4:
            raise ValueError('Edit window needs native boundary keys and at least three interior keys')
        start, end = map(float, times[keys])
        stance = entry['stance_s']
        if not isinstance(stance, list) or len(stance) != 2:
            raise ValueError('Finite stance seconds required')
        a, b = [number(v, 'stance time', start, end) for v in stance]
        if a >= b or np.count_nonzero((times >= a)&(times <= b)) < 2:
            raise ValueError('Stance must span at least two native keys')
        for c, d in windows.setdefault(foot, []):
            if max(start, c) < min(end, d): raise ValueError('Same-foot edit windows must not overlap')
        windows[foot].append((start, end))
        plane = entry['plane']
        if not isinstance(plane, dict) or set(plane) != {'normal_xyz', 'offset_m'}:
            raise ValueError('Static rig-world plane required')
        normal = plane['normal_xyz']
        if not isinstance(normal, list) or len(normal) != 3 or any(type(v) not in (int, float) or not np.isfinite(v) for v in normal) or abs(np.linalg.norm(normal)-1) > 1e-8:
            raise ValueError('Unit plane normal required')
        offset = number(plane['offset_m'], 'plane offset', -1000, 1000)
        clearance = number(entry['clearance_m'], 'clearance', .00025, .0045)
        gap = number(entry['maximum_gap_m'], 'stance gap', clearance+.00025, .005)
        displacement = number(entry['maximum_displacement_m'], 'displacement', .000001, .03)
        angle = number(entry['maximum_angle_degrees'], 'angle', .0001, 45)
        rows.append(dict(id=entry['id'], foot=foot, chain=chain, clock=times, edit_keys=keys,
                         edit_s=[start, end], stance_s=[a, b], up=np.asarray(normal), offset=-offset,
                         clearance=clearance, maximum_height=gap, displacement=displacement, angle=angle))
    branches = {r['foot']: descendants(rig.parents, r['chain'][0]) for r in rows}
    if len(branches) == 2 and np.any(branches['LeftFoot']&branches['RightFoot']):
        raise ValueError('Support chains must occupy separate rig branches')
    return resolved, rows
