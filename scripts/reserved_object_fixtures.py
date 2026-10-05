"""Construct and independently decode static primitive evaluation reservations."""
import argparse
import json
from pathlib import Path
import shutil

import numpy as np

from gltf_tools import accessor, append_accessor, read_glb, write_glb
from object_geometry import Geometry
from object_geometry_mesh import triangle_mesh
from strep import ROOT, now, read, save, sha256

METHODS = ('reserved_object_fixtures.py', 'object_geometry.py', 'object_geometry_mesh.py', 'gltf_tools.py', 'strep.py')
VERTEX_LIMIT_M = 1e-6


def catalog_cases(catalog):
    if (not isinstance(catalog, dict) or set(catalog) != {'schema', 'status', 'use_policy', 'limitations', 'objects'}
            or catalog['schema'] != 'strep-reserved-object-fixtures-v1'
            or catalog['status'] != 'reserved_not_motion_evaluated'):
        raise ValueError('Explicit unexecuted static reservation catalog required')
    if not isinstance(catalog['use_policy'], str) or not catalog['use_policy'].strip():
        raise ValueError('Reservation use policy required')
    if not isinstance(catalog['limitations'], list) or not catalog['limitations'] or any(
            not isinstance(v, str) or not v.strip() for v in catalog['limitations']):
        raise ValueError('Explicit limitations required')
    cases = catalog['objects']
    if not isinstance(cases, list) or not 1 <= len(cases) <= 32:
        raise ValueError('Choose 1-32 reserved objects')
    seen, geometries = set(), set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {'id', 'geometry', 'motion_trial_executed'}:
            raise ValueError('Explicit object fields required')
        identifier = case['id']
        if (not isinstance(identifier, str) or not 1 <= len(identifier) <= 64
                or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in identifier)
                or identifier in seen or case['motion_trial_executed'] is not False):
            raise ValueError('Distinct unexecuted named objects required')
        geometry = Geometry.parse(case['geometry'])
        # Finite authoring/resource contract; not an animation-quality gate.
        if any(not .005 <= d <= 10 for d in geometry.dimensions):
            raise ValueError('Fixture dimensions must lie within 0.005-10 metres')
        canonical = json.dumps(geometry.record(), sort_keys=True, separators=(',', ':'))
        if canonical in geometries:
            raise ValueError('Distinct object geometries required')
        seen.add(identifier)
        geometries.add(canonical)
    return cases


def _signed_distance(points, record):
    """Separate primitive arithmetic; never calls Geometry distance queries."""
    if record['shape'] == 'sphere':
        return np.sqrt(np.sum(points * points, axis=-1)) - record['radius_m']
    if record['shape'] == 'box':
        q = abs(points) - np.array(record['size_m']) / 2
    else:
        q = np.stack([np.sqrt(points[..., 0] ** 2 + points[..., 2] ** 2) - record['radius_m'],
                      abs(points[..., 1]) - record['height_m'] / 2], axis=-1)
    return np.sqrt(np.sum(np.maximum(q, 0) ** 2, axis=-1)) + np.minimum(np.max(q, axis=-1), 0)


def _extent(record):
    if record['shape'] == 'box':
        return np.array(record['size_m']) / 2
    radius = record['radius_m']
    return np.array([radius, radius if record['shape'] == 'sphere' else record['height_m'] / 2, radius])


def _anchors(record):
    extent = _extent(record)
    return [dict(id='negative-x' if sign < 0 else 'positive-x',
                 point_m=[float(sign * extent[0]), 0., 0.], outward_normal=[float(sign), 0., 0.]) for sign in (-1, 1)]


def _write(path, geometry):
    triangles, normals, approximation = triangle_mesh(geometry, tolerance_m=.001)
    doc = dict(asset=dict(version='2.0', generator='Strep static reserved primitive'), scene=0,
               scenes=[dict(nodes=[0])], nodes=[dict(name='ReservedObject', mesh=0)], meshes=[],
               buffers=[], bufferViews=[], accessors=[], materials=[dict(pbrMetallicRoughness=dict(
                   baseColorFactor=[.5, .5, .5, 1], roughnessFactor=.8, metallicFactor=0))])
    binary = bytearray()
    vertices = triangles.reshape(-1, 3)
    pi = append_accessor(doc, binary, vertices, 'VEC3')
    stored = vertices.astype('<f4').astype(float)
    doc['accessors'][pi].update(min=stored.min(0).tolist(), max=stored.max(0).tolist())
    ni = append_accessor(doc, binary, normals.reshape(-1, 3), 'VEC3')
    doc['meshes'] = [dict(primitives=[dict(attributes=dict(POSITION=pi, NORMAL=ni), mode=4, material=0)])]
    doc['nodes'][0]['extras'] = dict(strep_geometry=geometry.record(), strep_preview_mesh=approximation)
    write_glb(path, doc, binary)
    rounding = float(np.linalg.norm(stored - vertices, axis=1).max())
    return dict(**approximation, maximum_float32_vertex_rounding_m=rounding,
                conservative_preview_inset_with_rounding_m=approximation['max_radial_inset_m'] + rounding)


