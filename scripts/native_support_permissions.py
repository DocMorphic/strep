"""Explicit source/draft-bound extra foot rotations; the leg contract stays separate."""
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import read, sha256
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_support_spec import validate, number
from paired_temporal_neighbor import rotation_channels
from elbow_swivel import descendants
from native_foot_plant import mesh_accessor_payload, patch_geometry
from native_contact_diagnostics import measure
from native_review_support import serialized_screens


def validate_permissions(value, rig, rows, source_digest, draft_digest):
    fields = {'schema', 'source_sha256', 'draft_sha256', 'supports'}
    if (not isinstance(value, dict) or set(value) != fields
            or value['schema'] != 'strep-native-support-rotation-permissions-v1'
            or value['source_sha256'] != source_digest or value['draft_sha256'] != draft_digest):
        raise ValueError('Explicit source/draft-bound rotation permissions required')
    entries = value['supports']
    if not isinstance(entries, list) or not 1 <= len(entries) <= len(rows):
        raise ValueError('Declare additional rotations for named support intervals')
    by_id = {r['id']: r for r in rows}; channels = rotation_channels(rig.document, rig.binary)
    result = {}
    for entry in entries:
        if (not isinstance(entry, dict) or set(entry) != {'id', 'rotations'}
                or not isinstance(entry['id'], str) or entry['id'] not in by_id or entry['id'] in result
                or not isinstance(entry['rotations'], list) or not entry['rotations']):
            raise ValueError('Distinct existing support IDs and nonempty rotations required')
        row = by_id[entry['id']]; branch = descendants(rig.parents, row['chain'][-1]); nodes = set(); items = []
        for declaration in entry['rotations']:
            if not isinstance(declaration, dict) or set(declaration) != {'node', 'maximum_angle_degrees'}:
                raise ValueError('Explicit rotation node and cumulative angle bound required')
            node = declaration['node']
            if (type(node) is not int or node not in rig.joints or node in row['chain'] or node in nodes
                    or not branch[node] or node not in channels):
                raise ValueError('Distinct animated skin joints below the support foot required')
            if not np.array_equal(channels[node][1], row['clock']):
                raise ValueError('Additional rotations must share the original leg clock')
            angle = number(declaration['maximum_angle_degrees'], 'additional rotation angle', .0001, 45.)
            nodes.add(node); items.append(dict(node=node, angle=angle))
        result[entry['id']] = items
    return result


def preserve(source, candidate, rows, additions):
    """Only declared interior rotation keys may differ; every translation stays exact."""
    allowed = {n for r in rows for n in r['chain']} | {i['node'] for items in additions.values() for i in items}
    if len(source.channels) != len(candidate.channels) or source.duration != candidate.duration:
        raise ValueError('Native channels/duration changed')
    for old, new in zip(source.channels, candidate.channels):
        if old[:2] != new[:2] or old[4] != new[4] or not np.array_equal(old[2], new[2]):
            raise ValueError('Native channel identities/clocks changed')
        if old[1] != 'rotation' or old[0] not in allowed:
            if not np.array_equal(old[3], new[3]):
                raise ValueError('Unedited native track changed')
        else:
            frozen = np.ones(len(old[2]), bool)
            for row in rows:
                permitted = row['chain'] + [i['node'] for i in additions.get(row['id'], [])]
                if old[0] in permitted:
                    a, b = row['edit_keys']; frozen[a + 1:b] = False
            if not np.array_equal(old[3][frozen], new[3][frozen]):
                raise ValueError('Frozen native rotation keys changed')


