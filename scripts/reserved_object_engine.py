"""Headless static import of bound reserved objects; no animation or physics claim."""
import argparse
from collections import defaultdict
from pathlib import Path
import shutil
import subprocess

import numpy as np

from action_worker_lock import worker_lock
from gltf_tools import accessor, read_glb
from reserved_object_fixtures import METHODS as FIXTURE_METHODS, catalog_cases, decode_check
from strep import ROOT, now, read, save, sha256

METHODS = tuple(dict.fromkeys(FIXTURE_METHODS + ('reserved_object_engine.py', 'godot_reserved_object_audit.gd', 'action_worker_lock.py')))
NORMAL_COMPONENT_LIMIT = 1e-4
PLACEMENT_LIMIT_M = 1e-6


def inputs(construction):
    construction = Path(construction).resolve()
    result, request = read(construction/'result.json'), read(construction/'request.json')
    if (not result.get('static_geometry_pass') or result.get('motion_trials_executed') != 0
            or result.get('quality_approved') is not False or result.get('release_approved') is not False):
        raise ValueError('Unapproved static construction required')
    bindings = {str(construction/'result.json'): sha256(construction/'result.json'),
                str(construction/'request.json'): sha256(construction/'request.json')}
    if bindings[str(construction/'request.json')] != result['request_sha256'] or sha256(construction/'catalog.json') != result['catalog_sha256']:
        raise ValueError('Changed construction request or catalog')
    bindings[str(construction/'catalog.json')] = result['catalog_sha256']
    catalog = catalog_cases(read(construction/'catalog.json'))
    if [(r['id'],r['geometry']) for r in result['objects']] != [(r['id'],r['geometry']) for r in catalog]:
        raise ValueError('Construction population differs from reserved catalog')
    for name, digest in request['methods_sha256'].items():
        for path in (ROOT/'scripts'/name, construction/'implementation'/name):
            if sha256(path) != digest:
                raise ValueError('Changed static construction implementation')
            bindings[str(path)] = digest
    if set(request['methods_sha256']) != set(FIXTURE_METHODS):
        raise ValueError('Complete fixture source inventory required')
    records, seen = [], set()
    for row in result['objects']:
        asset = (construction/row['path']).resolve()
        if not asset.is_relative_to(construction) or row['id'] in seen:
            raise ValueError('Distinct contained fixture assets required')
        seen.add(row['id'])
        for path, digest in [(asset, row['glb_sha256']), (asset.parent/'descriptor.json', row['descriptor_sha256']),
                             (asset.parent/'verification.json', row['verification_sha256'])]:
            if sha256(path) != digest:
                raise ValueError('Changed reserved object file')
            bindings[str(path)] = digest
        descriptor = read(asset.parent/'descriptor.json')
        if descriptor['id'] != row['id'] or descriptor['geometry'] != row['geometry'] or descriptor['glb_sha256'] != row['glb_sha256']:
            raise ValueError('Contradictory fixture descriptor')
        geometry=row['geometry']
        height=(geometry['size_m'][1]/2 if geometry['shape']=='box' else
                geometry['radius_m'] if geometry['shape']=='sphere' else geometry['height_m']/2)
        if descriptor['canonical_grounded_pose'] != dict(translation_m=[0.,height,0.],rotation_xyzw=[0.,0.,0.,1.]):
            raise ValueError('Contradictory canonical grounded pose')
        checked = decode_check(asset, row['geometry'], descriptor['approximation'])
        if checked != read(asset.parent/'verification.json') or any(row[k] != v for k,v in checked.items()):
            raise ValueError('Static source checks do not reproduce')
        records.append(dict(id=row['id'], path=str(asset), sha256=row['glb_sha256'],
                            grounded_translation_m=descriptor['canonical_grounded_pose']['translation_m']))
    if not records or result['distinct_geometries'] != len(records):
        raise ValueError('Complete nonempty fixture population required')
    return dict(objects=records), bindings


def _array(value, shape, label):
    data = np.asarray(value, float)
    if data.shape != shape or not np.isfinite(data).all():
        raise ValueError('Invalid ' + label)
    return data


def _triangle_table(positions, normals):
    result = defaultdict(list)
    for p, n in zip(positions.reshape(-1,3,3), normals.reshape(-1,3,3)):
        order = sorted(range(3), key=lambda i: tuple(p[i]))
        key = tuple(p[order].reshape(-1))
        result[key].append(n[order])
    return result