def decode_check(path, record, approximation):
    """All stored vertices, normals, faces and edge incidences; finite mesh scope."""
    Geometry.parse(record)
    doc, binary = read_glb(path)
    if doc.get('scene') != 0 or doc.get('scenes') != [dict(nodes=[0])] or any(
            item.get('uri') for kind in ('buffers', 'images') for item in doc.get(kind, [])):
        raise ValueError('One self-contained fixture scene required')
    if doc.get('animations') or doc.get('skins') or len(doc.get('nodes', [])) != 1 or len(doc.get('meshes', [])) != 1:
        raise ValueError('One static unskinned fixture object required')
    node = doc['nodes'][0]
    if node.get('mesh') != 0 or node.get('extras', {}).get('strep_geometry') != record or any(
            k in node for k in ('matrix', 'translation', 'rotation', 'scale', 'children')):
        raise ValueError('Untransformed local primitive required')
    mesh = doc['meshes'][0]['primitives']
    if len(mesh) != 1 or mesh[0].get('mode') != 4 or set(mesh[0]['attributes']) != {'POSITION', 'NORMAL'} or 'indices' in mesh[0]:
        raise ValueError('One explicit nonindexed triangle surface required')
    attrs = mesh[0]['attributes']
    for index in attrs.values():
        item = doc['accessors'][index]
        if item['componentType'] != 5126 or item['type'] != 'VEC3':
            raise ValueError('Float32 position/normal storage required')
    vertices = accessor(doc, binary, attrs['POSITION']).astype(float)
    normals = accessor(doc, binary, attrs['NORMAL']).astype(float)
    if len(vertices) < 12 or len(vertices) % 3 or normals.shape != vertices.shape or not np.isfinite(vertices).all() or not np.isfinite(normals).all():
        raise ValueError('Complete finite triangle/normal population required')
    bounds = doc['accessors'][attrs['POSITION']]
    if bounds['min'] != vertices.min(0).tolist() or bounds['max'] != vertices.max(0).tolist():
        raise ValueError('Stored mesh bounds differ')
    distance = _signed_distance(vertices, record)
    if float(abs(distance).max()) > VERTEX_LIMIT_M:
        raise ValueError('Stored vertices leave the analytic primitive surface')
    if float(abs(np.linalg.norm(normals, axis=1) - 1).max()) > 2e-7:
        raise ValueError('Stored normals are not unit-range')
    faces = vertices.reshape(-1, 3, 3)
    cross = np.cross(faces[:, 1] - faces[:, 0], faces[:, 2] - faces[:, 0])
    if not np.all(np.einsum('ij,ij->i', cross, faces.mean(1)) > 0):
        raise ValueError('Degenerate or inward triangle')
    # Exact saved Float32 vertex identity: no coordinate rounding/tolerance merge.
    _, indices = np.unique(vertices, axis=0, return_inverse=True)
    edges = {}
    for face in indices.reshape(-1, 3):
        for a, b in zip(face, np.roll(face, -1)):
            edges.setdefault(tuple(sorted((int(a), int(b)))), []).append(1 if a < b else -1)
    if any(len(signs) != 2 or sum(signs) != 0 for signs in edges.values()):
        raise ValueError('Saved mesh is not closed with consistent winding')
    # Check the actual normals against analytic outward directions, independently.
    if record['shape'] == 'sphere':
        expected = vertices / np.linalg.norm(vertices, axis=1)[:, None]
    elif record['shape'] == 'box':
        expected = np.repeat(cross / np.linalg.norm(cross, axis=1)[:, None], 3, axis=0)
    else:
        expected = np.zeros_like(vertices)
        cap = abs(normals[:, 1]) > .5
        expected[cap, 1] = np.sign(vertices[cap, 1])
        side = ~cap
        radial = vertices[side][:, [0, 2]]
        expected[np.flatnonzero(side)[:, None], [0, 2]] = radial / np.linalg.norm(radial, axis=1)[:, None]
    if float(abs(normals - expected).max()) > 2e-7:
        raise ValueError('Saved normals differ from primitive outward directions')
    mesh_error = approximation['conservative_preview_inset_with_rounding_m']
    if not 0 <= mesh_error <= .001 + VERTEX_LIMIT_M:
        raise ValueError('Preview inset exceeds the fixed construction bound')
    maximum_inset = 0.
    for weights in ((1/3, 1/3, 1/3), (.5, .5, 0), (.5, 0, .5), (0, .5, .5)):
        samples = np.einsum('v,fvc->fc', np.array(weights), faces)
        sdf = _signed_distance(samples, record)
        if float(sdf.max()) > VERTEX_LIMIT_M or float((-sdf).max()) > mesh_error + 1e-12:
            raise ValueError('Saved preview interior samples exceed the declared inset')
        maximum_inset = max(maximum_inset, float((-sdf).max()))
    for anchor in _anchors(record):
        point = np.array(anchor['point_m'])
        if abs(float(_signed_distance(point[None], record)[0])) > 1e-12:
            raise ValueError('Reserved anchor is not on the analytic surface')
    return dict(stored_vertices=len(vertices), triangles=len(faces), unique_edges=len(edges),
                maximum_stored_surface_error_m=float(abs(distance).max()),
                maximum_checked_preview_inset_m=maximum_inset, static_geometry_pass=True,
                engine_checked=False, physics_checked=False, contact_reachability_checked=False,
                motion_trial_executed=False, quality_approved=False, release_approved=False)


