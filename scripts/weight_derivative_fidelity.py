"""Compare imported derivative skin against the unchanged original GLB skin.

The original reference must not become the quantized derivative itself.
Every original engine sample and surface vertex remains in the comparison.
"""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset, array
from rig_clip_import import AnimationSampler
from godot_weight_derivative import balanced_pairs
from imported_scene_geometry import ImportedGeometryScene, load_producer, METHODS as IMPORT_METHODS
from native_scene_engine import SKIN_POSITION_TOLERANCE

METHODS = tuple(dict.fromkeys(IMPORT_METHODS + ('godot_weight_derivative.py', 'weight_derivative_fidelity.py')))


def verify_derivative(original, derived):
    if original.document != derived.document or len(original.primitives) != len(derived.primitives):
        raise ValueError('Unchanged complete derivative document required')
    affected = set()
    for left, right in zip(original.primitives, derived.primitives):
        if left['joints'] is None:
            if not np.array_equal(left['positions'], right['positions']): raise ValueError('Rigid primitive changed')
            continue
        p = original.document['meshes'][original.document['nodes'][left['node']]['mesh']]['primitives'][left['primitive']]
        attrs = p['attributes']; channels = [0] + ([1] if 'WEIGHTS_1' in attrs else [])
        raw = np.concatenate([array(original.document, original.binary, attrs[f'WEIGHTS_{i}']) for i in channels], axis=1)
        joints, weights = balanced_pairs(left['joints'], raw)
        for kind, expected in [('JOINTS', joints), ('WEIGHTS', weights)]:
            actual = np.concatenate([array(derived.document, derived.binary, attrs[f'{kind}_{i}']) for i in channels], axis=1)
            if not np.array_equal(actual, expected): raise ValueError('Derivative differs from checked allocation/pair order')
            affected.update(attrs[f'{kind}_{i}'] for i in channels)
    for number in range(len(original.document['accessors'])):
        if number not in affected and not np.array_equal(array(original.document, original.binary, number),
                                                       array(derived.document, derived.binary, number)):
            raise ValueError('Non-influence accessor changed')
    return dict(document_unchanged=True, all_other_accessors_unchanged=True, checked_pair_encoding_exact=True)


def measure_original(original, sampler, scene, name):
    derived = scene.actors[name]['rig']; identity = verify_derivative(original, derived)
    p, r = scene.actors[name]['placement']; errors = []; witnesses = []
    for time in scene.times:
        reference = original.vertices(sampler.sample(float(time))) @ r.T + p
        actual = scene.actor_vertices(name, float(time))
        if actual.shape != reference.shape: raise ValueError('Complete comparable vertex population required')
        distance = np.linalg.norm(actual-reference, axis=1); index = int(distance.argmax())
        errors.append(float(distance[index])); witnesses.append(index)
    errors = np.asarray(errors); witnesses = np.asarray(witnesses); peak = int(errors.argmax())
    return dict(actor=name, samples=len(errors), vertices=len(reference), **identity,
        original_skin_reference_preserved=True, imported_weights_renormalized=False,
        maximum_position_error_m=float(errors[peak]), worst_time_s=float(scene.times[peak]),
        worst_source_vertex=int(witnesses[peak]), tolerance_m=SKIN_POSITION_TOLERANCE,
        samples_over_tolerance=int(np.sum(errors>SKIN_POSITION_TOLERANCE)),
        position_samples_passed=bool(np.all(errors<=SKIN_POSITION_TOLERANCE))), errors, witnesses


def bound_scene(producer, bindings, scene_id):
    paths = [Path(p) for p in bindings if Path(p).name == 'manifest.json']
    if len(paths) != 1: raise ValueError('One exact source manifest required')
    manifest = paths[0]; rows = [s for s in read(manifest)['scenes'] if s['id'] == scene_id]
    if len(rows) != 1: raise ValueError('One bound scene identity required')
    path = (manifest.parent/rows[0]['variants']['palm']).resolve()
    if str(path) not in bindings: raise ValueError('Original producer did not bind scene record')
    return read(path)['scene']