def reduce(request, raw):
    if raw.get('compression_disabled') is not True or not isinstance(raw.get('engine'), dict):
        raise ValueError('Explicit engine and uncompressed import record required')
    rows = raw.get('objects')
    if not isinstance(rows, list) or len(rows) != len(request['objects']) or {r['id'] for r in rows} != {r['id'] for r in request['objects']}:
        raise ValueError('Complete distinct imported object population required')
    records = {r['id']:r for r in rows}
    checks = []
    for item in request['objects']:
        if sha256(item['path']) != item['sha256']:
            raise ValueError('Saved bound object changed before reduction')
        doc, binary = read_glb(item['path'])
        attrs = doc['meshes'][0]['primitives'][0]['attributes']
        source_p = accessor(doc,binary,attrs['POSITION']).astype(float)
        source_n = accessor(doc,binary,attrs['NORMAL']).astype(float)
        row = records[item['id']]
        p = np.asarray(row['positions'],float)
        if p.ndim != 2 or p.shape[1] != 3 or not len(p) or not np.isfinite(p).all():
            raise ValueError('Complete finite imported vertices required')
        n = _array(row['normals'],p.shape,'imported normals')
        indices = row['indices']
        if not isinstance(indices,list) or any(type(i) is not int or not 0 <= i < len(p) for i in indices):
            raise ValueError('Invalid saved triangle indices')
        if indices:
            p, n = p[indices], n[indices]
        if len(p) != len(source_p):
            raise ValueError('Imported triangle population changed')
        # Exact positions; explicitly allow vertex/index reordering and Godot winding convention.
        source, imported = _triangle_table(source_p,source_n), _triangle_table(p,n)
        if set(source) != set(imported) or any(len(source[k]) != len(imported[k]) for k in source):
            raise ValueError('Imported triangle geometry differs from saved Float32 positions')
        normal_error = 0.
        for key, expected in source.items():
            actual = imported[key]
            for value in expected:
                scores = [float(abs(value-v).max()) for v in actual]
                best = int(np.argmin(scores)); normal_error=max(normal_error,scores[best]); actual.pop(best)
        if normal_error > NORMAL_COMPONENT_LIMIT:
            raise ValueError('Imported normals exceed fixed component limit')
        faces = p.reshape(-1,3,3)
        cross = np.cross(faces[:,1]-faces[:,0], faces[:,2]-faces[:,0])
        signs = np.einsum('ij,ij->i',cross,faces.mean(1))
        if not (np.all(signs>0) or np.all(signs<0)):
            raise ValueError('Imported triangles have inconsistent or degenerate winding')
        poses = row['poses']
        if not isinstance(poses,list) or len(poses) != 2:
            raise ValueError('Local-origin and grounded poses required')
        maximum_placement_error = 0.
        for pose, expected in zip(poses,([0.,0.,0.],item['grounded_translation_m'])):
            position = _array(pose['translation_m'],(3,),'engine placement')
            basis = _array(pose['basis_columns'],(3,3),'engine basis')
            error=float(np.linalg.norm(position-np.array(expected)))
            if error > PLACEMENT_LIMIT_M or float(abs(basis-np.eye(3)).max()) > 1e-6:
                raise ValueError('Imported local/grounded placement changed')
            maximum_placement_error=max(maximum_placement_error,error)
        checks.append(dict(id=item['id'], triangles=len(faces), complete_triangle_positions_exact=True,
                           maximum_normal_component_error=normal_error, maximum_placement_error_m=maximum_placement_error,
                           winding_convention='positive' if signs[0]>0 else 'negative', static_import_pass=True))
    return dict(objects=checks, static_import_pass=True, placement_observations=2*len(checks),
                normal_component_limit=NORMAL_COMPONENT_LIMIT, placement_limit_m=PLACEMENT_LIMIT_M,
                physics_checked=False, gpu_render_checked=False, contact_reachability_checked=False,
                motion_trial_executed=False, quality_approved=False, release_approved=False)


def run(construction, output, engine):
    construction,output,engine=[Path(p).resolve() for p in (construction,output,engine)]
    if output.exists() or output.is_relative_to(construction) or construction.is_relative_to(output):
        raise ValueError('Fresh separate import output required')
    # Acquire before creating outputs or importing any real asset.
    with worker_lock():
        request, bindings = inputs(construction)
        bindings[str(engine)] = sha256(engine)
        for name in METHODS: bindings[str(ROOT/'scripts'/name)] = sha256(ROOT/'scripts'/name)
        output.mkdir(parents=True)
        project=output/'project';project.mkdir()
        (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep reserved static object audit"\n',encoding='utf-8')
        script=ROOT/'scripts/godot_reserved_object_audit.gd'
        shutil.copyfile(script,project/'audit.gd')
        save(output/'request.json',request)
        save(output/'bindings.json',bindings)
        save(output/'pipeline.json',dict(at=now(),status='processing',stage='headless-static-object-import'))
        try:
            with (output/'engine.log').open('w',encoding='utf-8') as log:
                child=subprocess.run([str(engine),'--headless','--path',str(project),'--script','audit.gd','--',
                    str(output/'request.json'),str(output/'engine-output.json')],stdout=log,stderr=subprocess.STDOUT,
                    timeout=300,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if child.returncode:
                raise ValueError('Static object import failed; retained engine.log')
            raw=read(output/'engine-output.json');checked=reduce(request,raw)
            if any(sha256(path)!=digest for path,digest in bindings.items()) or sha256(project/'audit.gd') != bindings[str(script)]:
                raise ValueError('Bound import input or method changed')
            if read(output/'request.json') != request:
                raise ValueError('Import request changed')
            result=dict(at=now(),status='complete',engine=raw['engine'],**checked,
                        files_sha256={name:sha256(output/name) for name in ('request.json','bindings.json','engine.log','engine-output.json')},
                        scope='Static headless GLTFDocument import with compression disabled. Complete saved-position triangle population and two placements; no animation, physics, GPU, reachable grip or release evidence.')
            save(output/'result.json',result)
            save(output/'pipeline.json',dict(at=now(),status='complete'))
            return result
        except BaseException as exc:
            save(output/'pipeline.json',dict(at=now(),status='failed',error=str(exc),quality_approved=False,release_approved=False))
            raise


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('construction',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--engine',type=Path,required=True)
    args=parser.parse_args()
    print(run(args.construction,args.output,args.engine)['status'])
