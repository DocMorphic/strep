"""Exact static deformation identity for material patches across animated files.

Accessor packing and animation may change. Raw attributes, triangle ordering,
default nodes, skin binds and mapped profile fields must remain identical.
"""
import copy
import hashlib
import json
from rig_asset import array
from rig_material_patch import require, METHODS as MATERIAL_METHODS

METHODS = tuple(dict.fromkeys(MATERIAL_METHODS + ('rig_material_identity.py',)))
SCHEMA = 'strep-rig-material-identity-v1'


def packed_array(rig, number):
    item = rig.document['accessors'][number]
    normalized = item.get('normalized', False)
    require(type(normalized) is bool and (not normalized or item['componentType'] in (5120, 5121, 5122, 5123)),
            'Valid raw accessor normalization required')
    raw = dict(rig.document); raw['accessors'] = list(rig.document['accessors'])
    record = dict(item); record.pop('normalized', None); raw['accessors'][number] = record
    values = array(raw, rig.binary, number)
    metadata = {k: v for k, v in item.items() if k not in ('bufferView', 'byteOffset')}
    return dict(metadata=metadata, dtype=values.dtype.str, shape=list(values.shape),
                values_sha256=hashlib.sha256(values.tobytes(order='C')).hexdigest())


def descriptor(surface):
    """Bind every static mesh attribute in raw encoding, including zero weights."""
    surface.check_inputs(); rig = surface.rig; doc = rig.document
    meshes = copy.deepcopy(doc['meshes'])
    for mesh in meshes:
        for primitive in mesh['primitives']:
            primitive['attributes'] = {k: packed_array(rig, n) for k, n in primitive['attributes'].items()}
            if 'indices' in primitive:
                primitive['indices'] = packed_array(rig, primitive['indices'])
    skin = copy.deepcopy(rig.skin)
    if 'inverseBindMatrices' in skin:
        skin['inverseBindMatrices'] = packed_array(rig, skin['inverseBindMatrices'])
    profile = {k: copy.deepcopy(v) for k, v in surface.profile.items() if k != 'character_sha256'}
    result = dict(schema=SCHEMA, nodes=copy.deepcopy(doc['nodes']), skins=[skin], meshes=meshes,
        scenes=copy.deepcopy(doc['scenes']), selected_scene=doc.get('scene', 0), profile=profile,
        active_nodes=sorted(rig.active), parent_nodes=rig.parents,
        extensions_used=doc.get('extensionsUsed', []), extensions_required=doc.get('extensionsRequired', []))
    surface.check_inputs(); return result


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode('utf-8')).hexdigest()


def compare(source, target):
    before, after = descriptor(source), descriptor(target)
    require(digest(before) == digest(after), 'Material transfer changes static rig, raw mesh/skinning payload or profile')
    return dict(schema='strep-rig-material-identity-comparison-v1',
        source=dict(source.source), target=dict(target.source), identity_sha256=digest(before),
        complete_static_identity_equal=True, raw_weights_preserved=True,
        complete_nodes=len(source.rig.document['nodes']), complete_vertices=len(source.points),
        complete_triangles=len(source.faces), complete_primitives=len(source.rig.primitives),
        animations_compared=False, materials_textures_compared=False,
        anatomy_verified=False, quality_approved=False, release_approved=False,
        scope='Exact node graph/default transforms, complete original primitive metadata/attributes, '
              'indices, skin binds and all non-character-hash profile fields. Raw storage values/encoding '
              'are preserved; accessor offsets/packing and animation may change. No animation validity, '
              'material/texture payload, target correspondence, timing, motion or human approval.')