def run(pairs_path, output):
    pairs_path, output = Path(pairs_path).resolve(), Path(output).resolve()
    value = read(pairs_path)
    if value.get('schema') != 'strep-weight-roundtrip-pairs-v1' or not value['pairs'] or output.exists():
        raise ValueError('Explicit nonempty pairs and fresh output required')
    methods = {n: sha256(ROOT/'scripts'/n) for n in METHODS}; bindings = {str(pairs_path): sha256(pairs_path)}
    with worker_lock(), threadpool_limits(limits=1):
        output.mkdir(); implementation = output/'implementation'; implementation.mkdir()
        for n in methods: shutil.copyfile(ROOT/'scripts'/n, implementation/n)
        rows = []; arrays = {}; cache = {}; seen = set()
        save(output/'pipeline.json', dict(status='processing'))
        try:
            for pair in value['pairs']:
                identity = (pair['derivative_producer'], pair['derivative_id'])
                if identity in seen: raise ValueError('Distinct complete derivative scene pairs required')
                seen.add(identity)
                for key in ('original_producer', 'derivative_producer'):
                    path = pair[key]
                    if path not in cache: cache[path] = load_producer(path)
                    bindings.update(cache[path][3])
                old_result, old_request, _, old_bindings = cache[pair['original_producer']]
                new_result, new_request, new_observed, new_bindings = cache[pair['derivative_producer']]
                old = next(s for s in old_request['scenes'] if s['id']==pair['original_id'])
                new = next(s for s in new_request['scenes'] if s['id']==pair['derivative_id'])
                actual = next(s for s in new_observed['scenes'] if s['id']==new['id'])
                if (old['sample_times_s'] != new['sample_times_s'] or old['sample_clock'] != new['sample_clock']
                        or old['source_frame_count'] != new['source_frame_count'] or set(old['actors']) != set(new['actors'])
                        or set(pair['actor_receipts']) != set(old['actors'])):
                    raise ValueError('Unchanged complete original clock and actor population required')
                original_scene = bound_scene(old_result, old_bindings, old['id'])
                derived_scene = bound_scene(new_result, new_bindings, new['id'])
                comparison = copy.deepcopy(derived_scene); comparison['id'] = original_scene['id']
                for name in comparison['actors']:
                    comparison['actors'][name]['preview_glb'] = original_scene['actors'][name]['preview_glb']
                if comparison != original_scene: raise ValueError('Original motion, placements, contacts or object scene changed')
                scene = ImportedGeometryScene(derived_scene, new, actual); actor_rows = []
                index = len(rows); arrays[f'scene_{index}_times_s'] = scene.times
                for name in old['actors']:
                    receipt_path = Path(pair['actor_receipts'][name]); receipt = read(receipt_path)
                    bindings[str(receipt_path)] = sha256(receipt_path)
                    original_path, derived_path = Path(old['actors'][name]['path']), Path(new['actors'][name]['path'])
                    if (receipt['schema'] != 'strep-godot-weight-derivative-v1' or Path(receipt['source']) != original_path
                            or Path(receipt['output']) != derived_path or receipt['source_sha256'] != sha256(original_path)
                            or receipt['output_sha256'] != sha256(derived_path) or receipt['method_sha256'] != methods['godot_weight_derivative.py']):
                        raise ValueError('Exact original/derivative source receipt required')
                    rig = RigAsset.load(original_path); sampler = AnimationSampler(rig.document, rig.binary, 0, max_duration_s=None)
                    row, errors, witnesses = measure_original(rig, sampler, scene, name); actor_rows.append(row)
                    arrays[f'scene_{index}_actor_{len(actor_rows)-1}_errors_m'] = errors
                    arrays[f'scene_{index}_actor_{len(actor_rows)-1}_witnesses'] = witnesses
                rows.append(dict(original_id=old['id'], derivative_id=new['id'], actors=actor_rows))
                save(output/'pipeline.json', dict(status='processing', completed_scenes=len(rows)))
            if any(sha256(p)!=h for p,h in bindings.items()): raise ValueError('Fidelity input changed')
            if any(sha256(ROOT/'scripts'/n)!=h or sha256(implementation/n)!=h for n,h in methods.items()):
                raise ValueError('Fidelity method changed')
            np.savez_compressed(output/'observations.npz', **arrays)
            result = dict(status='complete', at=now(), rows=rows, inputs_sha256=bindings, implementation_sha256=methods,
                observations_sha256=sha256(output/'observations.npz'),
                original_skin_samples_passed=all(a['position_samples_passed'] for r in rows for a in r['actors']),
                collision_verified=False, quality_approved=False, release_approved=False)
            save(output/'result.json', result); save(output/'pipeline.json', dict(status='complete')); return result
        except Exception as error:
            save(output/'pipeline.json', dict(status='failed', error=str(error), completed_scenes=rows)); raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('pairs'); parser.add_argument('output')
    args = parser.parse_args(); result = run(args.pairs, args.output)
    print(dict(scenes=len(result['rows']), original_skin_samples_passed=result['original_skin_samples_passed'], release_approved=False))