def audit(source, candidate, draft, permissions_path, limits):
    """Original geometry/rate/support/contact audits plus the new permission bounds.

    An extended-contract pass is never reported as a leg-only contract pass.
    The existing all-joint source-rate bins and tolerance are retained.
    """
    bindings = {str(Path(p).resolve()): sha256(p) for p in (source, candidate, draft, permissions_path)}
    spec = read(draft); rig = RigAsset.load(source); changed = RigAsset.load(candidate)
    old = NativeSupportSampler(rig.document, rig.binary, 0); new = NativeSupportSampler(changed.document, changed.binary, 0)
    _, rows = validate(spec, rig, old, sha256(source))
    additions = validate_permissions(read(permissions_path), rig, rows, sha256(source), sha256(draft))
    preserve(old, new, rows, additions)
    diagnostics = measure(source, candidate, spec)
    # Keep stored mesh encoding/payload protection in addition to decoded skin identity.
    for mesh in rig.document['meshes']:
        for primitive in mesh['primitives']:
            ids = list(primitive['attributes'].values())
            if 'indices' in primitive: ids.append(primitive['indices'])
            ids.extend(i for target in primitive.get('targets', []) for i in target.values())
            for i in ids:
                a = mesh_accessor_payload(rig.document, rig.binary, i)
                b = mesh_accessor_payload(changed.document, changed.binary, i)
                if a[0] != b[0] or not np.array_equal(a[1], b[1]):
                    raise ValueError('Native mesh payload changed')
    for image in rig.document.get('images', []):
        if 'bufferView' in image:
            a = rig.document['bufferViews'][image['bufferView']]; b = changed.document['bufferViews'][image['bufferView']]
            first = a.get('byteOffset', 0); second = b.get('byteOffset', 0)
            if rig.binary[first:first + a['byteLength']] != changed.binary[second:second + b['byteLength']]:
                raise ValueError('Native image payload changed')
    contacts = []
    for row, observed in zip(rows, diagnostics['supports']):
        points, anchor, patch, refs = patch_geometry(rig, old, row)
        current = points(np.array([new.sample(float(t)) for t in observed['times_s']]))
        error = current[:, patch] - anchor[patch]; error -= (error @ row['up'])[..., None] * row['up']
        anchor_error = float(np.linalg.norm(error, axis=2).max())
        speed = observed['candidate']['maximum_patch_vertex_tangential_speed_m_s']; limit = limits[row['id']]
        contacts.append(dict(id=row['id'], source_patch_vertex_references=refs,
            maximum_patch_anchor_error_m=anchor_error, maximum_patch_speed_m_s=speed,
            maximum_anchor_error_m=limit['anchor'], maximum_speed_m_s=limit['speed'],
            passed=bool(anchor_error <= limit['anchor'] and speed <= limit['speed'])))
    screens = serialized_screens(source, candidate, spec)
    before = rotation_channels(rig.document, rig.binary); after = rotation_channels(changed.document, changed.binary)
    extra = []
    for row in rows:
        a, b = row['edit_keys']
        for item in additions.get(row['id'], []):
            node = item['node']
            angle = float(np.rad2deg((Rotation.from_quat(before[node][2][a:b + 1]).inv()
                * Rotation.from_quat(after[node][2][a:b + 1])).magnitude()).max())
            extra.append(dict(id=row['id'], node=node, maximum_local_angle_degrees=angle,
                authored_angle_degrees=item['angle'], serialization_tolerance_degrees=.0001,
                passed=bool(angle <= item['angle'] + .0001)))
    clearance = all(s['minimum_height_m'] >= r['clearance'] - 1e-8 for s, r in zip(screens['supports'], rows))
    contact_pass = all(c['passed'] for c in contacts); permission_pass = all(e['passed'] for e in extra)
    if any(sha256(p) != h for p, h in bindings.items()):
        raise ValueError('Extended support audit inputs changed')
    return dict(contacts=contacts, contact_samples_pass=contact_pass, support_screens=screens,
        authored_clearance_pass=clearance, additional_rotation_screens=extra,
        additional_rotation_bounds_pass=permission_pass,
        passed=bool(contact_pass and screens['passed'] and clearance and permission_pass),
        uses_extended_rotation_permissions=True, original_leg_only_preservation_verified=False,
        permissions_sha256=sha256(permissions_path), original_rate_caps_retained=True,
        diagnostics=diagnostics, quality_approved=False, training_admitted=False, release_approved=False,
        continuous_collision_certified=False, planted_contact_certified=False)