def build(catalog_path, output):
    catalog_path, output = Path(catalog_path).resolve(), Path(output).resolve()
    if output.exists() or catalog_path.is_relative_to(output):
        raise ValueError('Fresh fixture output separate from catalog required')
    digest = sha256(catalog_path)
    catalog = read(catalog_path)
    cases = catalog_cases(catalog)
    methods = {name: sha256(ROOT / 'scripts' / name) for name in METHODS}
    geometries = [Geometry.parse(case['geometry']) for case in cases]
    # Resource/tolerance validation before creating outputs, without motion sampling.
    for geometry in geometries:
        triangle_mesh(geometry, tolerance_m=.001)
    output.mkdir(parents=True)
    shutil.copyfile(catalog_path, output / 'catalog.json')
    for name in METHODS:
        path = output / 'implementation' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'scripts' / name, path)
    save(output / 'request.json', dict(at=now(), catalog_sha256=digest, methods_sha256=methods,
                                     numpy_version=np.__version__, no_model_or_character_inputs=True))
    records = []
    for case, geometry in zip(cases, geometries):
        folder = output / 'objects' / case['id']
        folder.mkdir(parents=True)
        asset = folder / 'object.glb'
        approximation = _write(asset, geometry)
        check = decode_check(asset, case['geometry'], approximation)
        extent = _extent(case['geometry'])
        descriptor = dict(id=case['id'], geometry=case['geometry'], anchors=_anchors(case['geometry']),
                          glb='object.glb', glb_sha256=sha256(asset), approximation=approximation,
                          canonical_grounded_pose=dict(translation_m=[0., float(extent[1]), 0.], rotation_xyzw=[0., 0., 0., 1.]),
                          source='Procedurally constructed by Strep; no downloaded object payload',
                          mass_material_and_runtime_physics_bound=False, scene_or_partner_binding_complete=False,
                          use_policy=catalog['use_policy'], motion_trial_executed=False, quality_approved=False, release_approved=False)
        save(folder / 'descriptor.json', descriptor)
        save(folder / 'verification.json', check)
        records.append(dict(id=case['id'], geometry=case['geometry'],
                            path=asset.relative_to(output).as_posix(), glb_sha256=sha256(asset),
                            descriptor_sha256=sha256(folder / 'descriptor.json'),
                            verification_sha256=sha256(folder / 'verification.json'), **check))
    if sha256(catalog_path) != digest or sha256(output / 'catalog.json') != digest or any(
            sha256(ROOT / 'scripts' / name) != value or sha256(output / 'implementation' / name) != value
            for name, value in methods.items()):
        raise ValueError('Fixture input or implementation changed during construction')
    result = dict(at=now(), catalog_sha256=digest, request_sha256=sha256(output / 'request.json'),
                  objects=records, distinct_geometries=len(cases), shape_families=sorted({g.shape for g in geometries}),
                  static_geometry_pass=all(r['static_geometry_pass'] for r in records),
                  engine_checked=False, physics_checked=False, held_out_scene_package_complete=False,
                  motion_trials_executed=0, quality_approved=False, release_approved=False,
                  limitations=catalog['limitations'])
    save(output / 'result.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('catalog', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.catalog, args.output)
    print(json.dumps(dict(objects=result['distinct_geometries'], static_geometry_pass=result['static_geometry_pass'],
                          motion_trials_executed=0, engine_checked=False, release_approved=False)))
