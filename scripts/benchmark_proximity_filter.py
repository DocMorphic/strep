"""Small matched query benchmark; never replaces a complete collision audit."""
import argparse
from pathlib import Path
import shutil
import time
import numpy as np
from strep import ROOT, read, save, sha256, now


def run(geometry, output, filter_rays=False):
    import trimesh
    from scipy.spatial.transform import Rotation
    from rig_asset import RigAsset, array
    from rig_clip_import import AnimationSampler
    from convex_partner_surface import candidates
    from proximity_candidate_filter import ProximityMesh
    geometry, output = Path(geometry).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh proximity benchmark required')
    request = read(geometry/'request.json'); manifest = read(geometry/'manifest.json')
    if sha256(geometry/'manifest.json') != request['manifest_sha256']: raise ValueError('Geometry input manifest changed')
    files = {str(geometry/name): sha256(geometry/name) for name in ['request.json', 'manifest.json']}
    for path, digest in request['inputs'].items():
        if sha256(path) != digest: raise ValueError('Geometry input changed')
        files[path] = digest
    audit = read(Path(request['export_audit'])/'request.json')
    refined = read(Path(audit['refinement'])/'request.json'); study = Path(refined['study'])
    original = read(study/'request.json'); prepared_path = Path(original['prepared_request']); prepared = read(prepared_path)
    if files.get(str(prepared_path)) != sha256(prepared_path): raise ValueError('Original clock and placements unbound')
    actors = []
    for name, entry in prepared['actors'].items():
        cases = [c for c in manifest['cases'] if c['id'] == 'candidate-'+name]
        if len(cases) != 1: raise ValueError('Distinct candidate actor required')
        case = cases[0]; path = (geometry/case['path']).resolve()
        if path.parent != geometry or sha256(path) != case['sha256']: raise ValueError('Candidate export changed')
        files[str(path)] = case['sha256']; rig = RigAsset.load(path)
        primitive = rig.primitives[0]; mesh = rig.document['meshes'][rig.document['nodes'][primitive['node']]['mesh']]['primitives'][primitive['primitive']]
        actors.append(dict(name=name, rig=rig, sampler=AnimationSampler(rig.document, rig.binary, 0),
            faces=array(rig.document, rig.binary, mesh['indices']).reshape(-1, 3),
            rotation=Rotation.from_quat(entry['placement']['rotation_xyzw']).as_matrix(), shift=np.asarray(entry['placement']['translation_m'])))
    output.mkdir(); (output/'implementation').mkdir(); methods = {}
    for name in ['benchmark_proximity_filter.py', 'proximity_candidate_filter.py', 'convex_partner_surface.py', 'rig_asset.py', 'rig_clip_import.py', 'gltf_tools.py', 'strep.py']:
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name); methods[name] = sha256(output/'implementation'/name)
    save(output/'request.json', dict(at=now(), geometry=str(geometry), inputs=files, implementation=methods, samples=[12, 55],
        source_witness_points=8, evenly_spaced_broadphase_points=24, query_chunk=16, filter_rays=filter_rays, trimesh_version=trimesh.__version__,
        scope='Fixed small diagnostic subset at two retained development times; includes deep witnesses and spaced hull candidates in both directions. No exhaustive correctness or performance claim; production queries unchanged.', quality_approved=False))
    rows = []
    for sample_index in [12, 55]:
        stamp = prepared['sample_times_seconds'][sample_index]
        witness_path = study/'source'/f'sample-{sample_index:03d}.json'
        if files.get(str(witness_path)) != sha256(witness_path): raise ValueError('Selected source witnesses unbound')
        witnesses = read(witness_path)
        vertices = [a['rig'].vertices(a['sampler'].sample(stamp))@a['rotation'].T+a['shift'] for a in actors]
        for s, t in [(0, 1), (1, 0)]:
            eligible, broad = candidates(vertices[s], vertices[t]); chosen = []
            eligible_set = set(eligible.tolist())
            chosen.extend(r['vertex'] for r in witnesses['directions'][s]['records'][:8] if r['vertex'] in eligible_set)
            if len(eligible): chosen.extend(eligible[np.linspace(0, len(eligible)-1, min(24, len(eligible))).astype(int)].tolist())
            ids = np.unique(chosen).astype(int); points = vertices[s][ids]
            mesh = trimesh.Trimesh(vertices[t], actors[t]['faces'], process=False)
            if not mesh.is_watertight or not mesh.is_winding_consistent: raise ValueError('Closed wound target required')
            began = time.perf_counter(); proxy = ProximityMesh(mesh, filter_rays=filter_rays); build_seconds = time.perf_counter()-began
            original_values = []; filtered_values = []; original_seconds = 0.; filtered_seconds = 0.
            for chunk, start in enumerate(range(0, len(ids), 16)):
                block = points[start:start+16]
                # Alternate order to expose rather than hide cache effects.
                order = [(mesh, 'original'), (proxy, 'filtered')]
                if chunk % 2: order.reverse()
                values = {}
                for target, label in order:
                    began = time.perf_counter(); values[label] = trimesh.proximity.signed_distance(target, block); elapsed = time.perf_counter()-began
                    if label == 'original': original_seconds += elapsed
                    else: filtered_seconds += elapsed
                original_values.extend(values['original'].tolist()); filtered_values.extend(values['filtered'].tolist())
            a, b = np.asarray(original_values), np.asarray(filtered_values)
            row = dict(sample=sample_index, time_s=stamp, source=actors[s]['name'], target=actors[t]['name'], vertex_ids=ids.tolist(),
                broadphase=broad, original_signed_m=original_values, filtered_signed_m=filtered_values,
                maximum_absolute_difference_m=float(np.abs(a-b).max(initial=0)), sign_disagreements=int(((a > 0) != (b > 0)).sum()),
                screen_disagreements=int(((a > .005) != (b > .005)).sum()), original_seconds=original_seconds,
                filtered_seconds=filtered_seconds, filter_build_seconds=build_seconds,
                original_face_candidates=proxy.triangles_tree.raw_candidates, filtered_face_candidates=proxy.triangles_tree.retained_candidates,
                ray_filter=dict(proxy.ray.statistics) if filter_rays else None)
            rows.append(row); save(output/'comparisons.json', rows)
            print({k:row[k] for k in ['sample', 'source', 'maximum_absolute_difference_m', 'original_seconds', 'filtered_seconds', 'original_face_candidates', 'filtered_face_candidates']}, flush=True)
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Benchmark input changed')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Benchmark method changed')
    save(output/'result.json', dict(at=now(), status='complete', request_sha256=sha256(output/'request.json'),
        comparisons_sha256=sha256(output/'comparisons.json'), sampled_points=sum(len(r['vertex_ids']) for r in rows),
        maximum_absolute_difference_m=max(r['maximum_absolute_difference_m'] for r in rows),
        sign_disagreements=sum(r['sign_disagreements'] for r in rows), screen_disagreements=sum(r['screen_disagreements'] for r in rows), quality_approved=False))


if __name__ == '__main__':
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('geometry', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--filter-rays', action='store_true')
    args = parser.parse_args()
    with threadpool_limits(limits=1): run(args.geometry, args.output, args.filter_rays)
